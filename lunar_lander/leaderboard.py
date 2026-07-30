"""Small, failure-tolerant local leaderboard."""

from __future__ import annotations

from datetime import date as calendar_date
import json
from pathlib import Path
from typing import TypedDict


MAX_ENTRIES = 10


try:
    LEADERBOARD_PATH = (
        Path.home() / ".moon_descent" / "leaderboard.json"
    )
except (OSError, RuntimeError):
    LEADERBOARD_PATH = Path(".moon_descent") / "leaderboard.json"


class LeaderboardEntry(TypedDict):
    score: int
    body: str
    name: str
    date: str


def apply_name_key(name: str, char: str) -> str:
    """Apply one text-entry key to a callsign and return the new value."""
    if char == "\b":
        return name[:-1]
    if len(char) != 1 or len(name) >= 10:
        return name
    candidate = char.upper()
    if candidate.isascii() and (candidate.isalnum() or candidate == "-"):
        return name + candidate
    return name


class Leaderboard:
    """Top-score storage that degrades to session-only data on I/O failure."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else LEADERBOARD_PATH
        self.entries: list[LeaderboardEntry] = []
        self.last_name = ""
        self.load()

    @staticmethod
    def _sorted(entries: list[LeaderboardEntry]) -> list[LeaderboardEntry]:
        return sorted(
            entries,
            key=lambda entry: entry["score"],
            reverse=True,
        )[:MAX_ENTRIES]

    @staticmethod
    def _validated_entry(value: object) -> LeaderboardEntry | None:
        if not isinstance(value, dict):
            return None
        try:
            score = int(value["score"])
            body = str(value["body"])
            name = str(value.get("name", "----"))
            entry_date = str(value["date"])
        except (KeyError, TypeError, ValueError):
            return None
        return {
            "score": score,
            "body": body,
            "name": name,
            "date": entry_date,
        }

    def load(self) -> list[LeaderboardEntry]:
        """Load valid entries; malformed or unavailable files act as empty."""
        try:
            stored = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(stored, list):
                raw_entries = stored
                self.last_name = ""
            elif isinstance(stored, dict):
                raw_entries = stored.get("entries", [])
                stored_last_name = stored.get("last_name", "")
                self.last_name = (
                    stored_last_name
                    if isinstance(stored_last_name, str)
                    else ""
                )
            else:
                self.entries = []
                self.last_name = ""
                return self.entries
            if not isinstance(raw_entries, list):
                self.entries = []
                return self.entries
            entries = [
                entry
                for value in raw_entries
                if (entry := self._validated_entry(value)) is not None
            ]
            self.entries = self._sorted(entries)
        except (OSError, TypeError, ValueError):
            self.entries = []
            self.last_name = ""
        return self.entries

    def save(self) -> None:
        """Persist the current table when the runtime permits file writes."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(
                    {
                        "last_name": self.last_name,
                        "entries": self.entries,
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except (OSError, TypeError, ValueError):
            # Web builds may expose an ephemeral or unavailable home directory.
            pass

    def add_entry(
        self,
        score: int,
        body: str,
        entry_date: str | None = None,
        *,
        name: str | None = None,
    ) -> LeaderboardEntry:
        entry: LeaderboardEntry = {
            "score": int(score),
            "body": str(body),
            "name": "----" if name is None else str(name),
            "date": entry_date or calendar_date.today().isoformat(),
        }
        if name is not None:
            self.last_name = entry["name"]
        self.entries.append(entry)
        self.entries = self._sorted(self.entries)
        self.save()
        return entry
