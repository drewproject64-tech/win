import unittest
from bot import (BOT_ABOUT, BOT_DESCRIPTION, BUTTONS, Bot, convert,
                 count_text, percentage, setup_profile)


class FakeAPI:
    def __init__(self):
        self.calls = []

    def call(self, method, **kwargs):
        self.calls.append((method, kwargs))


class ToolTests(unittest.TestCase):
    def test_percentages(self):
        self.assertIn("= 30", percentage("percent 15 200"))
        self.assertIn("Final price: 170", percentage("discount 200 15"))
        self.assertEqual(percentage("change 100 120"), "Percentage change: 20%")
        self.assertEqual(percentage("change -100 -80"), "Percentage change: 20%")

    def test_invalid_inputs(self):
        for value in ("change 0 10", "percent nan 3", "percent inf 4", "discount 20 110", "hello"):
            with self.assertRaises(ValueError):
                percentage(value)
        for value in ("5 kg to m", "-1 k to c", "1 cat to dog", "-5 lb to kg"):
            with self.assertRaises(ValueError):
                convert(value)

    def test_conversion(self):
        self.assertEqual(convert("1 mi to m"), "1 mi = 1609.344 m")
        self.assertEqual(convert("32 f to c"), "32 f = 0 c")
        self.assertEqual(convert("0 k to c"), "0 k = -273.15 c")
        self.assertEqual(convert("1 kg to g"), "1 kg = 1000 g")

    def test_count(self):
        self.assertEqual(count_text("Hi there\n"), "Words: 2\nCharacters (including spaces): 9\nCharacters (excluding whitespace): 7")

    def test_profile(self):
        api = FakeAPI()
        setup_profile(api)
        self.assertLessEqual(len(BOT_ABOUT), 120)
        self.assertLessEqual(len(BOT_DESCRIPTION), 512)
        self.assertIn(("setMyShortDescription", {"short_description": BOT_ABOUT, "language_code": ""}), api.calls)
        self.assertIn(("setMyDescription", {"description": BOT_DESCRIPTION, "language_code": "en"}), api.calls)

    def test_menu_and_chat_isolation(self):
        api, updates = FakeAPI(), []
        bot = Bot(api)
        def send(chat, text):
            bot.handle({"message": {"chat": {"id": chat, "type": "private"}, "text": text}})
            return api.calls[-1][1]["text"]
        self.assertIn("Welcome", send(1, "/start"))
        send(1, BUTTONS[0])
        self.assertIn("= 30", send(1, "percent 15 200"))
        self.assertIn("first", send(2, "percent 15 200"))
        send(1, BUTTONS[2])
        self.assertIn("Words: 2", send(1, "hello world"))
        send(1, "/cancel")
        self.assertNotIn(1, bot.modes)
        self.assertEqual(len(api.calls[-1][1]["reply_markup"]["keyboard"]), 3)


if __name__ == "__main__":
    unittest.main()
