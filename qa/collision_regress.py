#!/usr/bin/env python3
"""collision_regress.py — run the detector over fixture words for ONE font and
emit per-class collision counts. Run once per font (the detector segfaults with
>1 freetype.Face per process; isolate by process, not by loop)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from collision_check import CollisionDetector

KAAF = {"uniFEDB", "uniFEDC"}
ABOVE = {"uni064B","uni064C","uni064E","uni064F","uni0651","uni0652","uni0670","uni0653"}
BELOW = {"uni064D","uni0650"}
WAWREH = {"uniFEEE","uni0648","uniFEAE","uniFEAD","uniFEAF","uniFEB0","uni0631.alt","uni0631","uniFE86"}

def classify(mark, neighbor):
    if neighbor in KAAF and mark in ABOVE: return "kaaf_above"
    if mark in BELOW and neighbor in WAWREH: return "belowmark_wawreh"
    return "other"

def run(font, fixture):
    d = CollisionDetector(font)
    words = json.load(open(fixture, encoding="utf-8"))
    out = {}
    for cls, toks in words.items():
        counts = {"kaaf_above": 0, "belowmark_wawreh": 0, "other": 0}
        for tok in toks:
            for ma, ob, _ in d.collisions(tok, same_cluster_marks=True):
                counts[classify(ma, ob)] += 1
        out[cls] = counts
    return out

if __name__ == "__main__":
    font = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "fonts", "FatemiMaqala-Regular.ttf")
    fixture = os.path.join(os.path.dirname(__file__), "regression_words.json")
    print(json.dumps(run(font, fixture), ensure_ascii=False, indent=2))
