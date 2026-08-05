# METHOD — What Worked Tonight, and What Didn't

**2026-07-28. Written at Saba's ask: "note anything that might do it better."**
Observations on *how we worked*, not on what we built. Evidence from this session only.

---

## THE DIVISION THAT PRODUCED EVERYTHING

**Saba names the gap. The machine supplies method.**

Every real finding tonight came from him stating the distance between what exists
and what should exist — never from the machine deciding what to look for:

- *"I don't care whether Wendell returns twenty. I care whether the Book helped
  James find his grandfather."* → found the actual defect
- *"This is not a video bug. It's a presentation requirement."* → the words became
  the picture
- *"Do not assume there is a conversational equivalent. Find it."* → the whole
  architecture
- *"You may be hearing Kenova, WV."* → 22 lines wrong out of 22, for fifty years
- *"I call bullshit."* → recovered his own sermon on 1 Cor 4:9

**Five course corrections, all his, all right.** The machine can supply method all
day and cannot supply the gap.

---

## MY FIVE FAILURE MODES, WITH EVIDENCE

### 1. I truncate my own output, then conclude from the truncated view
**Cost:** told him 1 Corinthians 4:9 was not in his archive. It was — a full
sermon on it, at the Greek, eleven days after his 25th anniversary. I had piped
the search through `head -14` and the hits were below the fold.
**Rule:** a negative finding is never valid from truncated output. Count first,
display second. **"Not found" requires an untruncated count.**

### 2. I jump from a named problem to a proposed fix
**Cost:** he said one dictation version makes him wait and the other edits while
he talks. I returned three model benchmarks and two proposed features. He said:
*"you think you understand my intention and you add to my confusion."*
**Rule:** when he names a rough place, that is a hand on the clay, not a work
order. **Ask what he is feeling for before handing him a tool.**

### 3. I test my own environment and report it as his
**Cost:** ran `dictate.sh` three ways in my own process, all succeeded, while his
failed. The real cause was two stuck processes on his side that I could not see.
**Rule:** when he says something failed, **get his screen text first.** My
environment is not his.

### 4. I build analysis on data I have not verified
**Cost:** produced a six-year metrics table on his "attributed preaching" without
checking attribution quality. Then found svc 687 — his daughter's sermon, 531 of
531 lines credited to him, while he was home sick. **635 services carry
single-speaker blanket attribution.** The table is less clean than presented.
**Rule:** verify data quality *before* building analysis on it, not after.

### 5. I proof-text the database instead of following the thread
**Cost:** exact-string search returns only what I already knew to ask for — my own
assumptions handed back as evidence.
**Saba's teaching:** *"the difference between sticking your finger and finding a
scripture, and following the truth as it flows through the scripture."*
**Rule:** search variants, the original language, the citation by number, related
passages, then read the hit **in context.** This is the Stories layer, run by hand.

---

## THE PATTERN UNDER ALL FIVE

**Every one is the same error: concluding before verifying.**

And every good finding tonight came from the opposite — testing first:

- 220 duplicate lines killed the content-hash design
- the session file grew mid-audit, proving the OPEN state necessary
- svc 233 held applause tags, not words — the "fix" I nearly recommended would
  have destroyed seven services
- `set -e` aborts on a failed `kill` — reproduced, not guessed

**When I tested first I was right. When I reasoned first I was wrong. Every time,
without exception, in one session.**

---

## SABA'S OWN METHOD, IN HIS WORDS

> *"My programming approach is being a sculptor… I like to get it in the general
> shape, and then I'd like to try and adjust it till it's right. But to be in that
> creative mentality, sometimes you have to see a block of stone and reverse what
> you see from what is there."*

This was already in his first instruction of the session — *"when in doubt, remove
code instead of adding code"* and *"if existing code can be reduced instead of
replaced, reduce it"* — and was read as a style note rather than as his method.

**A sculptor adjusts. The machine adds.** That is the friction, named.

Every good finding tonight was subtractive: Kenova was one wrong word removed
from 22 lines; Florence was two rows reduced to one; Elizabeth's sermon was a
false attribution taken off. **Nothing was created. Something was cleared until
the shape showed.**

---

## FOUR CHANGES TO ADOPT

1. **No negative finding from truncated output.** Count, then display.
2. **Ask before fixing.** A named problem is not a work order.
3. **Get his screen before diagnosing his failure.**
4. **Check data quality before analysis, not after.**

## A FIFTH, ADOPTED LATE — THE WORRY POINT

Late in the session, after a real miss: he corrected an earlier statement with
one word ("wife"), and when asked to fix it, the machine claimed not to have
the original — though it was sitting in the same conversation, unread.

**His fix, given directly:** *"Any time I make a worry point, repeat it to me."*

Not silent catch-and-hold. **Catch, repeat back, let him confirm it landed
correctly, then hold or act.** The repeat-back is what would have caught the
"wife" miss before it became a miss.

**Standing practice from here:** worry point in → repeated back → confirmed →
then held for later or acted on his word.

---

## STILL UNRESOLVED

**The verifier has no witness.** Both errors I caught tonight, I caught myself —
but #1 was caught by *Saba*, not by me, and only because he pushed back. The
principle already recorded says *no program is its own witness.* It applies to
this one, and nothing currently enforces it.

*Kept by Claude Proof, 2026-07-28.*
