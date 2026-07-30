import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from lunar_lander.leaderboard import Leaderboard, apply_name_key


class ApplyNameKeyTests(unittest.TestCase):
    def test_accepts_letters_digits_hyphen_and_uppercases_letters(self) -> None:
        name = ""
        for char in "pJw-42":
            name = apply_name_key(name, char)

        self.assertEqual(name, "PJW-42")

    def test_rejects_unsupported_and_multi_character_input(self) -> None:
        self.assertEqual(apply_name_key("ACE", "_"), "ACE")
        self.assertEqual(apply_name_key("ACE", " "), "ACE")
        self.assertEqual(apply_name_key("ACE", "한"), "ACE")
        self.assertEqual(apply_name_key("ACE", "AB"), "ACE")

    def test_limits_callsigns_to_ten_characters(self) -> None:
        self.assertEqual(apply_name_key("ABCDEFGHIJ", "K"), "ABCDEFGHIJ")

    def test_backspace_removes_the_last_character(self) -> None:
        self.assertEqual(apply_name_key("ACE", "\b"), "AC")
        self.assertEqual(apply_name_key("", "\b"), "")


class LeaderboardTests(unittest.TestCase):
    def test_add_sorts_descending_and_trims_to_ten(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            leaderboard = Leaderboard(
                Path(temporary_directory) / "leaderboard.json"
            )
            for score in range(12):
                leaderboard.add_entry(
                    score,
                    f"BODY-{score}",
                    "2026-07-30",
                )

            self.assertEqual(len(leaderboard.entries), 10)
            self.assertEqual(
                [entry["score"] for entry in leaderboard.entries],
                list(range(11, 1, -1)),
            )

    def test_json_roundtrip_includes_name_and_last_name(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "nested" / "scores.json"
            with patch(
                "lunar_lander.leaderboard.LEADERBOARD_PATH",
                path,
            ):
                leaderboard = Leaderboard()
                leaderboard.add_entry(
                    420,
                    "MARS",
                    "2026-07-30",
                    name="PJW",
                )
                reloaded = Leaderboard()

            self.assertEqual(
                reloaded.entries,
                [
                    {
                        "score": 420,
                        "body": "MARS",
                        "name": "PJW",
                        "date": "2026-07-30",
                    }
                ],
            )
            self.assertEqual(reloaded.last_name, "PJW")
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(stored["last_name"], "PJW")
            self.assertEqual(stored["entries"][0]["name"], "PJW")

    def test_legacy_list_and_row_without_name_load_with_placeholder(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "leaderboard.json"
            path.write_text(
                json.dumps(
                    [
                        {
                            "score": 120,
                            "body": "MOON",
                            "date": "2026-07-29",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            leaderboard = Leaderboard(path)

            self.assertEqual(leaderboard.entries[0]["name"], "----")
            self.assertEqual(leaderboard.last_name, "")


if __name__ == "__main__":
    unittest.main()
