# Saba Remember — Setup Guide

This turns the files in this folder into a real app on your iPad.
You need a Mac with Xcode installed (free from the App Store) to do this —
I can't build or test the app myself since that requires Xcode, which only
runs on a Mac.

Big picture: five short steps, do them in order.


## Step 1 — Create the project

1. Open Xcode.
2. Choose "Create New Project."
3. Choose "iOS" then "App." Click Next.
4. Product Name: `Saba Remember`
5. Interface: SwiftUI. Language: Swift.
6. Save it anywhere you like (NOT inside this Saba Code folder — pick a
   simple location like your Desktop, a new folder).


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


## Step 5 — Run it on your iPad

1. Connect your iPad to the Mac with a cable (or make sure both are on
   the same Wi-Fi for wireless install).
2. At the top of Xcode, click the device dropdown (it might say
   "iPhone 15" or similar) and pick your iPad's name instead.
3. Click the big Play button (▶) at the top left.
4. First time only: on the iPad, go to Settings > General > VPN & Device
   Management, and trust your Apple ID / developer certificate.
5. The app should open. Tap Record, say something, tap Stop — it should
   show up in the list below a few seconds later. Try Paste + Save too.

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
