import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from lunar_lander.app import LunarLanderApp
from lunar_lander.pilot_id import (
    CHOSEONG,
    KOREAN_UI_TEXT,
    apply_pilot_id_key,
    is_valid_pilot_id,
)
from lunar_lander.resources import resource_path


def type_keys(keys: str, initials: str = "", phone: str = "") -> tuple[str, str]:
    for char in keys:
        initials, phone = apply_pilot_id_key(initials, phone, char)
    return initials, phone


class ApplyPilotIdKeyTests(unittest.TestCase):
    def test_dubeolsik_keys_become_initial_consonants(self) -> None:
        mapped = "".join(
            type_keys(key)[0] for key in "qwertasdfgzxcv"
        )
        self.assertEqual(mapped, "ㅂㅈㄷㄱㅅㅁㄴㅇㄹㅎㅋㅌㅊㅍ")

    def test_shift_makes_tense_consonants_only_where_they_exist(self) -> None:
        mapped = "".join(type_keys(key)[0] for key in "QWERT")
        self.assertEqual(mapped, "ㅃㅉㄸㄲㅆ")
        self.assertEqual(type_keys("S")[0], "ㄴ")
        self.assertEqual(type_keys("G")[0], "ㅎ")

    def test_vowel_keys_and_symbols_are_ignored(self) -> None:
        self.assertEqual(type_keys("yuiophjklbnm-_ ."), ("", ""))
        self.assertEqual(type_keys("ㅏ가"), ("", ""))
        self.assertEqual(apply_pilot_id_key("ㄱ", "1", ""), ("ㄱ", "1"))
        self.assertEqual(apply_pilot_id_key("ㄱ", "1", "qq"), ("ㄱ", "1"))

    def test_typed_consonant_characters_are_accepted(self) -> None:
        self.assertEqual(type_keys("ㅂㅈㅇ")[0], "ㅂㅈㅇ")

    def test_consonants_and_digits_fill_separate_fields(self) -> None:
        self.assertEqual(type_keys("q1w2d34"), ("ㅂㅈㅇ", "1234"))

    def test_fields_stop_at_their_maximum_length(self) -> None:
        self.assertEqual(type_keys("qwertasd123456"), ("ㅂㅈㄷㄱ", "1234"))

    def test_backspace_erases_phone_digits_before_initials(self) -> None:
        initials, phone = type_keys("qwd12")
        self.assertEqual(type_keys("\b", initials, phone), ("ㅂㅈㅇ", "1"))
        self.assertEqual(type_keys("\b\b", initials, phone), ("ㅂㅈㅇ", ""))
        self.assertEqual(type_keys("\b\b\b", initials, phone), ("ㅂㅈ", ""))
        self.assertEqual(type_keys("\b" * 9, initials, phone), ("", ""))


class ValidPilotIdTests(unittest.TestCase):
    def test_accepts_two_to_four_initials_and_four_digits(self) -> None:
        self.assertTrue(is_valid_pilot_id("ㅂㅈ", "0412"))
        self.assertTrue(is_valid_pilot_id("ㄴㄱㅁㅅ", "9999"))

    def test_rejects_wrong_lengths_or_characters(self) -> None:
        self.assertFalse(is_valid_pilot_id("ㅂ", "1234"))
        self.assertFalse(is_valid_pilot_id("ㅂㅈㅇㄱㄴ", "1234"))
        self.assertFalse(is_valid_pilot_id("ㅂㅈㅇ", "123"))
        self.assertFalse(is_valid_pilot_id("PJW", "1234"))
        self.assertFalse(is_valid_pilot_id("ㅂㅈㅇ", "12a4"))
        self.assertFalse(is_valid_pilot_id("ㅂㅈㅇ", "１２３４"))


class PilotIdKeyEventTests(unittest.TestCase):
    @staticmethod
    def char_for(key: int, mod: int = 0) -> str:
        event = pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod)
        return LunarLanderApp._pilot_id_char(event)

    def test_letter_keys_follow_shift_state(self) -> None:
        self.assertEqual(self.char_for(pygame.K_q), "q")
        self.assertEqual(self.char_for(pygame.K_r, pygame.KMOD_LSHIFT), "R")
        self.assertEqual(self.char_for(pygame.K_r, pygame.KMOD_CAPS), "r")

    def test_top_row_and_keypad_digits(self) -> None:
        self.assertEqual(self.char_for(pygame.K_7), "7")
        self.assertEqual(self.char_for(pygame.K_KP0), "0")
        self.assertEqual(self.char_for(pygame.K_KP9), "9")

    def test_other_keys_produce_nothing(self) -> None:
        self.assertEqual(self.char_for(pygame.K_F1), "")
        self.assertEqual(self.char_for(pygame.K_LEFT), "")


class KoreanFontCoverageTests(unittest.TestCase):
    def test_subset_font_draws_every_korean_ui_character(self) -> None:
        pygame.font.init()
        font = pygame.font.Font(
            resource_path("assets/fonts/NotoSansMonoCJKkr-Subset.otf"), 18
        )

        def pixels(char: str) -> bytes:
            surface = font.render(char, False, (255, 255, 255), (0, 0, 0))
            return pygame.image.tobytes(surface, "RGB")

        # 서브셋에 없는 글자는 모두 같은 .notdef 상자로 그려진다.
        missing_glyph = pixels("漢")
        characters = set("".join(KOREAN_UI_TEXT)) | set(CHOSEONG)
        missing = sorted(
            char
            for char in characters
            if not char.isspace() and pixels(char) == missing_glyph
        )

        self.assertEqual(
            missing,
            [],
            "한글 문구를 바꿨다면 scripts/make_korean_font.py를 다시 실행하세요",
        )
        self.assertEqual(pixels("가"), missing_glyph)


if __name__ == "__main__":
    unittest.main()
