# epub-info-extract

CLI utility to extract metadata, calculate reading/word statistics, summarize chapters, and split EPUB books into balanced text chunks designed for **Google NotebookLM** (500k word source limit) and **Gemini**.

## Features

- **Accurate Statistics:** Total chapters, total words (whitespace standard), average words/chapter, median chapter length, min/max word range.
- **Balanced Chunker:** Splits large EPUBs into balanced text chunks under a target word count (default: 400k words) or into explicit $N$ parts.
- **Chapter Summaries:** Quick extractive excerpt (head + tail paragraphs) or optional AI-generated summary using Gemini API.
- **Zero Heavy Frameworks:** Pure Python stdlib CLI + `ebooklib` & `beautifulsoup4`.

## Requirements

- Python >= 3.10
- [uv](https://github.com/astral-sh/uv) (recommended)

## Quick Start

Install dependencies with `uv`:

```bash
uv sync
```

### 1. View EPUB Statistics

```bash
uv run main.py info "Fantasy Simulator.epub"
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

List all chapters with individual word counts:
```bash
uv run main.py info "Fantasy Simulator.epub" --list
```

### 2. Split for NotebookLM / Gemini

NotebookLM enforces a 500,000-word limit per source file. By default, `split` chunks books into parts under 400,000 words:

```bash
# Auto-split into parts fitting 400k words each
uv run main.py split "Fantasy Simulator.epub"

# Or split into exact number of balanced parts
uv run main.py split "Fantasy Simulator.epub" --parts 5 --output-dir output
```

Output:
```text
Splitting 'Fantasy Simulator.epub' (1,622,865 words) into 5 part(s)...
  Fantasy_Simulator_001.txt:  324,486 words (Chapters    1 -  208)
  Fantasy_Simulator_002.txt:  324,411 words (Chapters  209 -  391)
  Fantasy_Simulator_003.txt:  325,029 words (Chapters  392 -  536)
  Fantasy_Simulator_004.txt:  325,091 words (Chapters  537 -  699)
  Fantasy_Simulator_005.txt:  323,848 words (Chapters  700 -  853)

Saved 5 files to 'output/'
```

### 3. Chapter Summaries & Excerpts

Fast local extractive excerpt (no API key needed):
```bash
uv run main.py summary "Fantasy Simulator.epub" --chapter 1
```

AI-powered summary via Gemini API (requires `GEMINI_API_KEY` environment variable):
```bash
set GEMINI_API_KEY=your_key_here
uv run main.py summary "Fantasy Simulator.epub" --chapter 1 --ai
```

## Running Tests

Run the built-in self-checks:

```bash
uv run python test_core.py
```

## License

MIT
