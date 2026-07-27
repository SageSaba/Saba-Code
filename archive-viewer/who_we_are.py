"""WHO WE ARE — the daily load.

Run this FIRST, at the start of every session, before touching anything else.
It reads the standing laws and the state of the book out of SQL in one shot, so
nothing has to be re-derived and Saba never has to say it twice.

    python3 who_we_are.py

Saba's design, 2026-07-26: the laws live in the archive, not in one AI's private
memory, so that any keeper and any AI at the well picks up the same book.
"""
import sqlite3
import os

SUG = "/Users/saba/Archive/Archive_Suggestions.db"
SER = "/Users/saba/Archive/Sermons.db"
CONV = "/Users/saba/Archive/Conversations.db"


def main():
    sug = sqlite3.connect(f"file:{SUG}?mode=ro", uri=True)
    ser = sqlite3.connect(f"file:{SER}?mode=ro", uri=True)
    conv = sqlite3.connect(f"file:{CONV}?mode=ro", uri=True)

    print("=" * 78)
    print("WHO WE ARE — read this before you do anything")
    print("=" * 78)

    for scope in ("who we are", "everything in this house", "every session"):
        for ruling, because in sug.execute(
            "SELECT ruling, because FROM rulings WHERE scope=? AND standing=1 ORDER BY id", (scope,)
        ):
            print("\n" + ruling)
            if because:
                print("  WHY: " + because)

    print("\n" + "=" * 78)
    print("THE STANDING LAWS")
    print("=" * 78)
    for rid, ruling, because, scope, on in sug.execute(
        """SELECT id, ruling, because, scope, ruled_on FROM rulings
           WHERE standing=1 AND scope NOT IN ('who we are','everything in this house','every session')
           ORDER BY id"""
    ):
        print(f"\n[{rid}] ({scope}, ruled {on})\n{ruling}")
        if because:
            print("  WHY: " + because)

    print("\n" + "=" * 78)
    print("THE STATE OF THE BOOK")
    print("=" * 78)
    svc = ser.execute("SELECT COUNT(*) FROM Services").fetchone()[0]
    lines = ser.execute("SELECT COUNT(*) FROM RawSegments").fetchone()[0]
    empty = ser.execute(
        "SELECT COUNT(*) FROM Services s WHERE NOT EXISTS (SELECT 1 FROM RawSegments r WHERE r.service_id=s.ID)"
    ).fetchone()[0]
    ppl = sug.execute("SELECT COUNT(*) FROM people").fetchone()[0]
    priv = sug.execute("SELECT COUNT(*) FROM people WHERE private=1").fetchone()[0]
    voiced = sug.execute("SELECT COUNT(DISTINCT person_id) FROM voiceprints").fetchone()[0]
    print(f"  services              {svc:,}   ({empty} with no transcript yet)")
    print(f"  transcript lines      {lines:,}")
    print(f"  people                {ppl}   ({voiced} have a voiceprint, {priv} carry sealed notes)")
    print("\n  Where the mass is — services by year:")
    years = {}
    for (d,) in ser.execute("SELECT CAST(preach_date AS TEXT) FROM Services"):
        y = d[:4]
        if y.isdigit():
            years[y] = years.get(y, 0) + 1
    for decade in sorted({y[:3] for y in years}):
        row = " ".join(f"{y}:{years[y]}" for y in sorted(years) if y.startswith(decade))
        print(f"    {decade}0s  {row}")

    print("\n" + "=" * 78)
    print("THE SCRIBE'S OWN LOG — how this machine fails, in its own words.")
    print("Never outranks a ruling. Saba's word corrects anything here.")
    print("=" * 78)
    try:
        for kind, what, instead, cost in sug.execute(
            "SELECT kind, what, instead, cost FROM scribe_log ORDER BY id"
        ):
            print(f"\n  [{kind}] {what}")
            if instead:
                print(f"     -> {instead}")
            if cost:
                print(f"     cost: {cost}")
    except sqlite3.OperationalError:
        print("  (no log yet)")

    print("\n" + "=" * 78)
    print("ARCHIVED CONVERSATIONS — no data lost to compression")
    print("=" * 78)
    try:
        for sid, started, total, user_msgs, asst_msgs in conv.execute(
            """SELECT session_id, started, total_messages, total_user_messages, total_assistant_messages
               FROM conversation_metadata ORDER BY started DESC LIMIT 3"""
        ):
            print(f"\n  {sid[:8]}...  ({started[:10]})")
            print(f"    {total} messages: {user_msgs} from Saba, {asst_msgs} responses")
    except sqlite3.OperationalError:
        print("  (no archived conversations yet)")

    print("\n" + "=" * 78)
    print("SESSION LOG — what happened and when")
    print("=" * 78)
    try:
        for sid, ts, kind, asked, done in sug.execute(
            """SELECT session_id, timestamp, event_type, what_was_asked, what_was_done
               FROM session_log ORDER BY timestamp DESC LIMIT 5"""
        ):
            print(f"\n  {ts[:10]}  [{kind}]")
            if asked:
                print(f"    asked: {asked[:70]}")
            if done:
                print(f"    done:  {done[:70]}")
    except sqlite3.OperationalError:
        print("  (no log yet)")

    print("\n" + "=" * 78)
    print("SEALED — do not surface, do not summarize, do not search into.")
    print("Opens only when Saba asks, or when his wife Barbara asks.")
    print("=" * 78)
    for pid, name in sug.execute("SELECT id, name FROM people WHERE private=1 ORDER BY id"):
        print(f"  person {pid:4d}  {name}")
    print("  Their MESSAGES stay fully open and searchable. The seal covers the private matter only.")
    print()


if __name__ == "__main__":
    main()
