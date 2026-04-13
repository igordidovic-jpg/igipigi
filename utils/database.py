"""
CFOS-XG PRO 75 TITAN - Database Module

SQLite database for match history, user preferences, and accuracy tracking.
Uses aiosqlite for async operations.
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DATABASE_URL", "cfos.db").replace("sqlite:///", "")

CREATE_MATCH_HISTORY = """
CREATE TABLE IF NOT EXISTS match_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    home TEXT NOT NULL,
    away TEXT NOT NULL,
    minute INTEGER,
    bet TEXT,
    confidence TEXT,
    p_goal REAL,
    mc_h REAL,
    mc_x REAL,
    mc_a REAL,
    score_home INTEGER DEFAULT 0,
    score_away INTEGER DEFAULT 0,
    final_result TEXT,
    correct INTEGER DEFAULT NULL,
    created_at TEXT NOT NULL,
    csv_data TEXT
)
"""

CREATE_USER_PREFS = """
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER PRIMARY KEY,
    alert_level TEXT DEFAULT 'HIGH',
    language TEXT DEFAULT 'ENG',
    preset TEXT DEFAULT 'balanced',
    updated_at TEXT NOT NULL
)
"""

CREATE_ACCURACY = """
CREATE TABLE IF NOT EXISTS accuracy_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    home TEXT,
    away TEXT,
    minute INTEGER,
    prediction TEXT,
    final_result TEXT,
    correct INTEGER,
    created_at TEXT NOT NULL
)
"""


class Database:
    """
    Async SQLite database manager.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._initialized = False

    async def initialize(self):
        """Create tables if they don't exist."""
        if not AIOSQLITE_AVAILABLE:
            logger.warning("aiosqlite not available, database disabled")
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(CREATE_MATCH_HISTORY)
            await db.execute(CREATE_USER_PREFS)
            await db.execute(CREATE_ACCURACY)
            await db.commit()
        self._initialized = True
        logger.info(f"Database initialized at {self.db_path}")

    async def save_match(
        self,
        user_id: int,
        decision: dict,
        csv_data: str = "",
        score_home: int = 0,
        score_away: int = 0,
    ) -> int:
        """
        Save a match analysis to history.

        Args:
            user_id: Telegram user ID
            decision: BetScorer.extract_decision() output
            csv_data: Original CSV input string
            score_home / score_away: Current score

        Returns:
            Row ID of inserted record
        """
        if not AIOSQLITE_AVAILABLE or not self._initialized:
            return -1

        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO match_history
                    (user_id, home, away, minute, bet, confidence, p_goal,
                     mc_h, mc_x, mc_a, score_home, score_away, created_at, csv_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    decision.get("home", ""),
                    decision.get("away", ""),
                    decision.get("minute", 0),
                    decision.get("bet", ""),
                    decision.get("confidence", ""),
                    decision.get("p_goal", 0.0),
                    decision.get("mc_h", 0.0),
                    decision.get("mc_x", 0.0),
                    decision.get("mc_a", 0.0),
                    score_home,
                    score_away,
                    now,
                    csv_data,
                ),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_match_history(self, user_id: int, limit: int = 10) -> list[dict]:
        """
        Get match history for a user.

        Args:
            user_id: Telegram user ID
            limit: Maximum number of records

        Returns:
            List of match dicts
        """
        if not AIOSQLITE_AVAILABLE or not self._initialized:
            return []

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM match_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_match_result(self, record_id: int, final_result: str, prediction: str):
        """
        Update a match record with final result for accuracy tracking.
        """
        if not AIOSQLITE_AVAILABLE or not self._initialized:
            return

        correct = 1 if _normalize_result(final_result) == _normalize_result(prediction) else 0
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE match_history SET final_result = ?, correct = ? WHERE id = ?",
                (final_result, correct, record_id),
            )
            await db.commit()

    async def get_accuracy(self, user_id: int) -> dict:
        """
        Get accuracy statistics for a user.

        Returns:
            dict with total, correct, accuracy (0.0-1.0), by_confidence
        """
        if not AIOSQLITE_AVAILABLE or not self._initialized:
            return {"total": 0, "correct": 0, "accuracy": 0.0}

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) as correct,
                       confidence
                FROM match_history
                WHERE user_id = ? AND correct IS NOT NULL
                GROUP BY confidence
                """,
                (user_id,),
            )
            rows = await cursor.fetchall()

            total_all = 0
            correct_all = 0
            by_conf = {}

            for row in rows:
                t = row[0] or 0
                c = row[1] or 0
                conf = row[2] or "UNKNOWN"
                total_all += t
                correct_all += c
                by_conf[conf] = {
                    "total": t,
                    "correct": c,
                    "accuracy": round(c / t, 3) if t > 0 else 0.0,
                }

            return {
                "total": total_all,
                "correct": correct_all,
                "accuracy": round(correct_all / total_all, 3) if total_all > 0 else 0.0,
                "by_confidence": by_conf,
            }

    async def get_user_prefs(self, user_id: int) -> dict:
        """Get user preferences, creating defaults if not exists."""
        if not AIOSQLITE_AVAILABLE or not self._initialized:
            return {"alert_level": "HIGH", "language": "ENG", "preset": "balanced"}

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM user_preferences WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)

            # Create defaults
            now = datetime.utcnow().isoformat()
            await db.execute(
                "INSERT INTO user_preferences (user_id, alert_level, language, preset, updated_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, "HIGH", "ENG", "balanced", now),
            )
            await db.commit()
            return {"user_id": user_id, "alert_level": "HIGH", "language": "ENG", "preset": "balanced"}

    async def set_user_pref(self, user_id: int, key: str, value: str):
        """Set a user preference value."""
        if not AIOSQLITE_AVAILABLE or not self._initialized:
            return

        # Use separate SQL strings per column to fully avoid f-string interpolation
        _SQL_SET_PREF: dict[str, str] = {
            "alert_level": """
                INSERT INTO user_preferences (user_id, alert_level, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET alert_level = ?, updated_at = ?
            """,
            "language": """
                INSERT INTO user_preferences (user_id, language, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET language = ?, updated_at = ?
            """,
            "preset": """
                INSERT INTO user_preferences (user_id, preset, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET preset = ?, updated_at = ?
            """,
        }
        if key not in _SQL_SET_PREF:
            return
        sql = _SQL_SET_PREF[key]

        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, (user_id, value, now, value, now))
            await db.commit()

    async def save_live_session(self, user_id: int, home: str, away: str, data: dict):
        """Save/update live tracking session data."""
        if not AIOSQLITE_AVAILABLE or not self._initialized:
            return

        # Use match_history for live sessions too
        await self.save_match(user_id, data)


def _normalize_result(value: str) -> str:
    """Normalize result/prediction value for comparison."""
    v = str(value).strip().upper()
    mapping = {
        "HOME": "HOME", "1": "HOME", "DOMACI": "HOME", "DOMAČI": "HOME",
        "AWAY": "AWAY", "2": "AWAY", "GOST": "AWAY",
        "DRAW": "DRAW", "X": "DRAW", "REMI": "DRAW",
    }
    return mapping.get(v, v)
