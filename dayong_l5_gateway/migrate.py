"""Run explicitly with L5_DATABASE_URL set; never automatically mutate DB on startup."""
import os
from pathlib import Path
import psycopg

SCHEMA = Path(__file__).with_name("schema.sql")
TABLES = ("l5_agents", "l5_messages", "l5_events")

def migrate():
    url = os.getenv("L5_DATABASE_URL")
    if not url:
        raise SystemExit("L5_DATABASE_URL missing; migration refused")
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA.read_text(encoding="utf-8"))
            cur.execute("SELECT tablename FROM pg_tables WHERE schemaname=current_schema() AND tablename = ANY(%s)", (list(TABLES),))
            present = {row[0] for row in cur.fetchall()}
            if present != set(TABLES):
                raise RuntimeError(f"Schema incomplete: {set(TABLES) - present}")
        print("L5 schema migration verified: 3 tables")
if __name__ == "__main__":
    migrate()
