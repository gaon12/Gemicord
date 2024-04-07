# Gemicord
Meet Gemini on Discord!

Gemicord is a Discord Bot that acts as a bot on Discord, allowing users to enter values, and leverages the Gemini API to deliver the values in response.

# What to bring
To use Gemicord, you'll need the following materials
* Python
  - You need to have Python installed, the version we tested is `3.10.12`.
* Python package
  - `discord.py` - the Discord bot framework package, which you can install like this `pip install discord`
  - `python-dotenv` - used to retrieve values from the `.env` where the API key is stored. You can install it like this `pip install python-dotenv`
* API key / token values
  - Gemini API key: You'll need a Gemini API key, which you can get from [Google AI Studio](https://aistudio.google.com/app/apikey).
  - Discord Bot Token: To run the Discord bot, you need a bot token, which you can get from [Discord Developer Protal](https://discord.com/developers/docs/intro).

# Enter your API key in .env
1. Open `.env.sample` with an editor.
2. `.env.sample` should look like this.
```env
GOOGLE_API_KEY=
DISCORD_BOT_TOKEN=
```
Where `GOOGLE_API_KEY` is your Gemini API key, and `DISCORD_BOT_TOKEN` is your Discord Bot token value. Be sure to enclose both ends in double quotes. Example:
```env
GOOGLE_API_KEY="Gemini_API"
DISCORD_BOT_TOKEN="Discord_Bot_Token"
```
Or something like this.

3. Rename the `.env.sample` file to `.env`.
4. Run Gemicord with `python run.py`.

# License
Gemicord is distributed under the MIT licence.