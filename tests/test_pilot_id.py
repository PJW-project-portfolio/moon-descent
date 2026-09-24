import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from lunar_lander.app import LunarLanderApp
from lunar_lander.pilot_id import apply_pilot_id_key, is_valid_pilot_id


def type_keys(keys: str, initials: str = "", phone: str = "") -> tuple[str, str]:
    for char in keys:
        initials, phone = apply_pilot_id_key(initials, phone, char)
    return initials, phone


class ApplyPilotIdKeyTests(unittest.TestCase):
    def test_letters_are_uppercased_into_initials(self) -> None:
        self.assertEqual(type_keys("hGd"), ("HGD", ""))

    def test_letters_and_digits_fill_separate_fields(self) -> None:
        self.assertEqual(type_keys("h0g4d12"), ("HGD", "0412"))

    def test_other_characters_are_ignored(self) -> None:
        self.assertEqual(type_keys("-_ .한é"), ("", ""))
        self.assertEqual(apply_pilot_id_key("HG", "1", ""), ("HG", "1"))
        self.assertEqual(apply_pilot_id_key("HG", "1", "AB"), ("HG", "1"))

    def test_fields_stop_at_their_maximum_length(self) -> None:
        self.assertEqual(type_keys("abcdef123456"), ("ABCD", "1234"))

    def test_backspace_erases_phone_digits_before_initials(self) -> None:
        initials, phone = type_keys("hgd12")
        self.assertEqual(type_keys("\b", initials, phone), ("HGD", "1"))
        self.assertEqual(type_keys("\b\b", initials, phone), ("HGD", ""))
        self.assertEqual(type_keys("\b\b\b", initials, phone), ("HG", ""))
        self.assertEqual(type_keys("\b" * 9, initials, phone), ("", ""))


class ValidPilotIdTests(unittest.TestCase):
    def test_accepts_two_to_four_initials_and_four_digits(self) -> None:
        self.assertTrue(is_valid_pilot_id("HG", "0412"))
        self.assertTrue(is_valid_pilot_id("NGMS", "9999"))

    def test_rejects_wrong_lengths_or_characters(self) -> None:
        self.assertFalse(is_valid_pilot_id("H", "1234"))
        self.assertFalse(is_valid_pilot_id("HGDAB", "1234"))
        self.assertFalse(is_valid_pilot_id("HGD", "123"))
        self.assertFalse(is_valid_pilot_id("hgd", "1234"))
        self.assertFalse(is_valid_pilot_id("HG-", "1234"))
        self.assertFalse(is_valid_pilot_id("HGD", "12a4"))
        self.assertFalse(is_valid_pilot_id("HGD", "１２３４"))


class PilotIdKeyEventTests(unittest.TestCase):
    @staticmethod
    def char_for(key: int) -> str:
        event = pygame.event.Event(pygame.KEYDOWN, key=key, mod=0)
        return LunarLanderApp._pilot_id_char(event)

    def test_letter_and_top_row_digit_keys(self) -> None:
        self.assertEqual(self.char_for(pygame.K_q), "q")
        self.assertEqual(self.char_for(pygame.K_7), "7")

    def test_keypad_digits(self) -> None:
        self.assertEqual(self.char_for(pygame.K_KP0), "0")
        self.assertEqual(self.char_for(pygame.K_KP9), "9")

    def test_other_keys_produce_nothing(self) -> None:
        self.assertEqual(self.char_for(pygame.K_F1), "")
        self.assertEqual(self.char_for(pygame.K_LEFT), "")


if __name__ == "__main__":
    unittest.main()
