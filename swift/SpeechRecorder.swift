//
//  SpeechRecorder.swift
//  Saba Remember
//
//  Records audio to a file, then transcribes it to text on-device.
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

    /// All microphones currently available (built-in, AirPods/Bluetooth,
    /// wired headset mic, external USB/Lightning mic, etc.).
    @Published var availableInputs: [AVAudioSessionPortDescription] = []
    /// Which one is currently selected for recording.
    @Published var selectedInputUID: String?

    private var audioRecorder: AVAudioRecorder?
    private var currentFileName: String?
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
        SFSpeechRecognizer.requestAuthorization { speechStatus in
            AVAudioApplication.requestRecordPermission { micGranted in
                DispatchQueue.main.async {
                    self.refreshAvailableInputs()
                    completion(speechStatus == .authorized && micGranted)
                }
            }
        }
    }

    // MARK: - Microphone selection

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

    // MARK: - Recording

    func startRecording() {
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.record, mode: .measurement, options: .allowBluetooth)
            try session.setActive(true)
            // Re-apply the chosen mic in case the system reset it when the
            // session was reconfigured.
            if let uid = selectedInputUID,
               let port = session.availableInputs?.first(where: { $0.uid == uid }) {
                try? session.setPreferredInput(port)
            }
        } catch {
            lastError = "Audio session error: \(error.localizedDescription)"
            return
        }

        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd_HHmmss"
        let fileName = "\(formatter.string(from: Date())).m4a"
        currentFileName = fileName
        let fileURL = audioFolder.appendingPathComponent(fileName)

        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]

        do {
            audioRecorder = try AVAudioRecorder(url: fileURL, settings: settings)
            audioRecorder?.record()
            isRecording = true
            lastError = nil
        } catch {
            lastError = "Could not start recording: \(error.localizedDescription)"
        }
    }

    /// Stops recording and returns the transcribed text plus the audio filename
    /// (relative to the Audio folder) via the completion handler.
    func stopRecording(completion: @escaping (String, String?) -> Void) {
        audioRecorder?.stop()
        isRecording = false
        try? AVAudioSession.sharedInstance().setActive(false)

        guard let fileName = currentFileName else {
            completion("", nil)
            return
        }
        let fileURL = audioFolder.appendingPathComponent(fileName)
        transcribe(fileURL: fileURL) { [weak self] text in
            completion(text, fileName)
            self?.isTranscribing = false
        }
    }

    // MARK: - Transcription

    private func transcribe(fileURL: URL, completion: @escaping (String) -> Void) {
        guard let recognizer = speechRecognizer, recognizer.isAvailable else {
            lastError = "Speech recognizer unavailable right now."
            completion("")
            return
        }

        isTranscribing = true
        let request = SFSpeechURLRecognitionRequest(url: fileURL)

        // Prefer on-device recognition when the device supports it —
        // keeps things working without needing a network connection.
        if recognizer.supportsOnDeviceRecognition {
            request.requiresOnDeviceRecognition = true
        }

        recognizer.recognitionTask(with: request) { [weak self] result, error in
            if let error = error {
                DispatchQueue.main.async {
                    self?.lastError = "Transcription error: \(error.localizedDescription)"
                    completion("")
                }
                return
            }
            guard let result = result, result.isFinal else { return }
            DispatchQueue.main.async {
                completion(result.bestTranscription.formattedString)
            }
        }
    }
}
