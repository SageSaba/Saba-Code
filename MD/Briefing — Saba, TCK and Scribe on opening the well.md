# Briefing — the call with TCK

*For the conversation Saba wants with The Crypt Keeper and Scribe about opening the well
on the Omaha box. Written 2026-07-25, from what Saba decided that night. It is a briefing,
not a plan: **nothing is built and nothing opens without his word.***

---

## 1. What is being opened, and what is not

**Opened:** the well — the archive answerable by **anyone's AI**, not only by ours. Saba's
standing goal: *"no limits on truth, rulings on the tender."* People bring their own
Claude, Grok or ChatGPT; the well returns **evidence with receipts** — service, date,
timestamp — and never speaks for anyone.

**Not opened:** the sealed rows, the private notes, the raw base itself. The books stay
here; the public rung serves answers, not the archive.

## 2. Entry: a key, not a login — Saba's decision

He will not make people log in: *"I want to give them instructions so they can use their
own AI."* So:

- **A key is a person.** Their AI sends it with every request. No password, no account.
- **A key comes from someone who already has one.** The vouch is the credential; the key
  only carries it. That is how James Doss and Jonathan Wagner came in.
- **Saba issues and revokes.** Revocation is instant.
- **Limits ride on the key, not the IP.** A church on one connection is not punished.
- **Keys expire unless used.** A dead key is a door left open.
- **IP is a hint, never an identity** — hashed, short retention, never shown as who someone
  is. (Saba proposed IP limits from his gaming days; they no longer work: carriers, whole
  households and churches share one address, and a VPN defeats it in one tap.)
- **A key is not proof of a human.** Treat it as *who vouched for this*.

## 3. The register — who came, and what they came for

Saba's idea, and it earns its place: **a record of who arrives, how they connect to this
ministry, and what they are looking for.** In this archive that is testimony, not
metadata — *"I am Wink Doss's grandson"* is the same kind of fact as anything on a tape.

It is also the only honest way to learn what people want. The 54 questions now in
`questions` were **almost all asked by Saba himself**, and `asked_by` is empty on every
row — a mirror, not a market.

**Laws it must obey or it becomes surveillance:** voluntary and plainly explained · never
a toll gate (the well answers someone who says nothing) · theirs to see and remove ·
**rated in the exclusion ledger from day one** · never sold, never shared, never used to
contact anyone uninvited.

**Small fix worth doing first:** record *who asked*. Ten people have used this and left no
trace.

## 4. Two front doors — Saba's sharpest design point

> *"People will be looking for their grandparents, but this current generation may just be
> looking for truth."*

- **Who was mine?** — a family finder: names, moments, voices, faces.
- **What is true?** — a subject well: teaching across sixty years and many voices.

Same data, two entrances. And the questions themselves tell you which kind of visitor
arrived: someone who narrows three times is a **diffuser**; someone who asks once and
leaves has their answer. No IP needed for that.

## 5. The gate — nothing opens until this passes

**`~/Archive/exclusions.json`** — the exclusion ledger. Mode 600, git-ignored, and it
**never travels**: not to the Omaha box, not to a gate, not to a helper's laptop, not into
a backup that leaves the house.

- Ratings **5 SEALED** · **4 RESTRICTED** · **3 SENSITIVE** · **2 CAUTION** · **1 OPEN**
- **A gate must ask before serving any row**, and **absence from the ledger is not
  approval — silence is not consent**
- Saba's idea, worth building: **the ledger gets its own API** — one authority, every gate
  must ask it. It returns a verdict only, never the sealed content. It **fails closed**:
  no answer, no service. It logs every question asked, so a mistake is caught before a
  stranger finds it.
- **The pre-flight, Saba's word — *"You can check all sides before we open"*:** the data,
  the code, the network (8765 already listens on the whole LAN), the files, consent for
  recordings of living people, and what would ride along in a backup.

## 6. Questions only TCK can answer

1. What does the box actually run — OS, Docker, what is already on it?
2. How is the address served: bare IP, a domain, a reverse proxy, TLS certificates?
3. **Who else has root**, and how is that access recorded?
4. Backups on his side: what, where, how often, and who can read them?
5. If the box were seized or subpoenaed, what is on it? (Answer should be: answers and
   logs, never the books.)
6. What does he want for running it, and what happens to the box if he steps away?
7. Rate limiting and abuse handling — his tooling or ours?
8. Can the well be taken down instantly by Saba alone, without TCK's help?

## 7. What Scribe brings to the call

The pre-flight audit, the ledger, the key design, and the register schema — as proposals.
**Machine proposes, witness disposes.** Saba decides; TCK builds the room it stands in;
Scribe keeps the record of what was decided, as it is said.

---

*The laws that travel with all of it: keep the original sacred · data sacred · every voice
named · unknowns stay unknown · nothing sent without the keeper's word · and do not finish
the book — leave the game for other people.*
