# PRINCIPLE — Provenance, Not Unanimity

**Recovered 2026-07-28 from screenshots of a ChatGPT session ("Project Context
Confirmation") that ran out of minutes before it could be saved.**

Transcribed by Claude from two screen captures supplied by Saba. Speaker
attribution preserved exactly, per the principle the passage itself describes.

---

## SABA'S WORDS — verbatim

> "Or if Robert or Ted or Suzette or 20 other people give you the voice, and I say
> by you, give the AI their voice, it should be treated as original content. Not
> the original of the sermon, but the original of the questions or the pursuit."

**This is the ruling.** Everything below is ChatGPT responding to it.

---

## CHATGPT'S RESPONSE — as recorded on screen

> "Yes. I think that's an important distinction, and I'd record it as a
> foundational principle of the system."

**The sentence it proposed for the design record:**

> **"The archive should preserve provenance, not enforce unanimity."**

> "In other words, the system's responsibility is to preserve what was said and
> make clear who is speaking at every layer. Interpretation remains open to
> examination, comparison, and discussion rather than being collapsed into a
> single authoritative voice."

**The elaboration, given under the heading "As your scribe":**

> **"Every participant's contribution becomes an original witness to their own
> journey."**
>
> "The sermon remains the original historical source.
>
> But when Robert asks a question, that question becomes the original record of
> Robert's inquiry.
>
> When Ted reflects on what he heard, that reflection becomes the original record
> of Ted's understanding at that moment.
>
> When Suzette tells her story, her voice becomes the original witness to her
> testimony."

**On the AI's role:**

> "Then the AI's role changes.
>
> The AI is not the author.
>
> The AI is the steward.
>
> It preserves:
> - the original sermon,
> - the original voice,
> - the original question,
> - the original response,
>
> and then produces interpretations that are clearly identified as
> interpretations."

**On what this yields:**

> "That means twenty people can encounter the same sermon and leave twenty
> different trails of inquiry. None of those trails overwrite the sermon, and none
> overwrite each other. They become part of the living history of how people
> engaged with the evidence."

> "I think this is a profound shift in the architecture. Up to now we've talked
> about preserving a historical archive. What you're describing is preserving
> **the history of engagement** with that archive."

> "So, years later, someone might ask:
>
> *'How did people wrestle with this teaching?'*
>
> And the system could answer:"

**⚠ The screenshot is cut off at that point. What the system could answer was not
captured. That sentence is lost unless it survives in the ChatGPT session.**

---

# WHAT THIS CHANGES IN THE EVIDENCE SYSTEM

Recorded by Claude, 2026-07-28. Marked as engineering assessment, not as Saba's
word or ChatGPT's.

## It widens the raw conversational layer

The architecture drafted tonight assumed **two** participants: Saba and an AI.
This principle says the layer must hold **many** — Robert, Ted, Suzette, and
anyone else who engages the record.

The schema already survives this without migration:

```sql
Participants (kind, name, vendor, person_id)   -- kind: human | model | tool
SegmentParticipants (segment_id, participant_id)
```

`person_id` already points at the people book. **A participant in a conversation
and a person in the archive become the same person.** Robert asking a question in
2026 and Robert Morey singing in 1987 resolve to one row.

**No schema change required. The design intent must be recorded so a future
implementer does not narrow it back to two.**

## It creates a second class of original

The completeness spec defines evidence as *what the vendor wrote to the JSONL*.
This principle says a participant's question is **original evidence of that
participant's inquiry** — not derived, not a summary, not an interpretation.

Consequence for the spec: `speech_class` needs a distinction between

- `human-utterance` — Saba, the keeper
- `participant-inquiry` — another person's question, reflection, or testimony

Both are raw. Neither is derived. **Currently the spec has only one human class,
and would flatten Robert's question into Saba's.**

## It sharpens what a summary may never do

Existing rule: *summaries are never evidence; every summary cites its segments.*

This principle adds: **a summary may never merge two participants' trails into
one voice.** Twenty trails stay twenty. The system reports who wrestled and how —
it does not average them into a consensus.

That is what "not enforce unanimity" means in code: no collapse across
participants, ever, at any layer.

## It answers a question the architecture had left open

D5 asked whether the archive is Claude-only or multi-vendor. This principle
answers a larger version of it: **the archive is not about which AI. It is about
which person.** The vendor is a detail of capture. The participant is the point.

---

# STATUS

- **Saba's ruling: recorded.**
- **ChatGPT's formulation: recorded, attributed, not merged with Saba's words.**
- **One sentence lost** to the screenshot cut — flagged above, not reconstructed.
- **Nothing implemented.** This is a design record awaiting Phase 1.

*Recovered because a conversation ran out of minutes. Which is the argument for
the system this principle describes.*
