#!/usr/bin/env python3
"""Bring Sharon Key's sermon notes (2011-2014) into Services.

One Services row per dated note file: preach_date by the LAW
(folder year > filename > text; a FILE STAMP counts as evidence when
it agrees with the folder year — Saba 2026-07-17 "some are accurate").
Title from words after the date; full text into Services.notes with a
source line. org and sermon_giver stay EMPTY — no blankets.

Walks year folders RECURSIVELY (2012/1201 etc.). Two files on one
date are two services (am/pm, different titles) — twins only when
their normalized names match (re-saves like "-Acer-PC", " (1)").
Skips rows this importer already made. Run with the DB backed up.
"""
import os, re, sqlite3, zipfile, html, datetime

DB = "/Users/saba/Archive/Sermons.db"
ROOT = "/Users/saba/Desktop/Sermon Notes"
YEARS = ["2011", "2012", "2013", "2014"]
MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}


def docx_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = re.sub(r"<w:p[ >]", "\n<w:p ", xml)
    text = html.unescape(re.sub(r"<[^>]+>", "", xml))
    return "\n".join(l.strip() for l in text.split("\n") if l.strip())


def parse_name(stem, folder_year):
    """-> (date 'YYYY-MM-DD', title) or None."""
    title = ""
    m = re.match(r"^(January|February|March|April|May|June|July|August|"
                 r"September|October|November|December) (\d{1,2}), (\d{4})"
                 r"(.*)$", stem)
    if m:
        y, mo, d = int(m.group(3)), MONTHS[m.group(1)], int(m.group(2))
        title = m.group(4)
    else:
        m = re.match(r"^(\d{4})[-_](\d{1,2})[-_](\d{1,2})(.*)$", stem)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            title = m.group(4)
        else:
            m = re.match(r"^(\d{2})(\d{2})(\d{2})(.*)$", stem)
            if m:
                y, mo, d = 2000 + int(m.group(1)), int(m.group(2)), int(m.group(3))
                title = m.group(4)
            else:
                return None
    if y != int(folder_year):
        y = int(folder_year)          # the folder rules
    try:
        date = datetime.date(y, mo, d).isoformat()
    except ValueError:
        return None
    title = re.sub(r"^[\s\-–_]+", "", title).strip()
    return date, title


def normalize(stem):
    s = re.sub(r"[-_ ]*Acer[-_ ]*PC", "", stem, flags=re.I)
    s = re.sub(r" \(\d+\)$", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def stamp_date(path, folder_year):
    d = datetime.date.fromtimestamp(os.path.getmtime(path))
    return d.isoformat() if d.year == int(folder_year) else None


def main():
    found = {}     # (date, normalized stem) -> (size, path, title, how)
    twins, unparsed = [], []
    for year in YEARS:
        for dirpath, dirs, files in os.walk(os.path.join(ROOT, year)):
            for name in sorted(files):
                if not name.endswith(".docx") or name.startswith("~"):
                    continue
                path = os.path.join(dirpath, name)
                stem = name[:-5]
                parsed = parse_name(stem, year)
                how = "filename"
                if parsed:
                    date, title = parsed
                else:
                    date = stamp_date(path, year)
                    if not date:
                        unparsed.append(name)
                        continue
                    title, how = stem, "file stamp within folder year"
                key = (date, normalize(stem))
                size = os.path.getsize(path)
                if key in found and found[key][0] >= size:
                    twins.append(name)
                    continue
                if key in found:
                    twins.append(os.path.basename(found[key][1]))
                found[key] = (size, path, title, how)

    db = sqlite3.connect(DB)
    existing = {(r[0], (r[1] or "").lower()) for r in db.execute(
        "SELECT preach_date, title FROM Services "
        "WHERE notes LIKE '[Sharon Key%'")}
    added = skipped = failed = 0
    for key in sorted(found):
        date = key[0]
        size, path, title, how = found[key]
        if (date, title.lower()) in existing:
            skipped += 1
            continue
        try:
            text = docx_text(path)
        except Exception as e:
            failed += 1
            print(f"{date}: could not read {os.path.basename(path)} — {e}")
            continue
        dating = "" if how == "filename" else f"; dated by {how}"
        notes = ("[Sharon Key's sermon notes — written record; "
                 f"source file: {os.path.relpath(path, ROOT)}{dating}]\n\n"
                 + text)
        db.execute(
            "INSERT INTO Services (preach_date, title, notes) VALUES (?,?,?)",
            (date, title, notes))
        print(f"{date}: added \"{title}\" ({how})")
        added += 1
    db.commit()
    print(f"\nadded {added} services · twins skipped {len(twins)} · "
          f"already present {skipped} · unreadable {failed} · "
          f"unparsed names {len(unparsed)}")
    for n in twins:
        print("  twin:", n)
    for n in unparsed:
        print("  unparsed:", n)


if __name__ == "__main__":
    main()
