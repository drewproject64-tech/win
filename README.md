# Win365

A Telegram utility bot with three persistent buttons beneath the message box:

- **Percentage Calculator:** `percent 15 200`, `discount 200 15`, `change 100 120`.
- **Unit Converter:** `140 lb to kg`, `5 km to mi`, `108 f to c`.
- **Text Counter:** counts words, Unicode code points including spaces, and characters excluding whitespace. Emoji sequences may contain multiple code points.

## Run

Requires Python 3.11 or newer; no third-party packages are needed.

1. Create your bot with Telegram's @BotFather.
2. Set `BOT_TOKEN` securely in the process/hosting environment. Never commit the token.
3. Run `python bot.py`.

On startup, `bot.py` sets the name **Win365**, About (`BOT_ABOUT`), Description (`BOT_DESCRIPTION`) and command menu via Telegram's API. Default and English profile text are configured. These constants can be edited in the code. Any other language overrides previously configured in BotFather should be kept consistent manually. Add a suitable profile picture through BotFather before advertising.

## Hosting

Run as an always-on background worker with start command `python bot.py` and environment variable `BOT_TOKEN`. Run exactly one instance per token. The bot uses long polling and removes any existing webhook on startup without dropping pending updates. It does not expose an HTTP server; do not use a hosting mode that requires a listening port.

## Commands and privacy

`/start` opens the tools; `/help` explains usage; `/cancel` resets the selected tool; `/privacy` explains input handling. Tools operate in private chats. Submitted text and calculations are not stored or logged. The last selected tool for up to 10,000 chats is kept in memory, and resets on restart or eviction. Telegram still processes messages according to its policies. No broadcast or database is included.

## Verification

Run `python -m unittest -v`. Tests cover calculations, invalid inputs, conversions, profile setup, menu routing and text counts. Live Telegram testing requires a valid BOT_TOKEN.

## Advertising

Describe the actual utility functions in the ad and use consistent branding and language. Keep the bot functional and its profile complete. Telegram decides whether an ad is approved; this implementation does not guarantee approval.
