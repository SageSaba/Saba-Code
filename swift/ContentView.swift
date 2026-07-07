//
//  ContentView.swift
//  Saba Remember
//
//  Big-button, big-text interface designed for easy tapping and reading:
//    1. One large Record button — speak, it transcribes and drops the
//       result into the editable box below so you can fix anything wrong
//       before it's saved.
//    2. That same box also takes pasted or typed text directly.
//    3. A list of everything you've saved, with a Read Aloud button on each.
//

import SwiftUI
import AVFoundation

struct ContentView: View {

    @StateObject private var recorder = SpeechRecorder()
    private let store = MemoryStore()
    private let synthesizer = AVSpeechSynthesizer()

    @State private var entries: [MemoryEntry] = []
    @State private var pastedText: String = ""
    @State private var statusMessage: String = ""
    // Tracks where the text currently in the box came from, so Save can
    // still tag/link it correctly even after you've edited it by hand.
    @State private var pendingSource: String = "text"
    @State private var pendingAudioFileName: String?

    /// The AI chat sites the "Send to…" menu offers. Add more here later by
    /// just adding another (name, urlString) pair.
    private let aiDestinations: [(name: String, urlString: String)] = [
        ("ChatGPT", "https://chatgpt.com"),
        ("Claude", "https://claude.ai"),
        ("Gemini", "https://gemini.google.com"),
        ("Grok", "https://grok.com"),
    ]

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {

                // MARK: Microphone selection
                // On Mac, which mic is used is controlled by macOS itself
                // (System Settings > Sound > Input) — so instead of an
                // in-app switcher that wouldn't really do anything there,
                // just show what's currently being used.
                #if targetEnvironment(macCatalyst)
                HStack {
                    Image(systemName: "mic.fill")
                    Text("Using your Mac's current input device (set in System Settings > Sound)")
                        .lineLimit(2)
                    Spacer()
                }
                .font(.title3)
                .padding()
                .frame(maxWidth: .infinity, minHeight: 54)
                .background(Color(.secondarySystemBackground))
                .cornerRadius(14)
                .padding(.horizontal)
                #else
                Menu {
                    ForEach(recorder.availableInputs, id: \.uid) { port in
                        Button {
                            recorder.selectInput(port)
                        } label: {
                            if port.uid == recorder.selectedInputUID {
                                Label(port.portName, systemImage: "checkmark")
                            } else {
                                Text(port.portName)
                            }
                        }
                    }
                    Button {
                        recorder.refreshAvailableInputs()
                    } label: {
                        Label("Refresh list", systemImage: "arrow.clockwise")
                    }
                } label: {
                    HStack {
                        Image(systemName: "mic.fill")
                        Text("Microphone: \(recorder.selectedInputName)")
                            .lineLimit(1)
                        Spacer()
                        Image(systemName: "chevron.up.chevron.down")
                    }
                    .font(.title3)
                    .padding()
                    .frame(maxWidth: .infinity, minHeight: 54)
                    .background(Color(.secondarySystemBackground))
                    .cornerRadius(14)
                }
                .padding(.horizontal)
                .disabled(recorder.isRecording)
                #endif

                // MARK: Record button
                Button(action: toggleRecording) {
                    VStack(spacing: 8) {
                        Image(systemName: recorder.isRecording ? "stop.circle.fill" : "mic.circle.fill")
                            .font(.system(size: 64))
                        Text(recorder.isRecording ? "Stop" : "Record")
                            .font(.title2).bold()
                    }
                    .frame(maxWidth: .infinity, minHeight: 140)
                    .foregroundColor(.white)
                    .background(recorder.isRecording ? Color.red : Color.blue)
                    .cornerRadius(20)
                }
                .padding(.horizontal)

                if recorder.isTranscribing {
                    ProgressView("Transcribing…")
                        .font(.title3)
                }

                if !statusMessage.isEmpty {
                    Text(statusMessage)
                        .font(.headline)
                        .foregroundColor(.secondary)
                }

                // MARK: Editable review box — shows what was just said or
                // pasted, and lets you fix anything before it's saved.
                VStack(alignment: .leading, spacing: 10) {
                    Text("What was captured (edit if needed)")
                        .font(.title3).bold()

                    TextEditor(text: $pastedText)
                        .font(.title3)
                        .frame(minHeight: 100)
                        .padding(8)
                        .onChange(of: pastedText) { newValue in
                            // If the box gets fully cleared by hand, forget
                            // any leftover voice/audio link so a fresh typed
                            // entry doesn't get mistakenly tagged as voice.
                            if newValue.isEmpty {
                                pendingSource = "text"
                                pendingAudioFileName = nil
                            }
                        }
                        .background(Color(.secondarySystemBackground))
                        .cornerRadius(12)

                    HStack(spacing: 16) {
                        Button(action: pasteFromClipboard) {
                            Label("Paste", systemImage: "doc.on.clipboard")
                                .font(.title3)
                                .frame(maxWidth: .infinity, minHeight: 54)
                        }
                        .buttonStyle(.bordered)

                        Button(action: saveTypedText) {
                            Label("Save", systemImage: "tray.and.arrow.down.fill")
                                .font(.title3)
                                .frame(maxWidth: .infinity, minHeight: 54)
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(pastedText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    }

                    // MARK: Send to an AI chat
                    // Copies the text and opens the chosen site — there's no
                    // free way for an outside app to drop text straight into
                    // any of these chats, so you paste it in yourself once
                    // it opens (Cmd+V, or long-press > Paste).
                    Menu {
                        ForEach(aiDestinations, id: \.name) { destination in
                            Button(destination.name) {
                                sendText(to: destination)
                            }
                        }
                    } label: {
                        Label("Send to…", systemImage: "paperplane.fill")
                            .font(.title3)
                            .frame(maxWidth: .infinity, minHeight: 54)
                    }
                    .buttonStyle(.bordered)
                    .disabled(pastedText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
                .padding(.horizontal)

                // MARK: Entry list
                List(entries) { entry in
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(entry.timestamp)
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                            Text(entry.content)
                                .font(.body)
                                .lineLimit(3)
                        }
                        Spacer()
                        Button(action: { readAloud(entry.content) }) {
                            Image(systemName: "speaker.wave.2.fill")
                                .font(.title2)
                                .frame(width: 54, height: 54)
                        }
                        .buttonStyle(.borderless)
                    }
                    .padding(.vertical, 6)
                }
                .listStyle(.plain)
            }
            .padding(.top)
            .navigationTitle("Saba Remember")
            .onAppear {
                refreshEntries()
                recorder.refreshAvailableInputs()
            }
        }
    }

    // MARK: - Actions

    private func toggleRecording() {
        if recorder.isRecording {
            statusMessage = ""
            recorder.stopRecording { text, audioFileName in
                if !text.isEmpty {
                    // Put it in the editable box instead of saving right
                    // away, so a misheard word can be fixed before it's
                    // committed. The original recording stays linked either way.
                    pastedText = text
                    pendingSource = "voice"
                    pendingAudioFileName = audioFileName
                    statusMessage = "Review below, then tap Save."
                } else {
                    statusMessage = recorder.lastError ?? "Didn't catch that — try again."
                }
            }
        } else {
            recorder.requestPermissions { granted in
                if granted {
                    statusMessage = ""
                    recorder.startRecording()
                } else {
                    statusMessage = "Microphone / Speech access needed — check Settings > Privacy."
                }
            }
        }
    }

    private func pasteFromClipboard() {
        if let clip = UIPasteboard.general.string {
            pastedText = clip
            pendingSource = "text"
            pendingAudioFileName = nil
        }
    }

    /// Copies the current box text and opens the chosen AI's website.
    /// There's no free, official way to hand text straight into ChatGPT,
    /// Claude, Gemini, or Grok from another app — so this gets you as close
    /// as possible: the text is already on your clipboard the moment the
    /// site opens, ready to paste (Cmd+V, or long-press > Paste).
    private func sendText(to destination: (name: String, urlString: String)) {
        let text = pastedText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        UIPasteboard.general.string = text
        if let url = URL(string: destination.urlString) {
            UIApplication.shared.open(url)
        }
        statusMessage = "Copied — paste it into \(destination.name) once it opens."
    }

    private func saveTypedText() {
        let text = pastedText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        store.save(content: text, source: pendingSource, audioPath: pendingAudioFileName)
        pastedText = ""
        pendingSource = "text"
        pendingAudioFileName = nil
        statusMessage = "Saved."
        refreshEntries()
    }

    private func readAloud(_ text: String) {
        let utterance = AVSpeechUtterance(string: text)
        utterance.rate = 0.45
        synthesizer.speak(utterance)
    }

    private func refreshEntries() {
        entries = store.fetchRecent()
    }
}

#Preview {
    ContentView()
}
