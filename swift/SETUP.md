# Saba Remember — Setup Guide

There's now a ready-made Xcode project sitting right in this folder:
`SabaRemember.xcodeproj`. This skips creating the project by hand — you just
open it and run it. You still need a Mac with Xcode installed (free from the
App Store) — I can't launch Xcode myself, only write the files.

One honest note: I built this project file by hand (not by actually running
Xcode, since that's not possible from here) and checked its structure with a
parser that confirmed all four files and the database library are wired up
correctly. It's a small risk it needs a tiny fix the first time you open it
in real Xcode — if Xcode shows any error on open, tell me exactly what it
says and I'll fix it immediately.

Three steps.


## Step 1 — Open it

In Finder, go to this `swift` folder and double-click `SabaRemember.xcodeproj`.
It should open in Xcode automatically, already showing all four files:
`SabaRememberApp.swift`, `ContentView.swift`, `MemoryStore.swift`,
`SpeechRecorder.swift`.

If it opens with no error and you see those four files on the left, the
project file worked. If you see an error dialog instead, copy its exact text
back to me.


## Step 2 — Pick your Apple ID for signing

1. Click the blue project icon at the very top of the left sidebar.
2. Click "Signing & Capabilities."
3. Under "Team," choose your Apple ID (if none is listed, click
   "Add Account…" and sign in with any Apple ID — free, no paid
   developer account needed just to try this on your own device).

Microphone and Speech permissions are already baked into the project — no
extra typing needed for those.

If you want this to also run on your Mac (not just iPad/iPhone): in this
same screen, under "Supported Destinations," click + and add "Mac."


## Step 3 — Run it

**On iPad or iPhone:**
1. Connect the device to the Mac with a cable (or same Wi-Fi for wireless).
2. At the top of Xcode, click the device dropdown and pick your device.
3. Click the big Play button (▶).
4. First time only: on the device, go to Settings > General > VPN & Device
   Management, and trust your Apple ID / developer certificate.
5. Tap Record, say something, tap Stop — it should appear in the list below
   a few seconds later. Try Paste + Save too.

**On Mac:**
1. Click the device dropdown, choose "My Mac."
2. Click Play. The app opens as a normal Mac window.
3. Allow microphone and speech recognition when macOS asks.
4. If you added "Mac" as a destination: click "Signing & Capabilities,"
   click "+ Capability," and add "Audio Input" — without this the Mac
   version can't use the microphone at all (not needed for iPad/iPhone).


## What happens to what you record

Every entry (voice or pasted text) is saved on the device itself, in a
database file called `mymemory.db`, inside the app's own storage — nothing
leaves the device. Voice entries keep the original audio recording
alongside the text too, so nothing is lost even if a transcription comes
out wrong — same principle as the sermon archive (keep the source, keep
the text, treat AI text as a best-effort guess).

This database is separate from the one already sitting in
`Python/remember/` on your Mac for now. When you're ready, we can talk
about syncing the two (e.g. through iCloud Drive) so entries from your
iPad/iPhone show up in the Mac viewer too.
