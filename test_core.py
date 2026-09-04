"""Self-check for non-trivial logic in main.py without external test frameworks."""

import os
from main import (
    calculate_stats,
    extractive_summary,
    find_epubs,
    slugify,
    split_chapters,
)


def test_slugify():
    assert slugify("Fantasy Simulator.epub") == "Fantasy_Simulator_epub"
    assert slugify("Fantasy Simulator") == "Fantasy_Simulator"
    assert slugify("My--Book! Name") == "My_Book_Name"


def test_find_epubs():
    found = find_epubs()
    assert len(found) >= 1, "Expected to find at least 1 EPUB in test workspace"
    assert any("Fantasy Simulator.epub" in p for p in found)


def test_calculate_stats():
    chapters = [
        {"words": 100},
        {"words": 200},
        {"words": 300},
        {"words": 400},
    ]
    stats = calculate_stats(chapters)
    assert stats["chapters"] == 4, "Chapter count mismatch"
    assert stats["total_words"] == 1000, "Total words mismatch"
    assert stats["avg_words"] == 250, "Average words mismatch"
    assert stats["median_words"] == 250, "Median words mismatch"
    assert stats["min_words"] == 100, "Min words mismatch"
    assert stats["max_words"] == 400, "Max words mismatch"


def test_split_chapters():
    chapters = [
        {"index": i, "words": 100, "title": f"Ch {i}", "text": "content"}
        for i in range(1, 11)
    ]
    # 10 chapters * 100 words = 1000 total words. 2 parts -> 5 chapters each.
    parts = split_chapters(chapters, 2)
    assert len(parts) == 2, f"Expected 2 parts, got {len(parts)}"
    assert sum(c["words"] for c in parts[0]) == 500
    assert sum(c["words"] for c in parts[1]) == 500
    assert parts[0][0]["index"] == 1
    assert parts[1][-1]["index"] == 10

    # Single part edge case
    single = split_chapters(chapters, 1)
    assert len(single) == 1
    assert len(single[0]) == 10


def test_extractive_summary():
    chapter = {
        "index": 1,
        "title": "Prologue",
        "words": 10,
        "text": "P1\n\nP2\n\nP3\n\nP4\n\nP5\n\nP6",
    }
    summary = extractive_summary(chapter, max_paras=2)
    assert "Prologue" in summary
    assert "P1" in summary and "P2" in summary
    assert "P5" in summary and "P6" in summary
    assert "omitted" in summary


if __name__ == "__main__":
    test_slugify()
    test_find_epubs()
    test_calculate_stats()
    test_split_chapters()
    test_extractive_summary()
    print("All core tests passed.")
