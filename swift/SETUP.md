# Saba Remember — Setup Guide

This turns the files in this folder into a real app on your iPad, iPhone,
and Mac. You need a Mac with Xcode installed (free from the App Store) to
do this — I can't build or test the app myself since that requires Xcode,
which only runs on a Mac.

Big picture: five short steps, do them in order.


## Step 1 — Create the project

1. Open Xcode.
2. Choose "Create New Project."
3. Choose "iOS" then "App." Click Next.
4. Product Name: `Saba Remember`
5. Interface: SwiftUI. Language: Swift.
6. Save it anywhere you like (NOT inside this Saba Code folder — pick a
   simple location like your Desktop, a new folder).
7. To also run this on your Mac (not just iPad/iPhone): after creating the
   project, click the blue project icon at the top of the left sidebar,
   click your target under "TARGETS," and in "Supported Destinations"
   click the + and add "Mac." (Older Xcode versions call this
   "Mac (Designed for iPad)" — same idea, just check that box instead.)


## Step 2 — Remove the files Xcode made for you

Xcode auto-creates two files you won't need:
- `Saba_RememberApp.swift`
- `ContentView.swift`

In Xcode's left sidebar, right-click each one and choose "Delete,"
then "Move to Trash."


## Step 3 — Add these four files instead

Drag these four files from this `swift` folder into Xcode's left sidebar
(drop them into the yellow project folder, not above/below it):

- `SabaRememberApp.swift`
- `ContentView.swift`
- `MemoryStore.swift`
- `SpeechRecorder.swift`

A box will pop up — make sure "Copy items if needed" is checked, then
click Finish.

Do NOT add `main.swift` or `SETUP.md` — those aren't part of the app.


## Step 4 — Turn on microphone and speech permissions

1. Click the blue project icon at the very top of the left sidebar.
2. Click the "Info" tab (if you don't see one, click the project name
   under "Targets" first).
3. Add two rows (hover over any row, click the + that appears):
   - Key: `Privacy - Microphone Usage Description`
     Value: `Used to record voice memories.`
   - Key: `Privacy - Speech Recognition Usage Description`
     Value: `Used to turn your voice into text.`
4. If you added the Mac destination in Step 1: click the "Signing &
   Capabilities" tab (next to Info), click "+ Capability," and add
   "Audio Input." Without this, the Mac version can't use the microphone
   at all (this checkbox isn't needed for iPad/iPhone, only Mac).


## Step 5 — Run it on your iPad, iPhone, or Mac

**For iPad or iPhone:**
1. Connect the device to the Mac with a cable (or make sure both are on
   the same Wi-Fi for wireless install).
2. At the top of Xcode, click the device dropdown (it might say
   "iPhone 15" or similar) and pick your device's name instead.
3. Click the big Play button (▶) at the top left.
4. First time only: on the device, go to Settings > General > VPN & Device
   Management, and trust your Apple ID / developer certificate.
5. The app should open. Tap Record, say something, tap Stop — it should
   show up in the list below a few seconds later. Try Paste + Save too.

**For Mac:**
1. At the top of Xcode, click the device dropdown and choose "My Mac."
2. Click the big Play button (▶). The app opens as a regular Mac window.
3. First time, macOS will ask to allow microphone and speech recognition —
   click Allow on both.
4. One difference on Mac: which physical microphone gets used is normally
   controlled by macOS itself (System Settings > Sound > Input), not by
   an app. The in-app microphone picker was built and tested with
   iPad/iPhone in mind — on Mac it may simply follow whatever mic is set
   as the system default rather than switching directly. Recording,
   transcribing, pasting, and read-aloud all work the same either way; if
   the in-app picker doesn't switch mics on Mac when we test it, that's
   the expected reason and we can adjust it together.

That's it — no App Store, no cost (a free Apple ID is enough for
installing on your own device; it just needs re-installing from Xcode
every 7 days unless you have a paid Apple Developer account, which
removes that limit for $99/year — not required to just try it out).


## What happens to what you record

Every entry (voice or pasted text) is saved on the iPad itself, in a
database file called `mymemory.db`, in the app's own storage — nothing
leaves the device. Voice entries also keep the original audio recording
alongside the text, so nothing is lost even if a transcription comes out
wrong — same principle as the sermon archive (keep the source, keep the
text, treat AI text as a best-effort guess).

This iPad database is separate from the `mymemory.db` already sitting in
`Python/remember/` on your Mac for now. When you're ready, we can talk
about syncing the two (e.g. through iCloud Drive) so entries from the
iPad show up in the Mac viewer too.
