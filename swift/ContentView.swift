//
//  ContentView.swift
//  Saba Remember
//
//  Stage 1:
//  Record -> Stop -> Transcribe -> approve and save to mymemory.db.
//  No raw JSON capture storage is used.
//

import SwiftUI
#if canImport(UIKit)
import UIKit
#else
import AppKit
#endif
import AVFoundation

struct ContentView: View {

    @StateObject private var recorder = SpeechRecorder()

    private let store = MemoryStore()
    private let synthesizer = AVSpeechSynthesizer()

    @State private var entries: [MemoryEntry] = []
    @State private var pastedText: String = ""
    @State private var statusMessage: String = ""
    @State private var pendingSource: String = "text"
    @State private var pendingAudioFileName: String?
    @State private var showSavedBanner = false
    @State private var lastSavedContent: String?
    @State private var autoStopWorkItem: DispatchWorkItem?

    @AppStorage("SabaRememberWindowWidth") private var savedWindowWidth: Double = 760
    @State private var showLastFivePicker = false

    private var preferredWindowWidth: Double { max(savedWindowWidth, 520) }

    // The window is a fixed-height bar: title bar + button strip + status line.
    // Width is remembered and resizable; height is pinned.
    private var barHeight: Double { 122 + Double(titleBarClearance) }

    // On the Mac the window's title bar (close/minimize buttons + "Saba Remember")
    // sits on top of the content, so the button row needs room below it.
    // On iPad/iPhone there is no title bar and no extra space is added.
    private var titleBarClearance: CGFloat {
        #if targetEnvironment(macCatalyst)
        return 38
        #elseif canImport(UIKit)
        return ProcessInfo.processInfo.isiOSAppOnMac ? 38 : 0
        #else
        return 0
        #endif
    }
    @State private var lastFiveSelection = 0

    private var recentFiveEntries: [MemoryEntry] {
        Array(entries.prefix(5))
    }

    var body: some View {
        ZStack(alignment: .top) {
            Color(red: 0.88, green: 0.75, blue: 0.89)
                .ignoresSafeArea()

            VStack(spacing: 8) {
                HStack(spacing: 10) {
                    recordButton
                    actionButton(title: "Last 5", icon: "list.bullet.clipboard", action: openLastFivePicker, shortcut: "l")
                    actionButton(title: "Copy", icon: "doc.on.doc", action: copyCaptured, shortcut: "c")
                    actionButton(title: "Paste", icon: "arrow.up.doc", action: pasteFromClipboard, shortcut: "v")
                    actionButton(title: "Clear", icon: "xmark.circle", action: clearText, shortcut: "x")
                    Spacer(minLength: 0)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 6)
                .padding(.horizontal, 8)
                .background(.ultraThinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 16))
                .frame(minWidth: 520, minHeight: 86)
                .padding(.bottom, 8)

                if !statusMessage.isEmpty {
                    Text(statusMessage)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .padding(.horizontal, 12)
                        .padding(.bottom, 4)
                }

            }
            .padding(.horizontal, 10)
            .padding(.top, titleBarClearance)
        }
        .frame(minWidth: 520, minHeight: barHeight, maxHeight: barHeight)
        .background(WindowSizeAccessor(initialSize: CGSize(width: preferredWindowWidth, height: barHeight)) { size in
            savedWindowWidth = size.width
        })
        .sheet(isPresented: $showLastFivePicker) {
            lastFiveChooser
        }
        .onAppear {
            refreshEntries()
            recorder.refreshAvailableInputs()
        }
    }

    private var lastFiveChooser: some View {
        VStack(spacing: 14) {
            Text("Last 5")
                .font(.headline.bold())

            if recentFiveEntries.isEmpty {
                Text("Nothing saved yet")
                    .foregroundStyle(.secondary)
                    .padding(.vertical, 20)
            } else {
                VStack(spacing: 8) {
                    ForEach(Array(recentFiveEntries.enumerated()), id: \.element.id) { index, entry in
                        Button {
                            applySelectedEntry(entry)
                        } label: {
                            HStack(alignment: .top, spacing: 8) {
                                Text("\(index + 1)")
                                    .font(.caption.bold())
                                    .foregroundStyle(index == lastFiveSelection ? .white : .secondary)
                                    .frame(width: 20)
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(entry.timestamp)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                    Text(entry.content)
                                        .font(.subheadline)
                                        .lineLimit(2)
                                        .multilineTextAlignment(.leading)
                                }
                                Spacer()
                            }
                            .padding(10)
                            .background(index == lastFiveSelection ? Color.blue.opacity(0.9) : Color(.secondarySystemBackground))
                            .foregroundStyle(index == lastFiveSelection ? .white : .primary)
                            .clipShape(RoundedRectangle(cornerRadius: 10))
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 4)
            }

            Text("Use ↑ ↓ and Return")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding()
        .frame(minWidth: 320, maxHeight: 320)
        .onAppear {
            lastFiveSelection = 0
        }
    }

    private func actionButton(title: String, icon: String, action: @escaping () -> Void, shortcut: String) -> some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.title2)
                .frame(width: 42, height: 42)
        }
        .buttonStyle(.bordered)
        .keyboardShortcut(KeyEquivalent(Character(shortcut)), modifiers: .command)
        .accessibilityLabel(title)
    }

    private var recordButton: some View {
        Button(action: recorder.isRecording ? stopRecording : startRecording) {
            ZStack {
                Circle()
                    .fill(Color(.systemGray4))
                    .frame(width: 42, height: 42)

                if recorder.isRecording {
                    BlinkingRecordingDot()
                } else {
                    Image(systemName: "mic.fill")
                        .font(.title2)
                        .foregroundColor(.primary)
                }
            }
        }
        .buttonStyle(.plain)
        .keyboardShortcut(KeyEquivalent("r"), modifiers: .command)
        .accessibilityLabel(recorder.isRecording ? "Stop recording" : "Start recording")
    }

    private func startRecording() {
        recorder.requestPermissions { granted in
            if granted {
                statusMessage = "Recording..."
                recorder.startRecording()
                scheduleAutoStop()
            } else {
                statusMessage = "Microphone and Speech access are required."
            }
        }
    }

    private func scheduleAutoStop() {
        cancelAutoStop()
        let workItem = DispatchWorkItem { [self] in
            stopRecording()
        }
        autoStopWorkItem = workItem
        DispatchQueue.main.asyncAfter(deadline: .now() + 60, execute: workItem)
    }

    private func cancelAutoStop() {
        autoStopWorkItem?.cancel()
        autoStopWorkItem = nil
    }

    private func copyCaptured() {
        let text = pastedText.trimmingCharacters(
            in: .whitespacesAndNewlines
        )
        guard !text.isEmpty else { return }

        copyToClipboard(text)
        statusMessage = "Captured text copied. It is ready to paste."
    }

    private func copyToClipboard(_ text: String) {
        #if canImport(UIKit)
        UIPasteboard.general.string = text
        #elseif canImport(AppKit)
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(text, forType: .string)
        #endif
    }

    private func saveCapturedText(_ text: String, source: String, audioPath: String?, auto: Bool = false) {
        if text == lastSavedContent {
            if !auto {
                statusMessage = "This text is already saved."
            }
            return
        }

        let didSave = store.save(
            content: text,
            source: source,
            audioPath: audioPath
        )

        guard didSave else {
            statusMessage = "Save to mymemory.db failed."
            return
        }

        lastSavedContent = text
        refreshEntries()

        withAnimation {
            showSavedBanner = true
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) {
            withAnimation {
                showSavedBanner = false
            }
        }

        statusMessage = auto
            ? "Automatically saved last statement to mymemory.db."
            : "Approved text is now in mymemory.db."
    }

    private func pasteFromClipboard() {
        let text = (UIPasteboard.general.string ?? "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        pastedText = text
        pendingSource = "text"
        pendingAudioFileName = nil

        guard !text.isEmpty else {
            statusMessage = "Clipboard is empty."
            return
        }

        saveCapturedText(text, source: "text", audioPath: nil, auto: true)
        statusMessage = "Pasted and saved to mymemory.db."
    }

    private func clearText() {
        pastedText = ""
        pendingSource = "text"
        pendingAudioFileName = nil
        statusMessage = "Screen cleared. The pending text is gone." 
    }

    private func stopRecording() {
        cancelAutoStop()
        if recorder.isRecording {
            statusMessage = ""
            recorder.stopRecording { text, audioFileName in
                let cleaned = text.trimmingCharacters(in: .whitespacesAndNewlines)
                guard !cleaned.isEmpty else {
                    statusMessage = recorder.lastError ?? "Didn't catch that — try again."
                    return
                }

                pastedText = cleaned
                pendingSource = "voice"
                pendingAudioFileName = audioFileName
                copyToClipboard(cleaned)
                saveCapturedText(cleaned, source: "voice", audioPath: audioFileName, auto: true)
                statusMessage = "Voice copied — ready to be pasted ⌘V."
            }
        }
    }

    private func openLastFivePicker() {
        refreshEntries()
        showLastFivePicker = true
    }

    private func applySelectedEntry(_ entry: MemoryEntry) {
        pastedText = entry.content
        pendingSource = "text"
        pendingAudioFileName = nil
        statusMessage = "Loaded: \(entry.content)"
        showLastFivePicker = false
    }

    private func playLatest() {
        guard let latest = store.fetchLatest() else {
            statusMessage = "Nothing has been approved yet."
            return
        }

        statusMessage =
            "Last approved (\(latest.timestamp)): \(latest.content)"

        let utterance = AVSpeechUtterance(string: latest.content)
        utterance.rate = 0.45
        synthesizer.speak(utterance)
    }

    private func refreshEntries() {
        entries = store.fetchRecent()
    }
}

private struct BlinkingRecordingDot: View {
    @State private var dimmed = false

    var body: some View {
        Circle()
            .fill(Color.red)
            .frame(width: 18, height: 18)
            .opacity(dimmed ? 0.15 : 1.0)
            .onAppear {
                withAnimation(.easeInOut(duration: 0.6).repeatForever(autoreverses: true)) {
                    dimmed = true
                }
            }
    }
}

private struct WindowSizeAccessor: View {
    let initialSize: CGSize
    let onChange: (CGSize) -> Void

    var body: some View {
        WindowSizeAccessorBridge(initialSize: initialSize, onChange: onChange)
            .frame(width: 0, height: 0)
    }
}

private struct WindowSizeAccessorBridge: View {
    let initialSize: CGSize
    let onChange: (CGSize) -> Void

    var body: some View {
        #if canImport(UIKit)
        UIKitWindowSizeAccessor(initialSize: initialSize, onChange: onChange)
        #else
        AppKitWindowSizeAccessor(initialSize: initialSize, onChange: onChange)
        #endif
    }
}

#if canImport(UIKit)
private struct UIKitWindowSizeAccessor: UIViewControllerRepresentable {
    let initialSize: CGSize
    let onChange: (CGSize) -> Void

    func makeUIViewController(context: Context) -> UIViewController {
        let controller = UIViewController()
        controller.view.isHidden = true
        return controller
    }

    func updateUIViewController(_ uiViewController: UIViewController, context: Context) {
        DispatchQueue.main.async {
            guard let window = uiViewController.view.window else { return }

            // Pin the window height to the bar; only the width can be resized.
            if let restrictions = window.windowScene?.sizeRestrictions {
                restrictions.minimumSize = CGSize(width: 520, height: initialSize.height)
                restrictions.maximumSize = CGSize(width: 4000, height: initialSize.height)
            }

            if !context.coordinator.didSetInitialSize {
                context.coordinator.didSetInitialSize = true
                var frame = window.frame
                frame.size = initialSize
                if let scene = uiViewController.view.window?.windowScene {
                    scene.title = scene.title // keep scene alive
                }
                window.rootViewController?.view.window?.frame = frame
            }

            let newSize = window.bounds.size
            if newSize != context.coordinator.lastReportedSize {
                context.coordinator.lastReportedSize = newSize
                onChange(newSize)
            }
        }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    class Coordinator: NSObject {
        var lastReportedSize: CGSize = .zero
        var didSetInitialSize = false
    }
}
#else
private struct AppKitWindowSizeAccessor: NSViewControllerRepresentable {
    let initialSize: CGSize
    let onChange: (CGSize) -> Void

    func makeNSViewController(context: Context) -> NSViewController {
        let controller = NSViewController()
        controller.view = NSView(frame: .zero)
        controller.view.isHidden = true
        return controller
    }

    func updateNSViewController(_ nsViewController: NSViewController, context: Context) {
        DispatchQueue.main.async {
            guard let window = nsViewController.view.window else { return }

            // Pin the window height to the bar; only the width can be resized.
            window.contentMinSize = NSSize(width: 520, height: initialSize.height)
            window.contentMaxSize = NSSize(width: 4000, height: initialSize.height)

            if !context.coordinator.didSetInitialSize {
                context.coordinator.didSetInitialSize = true
                window.setContentSize(initialSize)
            }

            let newSize = window.contentLayoutRect.size
            if newSize != context.coordinator.lastReportedSize {
                context.coordinator.lastReportedSize = newSize
                onChange(newSize)
            }
        }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    class Coordinator: NSObject {
        var lastReportedSize: CGSize = .zero
        var didSetInitialSize = false
    }
}
#endif

extension Collection {
    subscript(safe index: Index) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}

#Preview {
    ContentView()
}
