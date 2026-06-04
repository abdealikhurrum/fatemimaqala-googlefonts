# qa/test_detector_reuse.py
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from collision_check import CollisionDetector, DEFAULT_FONT

WORDS = [
    "بِسْمِ اللّٰهِ الرَّحْمٰنِ الرَّحِيْمِ",
    "شَمْلَكُمْ مُلْكَهُ كُلَّمَا",
    "بِنُحُوسِها",
    "إِيَّاكَ أَنْعَمْتَ",
]

def test_many_calls_one_process_no_crash():
    # Before the fix this segfaults (exit 139) on the 2nd call because
    # collisions() builds a fresh freetype.Face each time.
    d = CollisionDetector(DEFAULT_FONT)
    counts = [len(d.collisions(w, same_cluster_marks=True)) for w in WORDS]
    assert len(counts) == len(WORDS)

def test_single_call_result_stable():
    d = CollisionDetector(DEFAULT_FONT)
    # mulkahu has a known kaaf-above collision in the shipped font
    hits = d.collisions("مُلْكَهُ", same_cluster_marks=True)
    assert any(b in ("uniFEDC", "uniFEDB") for _, b, _ in hits)
