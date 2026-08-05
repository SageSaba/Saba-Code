# Untranscribed Services Inventory — 2026-07-29

**Status:** 384 services in archive catalog with media_path but no RawSegments transcribed

## How This Was Found

**Objective:** Locate October 2000 "In One Accord" meeting (Greenville, 6-service cluster with Joe, Jerry, Brett Barry, Steve & Tiffany Nanny).

**Method:**
1. Searched Services table for org_code='PCCF' (Greenville location)
2. Filtered to 1998-2002 timeframe (Saba's specified range for Rev. Helm nursing home era)
3. Found clusters of services within single months (densest recording periods)
4. Identified October 2000 as 6-service cluster matching description
5. Located "In One Accord" (service ID 2147, date 2000-10-09)

**Finding:** Service is cataloged with title and media_path, but zero RawSegments (untranscribed).

```
Service ID: 2147
Date: 2000-10-09
Title: Rev Loran Helm In One Accord 1 tape
Org: PCCF
Media Path: /Volumes/Data/Video Archive/CF Archive/2019_10_25 PCCF_10_09_2000a_Rev_Loran_Helm_In_One_Accord_1_tape [S1YQ_eTbIlc].webm
Audio Extracted: Yes (in_one_accord.wav, scratchpad)
Transcribed: No (RawSegments count = 0)
```

## Scale of the Problem

**Total untranscribed:** 384 services
- Media files exist and are accessible
- Service metadata is complete (title, date, org, media_path)
- RawSegments layer is empty — no transcript layer built yet

This represents significant work waiting in the queue before subjects layer, stories layer, or any interpretation/ruling layer can be built.

## What's Needed

Transcription work to populate RawSegments for these 384 services. Current blockers encountered 2026-07-29:
- OpenAI Whisper: SSL certificate chain issue (self-signed cert in proxy/firewall)
- macOS native speech-to-text: no command-line API available
- Python speech_recognition: `recognize_apple()` method not available in installed version

## Next Steps

1. Resolve transcription tool (Whisper SSL, alternative tool, or paid API)
2. Prioritize which 384 services to transcribe first (by date? by org? by speaker?)
3. Build pipeline to batch-transcribe and store RawSegments

---

*Logged by Scribe, 2026-07-29*
