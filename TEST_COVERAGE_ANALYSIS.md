# Test Coverage Analysis: Saba Code Repository

## Executive Summary

**Current Test Coverage: 0%**

The repository contains approximately **6,951 lines of Python code** and **~200 lines of Swift code** across multiple projects, but **no test files exist** in the codebase. This analysis identifies critical areas where tests should be implemented to improve reliability and maintainability.

---

## Codebase Overview

### Python Projects
- **Archive Viewer** (~42 modules): API server, database management, text processing
- **Remember Module** (~5 modules): Memory management API, GUI application
- **Swift Application**: iOS/macOS memory app with database and audio recording

### Current Structure
```
├── archive-viewer/          (43 Python files)
├── Python/remember/         (5 Python files)
├── swift/                   (6 Swift files)
└── html/                    (web assets)
```

---

## Critical Areas Needing Test Coverage

### 1. **HIGH PRIORITY: Database Operations**

#### `archive-viewer/connector.py` (200+ lines)
- **What it does**: Read-only HTTP API over Sermons.db
- **Critical functions**:
  - `connect_ro()` - Opens database in read-only mode
  - `check_schema()` - Validates database schema
  - `has_parts_table()` - Checks for optional table
  - Search endpoint handlers

**Why tests matter**: Database connection failures could crash the API. Schema validation prevents runtime errors.

**Proposed tests**:
```python
def test_connect_ro_with_valid_database()
def test_connect_ro_with_missing_database()
def test_connect_ro_with_disconnected_drive()
def test_check_schema_with_valid_database()
def test_check_schema_missing_required_columns()
def test_check_schema_missing_required_table()
```

#### `Python/remember/memory_connector.py` (300+ lines)
- **What it does**: Read-only HTTP API over mymemory.db
- **Critical functions**:
  - `connect_ro()` - Opens memory database
  - `fetch_minutes()` - Retrieves all memory entries
  - `search_minutes(query, limit)` - Searches memories by keywords
  - `minutes_on_day(date_text)` - Filters by date
  - `clamp_limit()` - Validates numeric input

**Why tests matter**: Input validation is critical for API security. Searching logic must correctly score and sort results.

**Proposed tests**:
```python
def test_fetch_minutes_returns_list()
def test_fetch_minutes_ignores_empty_content()
def test_search_minutes_empty_query_returns_empty()
def test_search_minutes_single_word_match()
def test_search_minutes_multiple_words_scoring()
def test_search_minutes_respects_limit()
def test_clamp_limit_negative_input()
def test_clamp_limit_exceeds_max()
def test_minutes_on_day_invalid_date_format()
def test_minutes_on_day_valid_date()
```

#### `archive-viewer/db_vault.py`
- **What it does**: Backs up databases to alternate drives
- **Critical functions**:
  - Database backup logic with integrity checking
  - Path validation and directory creation

**Why tests matter**: Data loss risk if backup logic fails silently.

**Proposed tests**:
```python
def test_backup_creates_destination_directory()
def test_backup_preserves_database_integrity()
def test_backup_handles_missing_source()
def test_backup_generates_timestamped_filename()
```

---

### 2. **HIGH PRIORITY: Text Processing & Search**

#### `archive-viewer/spell_correct.py` (97 lines)
- **What it does**: Spell correction using Optimal String Alignment (OSA) distance
- **Critical functions**:
  - `_osa_leq(a, b, maxd)` - Calculates edit distance with transpositions
  - `correct_word(word)` - Finds nearest match in vocabulary
  - `correct_query(text)` - Corrects all words in a phrase

**Why tests matter**: The OSA algorithm is complex. Regressions in spelling correction would degrade search quality.

**Proposed tests**:
```python
def test_osa_leq_identical_strings_distance_zero()
def test_osa_leq_single_insertion()
def test_osa_leq_single_deletion()
def test_osa_leq_single_substitution()
def test_osa_leq_transposition_counts_as_one()
def test_osa_leq_exceeds_max_distance_returns_false()
def test_correct_word_already_correct()
def test_correct_word_typo_edit_distance_1()
def test_correct_word_typo_edit_distance_2()
def test_correct_word_unknown_short_word()
def test_correct_query_preserves_case()
def test_correct_query_tracks_changes()
def test_correct_query_mixed_correct_and_incorrect()
```

#### `archive-viewer/meanings_search.py`
- **What it does**: Semantic search using embeddings
- **Critical functions**:
  - `embed_one(text)` - Calls Ollama API to embed text
  - Main search loop with ranking

**Why tests matter**: Embedding API calls can fail. Ranking logic affects search result quality.

**Proposed tests**:
```python
def test_embed_one_with_valid_text()
def test_embed_one_handles_ollama_timeout()
def test_embed_one_returns_normalized_embedding()
def test_search_ranking_by_relevance_score()
```

---

### 3. **MEDIUM PRIORITY: Data Import & Processing**

#### Import modules (15+ files like `cf_import.py`, `wog_import.py`, `xwalls_import.py`)
- **What they do**: Convert external data formats into the archive database
- **Risk**: Silent data corruption or loss during import

**Example tests**:
```python
def test_import_validates_source_file_exists()
def test_import_parses_expected_columns()
def test_import_handles_malformed_rows()
def test_import_generates_audit_log()
def test_import_rollback_on_schema_error()
```

#### Batch processing modules (`batch_classify_mentions.py`, `clock_repair_batch.py`)
- **Risk**: Incomplete processing, data consistency errors

**Example tests**:
```python
def test_batch_process_completes_all_items()
def test_batch_process_reports_failures()
def test_batch_process_idempotent_rerun()
```

---

### 4. **MEDIUM PRIORITY: File I/O & Path Operations**

#### Modules with file operations:
- `status.py` - Reads process info and database file status
- `load_transcript.py` - Imports transcript files
- `transcript_exporter.py` - Exports transcripts

**Why tests matter**: File not found errors, permission issues, encoding problems.

**Proposed tests**:
```python
def test_file_reader_handles_utf8()
def test_file_reader_handles_macos_line_endings()
def test_file_reader_missing_file_raises_error()
def test_path_operations_handle_unicode_filenames()
def test_export_creates_parent_directories()
```

---

### 5. **MEDIUM PRIORITY: API Input Validation**

#### `Python/remember/memory_connector.py` endpoints:
- `/search` - validates query text
- `/on-day` - validates date format
- `/form-command` - extracts commands from text
- `/ask-local` - handles time-based queries

**Proposed tests**:
```python
def test_api_search_endpoint_empty_query()
def test_api_search_endpoint_sql_injection_attempt()
def test_api_search_endpoint_oversized_limit()
def test_api_date_endpoint_malformed_date()
def test_api_date_endpoint_future_dates()
```

---

### 6. **LOWER PRIORITY: Swift Code**

#### `swift/MemoryStore.swift`
- **What it does**: SQLite database interface for iOS/macOS
- **Critical functions**:
  - `save(content:source:audioPath)` - Writes to database
  - Database initialization

**Proposed tests**:
```swift
func testSaveValidEntry() // verifies row was inserted
func testSaveHandlesEmptyContent()
func testDatabaseInitialization()
func testFetchEntries()
```

---

## Test Infrastructure Recommendations

### Testing Framework
- **Python**: pytest (simple, extensible, works with CI/CD)
- **Swift**: XCTest (built-in to Xcode)

### Project Structure
```
Saba-Code/
├── archive-viewer/
│   ├── *.py
│   └── tests/
│       ├── test_connector.py
│       ├── test_spell_correct.py
│       ├── test_meanings_search.py
│       ├── test_db_vault.py
│       ├── test_imports.py
│       └── conftest.py (fixtures)
├── Python/remember/
│   ├── *.py
│   └── tests/
│       ├── test_memory_connector.py
│       ├── test_remember.py
│       └── conftest.py
└── swift/
    └── SabaRememberTests/
        ├── MemoryStoreTests.swift
        └── SpeechRecorderTests.swift
```

### Test Fixtures & Mocks
1. **In-memory SQLite databases** for testing without real data
2. **Mock HTTP servers** for testing API clients
3. **Temporary directories** for file I/O tests
4. **Fixture files** with known test data (CSVs, transcripts)

### CI/CD Integration
- Run tests on every commit to develop branch
- Report coverage metrics
- Block merges if coverage drops
- Example: GitHub Actions workflow

---

## Priority Implementation Order

### Phase 1 (Highest Impact - 2-3 weeks)
1. **spell_correct.py** - Algorithmic correctness is critical
2. **memory_connector.py search functions** - Core search functionality
3. **Database connectivity** - `connect_ro()`, schema validation
4. **API input validation** - Security and robustness

### Phase 2 (High Value - 2-3 weeks)
1. **Import modules** - Data integrity critical
2. **Batch processing** - Completeness and idempotency
3. **Date/time handling** - Edge cases
4. **File operations** - Encoding and permissions

### Phase 3 (Polish - 1-2 weeks)
1. **Swift tests**
2. **Edge cases and error scenarios**
3. **Integration tests** (if needed)

---

## Estimated Test Coverage Goals

| Phase | Component | Est. Tests | Coverage Goal |
|-------|-----------|-----------|--------------|
| 1 | Core search & API | 40-50 | 80%+ |
| 2 | Data import & processing | 60-80 | 75%+ |
| 3 | UI & Integration | 20-30 | 70%+ |
| **Total** | | **120-160** | **75%+** |

---

## Quick Start: Write Your First Test

```python
# archive-viewer/tests/test_spell_correct.py
import pytest
from spell_correct import correct_word, correct_query

def test_correct_word_fixes_typo():
    assert correct_word("isreal") == "israel"
    assert correct_word("jerusaelm") == "jerusalem"

def test_correct_word_preserves_correct_spelling():
    assert correct_word("israel") == "israel"

def test_correct_query_handles_phrase():
    corrected, changes = correct_query("the God of Isreal")
    assert "israel" in corrected.lower()
    assert len(changes) == 1  # Only "Isreal" was changed
```

**To run**:
```bash
pip install pytest
pytest archive-viewer/tests/test_spell_correct.py -v
```

---

## Benefits of Implementation

✅ **Confidence in changes** - Refactor without fear of breaking functionality  
✅ **Faster debugging** - Tests pinpoint failures immediately  
✅ **Documentation** - Tests show how functions should behave  
✅ **Regression prevention** - Catch bugs before production  
✅ **Easier onboarding** - New contributors understand code through tests  
✅ **Quality metrics** - Track code quality over time  
