# epub-info-extract

CLI and interactive terminal tool to inspect EPUB metadata, calculate reading/word statistics, summarize chapters, and split books into balanced chunks designed for **Google NotebookLM** (500k word source limit) and **Gemini**.

## Features

- **Interactive TUI:** Searchable fuzzy picker to select EPUBs from `epubs/` and run actions with arrow keys.
- **Accurate Statistics:** Total chapters, total words (whitespace standard), average words/chapter, median length, and min/max range.
- **Gemini / NotebookLM Chunker:** Auto-splits EPUBs into balanced chunks (default: <=400k words) saved to `output/{book_name}/{book_name}_1.txt`, `{book_name}_2.txt`, etc.
- **Chapter Summaries:** Instant local extractive preview (head + tail) or optional Gemini AI summary.
- **Dedicated Storage:** Place all `.epub` files inside `epubs/` (git-ignored).

## Requirements

- Python >= 3.10
- [uv](https://github.com/astral-sh/uv)

## Setup

Drop your `.epub` files into the `epubs/` directory, then install dependencies:

```bash
uv sync
```

## Usage

### 1. Interactive Terminal UI (Recommended)

Run without arguments to launch the interactive menu with fuzzy search:

```bash
uv run main.py
```

Features in TUI:
- Select and search any `.epub` in `epubs/`
- View statistics
- Split for NotebookLM with custom or auto parts
- Search chapters by name or number to read summaries / excerpts

---

### 2. Direct CLI Commands

#### View Statistics

```bash
uv run main.py info "epubs/Fantasy Simulator.epub"

# Or list all chapters with word counts:
uv run main.py info "epubs/Fantasy Simulator.epub" --list
```

Output:
```text
File:           Fantasy Simulator.epub
Total Chapters: 853
Total Words:    1,622,865 words (~1.62M)
Average:        ~1,903 words/chapter
Median:         1,875 words
Word Range:     597 – 3,285 words
```

#### Split for NotebookLM / Gemini

Splits into `output/{nameepub}/{nameepub}_1.txt`, `{nameepub}_2.txt`, etc.:

```bash
# Auto-split to fit under 400k words per part:
uv run main.py split "epubs/Fantasy Simulator.epub"

# Or split into exact number of balanced parts:
uv run main.py split "epubs/Fantasy Simulator.epub" --parts 5
```

Output:
```text
Splitting 'epubs/Fantasy Simulator.epub' (1,622,865 words) into 5 part(s)...
  Fantasy_Simulator_1.txt:  324,486 words (Chapters    1 -  208)
  Fantasy_Simulator_2.txt:  324,411 words (Chapters  209 -  391)
  Fantasy_Simulator_3.txt:  325,029 words (Chapters  392 -  536)
  Fantasy_Simulator_4.txt:  325,091 words (Chapters  537 -  699)
  Fantasy_Simulator_5.txt:  323,848 words (Chapters  700 -  853)

Saved 5 files in 'output\Fantasy_Simulator/'
```

#### Chapter Summary & Excerpt

Fast local extractive excerpt (no API key needed):
```bash
uv run main.py summary "epubs/Fantasy Simulator.epub" --chapter 1
```

AI summary via Gemini API (requires `GEMINI_API_KEY` in environment):
```bash
set GEMINI_API_KEY=your_key_here
uv run main.py summary "epubs/Fantasy Simulator.epub" --chapter 1 --ai
```

## Running Tests

```bash
uv run python test_core.py
```

## License

MIT
