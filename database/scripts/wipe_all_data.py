#!/usr/bin/env python3
"""
Wipe All Data - Danger Zone

This script deletes all data from core StockAI tables:
- stockai.stock_prices
- stockai.foreign_trades
- stockai.stock_statistics
- stockai.vn100_history
- stockai.vn100_current

Usage:
  python database/scripts/wipe_all_data.py --yes

Environment variables for DB connection are respected (see DatabaseConfig).
"""

import argparse
import sys
from sqlalchemy import text

from database.api.database import DatabaseManager


def wipe_all() -> None:
    db = DatabaseManager()
    db.initialize()
    engine = db.get_engine()

    stmts = [
        # Order matters because of FKs; child tables first
        "DELETE FROM stockai.stock_prices;",
        "DELETE FROM stockai.foreign_trades;",
        "DELETE FROM stockai.stock_statistics;",
        "DELETE FROM stockai.vn100_history;",
        "DELETE FROM stockai.vn100_current;",
    ]

    with engine.connect() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))
        conn.commit()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Wipe all StockAI data (DANGER)")
    parser.add_argument("--yes", action="store_true", help="Confirm wiping all data")
    args = parser.parse_args(argv)

    if not args.yes:
        print("Refusing to run without --yes")
        return 2

    wipe_all()
    print("✅ All data wiped from core tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


