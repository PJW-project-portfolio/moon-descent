from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from lunar_lander.leaderboard import Leaderboard


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

    def test_json_roundtrip_uses_configured_path(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "nested" / "scores.json"
            with patch(
                "lunar_lander.leaderboard.LEADERBOARD_PATH",
                path,
            ):
                leaderboard = Leaderboard()
                leaderboard.add_entry(420, "MARS", "2026-07-30")
                reloaded = Leaderboard()

            self.assertEqual(
                reloaded.entries,
                [
                    {
                        "score": 420,
                        "body": "MARS",
                        "date": "2026-07-30",
                    }
                ],
            )


if __name__ == "__main__":
    unittest.main()
