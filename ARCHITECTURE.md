# Architecture Overview

## High-level flow

```
CLI args
  │
  ▼
main.py ──► Runner
  │
  ├──► Executor (browser session + navigation)
  │       │
  │       └── page_source (HTML string)
  │
  ├──► Parser (HTML → ColumnData)
  │
  └──► IO Handler (ColumnData → CSV)
```

## Layer responsibilities

### `executor/`
Owns all Selenium interactions. No business logic lives here — only browser primitives.

### `parser/`
Pure transformation layer. Receives an HTML string, returns structured data. No I/O, no Selenium.

### `io_handler/`
Owns all file system writes.

### `runner/`
Orchestrator. Calls the three layers above in the correct order. Contains pagination logic and error handling.

### `utils/`
Shared infrastructure with no layer affiliation.

## Data types

```python
StrOrNull = str | Literal["null"]
DataList = List[StrOrNull]

ColumnData:
    title: DataList
    type: DataList
    address: DataList
    rating: DataList
```
