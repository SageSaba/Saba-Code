# The Study Version of *A Voice in the Wilderness*

*Designed by Saba, 2026-07-24, in conversation. Scribed, not invented. Nothing here is built yet.*

---

## The shift

It began as a Hebrew edition. Saba changed it mid-thought:

> "I think I want to shift my opinion. This does not need to be a Hebrew version of *A Voice in the Wilderness*. It needs to be a **study version** of *A Voice in the Wilderness*."

Hebrew is not the point. It is one of the tools. So are Spanish, the voices, the letter meanings. The thing itself is an edition a person can **study in**, and the other editions are editions *of* it.

## Why only this house can make it

Anyone can typeset the book. Nobody else can set a line of it beside **the tape where Rev. Helm preached that same thing, in his own voice, with the date on it.**

The study apparatus is not scholarship bought in — it is 3,016,461 lines of the man's own preaching, already in the house, already searchable. That is the whole advantage and it is not copyable.

---

## The parts

### 1. The text, and a voice reading it
Daniel Light's English reading already exists — 26 chapters, in `~/Desktop/AVITW Living Book/`, with a working read-along (chapters listed, text scrolling with the voice, tap to jump). **That page is the seed of this one**, not a new build.

### 2. Boxes that move together
When a language edition is in play, the reading runs in parallel columns, all scrolling with the voice, tap any line in any column to jump the voice there:

- **The language** (e.g. Hebrew — right-to-left inside its own box)
- **Transliteration** — so someone who cannot read the script can still say the words
- **English — the original**

Open: whether the whole page flips for a right-to-left reader, and whether transliteration is permanent or a toggle.

### 3. Touch a word and it pauses
Saba: *"It would be moving too fast… they definitely have to be able to pause it if they wanted to look at what it was spelling."*

**The gesture that means "wait, what is that" is the same gesture that stops the voice.** Touching a word pauses; closing it resumes. No pause button to aim for. This gives two ways of using one page: let it run and it is a reading; touch it and it is a study.

### 4. The word lens — the letters opened
Touch a Hebrew word and it splits into its letters, each carrying its meaning. **The meanings are Saba's own**, already authored, already in the repo: `html/Alphabet/a-z.json` — 22 letters, e.g.

- **Bet** — house, family, in
- **Pe** — mouth, speak, edge
- **Nun** — seed, continue, heir

That is the credo itself (the pierced ear, the mouth, the house, the seed) driving the tool.

**To close before building:** the five final forms — ך ם ן ף ץ — are not in the file and must fold back to kaf, mem, nun, pe, tsade, or the lens goes blank exactly where a word ends.

### 5. The reader chooses the meaning — and builds the reading
Saba's own idea, and the heart of it:

> "I gave several meanings and some of them have more meanings. What if I could let them choose which meaning of the letter it took? And as they went through it, then it summed up and made… what was designed by themselves."
> "I'm trusting their discernment to pick the right choice. And even if they changed it, they'd still be able to see what that reflected."

Each letter offers its two or three senses. The reader walks the word and picks. The page composes what they chose into **their** reading.

Three things this requires:

- **It must recompose instantly.** Change one letter's sense and the whole word turns, at once. If there is a wait, the comparison dies and it becomes a quiz. The turning *is* the teaching.
- **It sits beside the translation, never on top of it.** One box says what the text means; this box says what *you* made. If those blur, the tool stops being trustworthy.
- **It is kept under their name.** Not "the meaning" — *your reading*, saved with who and when, like every claim in this house. Two people build the same word differently and both are worth seeing.

### 6. The archive beside the page
For any line: where Helm taught this, where Saba taught it, where someone testified to it — service, date, second, playable. This is what makes it a study edition rather than a nicer book.

### 7. The rulings
Where the book says something the house has since weighed. Two drafts exist already in `Archive_Suggestions.db` `book_rulings` (the rod, ch. 10; the watchman, ch. 25). "Keep the original alone" and "rule the error" are companions.

---

## The laws it must obey

1. **The original is never altered.** Any edition is a derivative layer, standing where an AI interpretation stands over the raw record.
2. **Exactly one thing on the page is AI-made — the translation — and it wears its label.** Saba, 2026-07-24: *"I don't think I care about the AI translation, as long as it's noted."*
3. **The letter meanings are NOT the machine's.** They are a fixed lookup against Saba's table — same word, same answer, forever. Precomputed, instant, no model involved.
4. **Every voice is named.** The bar says who is reading this chapter — a man, or a machine, plainly.
5. **Every reader's work carries their name and date.**

---

## The editions, and how the book travels

**Each language is read aloud by people that language's community respects — a chapter each.** Not one hired narrator, not a synthesised voice. Nobody carries 26 chapters; the readers become part of the work rather than a service bought — *participation, not accomplishment*.

- **Hebrew** — Rev. Daniel Light **speaks** Hebrew and sings it on tape (a 1990 recording of him singing in Hebrew is in `Archive Viewer/voiceprints/`; also the 1976 "Jerusalem of Gold" services). He can simply be asked. Also possible: Rabbi Moshe of Jerusalem, and other respected Hebrew speakers, a chapter each.
- **Spanish** — the ten surviving churches **John Cook** planted in Mexico (person #56; ~50 planted, at least 10 still active and waiting for this teaching), plus the 22–23 Spanish speakers already listening to EVM. The weightiest chapters to the most seasoned readers. The Spanish text Dr. Roundtree rescued from a dumpster is the source.

**A machine-voiced edition may ship first, labeled, and be replaced chapter by chapter as human readers deliver.** The edition improves in public, and the tiredness of a synthetic voice is itself the invitation: someone hears it and says "I'll read one."

**Start with one chapter.** It proves the sound before twenty-six are asked for, and one finished chapter is something to put in front of Jerry Keller and the EVM board as a thing that exists rather than a thing proposed.

---

## Whose it is

The work belongs in **Pastor Jerry Keller's hands, under Evangel Voice Missions** — a gospel carried by voices, to the mission field. It is already inside EVM's own mandate. Saba's son-in-law **Pastor James Doss** sits on that board.

Saba is asking for no seat. He is handing a brother a work. **Saba sends, never Claude** — no message goes to Jerry, to Daniel, or to any pastor except by Saba's own hand.

---

## What already exists (nothing here needs to be made)

| Piece | Where |
|---|---|
| The English reading, 26 chapters, with a working read-along | `~/Desktop/AVITW Living Book/` |
| The letter table, 22 letters, Saba's own meanings | `html/Alphabet/a-z.json` (identical in `.csv` and `.numbers`) |
| Daniel Light singing in Hebrew, 1990 | `Archive Viewer/voiceprints/` |
| The archive to hang it on | `~/Archive/Sermons.db` — 2,635 services, 3,016,461 lines |
| The rulings shelf | `Archive_Suggestions.db` → `book_rulings` |
| Spanish *Voice in the Wilderness* | Dr. Roundtree's rescued copy |

## Open, awaiting Saba's word

- Which chapter is the test.
- Whether the page flips wholly for a right-to-left reader; whether transliteration is permanent or a toggle.
- Whether the letter audio is spoken, and by whom (the `alphabet-jjp.mp3` in the Alphabet folder is Saba's own practice at learning to say them).
- Whether readers' constructions are private, shared with the house, or public.
