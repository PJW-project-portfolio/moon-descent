"""Small, failure-tolerant local leaderboard with a full run log."""

from __future__ import annotations

import csv
from datetime import datetime
import json
from pathlib import Path
from typing import TypedDict


MAX_ENTRIES = 10
RECORDS_FILENAME = "records.csv"
RECORD_FIELDS = ("recorded_at", "initials", "phone_last4", "score", "body")


try:
    LEADERBOARD_PATH = (
        Path.home() / ".moon_descent" / "leaderboard.json"
    )
except (OSError, RuntimeError):
    LEADERBOARD_PATH = Path(".moon_descent") / "leaderboard.json"


class LeaderboardEntry(TypedDict):
    score: int
    body: str
    initials: str
    phone_last4: str
    date: str


class Leaderboard:
    """Top-10 table plus an append-only CSV of every recorded run.

    Both files degrade to session-only data on I/O failure. ``storage_error``
    reports whether the latest record failed to reach either file; CSV rows
    that could not be written are retried with the next record.
    """

    def __init__(
        self,
        path: Path | None = None,
        records_path: Path | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else LEADERBOARD_PATH
        self.records_path = (
            Path(records_path)
            if records_path is not None
            else self.path.with_name(RECORDS_FILENAME)
        )
        self.entries: list[LeaderboardEntry] = []
        self.storage_error = False
        self._pending_records: list[tuple[str, str, str, int, str]] = []
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
            # 초성 도입 전 기록은 기존 닉네임을 초성 칸에 그대로 보여 준다.
            initials = str(value.get("initials", value.get("name", "----")))
            phone_last4 = str(value.get("phone_last4", "----"))
            entry_date = str(value["date"])
        except (KeyError, TypeError, ValueError):
            return None
        return {
            "score": score,
            "body": body,
            "initials": initials,
            "phone_last4": phone_last4,
            "date": entry_date,
        }

    def load(self) -> list[LeaderboardEntry]:
        """Load valid entries; malformed or unavailable files act as empty."""
        try:
            stored = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(stored, list):
                raw_entries = stored
            elif isinstance(stored, dict):
                raw_entries = stored.get("entries", [])
            else:
                self.entries = []
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
        return self.entries

    def save(self) -> None:
        """Persist the current table when the runtime permits file writes."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(
                    {"entries": self.entries},
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except (OSError, TypeError, ValueError):
            # Web builds may expose an ephemeral or unavailable home directory.
            self.storage_error = True

    def _append_records(self) -> None:
        """Append pending runs to the CSV log (kept for retry on failure)."""
        try:
            self.records_path.parent.mkdir(parents=True, exist_ok=True)
            write_header = (
                not self.records_path.exists()
                or self.records_path.stat().st_size == 0
            )
            # utf-8-sig: 엑셀에서 열어도 초성이 깨지지 않도록 파일 맨 앞에만
            # BOM을 쓴다(이어 쓰기에서는 BOM을 다시 쓰지 않음).
            with self.records_path.open(
                "a", encoding="utf-8-sig", newline=""
            ) as records_file:
                writer = csv.writer(records_file)
                if write_header:
                    writer.writerow(RECORD_FIELDS)
                writer.writerows(self._pending_records)
            self._pending_records.clear()
        except (OSError, ValueError):
            # 엑셀이 파일을 열고 있으면 Windows에서 쓰기가 거부된다.
            self.storage_error = True

    def add_entry(
        self,
        score: int,
        body: str,
        entry_date: str | None = None,
        *,
        initials: str = "----",
        phone_last4: str = "----",
        recorded_at: datetime | None = None,
    ) -> LeaderboardEntry:
        recorded_at = recorded_at or datetime.now()
        entry: LeaderboardEntry = {
            "score": int(score),
            "body": str(body),
            "initials": str(initials),
            "phone_last4": str(phone_last4),
            "date": entry_date or recorded_at.date().isoformat(),
        }
        self.entries.append(entry)
        self.entries = self._sorted(self.entries)
        self._pending_records.append(
            (
                recorded_at.strftime("%Y-%m-%d %H:%M:%S"),
                entry["initials"],
                entry["phone_last4"],
                entry["score"],
                entry["body"],
            )
        )
        self.storage_error = False
        self.save()
        self._append_records()
        return entry
