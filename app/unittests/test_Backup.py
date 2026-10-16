"""Backups preserve committed snapshots and refuse destructive destinations."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.backup import backup


class BackupTests(unittest.TestCase):
    def test_live_wal_backup_and_restore_preserve_committed_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, snapshot, restored = [
                root / name
                for name in ("source.sqlite3", "backup.sqlite3", "restored.sqlite3")
            ]
            connection = sqlite3.connect(source)
            self.addCleanup(connection.close)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("CREATE TABLE snapshots (revision INTEGER)")
            connection.execute("INSERT INTO snapshots VALUES (1)")
            connection.commit()
            connection.execute("INSERT INTO snapshots VALUES (2)")
            backup(source, snapshot)
            backup(snapshot, restored)
            with sqlite3.connect(restored) as reader:
                self.assertEqual(
                    reader.execute("SELECT * FROM snapshots").fetchall(), [(1,)]
                )
                self.assertEqual(
                    reader.execute("PRAGMA integrity_check").fetchone(), ("ok",)
                )
            connection.rollback()

    def test_missing_corrupt_existing_and_same_destination_are_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / "source.sqlite3", root / "target.sqlite3"
            with self.assertRaises(sqlite3.Error):
                backup(source, target)
            self.assertFalse(source.exists())
            self.assertFalse(target.exists())
            source.write_bytes(b"not a SQLite database")
            with self.assertRaises(sqlite3.Error):
                backup(source, target)
            self.assertFalse(target.exists())
            target.write_bytes(b"existing data")
            with self.assertRaises(FileExistsError):
                backup(source, target)
            self.assertEqual(target.read_bytes(), b"existing data")
            with self.assertRaises(ValueError):
                backup(source, source)
            self.assertEqual(source.read_bytes(), b"not a SQLite database")
