"""Win365: a dependency-free Telegram utility bot. Python 3.11+."""
import json
import logging
import math
import os
import re
import signal
import time
from collections import OrderedDict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BOT_NAME = "Win365"
BOT_ABOUT = "Win365 utility tools: percentage calculations, unit conversions, and word and character counts."
BOT_DESCRIPTION = (
    "Win365 provides three free tools inside Telegram.\n\n"
    "Percentage Calculator: calculate percentages, discounts and percentage changes.\n"
    "Unit Converter: convert weight, length and temperature.\n"
    "Text Counter: count words and characters in text you send.\n\n"
    "Tap Start, choose a tool and follow its input example."
)
BUTTONS = ("Percentage Calculator", "Unit Converter", "Text Counter")
KEYBOARD = {"keyboard": [[b] for b in BUTTONS], "resize_keyboard": True,
            "is_persistent": True}
PROMPTS = {
    BUTTONS[0]: "Send one of these formats:\npercent 15 200 — 15% of 200\ndiscount 200 15 — 15% off 200\nchange 100 120 — percentage change from 100 to 120",
    BUTTONS[1]: "Send a value and units, e.g. 140 lb to kg, 5 km to mi, or 108 f to c.\nSupported: kg, g, lb, oz; m, cm, km, in, ft, mi; c, f, k.",
    BUTTONS[2]: "Send your text. I will count words, characters (including spaces), and characters excluding whitespace.",
}


def number(raw):
    value = float(raw)
    if not math.isfinite(value) or abs(value) > 1e100:
        raise ValueError("Use a finite number with magnitude no greater than 1e100.")
    return value


def fmt(value):
    return format(value, ".10g")


def percentage(text):
    parts = text.lower().split()
    if len(parts) != 3 or parts[0] not in {"percent", "discount", "change"}:
        raise ValueError(PROMPTS[BUTTONS[0]])
    op, a, b = parts[0], number(parts[1]), number(parts[2])
    if op == "percent":
        return f"{fmt(a)}% of {fmt(b)} = {fmt(a * b / 100)}"
    if op == "discount":
        if a < 0 or not 0 <= b <= 100:
            raise ValueError("Use a nonnegative price and a discount between 0 and 100.")
        return f"Discount: {fmt(a * b / 100)}\nFinal price: {fmt(a * (1 - b / 100))}"
    if a == 0:
        raise ValueError("Percentage change is undefined when the original value is zero.")
    return f"Percentage change: {fmt((b - a) / abs(a) * 100)}%"


UNITS = {
    "kg": ("weight", 1), "g": ("weight", .001),
    "lb": ("weight", .45359237), "oz": ("weight", .028349523125),
    "m": ("length", 1), "cm": ("length", .01), "km": ("length", 1000),
    "in": ("length", .0254), "ft": ("length", .3048), "mi": ("length", 1609.344),
}


def convert(text):
    match = re.fullmatch(r"\s*(\S+)\s+([a-z]+)\s+to\s+([a-z]+)\s*", text.lower())
    if not match:
        raise ValueError(PROMPTS[BUTTONS[1]])
    raw, source, target = match.groups()
    value = number(raw)
    if source in {"c", "f", "k"} and target in {"c", "f", "k"}:
        celsius = (value - 32) * 5 / 9 if source == "f" else value - 273.15 if source == "k" else value
        if celsius < -273.15 - 1e-10:
            raise ValueError("Temperature cannot be below absolute zero.")
        result = celsius * 9 / 5 + 32 if target == "f" else celsius + 273.15 if target == "k" else celsius
    elif source in UNITS and target in UNITS and UNITS[source][0] == UNITS[target][0]:
        if value < 0:
            raise ValueError("Use a nonnegative weight or length.")
        result = value * UNITS[source][1] / UNITS[target][1]
    else:
        raise ValueError("Choose supported units of the same type.\n" + PROMPTS[BUTTONS[1]])
    return f"{fmt(value)} {source} = {fmt(result)} {target}"


def count_text(text):
    return (f"Words: {len(text.split())}\nCharacters (including spaces): {len(text)}\n"
            f"Characters (excluding whitespace): {sum(not c.isspace() for c in text)}")


class APIError(Exception):
    def __init__(self, code, retry_after=3):
        self.code, self.retry_after = code, retry_after
        super().__init__(f"Telegram API error {code}")


class Telegram:
    def __init__(self, token):
        self.base = f"https://api.telegram.org/bot{token}/"

    def call(self, method, **payload):
        request = Request(self.base + method, json.dumps(payload).encode(),
                          {"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=40) as response:
                data = json.load(response)
        except HTTPError as error:
            try:
                data = json.loads(error.read())
            except (ValueError, OSError):
                raise APIError(error.code) from None
        if not data.get("ok"):
            raise APIError(data.get("error_code", 500), data.get("parameters", {}).get("retry_after", 3))
        return data["result"]


def setup_profile(api):
    for language in ("", "en"):
        api.call("setMyName", name=BOT_NAME, language_code=language)
        api.call("setMyShortDescription", short_description=BOT_ABOUT, language_code=language)
        api.call("setMyDescription", description=BOT_DESCRIPTION, language_code=language)
    api.call("setMyCommands", commands=[
        {"command": "start", "description": "Open the three tools"},
        {"command": "help", "description": "Learn how to use Win365"},
        {"command": "cancel", "description": "Return to the menu"},
        {"command": "privacy", "description": "How your input is handled"},
    ])


class Bot:
    def __init__(self, api):
        self.api, self.modes = api, OrderedDict()

    def handle(self, update):
        message = update.get("message", {})
        if message.get("chat", {}).get("type") != "private":
            return
        chat = message["chat"]["id"]
        text = message.get("text", "")
        command = text.split()[0].split("@")[0].lower() if text.startswith("/") else ""
        if command in {"/start", "/cancel"}:
            self.modes.pop(chat, None)
            reply = ("Welcome to Win365. Three free tools inside Telegram:\n"
                     "Percentage Calculator, Unit Converter and Text Counter.\n"
                     "Choose a tool below to see a worked example, then send your own input.")
        elif command == "/help":
            reply = "Choose a tool below, then follow its instructions. You can switch tools at any time. Use /cancel to return to the menu."
        elif command == "/privacy":
            reply = "Win365 processes your text to return results. It does not save submitted text or calculations to a database or log. Your selected tool is kept temporarily in memory and cleared on restart. Telegram processes messages under its own privacy policy."
        elif command:
            reply = "Unknown command. Use /start to open the tools or /help for instructions."
        elif text in BUTTONS:
            self.modes[chat] = text
            self.modes.move_to_end(chat)
            if len(self.modes) > 10000:
                self.modes.popitem(last=False)
            examples = {
                BUTTONS[0]: "Example: percent 15 200\n" + percentage("percent 15 200"),
                BUTTONS[1]: "Example: 140 lb to kg\n" + convert("140 lb to kg"),
                BUTTONS[2]: "Example text: Hello world\n" + count_text("Hello world"),
            }
            reply = examples[text] + "\n\n" + PROMPTS[text]
        elif not text:
            reply = "Please send text or choose one of the tools below."
        elif chat not in self.modes:
            reply = "Choose a tool below first."
        else:
            try:
                reply = {BUTTONS[0]: percentage, BUTTONS[1]: convert, BUTTONS[2]: count_text}[self.modes[chat]](text)
            except (ValueError, OverflowError):
                reply = "Please check your input.\n" + PROMPTS[self.modes[chat]]
        self.api.call("sendMessage", chat_id=chat, text=reply, reply_markup=KEYBOARD)


def main():
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("Set BOT_TOKEN in your hosting environment before starting Win365.")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    api = Telegram(token)
    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    # Startup retries recover from temporary Telegram/network failures without exposing the token.
    while running:
        try:
            setup_profile(api)
            api.call("deleteWebhook", drop_pending_updates=False)
            break
        except APIError as error:
            if error.code in {401, 404, 409}:
                raise SystemExit(f"Startup failed (API {error.code}); check token and other bot instances.") from None
            logging.warning("Profile setup delayed (API %s).", error.code)
            time.sleep(min(error.retry_after, 30))
        except (URLError, TimeoutError, OSError, ValueError):
            logging.warning("Profile setup delayed by a network error.")
            time.sleep(3)
    bot, offset = Bot(api), 0
    logging.info("Win365 is running.")
    while running:
        try:
            updates = api.call("getUpdates", offset=offset, timeout=25, allowed_updates=["message"])
            for update in updates:
                if not running:
                    break
                try:
                    bot.handle(update)
                except APIError as error:
                    if error.code not in {400, 403}:
                        raise
                    logging.info("Skipped unavailable chat (API %s).", error.code)
                offset = update["update_id"] + 1
        except APIError as error:
            if error.code in {401, 404, 409}:
                raise SystemExit(f"Polling stopped (API {error.code}); check token and run only one instance.") from None
            logging.warning("Polling delayed (API %s).", error.code)
            time.sleep(min(error.retry_after, 30))
        except (URLError, TimeoutError, OSError, ValueError):
            logging.warning("Temporary network error; retrying.")
            time.sleep(3)


if __name__ == "__main__":
    main()
