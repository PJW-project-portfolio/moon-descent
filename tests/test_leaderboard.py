import csv
from datetime import datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from lunar_lander.leaderboard import RECORD_FIELDS, Leaderboard


def read_records(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as records_file:
        return list(csv.reader(records_file))


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

    def test_json_roundtrip_includes_initials_and_phone(self) -> None:
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
                    initials="ㅂㅈㅇ",
                    phone_last4="0412",
                )
                reloaded = Leaderboard()

            self.assertEqual(
                reloaded.entries,
                [
                    {
                        "score": 420,
                        "body": "MARS",
                        "initials": "ㅂㅈㅇ",
                        "phone_last4": "0412",
                        "date": "2026-07-30",
                    }
                ],
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(stored["entries"][0]["initials"], "ㅂㅈㅇ")
            self.assertEqual(stored["entries"][0]["phone_last4"], "0412")
            self.assertNotIn("last_name", stored)

    def test_legacy_callsign_moves_to_initials_column(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "leaderboard.json"
            path.write_text(
                json.dumps(
                    {
                        "last_name": "PJW",
                        "entries": [
                            {
                                "score": 300,
                                "body": "MARS",
                                "name": "PJW",
                                "date": "2026-07-30",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            leaderboard = Leaderboard(path)

            self.assertEqual(leaderboard.entries[0]["initials"], "PJW")
            self.assertEqual(leaderboard.entries[0]["phone_last4"], "----")

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

            self.assertEqual(leaderboard.entries[0]["initials"], "----")
            self.assertEqual(leaderboard.entries[0]["phone_last4"], "----")


class RecordsLogTests(unittest.TestCase):
    def test_every_run_is_logged_even_after_top_ten_trims_it(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            leaderboard = Leaderboard(
                Path(temporary_directory) / "leaderboard.json"
            )
            for score in range(12):
                leaderboard.add_entry(
                    score,
                    "MOON",
                    initials="ㅂㅈㅇ",
                    phone_last4=f"{score:04d}",
                    recorded_at=datetime(2026, 9, 24, 14, 3, score),
                )

            records_path = Path(temporary_directory) / "records.csv"
            rows = read_records(records_path)
            self.assertEqual(len(leaderboard.entries), 10)
            self.assertEqual(rows[0], list(RECORD_FIELDS))
            self.assertEqual(len(rows), 13)
            self.assertEqual(
                rows[1],
                ["2026-09-24 14:03:00", "ㅂㅈㅇ", "0000", "0", "MOON"],
            )
            self.assertEqual(rows[-1][2], "0011")
            self.assertFalse(leaderboard.storage_error)

    def test_log_starts_with_a_single_bom_for_excel(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "leaderboard.json"
            Leaderboard(path).add_entry(10, "MOON", initials="ㄱㄴ")
            Leaderboard(path).add_entry(20, "MARS", initials="ㄷㄹ")

            raw = (Path(temporary_directory) / "records.csv").read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
            self.assertEqual(raw.count(b"\xef\xbb\xbf"), 1)
            self.assertEqual(raw.count(b"recorded_at"), 1)

    def test_unwritable_log_is_reported_and_retried_next_run(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            records_path = Path(temporary_directory) / "records.csv"
            leaderboard = Leaderboard(
                Path(temporary_directory) / "leaderboard.json",
                records_path,
            )
            records_path.mkdir()  # 파일 자리를 막아 쓰기 실패를 재현

            leaderboard.add_entry(10, "MOON", initials="ㄱㄴ")

            self.assertTrue(leaderboard.storage_error)
            self.assertEqual(len(leaderboard.entries), 1)
            records_path.rmdir()
            leaderboard.add_entry(20, "MARS", initials="ㄷㄹ")

            self.assertFalse(leaderboard.storage_error)
            rows = read_records(records_path)
            self.assertEqual(
                [row[1] for row in rows[1:]],
                ["ㄱㄴ", "ㄷㄹ"],
            )


if __name__ == "__main__":
    unittest.main()
