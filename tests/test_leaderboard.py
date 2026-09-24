import csv
from datetime import datetime
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from lunar_lander import leaderboard as leaderboard_module
from lunar_lander.leaderboard import RECORD_FIELDS, Leaderboard


def read_records(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as records_file:
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
            ), patch(
                "lunar_lander.leaderboard.LEGACY_LEADERBOARD_PATH",
                Path(temporary_directory) / "legacy" / "leaderboard.json",
            ):
                leaderboard = Leaderboard()
                leaderboard.add_entry(
                    420,
                    "MARS",
                    "2026-07-30",
                    initials="HGD",
                    phone_last4="0412",
                )
                reloaded = Leaderboard()

            self.assertEqual(
                reloaded.entries,
                [
                    {
                        "score": 420,
                        "body": "MARS",
                        "initials": "HGD",
                        "phone_last4": "0412",
                        "date": "2026-07-30",
                    }
                ],
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(stored["entries"][0]["initials"], "HGD")
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
                    initials="HGD",
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
                ["2026-09-24 14:03:00", "HGD", "0000", "0", "MOON"],
            )
            self.assertEqual(rows[-1][2], "0011")
            self.assertFalse(leaderboard.storage_error)

    def test_header_is_written_once_across_sessions(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "leaderboard.json"
            Leaderboard(path).add_entry(10, "MOON", initials="GN")
            Leaderboard(path).add_entry(20, "MARS", initials="DR")

            rows = read_records(Path(temporary_directory) / "records.csv")
            self.assertEqual(rows[0], list(RECORD_FIELDS))
            self.assertEqual([row[1] for row in rows[1:]], ["GN", "DR"])

    def test_unwritable_log_is_reported_and_retried_next_run(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            records_path = Path(temporary_directory) / "records.csv"
            leaderboard = Leaderboard(
                Path(temporary_directory) / "leaderboard.json",
                records_path,
            )
            records_path.mkdir()  # 파일 자리를 막아 쓰기 실패를 재현

            leaderboard.add_entry(10, "MOON", initials="GN")

            self.assertTrue(leaderboard.storage_error)
            self.assertEqual(len(leaderboard.entries), 1)
            records_path.rmdir()
            leaderboard.add_entry(20, "MARS", initials="DR")

            self.assertFalse(leaderboard.storage_error)
            rows = read_records(records_path)
            self.assertEqual(
                [row[1] for row in rows[1:]],
                ["GN", "DR"],
            )


class DefaultLocationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary_directory = TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name)
        self.game_path = self.root / "game" / "records" / "leaderboard.json"
        self.legacy_path = self.root / "home" / ".moon_descent" / "leaderboard.json"
        for name, value in (
            ("LEADERBOARD_PATH", self.game_path),
            ("LEGACY_LEADERBOARD_PATH", self.legacy_path),
        ):
            path_patch = patch(f"lunar_lander.leaderboard.{name}", value)
            path_patch.start()
            self.addCleanup(path_patch.stop)

    def write_legacy_files(self) -> None:
        self.legacy_path.parent.mkdir(parents=True)
        self.legacy_path.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "score": 300,
                            "body": "MARS",
                            "initials": "HGD",
                            "phone_last4": "0412",
                            "date": "2026-09-24",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.legacy_path.with_name("records.csv").write_text(
            "recorded_at,initials,phone_last4,score,body\n"
            "2026-09-24 10:00:00,HGD,0412,300,MARS\n",
            encoding="utf-8",
        )

    def test_records_go_to_the_game_folder_by_default(self) -> None:
        leaderboard = Leaderboard()
        leaderboard.add_entry(10, "MOON", initials="GN", phone_last4="1111")

        self.assertEqual(leaderboard.path, self.game_path)
        self.assertTrue(self.game_path.is_file())
        self.assertTrue(self.game_path.with_name("records.csv").is_file())
        self.assertFalse(self.legacy_path.parent.exists())

    def test_unwritable_game_folder_falls_back_to_home_folder(self) -> None:
        blocker = self.root / "game"
        blocker.write_text("not a folder", encoding="utf-8")

        leaderboard = Leaderboard()

        self.assertEqual(leaderboard.path, self.legacy_path)
        self.assertEqual(
            leaderboard.records_path,
            self.legacy_path.with_name("records.csv"),
        )

    def test_legacy_files_are_copied_once_and_kept(self) -> None:
        self.write_legacy_files()

        leaderboard = Leaderboard()

        self.assertEqual(leaderboard.entries[0]["initials"], "HGD")
        self.assertEqual(
            read_records(self.game_path.with_name("records.csv"))[1][1],
            "HGD",
        )
        self.assertTrue(self.legacy_path.is_file())

    def test_existing_game_folder_files_are_not_overwritten(self) -> None:
        self.write_legacy_files()
        Leaderboard().add_entry(50, "MOON", initials="KY", phone_last4="2222")
        self.legacy_path.write_text('{"entries": []}', encoding="utf-8")

        reloaded = Leaderboard()

        self.assertEqual(
            [entry["initials"] for entry in reloaded.entries],
            ["HGD", "KY"],
        )


class GameFolderTests(unittest.TestCase):
    def test_source_checkout_uses_the_project_root(self) -> None:
        folder = leaderboard_module._game_folder()
        self.assertTrue((folder / "main.py").is_file())

    def test_packaged_build_uses_the_executable_folder(self) -> None:
        with patch.object(sys, "frozen", True, create=True), patch.object(
            sys, "executable", "/opt/MoonDescent/MoonDescent.exe"
        ):
            folder = leaderboard_module._game_folder()
        self.assertEqual(folder, Path("/opt/MoonDescent").resolve())

    def test_macos_app_uses_the_folder_holding_the_bundle(self) -> None:
        with patch.object(sys, "frozen", True, create=True), patch.object(
            sys,
            "executable",
            "/Users/pilot/Games/MoonDescent.app/Contents/MacOS/MoonDescent",
        ):
            folder = leaderboard_module._game_folder()
        self.assertEqual(folder, Path("/Users/pilot/Games").resolve())


if __name__ == "__main__":
    unittest.main()
