# The Sorts and the Questions

*Saba, 2026-07-25: "I did want a database of sorts and questions so I could refer to them
when I built the system." This is that reference, drawn from what already exists — not
invented. The questions are REAL: 54 of them, actually asked of Ask the Archive
(port 8768), with their answers, confidence and receipts still in `questions`.*

---

## I. THE SHAPES PEOPLE ASK IN

Every question so far falls into one of six shapes. A query interface only has to serve
these six.

1. **A person, alone.** *Joe Nance* · *Jerry Keller* · *Taylor Keller*
   → give me this person's moments.
2. **A person on a subject.** *"Show Thomas Young on how to pray"* · *"Show me Jerry Keller on EVM"*
   → intersect a person with a theme.
3. **A yes/no about teaching.** *"Did Thomas teach how to do corporate prayer?"*
   → the honest answer includes NO, with what was found instead.
4. **A subject, alone, then narrowed.** *"5 minute sermons"* → *"...method of Jesus"* → *"...in TRCF"*
   → the narrowing is a conversation, not a new search.
5. **A person and a moment-quality.** *"a song where Elizabeth Doss laughed"*
   → asking for a FEELING inside a moment. Nothing ordinary does this. It is the hardest
   and the most human question in the corpus, and it is the one worth building for.
6. **A named thing.** *"Joe Nance pierced ears"*
   → a specific teaching, already marked.

## II. THE SORTS THAT EXIST TODAY

| sort | count |
|---|---|
| `song` | 819 |
| `sermon` | 522 |
| `testimony` | 9 |
| `prayer` | 3 |
| `exhortation` | 2 |
| `Sermon` | 1 |

**Saba's ruling on sorts (2026-07-24):** log the MINUTES, not the experience. Kinds
**overlap** — a stretch can be song AND prayer, so tagging is multiple, never exclusive.
**Prayer is the ground** under a waiting meeting. Only SONG divides cleanly, because
someone is *called* to sing.

**⚠️ Two things to fix before any toggle is built on these:**
- one stray capitalised `Sermon` (1 row) would fall outside a `kind='sermon'` filter
- **24 rows have a blank kind** — they belong to no sort at all

## III. THE OTHER AXES A TOGGLE NEEDS

- **Collection** — WOG · TRCF · CF Archive · Without Walls · Sukkot 2013 · ChurchRecords
- **Review state** — reviewed vs un-reviewed (Saba's own old book-prep material over-surfaces)
- **Person** — speaker vs merely mentioned; the two are constantly confused
- **Era** — the same man at 30 and at 80 is two different voices ([[layered-identification]])
- **Honour** — where Rev. Helm speaks a FULL name; conferral, not address

## IV. THE LAWS ANY BUILT SYSTEM INHERITS

- The machine **offers a spread** of moments from several speakers; it never blends them
  into one answer and never speaks for anyone.
- **Receipts always** — service, date, timestamp. An answer without them is a rumour.
- **Unknowns stay unknown.** A blank is better than a guess.
- **Nothing serves a row without asking the exclusion ledger first**, and absence from
  that ledger is not approval.
- **Do not finish the book.** Leave the game for other people.

---

## V. THE QUESTION CORPUS — all 54, in the order they were asked

1. How has Elizabeth Doss carried on the message after her father retired
2. How has Elizabeth Doss carried on the message after her father retired
3. Shoe me Jerry keller on EVM
4. Shoe thomas young on how to pray
5. Thomas spoke on corporate prayer and how to do it
6. 5 minute sermons
7. 5 minute sermons method of Jesus
8. 5 minute sermons method of Jesus in TRCF
9. Did Thomas teach how to do corporate prayer?
10. Can you show me a
 song where Elizabeth Doss laughed
11. Joe Nance pierced ears
12. Joe Nance
13. Jerry Keller
14. Taylor Keller
15. james doss
16. james doss — James is the minister AT TRCF?  is there no messages?
17. james doss
18. james doss
19. Thomas Young
20. Barbara Young
21. Donna Goldsmith (Ashmus)
22. Bea Mullins
23. Elsie Parsley
24. Sally davis
25. Lori Lloyd (Wagner)
26. Lori Lloyd (Wagner)
27. Lori Lloyd
28. Lori Perkins
29. Lori Perkins
30. Lori Llyod
31. Lori Lloyd
32. Jonathan Wagner
33. Joe Nance
34. elizabeth Doss sharing
35. elizabeth Doss singing
36. Connie Kilbourne
37. Connie Kilbourne — Sickness is still going on and I am sure if you looked at TRCF you would find more
38. What is the thoughts about Isreal
39. What is the thoughts about Israel
40. What is the thoughts about Israel
41. Jonathan wagner
42. daniel light
43. daniel lightIs it complete. some of the searches are bad
44. Thomas Young in RFOD
45. Thomas Young in RFOD — I am Not Davic Younf He is the Brother of Guy (GI) Young or (Lajeunesse)
46. Thomas Young in RFOD — I am Not Davic Younf He is the Brother of Guy (GI) Young or (Lajeunesse) — Good Jon Daniel and David Jones are twins
47. Thomas Young in RFOD — I am Not Davic Younf He is the Brother of Guy (GI) Young or (Lajeunesse) — Good Jon Daniel and David Jones are twins — Guy Leads singing often IN RFOD meetings
48. Thomas Young in RFOD — I am Not Davic Younf He is the Brother of Guy (GI) Young or (Lajeunesse) — Good Jon Daniel and David Jones are twins — Guy Leads singing often IN RFOD meetings — nd on 2016-10-15 he jokes about a child called "our little david," clarifying "that's liam by the way his name is not david" (2016-10-15 at 1:18:19) — a different, unrelated "David" nickname mix-up, not connected to Guy or Daniel.  The kid is named "LIAM"
49. Joe Nance
50. What did Barbara say about joy?
51. Barbara Young
52. Vicki Neuman
53. Vicki Newman
54. Vicki Newman
