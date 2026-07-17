#!/usr/bin/env python3
"""Bring Sharon Key's sermon notes (2011-2014) into Services.

One Services row per dated note file: preach_date by the LAW
(folder year > filename > text — file dates never), title from any
words after the date in the filename, the note's full text into
Services.notes with a source line first. org and sermon_giver stay
EMPTY — no blankets; Saba's word or evidence fills them later.

Twins (two files, one date): the largest file wins, the twin is
logged and skipped. Dates already present in Services are skipped.
Never touches existing rows. Run with the DB backed up first.
"""
import os, re, sqlite3, zipfile, html, datetime

DB = "/Volumes/Data/Video Archive/SQL Files/Sermons.db"
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


def main():
    found = {}     # date -> (size, path, title)
    twins, unparsed = [], []
    for year in YEARS:
        folder = os.path.join(ROOT, year)
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".docx") or name.startswith("~"):
                continue
            path = os.path.join(folder, name)
            parsed = parse_name(name[:-5], year)
            if not parsed:
                unparsed.append(name)
                continue
            date, title = parsed
            size = os.path.getsize(path)
            if date in found and found[date][0] >= size:
                twins.append(name)
                continue
            if date in found:
                twins.append(os.path.basename(found[date][1]))
            found[date] = (size, path, title)

    db = sqlite3.connect(DB)
    existing = {r[0] for r in db.execute("SELECT preach_date FROM Services")}
    added = skipped = failed = 0
    for date in sorted(found):
        size, path, title = found[date]
        if date in existing:
            skipped += 1
            print(f"{date}: a Services row already exists — skipped")
            continue
        try:
            text = docx_text(path)
        except Exception as e:
            failed += 1
            print(f"{date}: could not read {os.path.basename(path)} — {e}")
            continue
        notes = ("[Sharon Key's sermon notes — written record; "
                 f"source file: {os.path.relpath(path, ROOT)}]\n\n" + text)
        db.execute(
            "INSERT INTO Services (preach_date, title, notes) VALUES (?,?,?)",
            (date, title, notes))
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
