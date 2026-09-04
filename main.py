#!/usr/bin/env python3
"""EPUB extractor and chunker for NotebookLM / Gemini."""

import argparse
import json
import math
import os
import re
import statistics
import sys
import urllib.error
import urllib.request
from bs4 import BeautifulSoup
from ebooklib import epub

# Ensure clean UTF-8 output across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_chapters(epub_path: str) -> list[dict]:
    """Read EPUB spine items and extract clean text and word counts."""
    if not os.path.exists(epub_path):
        raise FileNotFoundError(f"EPUB file not found: {epub_path}")

    book = epub.read_epub(epub_path)

    # Map href to title from TOC
    toc_map = {}

    def parse_toc(entries):
        for entry in entries:
            if isinstance(entry, (list, tuple)):
                parse_toc(entry)
            elif hasattr(entry, "href") and hasattr(entry, "title"):
                clean_href = entry.href.split("#")[0]
                toc_map[clean_href] = entry.title

    parse_toc(book.toc)

    chapters = []
    for item_id, _ in book.spine:
        item = book.get_item_with_id(item_id)
        if not item:
            continue

        raw = item.get_content()
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()

        text = soup.get_text()
        clean_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        if not clean_text:
            continue

        words = len(clean_text.split())
        name = item.get_name()

        # Chapter title resolution: TOC -> heading tag -> fallback
        title = toc_map.get(name)
        if not title:
            h = soup.find(["h1", "h2", "title"])
            title = h.get_text().strip() if h else f"Chapter {len(chapters) + 1}"

        chapters.append(
            {
                "index": len(chapters) + 1,
                "name": name,
                "title": title,
                "text": clean_text,
                "words": words,
            }
        )

    return chapters


def calculate_stats(chapters: list[dict]) -> dict:
    """Calculate word count statistics for chapters."""
    counts = [c["words"] for c in chapters]
    total_words = sum(counts)
    count = len(chapters)
    return {
        "chapters": count,
        "total_words": total_words,
        "avg_words": total_words / count if count else 0,
        "median_words": statistics.median(counts) if counts else 0,
        "min_words": min(counts) if counts else 0,
        "max_words": max(counts) if counts else 0,
    }


def cmd_info(args: argparse.Namespace) -> None:
    chapters = load_chapters(args.epub)
    stats = calculate_stats(chapters)
    total = stats["total_words"]
    million_str = f" (~{total / 1_000_000:.2f}M)" if total >= 100_000 else ""

    print(f"File:           {os.path.basename(args.epub)}")
    print(f"Total Chapters: {stats['chapters']:,}")
    print(f"Total Words:    {stats['total_words']:,} words{million_str}")
    print(f"Average:        ~{stats['avg_words']:,.0f} words/chapter")
    print(f"Median:         {stats['median_words']:,.0f} words")
    print(f"Word Range:     {stats['min_words']:,} – {stats['max_words']:,} words")

    if args.list:
        print("\nChapters:")
        for c in chapters:
            print(f"  [{c['index']:>4}] {c['title']:<45} ({c['words']:,} words)")


def split_chapters(chapters: list[dict], target_parts: int) -> list[list[dict]]:
    """Partition chapters into balanced chunks."""
    if target_parts <= 1:
        return [chapters]

    total_words = sum(c["words"] for c in chapters)
    target_per_part = total_words / target_parts

    cumulative = []
    running = 0
    for c in chapters:
        running += c["words"]
        cumulative.append(running)

    split_indices = [0]
    for part in range(1, target_parts):
        target = part * target_per_part
        best_cut = min(
            range(split_indices[-1] + 1, len(chapters)),
            key=lambda i: abs(cumulative[i - 1] - target),
        )
        split_indices.append(best_cut)
    split_indices.append(len(chapters))

    parts = []
    for p in range(target_parts):
        parts.append(chapters[split_indices[p] : split_indices[p + 1]])
    return parts


def cmd_split(args: argparse.Namespace) -> None:
    chapters = load_chapters(args.epub)
    total_words = sum(c["words"] for c in chapters)
    base_name = os.path.splitext(os.path.basename(args.epub))[0].replace(" ", "_")

    # Gemini Notebook / NotebookLM max source limit = 500,000 words.
    if args.parts:
        parts_count = args.parts
    else:
        max_words = args.max_words
        parts_count = max(1, math.ceil(total_words / max_words))

    print(f"Splitting '{args.epub}' ({total_words:,} words) into {parts_count} part(s)...")
    parts = split_chapters(chapters, parts_count)

    os.makedirs(args.output_dir, exist_ok=True)
    out_files = []

    for idx, part in enumerate(parts, 1):
        start_ch = part[0]["index"]
        end_ch = part[-1]["index"]
        part_words = sum(c["words"] for c in part)
        filename = f"{base_name}_{idx:03d}.txt"
        filepath = os.path.join(args.output_dir, filename)

        header = (
            f"{base_name} - Part {idx} of {parts_count}\n"
            f"Chapters {start_ch} to {end_ch} (of {len(chapters)})\n"
            f"Total Words: {part_words:,}\n"
            f"{'=' * 60}\n\n"
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header)
            for i, c in enumerate(part):
                if i > 0:
                    f.write("\n\n---\n\n")
                f.write(f"### {c['title']}\n\n{c['text']}")

        out_files.append((filename, part_words, start_ch, end_ch))
        print(f"  {filename}: {part_words:>8,} words (Chapters {start_ch:>4} - {end_ch:>4})")

    print(f"\nSaved {len(out_files)} files to '{args.output_dir}/'")


# ponytail: extractive excerpt by default; upgrades to Gemini API via urllib when GEMINI_API_KEY set + --ai passed.
def summarize_chapter(chapter: dict, use_ai: bool = False) -> str:
    if use_ai:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return (
                "[Notice] GEMINI_API_KEY environment variable not found. Showing extractive summary:\n\n"
                + extractive_summary(chapter)
            )
        return ai_summary(chapter, api_key)
    return extractive_summary(chapter)


def extractive_summary(chapter: dict, max_paras: int = 2) -> str:
    paragraphs = [p.strip() for p in chapter["text"].split("\n") if p.strip()]
    if not paragraphs:
        return "[Empty chapter]"
    if len(paragraphs) <= max_paras * 2:
        body = "\n\n".join(paragraphs)
    else:
        head = "\n\n".join(paragraphs[:max_paras])
        tail = "\n\n".join(paragraphs[-max_paras:])
        body = f"{head}\n\n[... {len(paragraphs) - (max_paras * 2)} paragraphs omitted ...]\n\n{tail}"

    return (
        f"Chapter {chapter['index']}: {chapter['title']}\n"
        f"Length: {chapter['words']:,} words | {len(paragraphs)} paragraphs\n\n"
        f"{body}"
    )


def ai_summary(chapter: dict, api_key: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = (
        f"Provide a concise summary (3-5 bullet points) of Chapter {chapter['index']}: {chapter['title']}.\n"
        f"Focus on key plot events and character actions.\n\n"
        f"Text:\n{chapter['text'][:15000]}"
    )
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return f"AI Summary - Chapter {chapter['index']} ({chapter['title']}):\n\n" + parts[0]["text"]
            return "[Gemini returned empty response]"
    except urllib.error.URLError as e:
        return f"[Gemini API request failed: {e}]. Falling back to extractive:\n\n" + extractive_summary(chapter)


def cmd_summary(args: argparse.Namespace) -> None:
    chapters = load_chapters(args.epub)
    idx = args.chapter - 1
    if idx < 0 or idx >= len(chapters):
        print(f"Error: Chapter {args.chapter} out of range (1 to {len(chapters)})", file=sys.stderr)
        sys.exit(1)

    ch = chapters[idx]
    print(summarize_chapter(ch, use_ai=args.ai))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract statistics, split for Gemini/NotebookLM, or summarize EPUB chapters."
    )
    subparsers = parser.add_subparsers(dest="command")

    # info
    p_info = subparsers.add_parser("info", help="Display EPUB statistics and word counts")
    p_info.add_argument("epub", help="Path to EPUB file")
    p_info.add_argument("--list", action="store_true", help="List all chapters and word counts")

    # split
    p_split = subparsers.add_parser("split", help="Split EPUB into NotebookLM/Gemini chunk files")
    p_split.add_argument("epub", help="Path to EPUB file")
    p_split.add_argument(
        "--max-words",
        type=int,
        default=400_000,
        help="Max words per chunk (default 400,000, fitting NotebookLM 500k limit)",
    )
    p_split.add_argument("--parts", type=int, default=None, help="Explicit number of parts to split into")
    p_split.add_argument("--output-dir", default="output", help="Directory for split text files (default: output)")

    # summary
    p_sum = subparsers.add_parser("summary", help="Show extractive or AI summary of a chapter")
    p_sum.add_argument("epub", help="Path to EPUB file")
    p_sum.add_argument("--chapter", type=int, required=True, help="Chapter number (1-based index)")
    p_sum.add_argument("--ai", action="store_true", help="Use Gemini API for summary (requires GEMINI_API_KEY)")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "info":
        cmd_info(args)
    elif args.command == "split":
        cmd_split(args)
    elif args.command == "summary":
        cmd_summary(args)


if __name__ == "__main__":
    main()
