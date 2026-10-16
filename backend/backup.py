"""Consistent SQLite backups without overwriting an existing destination.

Usage: python -m backend.backup SOURCE DESTINATION
Restoring uses the same command while the server is stopped, with a new path.
"""

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path


def backup(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError("Source and destination must be different files")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Read-only mode refuses to create a missing source database.
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as reader:
        with destination.open("xb"):
            pass
        try:
            with closing(sqlite3.connect(destination)) as writer:
                reader.backup(writer)
                if writer.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise ValueError("Backup integrity check failed")
        except BaseException:
            destination.unlink()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        backup(args.source, args.destination)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, "Backup failed: " + str(error) + "\n")
    print("Database copy completed and integrity checked.")


if __name__ == "__main__":
    main()
