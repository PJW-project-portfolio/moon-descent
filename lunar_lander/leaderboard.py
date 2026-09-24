"""Small, failure-tolerant local leaderboard with a full run log."""

from __future__ import annotations

import csv
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import TypedDict


MAX_ENTRIES = 10
RECORDS_FILENAME = "records.csv"
RECORD_FIELDS = ("recorded_at", "initials", "phone_last4", "score", "body")


def _game_folder() -> Path:
    """Folder the game was launched from: project root or packaged app folder."""
    if getattr(sys, "frozen", False):
        folder = Path(sys.executable).resolve().parent
        # macOS: MoonDescent.app/Contents/MacOS → .app을 담고 있는 폴더
        if folder.name == "MacOS" and folder.parent.name == "Contents":
            folder = folder.parent.parent.parent
        return folder
    return Path(__file__).resolve().parent.parent


# 운영자가 바로 찾을 수 있도록 게임 폴더 옆 records/에 저장한다.
LEADERBOARD_PATH = _game_folder() / "records" / "leaderboard.json"

# 이전 버전의 저장 위치. 게임 폴더에 쓸 수 없을 때의 대체 경로이기도 하다.
try:
    LEGACY_LEADERBOARD_PATH = (
        Path.home() / ".moon_descent" / "leaderboard.json"
    )
except (OSError, RuntimeError):
    LEGACY_LEADERBOARD_PATH = Path(".moon_descent") / "leaderboard.json"


def _is_writable_dir(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=folder):
            pass
    except OSError:
        return False
    return True


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
        use_default = path is None
        if path is None:
            # 게임 폴더가 읽기 전용이면(예: 다운로드 폴더에서 바로 연 macOS 앱)
            # 이전 위치인 홈 폴더를 쓴다.
            path = (
                LEADERBOARD_PATH
                if _is_writable_dir(LEADERBOARD_PATH.parent)
                else LEGACY_LEADERBOARD_PATH
            )
        self.path = Path(path)
        self.records_path = (
            Path(records_path)
            if records_path is not None
            else self.path.with_name(RECORDS_FILENAME)
        )
        self.entries: list[LeaderboardEntry] = []
        self.storage_error = False
        self._pending_records: list[tuple[str, str, str, int, str]] = []
        if use_default:
            self._adopt_legacy_files()
        self.load()

    def _adopt_legacy_files(self) -> None:
        """Copy files an older version kept in the home folder, once.

        The originals stay where they are; nothing is copied over files
        that already exist in the current folder.
        """
        legacy_records_path = LEGACY_LEADERBOARD_PATH.with_name(
            RECORDS_FILENAME
        )
        for legacy, current in (
            (LEGACY_LEADERBOARD_PATH, self.path),
            (legacy_records_path, self.records_path),
        ):
            if legacy == current or current.exists() or not legacy.is_file():
                continue
            try:
                current.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(legacy, current)
            except OSError:
                pass

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
            # 파일럿 ID 도입 전 기록은 기존 닉네임을 이니셜 칸에 보여 준다.
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
            with self.records_path.open(
                "a", encoding="utf-8", newline=""
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
