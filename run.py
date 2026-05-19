import asyncio
import logging
import os
from typing import Any

import discord
from discord.ext import commands
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Discord 일반 메시지의 기본 최대 길이는 2000자입니다.
# 안전하게 전송하기 위해 약간 여유를 둔 길이로 나눕니다.
DISCORD_MESSAGE_LIMIT = 1900

# 사용자가 질문을 입력하지 않았을 때 사용할 기본 프롬프트입니다.
DEFAULT_IMAGE_PROMPT = "첨부된 이미지를 자세히 설명해 주세요."
DEFAULT_REPLY_PROMPT = "답장한 메시지를 바탕으로 사용자의 요청에 답변해 주세요."

# Discord 첨부 파일 중 Gemini에 직접 전달할 이미지 MIME 타입입니다.
SUPPORTED_IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/heic",
    "image/heif",
}

# 실행 로그를 보기 쉽게 설정합니다.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gemicord")

# .env 파일에 있는 환경변수를 읽습니다.
load_dotenv()

# 필수 환경변수를 읽습니다.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# 모델명은 환경변수로 바꿀 수 있게 하되, 값이 없으면 기본 모델을 사용합니다.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def require_environment_variable(name: str, value: str | None) -> str:
    """
    필수 환경변수가 비어 있는지 확인합니다.

    Args:
        name: 환경변수 이름입니다.
        value: 환경변수 값입니다.

    Returns:
        검증된 환경변수 값입니다.

    Raises:
        RuntimeError: 환경변수가 비어 있으면 발생합니다.
    """
    if value is None or value.strip() == "":
        raise RuntimeError(f"필수 환경변수 {name} 값이 비어 있습니다. .env 파일을 확인해 주세요.")

    return value


GOOGLE_API_KEY = require_environment_variable("GOOGLE_API_KEY", GOOGLE_API_KEY)
DISCORD_BOT_TOKEN = require_environment_variable("DISCORD_BOT_TOKEN", DISCORD_BOT_TOKEN)

# Gemini API 클라이언트를 생성합니다.
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)

# Discord 봇이 메시지 내용과 서버 메시지를 읽을 수 있도록 intent를 설정합니다.
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

# 명령어 접두사가 '!'인 Discord 봇을 생성합니다.
bot = commands.Bot(command_prefix="!", intents=intents, heartbeat_timeout=60)


@bot.event
async def on_ready() -> None:
    """
    봇이 Discord에 정상적으로 연결되었을 때 호출됩니다.
    """
    if bot.user is None:
        logger.info("Discord에 로그인했지만 봇 사용자 정보를 확인하지 못했습니다.")
        return

    logger.info("Logged in as %s (%s)", bot.user.name, bot.user.id)


def split_text(text: str, limit: int = DISCORD_MESSAGE_LIMIT) -> list[str]:
    """
    긴 텍스트를 Discord 메시지 제한에 맞게 여러 조각으로 나눕니다.

    Args:
        text: 전송할 전체 텍스트입니다.
        limit: 한 메시지에 담을 최대 문자 수입니다.

    Returns:
        Discord에 순서대로 보낼 텍스트 조각 목록입니다.
    """
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining_text = text

    while len(remaining_text) > limit:
        # 문단 단위로 자연스럽게 나누기 위해 제한 길이 안에서 마지막 줄바꿈을 찾습니다.
        split_index = remaining_text.rfind("\n", 0, limit)

        # 줄바꿈이 너무 앞에 있으면 공백 기준으로 다시 나눕니다.
        if split_index < limit // 2:
            split_index = remaining_text.rfind(" ", 0, limit)

        # 적당한 구분점을 찾지 못하면 제한 길이에서 강제로 자릅니다.
        if split_index <= 0:
            split_index = limit

        chunks.append(remaining_text[:split_index].strip())
        remaining_text = remaining_text[split_index:].strip()

    if remaining_text:
        chunks.append(remaining_text)

    return chunks


async def send_long_response(message: discord.Message, text: str) -> None:
    """
    Gemini 응답을 Discord 메시지 제한에 맞게 전송합니다.

    첫 번째 조각은 기존 로딩 메시지를 수정하고, 이후 조각은 새 메시지로 보냅니다.

    Args:
        message: 수정할 로딩 메시지입니다.
        text: 전송할 전체 응답 텍스트입니다.
    """
    if text.strip() == "":
        await message.edit(content="응답이 비어 있습니다.")
        return

    chunks = split_text(text)
    await message.edit(content=chunks[0])

    for chunk in chunks[1:]:
        await message.channel.send(chunk)


async def extract_reply_context(ctx: commands.Context[Any]) -> str | None:
    """
    사용자가 다른 메시지에 답장하면서 명령어를 실행했는지 확인하고 원본 메시지를 가져옵니다.

    Args:
        ctx: Discord 명령어 컨텍스트입니다.

    Returns:
        답장 대상 메시지 내용입니다. 답장 대상이 없거나 내용을 읽을 수 없으면 None입니다.
    """
    reference = ctx.message.reference
    if reference is None:
        return None

    resolved_message = reference.resolved

    # Discord가 이미 답장 대상 메시지를 포함해서 전달한 경우입니다.
    if isinstance(resolved_message, discord.Message):
        replied_message = resolved_message
    else:
        # resolved가 비어 있으면 message_id로 직접 조회합니다.
        if reference.message_id is None:
            return None

        try:
            replied_message = await ctx.channel.fetch_message(reference.message_id)
        except discord.DiscordException:
            logger.exception("답장 대상 메시지를 가져오지 못했습니다.")
            return None

    author_name = replied_message.author.display_name
    content = replied_message.content.strip()

    # 답장 대상 메시지가 텍스트 없이 첨부 파일만 가진 경우도 표시합니다.
    attachment_lines = [attachment.url for attachment in replied_message.attachments]
    attachment_text = "\n".join(attachment_lines)

    if content == "" and attachment_text == "":
        return None

    return f"다음은 사용자가 답장한 Discord 메시지입니다.\n작성자: {author_name}\n내용:\n{content}\n{attachment_text}".strip()


async def extract_image_parts(ctx: commands.Context[Any]) -> list[types.Part]:
    """
    사용자가 명령어와 함께 첨부한 이미지 파일을 Gemini 입력 형식으로 변환합니다.

    Args:
        ctx: Discord 명령어 컨텍스트입니다.

    Returns:
        Gemini에 전달할 이미지 Part 목록입니다.
    """
    image_parts: list[types.Part] = []

    for attachment in ctx.message.attachments:
        content_type = attachment.content_type

        # Discord가 MIME 타입을 제공하지 않거나 지원하지 않는 이미지이면 건너뜁니다.
        if content_type not in SUPPORTED_IMAGE_MIME_TYPES:
            continue

        try:
            image_bytes = await attachment.read()
        except discord.DiscordException:
            logger.exception("첨부 이미지를 읽지 못했습니다: %s", attachment.filename)
            continue

        image_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=content_type))

    return image_parts


async def generate_content(prompt: str, image_parts: list[types.Part]) -> str:
    """
    Gemini API를 호출해 텍스트 또는 이미지 기반 응답을 생성합니다.

    Args:
        prompt: 사용자 질문과 필요한 문맥을 합친 텍스트입니다.
        image_parts: Gemini에 함께 전달할 이미지 목록입니다.

    Returns:
        Gemini가 생성한 응답 텍스트입니다.
    """
    contents: list[Any] = [prompt]
    contents.extend(image_parts)

    response = await gemini_client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
    )

    if response.text is None or response.text.strip() == "":
        return "응답이 비어 있습니다."

    return response.text


@bot.command(name="gemini")
async def gemini(ctx: commands.Context[Any], *, arg: str = "") -> None:
    """
    Gemini에게 질문합니다.

    지원하는 사용 방식:
    - !gemini 질문 내용
    - 이미지 첨부 후 !gemini 이 이미지를 설명해줘
    - 다른 메시지에 답장하면서 !gemini 요약해줘
    """
    user_prompt = arg.strip()
    reply_context = await extract_reply_context(ctx)
    image_parts = await extract_image_parts(ctx)

    # 텍스트 없이 이미지만 첨부한 경우에도 자연스럽게 동작하게 합니다.
    if user_prompt == "" and image_parts:
        user_prompt = DEFAULT_IMAGE_PROMPT

    # 텍스트 없이 답장만 한 경우에도 자연스럽게 동작하게 합니다.
    if user_prompt == "" and reply_context is not None:
        user_prompt = DEFAULT_REPLY_PROMPT

    if user_prompt == "" and reply_context is None and not image_parts:
        await ctx.send("질문을 입력하거나 이미지를 첨부해 주세요. 예: `!gemini 이 이미지를 설명해줘`")
        return

    prompt_parts: list[str] = []

    if reply_context is not None:
        prompt_parts.append(reply_context)

    prompt_parts.append(f"사용자 요청:\n{user_prompt}")
    final_prompt = "\n\n".join(prompt_parts)

    loading_message = await ctx.send("응답을 생성하는 중입니다...")

    try:
        response_text = await generate_content(final_prompt, image_parts)
        await send_long_response(loading_message, response_text)
    except Exception:
        logger.exception("Gemini 응답 생성 중 오류가 발생했습니다.")
        await loading_message.edit(content="요청을 처리하는 중 오류가 발생했습니다. API 키, 모델명, 첨부 파일 형식을 확인해 주세요.")


bot.run(DISCORD_BOT_TOKEN)
