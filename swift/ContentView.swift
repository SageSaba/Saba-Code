//
//  ContentView.swift
//  Saba Remember
//
//  Big-button, big-text interface designed for easy tapping and reading:
//    1. One large Record button — speak, it transcribes automatically.
//    2. A paste-in text box — paste or type, then Save.
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

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {

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

                // MARK: Paste / type text box
                VStack(alignment: .leading, spacing: 10) {
                    Text("Or paste / type text")
                        .font(.title3).bold()

                    TextEditor(text: $pastedText)
                        .font(.title3)
                        .frame(minHeight: 100)
                        .padding(8)
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
            .onAppear(perform: refreshEntries)
        }
    }

    // MARK: - Actions

    private func toggleRecording() {
        if recorder.isRecording {
            statusMessage = ""
            recorder.stopRecording { text, audioFileName in
                if !text.isEmpty {
                    store.save(content: text, source: "voice", audioPath: audioFileName)
                    statusMessage = "Saved: \(text)"
                    refreshEntries()
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
        }
    }

    private func saveTypedText() {
        let text = pastedText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        store.save(content: text, source: "text", audioPath: nil)
        pastedText = ""
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
