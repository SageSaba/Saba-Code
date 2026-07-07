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

    private var audioRecorder: AVAudioRecorder?
    private var currentFileName: String?
    private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))

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
                    completion(speechStatus == .authorized && micGranted)
                }
            }
        }
    }

    // MARK: - Recording

    func startRecording() {
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.record, mode: .measurement, options: .duckOthers)
            try session.setActive(true)
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
