"""Organizer-only DB setup. No wallet credit occurs until an authenticated claim.

Examples:
 python tools/hackathon_admin.py seed --name "Hackathon 2026" --count 50 --prefix HACK --activate
 python tools/hackathon_admin.py seed --name "Hackathon 2026" --team-ids-file private-team-ids.txt
 python tools/hackathon_admin.py close --name "Hackathon 2026"
"""

import argparse
import os
import re
from pathlib import Path

import psycopg2
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def setup_campaign(connection, name, team_ids, activate=False):
    if not name.strip() or len(name) > 120:
        raise ValueError("Campaign name must be 1–120 characters")
    ids = [value.strip().upper() for value in team_ids]
    if (
        not ids
        or len(ids) > 10000
        or len(set(ids)) != len(ids)
        or not all(re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{2,63}", value) for value in ids)
    ):
        raise ValueError("Provide 1–10000 unique valid Team IDs")
    with connection.cursor() as cur:
        cur.execute(
            "insert into public.hackathon_campaigns(name) values(%s) on conflict(name) do nothing",
            (name,),
        )
        cur.execute(
            "select id from public.hackathon_campaigns where name=%s for update",
            (name,),
        )
        campaign = cur.fetchone()[0]
        for team in ids:
            cur.execute(
                "insert into public.hackathon_team_grants(campaign_id,team_id) values(%s,%s) on conflict(campaign_id,team_id) do nothing",
                (campaign, team),
            )
        if activate:
            # Never silently deactivate a different campaign.
            cur.execute(
                "update public.hackathon_campaigns set status='ACTIVE',updated_at=now() where id=%s",
                (campaign,),
            )
    return len(ids)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["seed", "close"])
    parser.add_argument("--name", required=True)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--prefix", default="HACK")
    parser.add_argument("--team-ids-file", type=Path)
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args()
    url = os.getenv("DATABASE_URL") or dotenv_values(ROOT / ".env").get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL must be configured privately")
    conn = psycopg2.connect(url, sslmode="require", connect_timeout=10)
    try:
        with conn:
            if args.command == "close":
                with conn.cursor() as cur:
                    cur.execute(
                        "update public.hackathon_campaigns set status='INACTIVE',updated_at=now() where name=%s",
                        (args.name,),
                    )
                    if cur.rowcount != 1:
                        raise ValueError("Campaign not found")
                print("Campaign closed to new claims; existing grants unchanged")
            else:
                ids = (
                    args.team_ids_file.read_text(encoding="utf-8").splitlines()
                    if args.team_ids_file
                    else [f"{args.prefix}-{i:03}" for i in range(1, args.count + 1)]
                )
                count = setup_campaign(conn, args.name, ids, args.activate)
                print(
                    f"Campaign configured with {count} Team IDs; no wallets or funds issued by seeding"
                )
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            str(exc)
            if type(exc) is ValueError
            else "Organizer operation failed; check active campaign uniqueness and migration state"
        )
        raise SystemExit(1)
