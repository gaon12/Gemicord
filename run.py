import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import google.generativeai as genai
import re
import asyncio

# .env 파일로부터 환경변수를 로드합니다.
load_dotenv()

# 환경변수에서 Google API 키와 Discord 봇 토큰을 읽어옵니다.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Google API를 사용하기 위해 API 키를 설정합니다.
genai.configure(api_key=GOOGLE_API_KEY)

# Discord 봇의 intents를 설정합니다.
# 여기서는 모든 intents를 활성화하지만, 실제 사용 시에는 필요한 intents만 활성화하는 것이 좋습니다.
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.guild_messages = True  # 서버 내 메시지 수신을 위해 추가

# Client 객체를 생성할 때 heartbeat_timeout을 설정합니다.
client = discord.Client(intents=intents, heartbeat_timeout=60)  # 기본값은 10초이며, 여기서는 60초로 설정

# 명령어 접두사가 '!'인 Bot 객체를 생성합니다. client를 전달합니다.
bot = commands.Bot(command_prefix='!', intents=intents, heartbeat_timeout=60)

@bot.event
async def on_ready():
    """
    봇이 Discord에 연결되었을 때 호출되는 이벤트 핸들러입니다.
    """
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

def parse_model_settings(content):
    """
    사용자 입력에서 모델 설정을 파싱하는 함수입니다.
    
    입력: 
    - content: 사용자 입력 문자열
    
    반환:
    - settings: 파싱된 모델 설정의 딕셔너리
    - invalid_settings: 유효하지 않은 설정의 리스트
    - prompt: 설정을 제외한 원본 텍스트
    """
    pattern = r'\((.*?)\)'  # 설정값을 찾기 위한 정규 표현식
    matches = re.search(pattern, content)
    settings = {}
    invalid_settings = []

    if matches:
        settings_str = matches.group(1)
        if settings_str:  # 설정 문자열이 있으면 파싱 진행
            key_values = settings_str.split(',')
            for key_value in key_values:
                try:
                    key, value = key_value.split('=')
                except ValueError:
                    continue  # '='를 포함하지 않는 문자열은 무시
                key = key.strip()
                value = value.strip()
                # 설정값 유효성 검사 및 할당
                try:
                    if key in ["temperature", "top_p"]:
                        settings[key] = float(value)
                    elif key in ["top_k", "max_output_tokens"]:
                        settings[key] = int(value)
                except ValueError:
                    invalid_settings.append(key)

    end_idx = matches.end() if matches else 0
    prompt = content[end_idx:].strip()
    return settings, invalid_settings, prompt

async def generate_content_async(prompt, settings):
    """
    비동기적으로 콘텐츠를 생성하는 함수입니다.
    """
    model = genai.GenerativeModel('gemini-1.5-pro-latest', generation_config=settings)
    return await asyncio.to_thread(model.generate_content, prompt)

@bot.command()
async def gemini(ctx, *, arg):
    """
    '!gemini' 명령어로 텍스트 생성을 요청하는 사용자 정의 명령어입니다.
    
    입력:
    - ctx: 명령어 컨텍스트
    - arg: 사용자가 입력한 모든 텍스트
    """
    settings, invalid_settings, prompt = parse_model_settings(arg)
    loading_text = 'Loading...'
    if invalid_settings:
        loading_text += f' Invalid model setting(s): {", ".join(invalid_settings)}'
    loading_message = await ctx.send(loading_text)

    try:
        response = await generate_content_async(prompt, settings)
        await loading_message.edit(content=f'{response.text}')
    except Exception as e:
        error_message = 'An error occurred while processing your request.'
        if 'API key not valid' in str(e):
            error_message = 'API 키가 올바르지 않습니다. 설정을 확인해주세요.'
        await loading_message.edit(content=error_message)

# 디스코드 봇을 실행합니다. 이는 토큰을 사용하여 Discord API에 로그인합니다.
bot.run(DISCORD_BOT_TOKEN)
