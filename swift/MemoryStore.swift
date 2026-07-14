//
//  MemoryStore.swift
//  Saba Remember
//
//  Reads and writes the shared mymemory.db SQLite database.
//  Same file format your Mac-side Remember.py viewer already reads
//  (table: memories, columns: timestamp, content, source, audio_path).
//

import Foundation
import SQLite3

struct MemoryEntry: Identifiable {
    let id: Int
    let timestamp: String
    let content: String
    let source: String       // "voice" or "text"
    let audioPath: String?   // filename in Audio/ folder, or nil
}

final class MemoryStore {

    private var db: OpaquePointer?
    let dbURL: URL

    init() {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        dbURL = docs.appendingPathComponent("mymemory.db")
        openDatabase()
        createTableIfNeeded()
    }

    private func openDatabase() {
        if sqlite3_open(dbURL.path, &db) != SQLITE_OK {
            print("Unable to open database at \(dbURL.path)")
            db = nil
        }
    }

    private func createTableIfNeeded() {
        // Matches the schema already used by the Mac Python viewer,
        // plus the two extra columns (source, audio_path) added for this app.
        let sql = """
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            content TEXT,
            source TEXT DEFAULT 'text',
            audio_path TEXT
        );
        """
        execute(sql)
    }

    @discardableResult
    private func execute(_ sql: String) -> Bool {
        var stmt: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK else {
            print("Prepare failed: \(String(cString: sqlite3_errmsg(db)))")
            return false
        }
        defer { sqlite3_finalize(stmt) }
        guard sqlite3_step(stmt) == SQLITE_DONE else {
            print("Step failed: \(String(cString: sqlite3_errmsg(db)))")
            return false
        }
        return true
    }

    /// Save a new memory entry. `source` is "voice" or "text".
    /// `audioPath` is the filename of the linked audio recording, if any.
    /// Returns true only if the row actually made it into the database —
    /// callers should check this before telling the user it was saved.
    @discardableResult
    func save(content: String, source: String, audioPath: String?) -> Bool {
        let sql = "INSERT INTO memories (timestamp, content, source, audio_path) VALUES (?, ?, ?, ?);"
        var stmt: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK else {
            print("Insert prepare failed: \(String(cString: sqlite3_errmsg(db)))")
            return false
        }
        defer { sqlite3_finalize(stmt) }

        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
        let ts = formatter.string(from: Date())

        sqlite3_bind_text(stmt, 1, ts, -1, SQLITE_TRANSIENT_TYPE)
        sqlite3_bind_text(stmt, 2, content, -1, SQLITE_TRANSIENT_TYPE)
        sqlite3_bind_text(stmt, 3, source, -1, SQLITE_TRANSIENT_TYPE)
        if let audioPath = audioPath {
            sqlite3_bind_text(stmt, 4, audioPath, -1, SQLITE_TRANSIENT_TYPE)
        } else {
            sqlite3_bind_null(stmt, 4)
        }

        guard sqlite3_step(stmt) == SQLITE_DONE else {
            print("Insert failed: \(String(cString: sqlite3_errmsg(db)))")
            return false
        }
        // Confirm the row is really there (not just that SQLite said OK) —
        // belt-and-suspenders so "Saved" is never shown for a phantom write.
        return sqlite3_changes(db) > 0
    }

    /// Fetch the most recent entries, newest first.
    func fetchRecent(limit: Int = 50) -> [MemoryEntry] {
        let sql = "SELECT id, timestamp, content, source, audio_path FROM memories ORDER BY id DESC LIMIT ?;"
        var stmt: OpaquePointer?
        var results: [MemoryEntry] = []
        guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK else { return results }
        defer { sqlite3_finalize(stmt) }

        sqlite3_bind_int(stmt, 1, Int32(limit))

        while sqlite3_step(stmt) == SQLITE_ROW {
            let id = Int(sqlite3_column_int(stmt, 0))
            let ts = sqlite3_column_text(stmt, 1).map { String(cString: $0) } ?? ""
            let content = sqlite3_column_text(stmt, 2).map { String(cString: $0) } ?? ""
            let source = sqlite3_column_text(stmt, 3).map { String(cString: $0) } ?? "text"
            let audioPath = sqlite3_column_text(stmt, 4).map { String(cString: $0) }
            results.append(MemoryEntry(id: id, timestamp: ts, content: content, source: source, audioPath: audioPath))
        }
        return results
    }

    /// The single most recent entry, if any — used for "What did I just say?"
    /// so that button proves a real round-trip to the database, not just
    /// whatever happens to still be sitting in on-screen state.
    func fetchLatest() -> MemoryEntry? {
        fetchRecent(limit: 1).first
    }

    /// Search saved memories by text and/or a date range (inclusive).
    /// Pass an empty query and nil dates to get everything, newest first.
    func search(query: String, startDate: Date?, endDate: Date?, limit: Int = 200) -> [MemoryEntry] {
        var sql = "SELECT id, timestamp, content, source, audio_path FROM memories WHERE 1=1"
        let trimmedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmedQuery.isEmpty { sql += " AND content LIKE ?" }
        if startDate != nil { sql += " AND substr(timestamp,1,10) >= ?" }
        if endDate != nil { sql += " AND substr(timestamp,1,10) <= ?" }
        sql += " ORDER BY id DESC LIMIT ?;"

        var stmt: OpaquePointer?
        var results: [MemoryEntry] = []
        guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK else { return results }
        defer { sqlite3_finalize(stmt) }

        var idx: Int32 = 1
        if !trimmedQuery.isEmpty {
            sqlite3_bind_text(stmt, idx, "%\(trimmedQuery)%", -1, SQLITE_TRANSIENT_TYPE)
            idx += 1
        }
        let dayFormatter = DateFormatter()
        dayFormatter.dateFormat = "yyyy-MM-dd"
        if let startDate = startDate {
            sqlite3_bind_text(stmt, idx, dayFormatter.string(from: startDate), -1, SQLITE_TRANSIENT_TYPE)
            idx += 1
        }
        if let endDate = endDate {
            sqlite3_bind_text(stmt, idx, dayFormatter.string(from: endDate), -1, SQLITE_TRANSIENT_TYPE)
            idx += 1
        }
        sqlite3_bind_int(stmt, idx, Int32(limit))

        while sqlite3_step(stmt) == SQLITE_ROW {
            let id = Int(sqlite3_column_int(stmt, 0))
            let ts = sqlite3_column_text(stmt, 1).map { String(cString: $0) } ?? ""
            let content = sqlite3_column_text(stmt, 2).map { String(cString: $0) } ?? ""
            let source = sqlite3_column_text(stmt, 3).map { String(cString: $0) } ?? "text"
            let audioPath = sqlite3_column_text(stmt, 4).map { String(cString: $0) }
            results.append(MemoryEntry(id: id, timestamp: ts, content: content, source: source, audioPath: audioPath))
        }
        return results
    }
}

// sqlite3_bind_text needs a "transient" destructor constant so SQLite copies
// the string instead of holding a dangling pointer.
private let SQLITE_TRANSIENT_TYPE = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
