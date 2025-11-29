"""Record code changes to Spectrena lineage database."""

import hashlib
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def find_lineage_db() -> Optional[Path]:
    """
    Find lineage database in project hierarchy.

    Searches upward from current directory for:
    - .spectrena/lineage.db (SQLite)
    - .spectrena/lineage (SurrealDB embedded)

    Returns:
        Path to database directory/file, or None if not found

    """
    current = Path.cwd()

    for parent in [current, *list(current.parents)]:
        # Check for SQLite
        sqlite_path = parent / ".spectrena" / "lineage.db"
        if sqlite_path.exists():
            return sqlite_path

        # Check for SurrealDB embedded
        surreal_path = parent / ".spectrena" / "lineage"
        if surreal_path.exists() and surreal_path.is_dir():
            return surreal_path

    return None


def get_active_task() -> Optional[dict]:
    """
    Get currently active task from phase_state.

    Returns:
        Dict with keys: current_task_id, title, plan_id, spec_id
        or None if no active task or database not found

    """
    db_path = find_lineage_db()
    if not db_path:
        return None

    # SQLite implementation
    if str(db_path).endswith(".db"):
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                row = conn.execute(
                    """
                    SELECT ps.current_task_id, t.title, t.plan_id, p.spec_id
                    FROM phase_state ps
                    LEFT JOIN tasks t ON ps.current_task_id = t.task_id
                    LEFT JOIN plans p ON t.plan_id = p.plan_id
                    WHERE ps.id = 1 AND ps.current_task_id IS NOT NULL
                """
                ).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.debug(f"Error querying active task: {e}")
            return None

    # SurrealDB not yet implemented - would require async client
    # For now, gracefully degrade
    logger.debug("SurrealDB lineage tracking not yet implemented")
    return None


def record_change(
    task_id: str,
    file_path: str,
    change_type: str,
    tool_used: str,
    symbol_fqn: Optional[str] = None,
    old_content: Optional[str] = None,
    new_content: Optional[str] = None,
) -> Optional[int]:
    """
    Record a code change in the lineage database.

    Called automatically by modified Serena tools after edits.

    Args:
        task_id: Spectrena task ID (e.g., "CORE-001-T01")
        file_path: Path to modified file
        change_type: Type of change ("modify", "create", "delete", "rename")
        tool_used: Name of Serena tool used
        symbol_fqn: Fully qualified symbol name (e.g., "src/auth.py:User.authenticate")
        old_content: Content before change (for diffing)
        new_content: Content after change (for diffing)

    Returns:
        ID of recorded change, or None if recording failed/not available

    """
    db_path = find_lineage_db()
    if not db_path:
        # Graceful degradation - no DB, no recording
        logger.debug("No lineage database found, skipping change recording")
        return None

    # Generate content hashes for efficient storage
    old_hash = hashlib.sha256(old_content.encode()).hexdigest()[:16] if old_content else None
    new_hash = hashlib.sha256(new_content.encode()).hexdigest()[:16] if new_content else None

    timestamp = datetime.now(UTC).isoformat()

    # SQLite implementation
    if str(db_path).endswith(".db"):
        try:
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO code_changes
                    (task_id, file_path, symbol_fqn, change_type, tool_used,
                     old_content_hash, new_content_hash, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (task_id, file_path, symbol_fqn, change_type, tool_used, old_hash, new_hash, timestamp),
                )
                conn.commit()
                logger.info(f"Recorded change for task {task_id}: {tool_used} on {file_path}")
                return cursor.lastrowid
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.warning(f"Failed to record change to lineage database: {e}")
            return None

    # SurrealDB implementation - TODO
    # Would use async surrealdb client here
    logger.debug("SurrealDB change recording not yet implemented")
    return None
