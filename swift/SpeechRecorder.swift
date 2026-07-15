//
//  SpeechRecorder.swift
//  Saba Remember
//
//  Writes as you speak: the microphone feeds the speech recognizer LIVE
//  while the very same audio is written to an .m4a evidence file. The
//  text accumulates during the recording, so if recognition hiccups
//  midway, everything heard up to that moment is still delivered and
//  saved — never nothing.
//  Requires two Info.plist keys (see the setup guide):
//    NSMicrophoneUsageDescription
//    NSSpeechRecognitionUsageDescription
//

import Foundation
import AVFoundation
import Speech

@MainActor
final class SpeechRecorder: NSObject, ObservableObject {

    @Published var isRecording = false
    @Published var isTranscribing = false
    @Published var lastError: String?

    #if !targetEnvironment(macCatalyst)
    /// All microphones currently available (built-in, AirPods/Bluetooth,
    /// wired headset mic, external USB/Lightning mic, etc.).
    /// Not available on Mac: Apple doesn't expose this port-list API under
    /// Mac Catalyst, since Mac audio input is chosen system-wide instead
    /// (System Settings > Sound > Input) rather than per-app.
    @Published var availableInputs: [AVAudioSessionPortDescription] = []
    #endif
    /// Which one is currently selected for recording (iPad/iPhone only).
    @Published var selectedInputUID: String?

    private let audioEngine = AVAudioEngine()
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private var audioFile: AVAudioFile?
    private var currentFileName: String?
    /// Everything the recognizer has heard so far — grows while you speak.
    private var liveText = ""
    private var finishCompletion: ((String, String?) -> Void)?
    private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private let selectedInputDefaultsKey = "SabaRemember.selectedMicUID"

    /// Folder inside the app's Documents where recordings are kept,
    /// so every entry's original audio is preserved (the "evidence layer").
    private var audioFolder: URL {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let folder = docs.appendingPathComponent("Audio", isDirectory: true)
        if !FileManager.default.fileExists(atPath: folder.path) {
            try? FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        }
        return folder
    }

    // MARK: - Permissions

    func requestPermissions(completion: @escaping (Bool) -> Void) {
        // Using the AVAudioSession-based permission call (rather than the
        // newer AVAudioApplication one) so this same code works reliably
        // on iPhone, iPad, AND Mac (via Mac Catalyst).
        SFSpeechRecognizer.requestAuthorization { speechStatus in
            AVAudioSession.sharedInstance().requestRecordPermission { micGranted in
                DispatchQueue.main.async {
                    self.refreshAvailableInputs()
                    completion(speechStatus == .authorized && micGranted)
                }
            }
        }
    }

    // MARK: - Microphone selection
    //
    // The port-list APIs used here (AVAudioSessionPortDescription and
    // friends) aren't available on Mac, even via Mac Catalyst — Apple only
    // built them for iPhone/iPad. On Mac, which mic gets used is controlled
    // by macOS itself (System Settings > Sound > Input), so there's simply
    // nothing for this app to do there. The #if below compiles a real
    // picker on iPhone/iPad and a harmless no-op version on Mac.

    #if !targetEnvironment(macCatalyst)

    /// Call this any time you want the mic list to reflect what's currently
    /// plugged in / connected (e.g. when opening the mic picker, or when
    /// headphones get plugged in or unplugged).
    func refreshAvailableInputs() {
        let session = AVAudioSession.sharedInstance()
        // Session needs to be active at least once for availableInputs to
        // reliably include Bluetooth/external mics, not just Built-In.
        try? session.setCategory(.record, mode: .measurement, options: .allowBluetooth)
        try? session.setActive(true)

        availableInputs = session.availableInputs ?? []

        // Restore the last choice if it's still connected, otherwise fall
        // back to whatever the system currently prefers.
        if let savedUID = UserDefaults.standard.string(forKey: selectedInputDefaultsKey),
           let match = availableInputs.first(where: { $0.uid == savedUID }) {
            selectInput(match)
        } else {
            selectedInputUID = session.preferredInput?.uid
        }
    }

    /// Switch to a specific microphone (built-in, AirPods, wired headset,
    /// external USB/Lightning mic, etc.) and remember the choice.
    func selectInput(_ port: AVAudioSessionPortDescription) {
        do {
            try AVAudioSession.sharedInstance().setPreferredInput(port)
            selectedInputUID = port.uid
            UserDefaults.standard.set(port.uid, forKey: selectedInputDefaultsKey)
        } catch {
            lastError = "Couldn't switch microphone: \(error.localizedDescription)"
        }
    }

    /// Friendly name for the currently selected mic, for display in the UI.
    var selectedInputName: String {
        availableInputs.first(where: { $0.uid == selectedInputUID })?.portName ?? "Default Microphone"
    }

    #else

    /// On Mac there's no per-app mic list to refresh — nothing to do.
    func refreshAvailableInputs() {
        try? AVAudioSession.sharedInstance().setCategory(.record, mode: .measurement)
        try? AVAudioSession.sharedInstance().setActive(true)
    }

    /// On Mac, always the system's current default input.
    var selectedInputName: String { "your Mac's system default microphone" }

    #endif

    // MARK: - Recording (write-as-you-speak)

    func startRecording() {
        let session = AVAudioSession.sharedInstance()
        do {
            #if targetEnvironment(macCatalyst)
            try session.setCategory(.record, mode: .measurement)
            #else
            try session.setCategory(.record, mode: .measurement, options: .allowBluetooth)
            #endif
            try session.setActive(true)
            #if !targetEnvironment(macCatalyst)
            // Re-apply the chosen mic in case the system reset it when the
            // session was reconfigured. (Mac has no per-app mic list, so
            // this step is iPhone/iPad only.)
            if let uid = selectedInputUID,
               let port = session.availableInputs?.first(where: { $0.uid == uid }) {
                try? session.setPreferredInput(port)
            }
            #endif
        } catch {
            lastError = "Audio session error: \(error.localizedDescription)"
            return
        }

        guard let recognizer = speechRecognizer, recognizer.isAvailable else {
            lastError = "Speech recognizer unavailable right now."
            return
        }

        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd_HHmmss"
        let fileName = "\(formatter.string(from: Date())).m4a"
        currentFileName = fileName
        let fileURL = audioFolder.appendingPathComponent(fileName)

        let request = SFSpeechAudioBufferRecognitionRequest()
        request.shouldReportPartialResults = true
        // Prefer on-device recognition when the device supports it —
        // keeps things working without needing a network connection.
        if recognizer.supportsOnDeviceRecognition {
            request.requiresOnDeviceRecognition = true
        }
        recognitionRequest = request
        liveText = ""

        let inputNode = audioEngine.inputNode
        let format = inputNode.outputFormat(forBus: 0)

        // The evidence file keeps the mic's own sample rate and channel
        // count — whatever the tap delivers is exactly what gets written.
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: format.sampleRate,
            AVNumberOfChannelsKey: Int(format.channelCount),
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
        do {
            audioFile = try AVAudioFile(forWriting: fileURL, settings: settings)
        } catch {
            lastError = "Could not open the recording file: \(error.localizedDescription)"
            return
        }

        // One stream of sound, two destinations: the evidence file and
        // the recognizer. (The tap runs on the audio thread, so it only
        // touches the two locals captured here.)
        let file = audioFile
        inputNode.removeTap(onBus: 0)
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in
            try? file?.write(from: buffer)
            request.append(buffer)
        }

        recognitionTask = recognizer.recognitionTask(with: request) { [weak self] result, error in
            DispatchQueue.main.async {
                guard let self = self else { return }
                if let result = result {
                    self.liveText = result.bestTranscription.formattedString
                    if result.isFinal { self.finishDelivery() }
                }
                if error != nil {
                    // The point of write-as-you-speak: a hiccup delivers
                    // everything heard so far instead of nothing.
                    self.finishDelivery()
                }
            }
        }

        do {
            audioEngine.prepare()
            try audioEngine.start()
            isRecording = true
            lastError = nil
        } catch {
            lastError = "Could not start recording: \(error.localizedDescription)"
            inputNode.removeTap(onBus: 0)
            recognitionTask?.cancel()
            recognitionTask = nil
            recognitionRequest = nil
            audioFile = nil
        }
    }

    /// Stops recording and returns the accumulated text plus the audio
    /// filename (relative to the Audio folder) via the completion handler.
    func stopRecording(completion: @escaping (String, String?) -> Void) {
        guard isRecording else {
            completion("", nil)
            return
        }
        isRecording = false
        isTranscribing = true
        finishCompletion = completion

        audioEngine.inputNode.removeTap(onBus: 0)
        audioEngine.stop()
        audioFile = nil                      // closes the evidence file
        recognitionRequest?.endAudio()       // recognizer wraps up

        // If the recognizer neither finalizes nor errors within a few
        // seconds, deliver what has been heard rather than keep waiting.
        DispatchQueue.main.asyncAfter(deadline: .now() + 8) { [weak self] in
            self?.finishDelivery()
        }
    }

    /// Hands the accumulated text to whoever asked for it. Safe to call
    /// more than once — only the first call after a stop delivers.
    private func finishDelivery() {
        guard let completion = finishCompletion else { return }
        finishCompletion = nil
        recognitionTask?.cancel()
        recognitionTask = nil
        recognitionRequest = nil
        isTranscribing = false
        try? AVAudioSession.sharedInstance().setActive(false)
        completion(liveText.trimmingCharacters(in: .whitespacesAndNewlines),
                   currentFileName)
    }
}
