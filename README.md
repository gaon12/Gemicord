# Gemicord

Meet Gemini on Discord!

Gemicord is a Discord bot that lets users talk to Gemini directly from Discord. It supports text prompts, image prompts, reply-based context, and long responses that are automatically split into Discord-friendly messages.

## Features

- Ask Gemini with `!gemini`.
- Attach an image and ask Gemini to describe or analyze it.
- Reply to an existing Discord message and ask Gemini to summarize, explain, or transform it.
- Send long Gemini responses by automatically splitting them into multiple Discord messages.
- Configure the Gemini model with an environment variable.

## Requirements

- Python 3.10 or newer
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
- A Discord bot token from the [Discord Developer Portal](https://discord.com/developers/docs/intro)

## Installation

1. Clone this repository.

```bash
git clone https://github.com/gaon12/Gemicord.git
cd Gemicord
```

2. Create and activate a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, use this instead.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install the required packages.

```bash
pip install -r requirements.txt
```

4. Copy `.env.sample` to `.env`.

```bash
cp .env.sample .env
```

On Windows PowerShell, use this instead.

```powershell
Copy-Item .env.sample .env
```

5. Fill in `.env`.

```env
GOOGLE_API_KEY="your-gemini-api-key"
DISCORD_BOT_TOKEN="your-discord-bot-token"
GEMINI_MODEL="gemini-2.5-flash"
```

6. Run the bot.

```bash
python run.py
```

## Usage

Ask a normal text question.

```text
!gemini Explain what Gemini is in simple terms.
```

Attach an image and ask about it.

```text
!gemini What is happening in this image?
```

Reply to a Discord message and ask Gemini to use that message as context.

```text
!gemini Summarize this message.
```

If you attach an image without writing a prompt, Gemicord asks Gemini to describe the image by default.

If you reply to a message without writing a prompt, Gemicord asks Gemini to answer based on the replied message by default.

## Discord setup note

This bot reads message content, so the Message Content Intent must be enabled in the Discord Developer Portal for your bot application.

## License

Gemicord is distributed under the MIT license.
