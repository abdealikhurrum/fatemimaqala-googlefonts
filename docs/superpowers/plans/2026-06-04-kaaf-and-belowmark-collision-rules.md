# Kaaf + Below-Mark Collision Rules — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the dominant inter-character diacritic collisions in `FatemiMaqala-Regular` — the medial/initial kaaf arm over a preceding above-mark, and the below-mark (kasra) under a letter followed by a connected waw/reh — by editing the font's OpenType layout plus scripted new mark glyphs, with the pixel detector as the objective oracle.

**Architecture:** All shaping fixes live in `sources/FatemiMaqala-Regular.ufo/features.fea`; new mark/letter variants are added to the UFO *by script* (no manual drawing). Each fix is "move the offender away from the mark," using the mechanism the APCD corpus shows will actually fire: wide-tatweel insertion (connecting bases), kern (non-joining bases), and a re-anchored kasra variant (below-mark). "Only when marked" is achieved by matching the mark in the GSUB backtrack. The test loop is `fontmake` build → pixel detector, isolated one-font-per-process.

**Tech Stack:** Python `.venv` (fontmake, ufo2ft, skia-pathops, defcon, fonttools, uharfbuzz, freetype-py, numpy, pillow); feaLib OpenType; the existing `qa/collision_check.py` detector.

**Spec:** `docs/superpowers/specs/2026-06-04-kaaf-and-belowmark-collision-rules-design.md`

---

## Environment facts (already established — do not re-derive)

- A `.venv` exists at repo root with all build + detector deps installed. Activate with `. .venv/bin/activate` for every step.
- **Build command (≈3.5s):** `fontmake -u sources/FatemiMaqala-Regular.ufo -o ttf --output-path <OUT>.ttf`
  - **Do NOT** use raw `ufo2ft.compileTTF` — its output omits fontmake's filters and segfaults FreeType at 600px.
- **Detector is freetype-py-fragile:** creating more than one `freetype.Face` per process segfaults in `load_glyph`. `qa/collision_check.py:collisions()` currently makes a *new* Face on every call → crashes on the 2nd call. **Task 1 fixes this.** The regression harness runs **one font per process**.
- Feature edits go in `sources/FatemiMaqala-Regular.ufo/features.fea` (the UFO's own file). `sources/features.full.fea` is a separate copy — leave it alone.
- Confirmed glyphs: `uni0640.1` (adv 270, "little" tatweel), `uni0640.3` (adv 890, "wide"); `uniFEDC` (medial kaaf), `uniFEDB` (initial kaaf). `@aboveSingle`/`@belowSingle` markClasses defined at features.fea ~4662–4681.
- feaLib compile re-verify (from REHAB.md): a clean compile is the gate after every feature edit; `fontmake` failing to build = compile error.

---

## File structure

- `qa/collision_check.py` — **modify** (Task 1): create one reusable `freetype.Face` in `__init__`.
- `qa/collision_regress.py` — **create** (Task 2): one-font-per-process regression runner.
- `qa/regression_words.json` — **create** (Task 2): fixtures (real corpus words per collision class).
- `qa/build_kaaf_classes.py` — **create** (Task 4): enumerate positional variants → `kaaf_classes.fea`.
- `sources/FatemiMaqala-Regular.ufo/features.fea` — **modify** (Tasks 5–7): new lookups + feature wiring.
- `qa/make_variant_glyphs.py` — **create** (Task 7): script that adds re-anchored kasra glyph(s) to the UFO.
- `docs/superpowers/specs/2026-06-04-...-design.md` — **modify** (Task 7): record the below-mark mechanism decision.

---

## Task 1: Fix the detector's multi-Face segfault (reuse one FreeType Face)

**Files:**
- Modify: `qa/collision_check.py` (the `CollisionDetector.__init__` and `collisions` method)
- Test: `qa/test_detector_reuse.py` (create)

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run it to verify it fails (segfault)**

Run: `. .venv/bin/activate && python3 -m pytest qa/test_detector_reuse.py -v` (install pytest if missing: `pip install -q pytest`)
Expected: `test_many_calls_one_process_no_crash` crashes the process (exit 139 / "Fatal Python error: Segmentation fault" in `load_glyph`).

- [ ] **Step 3: Make the minimal fix — build the Face once, reuse it**

In `qa/collision_check.py`, in `CollisionDetector.__init__`, after `self.face = hb.Face(self.data)` add:

```python
        self.ft = freetype.Face(self.path)
```

In `collisions(...)`, delete the per-call construction line:

```python
        ft = freetype.Face(self.path); ft.set_char_size(int(px * 64))
```

and replace it with reuse of the cached Face:

```python
        ft = self.ft; ft.set_char_size(int(px * 64))
```

(Everything else in `collisions` is unchanged.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `. .venv/bin/activate && python3 -m pytest qa/test_detector_reuse.py -v`
Expected: both tests PASS, no segfault.

- [ ] **Step 5: Commit**

```bash
git add qa/collision_check.py qa/test_detector_reuse.py
git commit -m "fix(qa): reuse one freetype.Face in detector (multi-Face segfault)

collisions() built a fresh freetype.Face per call; >1 Face per process
segfaults freetype-py in load_glyph. Build it once in __init__ and reuse.
Single-call results unchanged."
```

---

## Task 2: Regression harness + fixture words

**Files:**
- Create: `qa/collision_regress.py`
- Create: `qa/regression_words.json`
- Test: same file, run as a script (self-checking)

- [ ] **Step 1: Write the fixture file with real corpus words**

```json
{
  "kaaf_clearTop":   ["شَمْلَكُمْ", "هِجرانُكُم", "زَكيةُ", "أَندُبُكُم", "صبرُكم", "وَخَيرُكُمُ"],
  "kaaf_dotted":     ["فاحْتَكِمَ", "يَستَكبِرونَ", "أَنْتَجِعْ", "فَأَكثر", "نُكِبَت"],
  "kaaf_longAsc":    ["مُلْكَهُ", "كَلُّكُم", "اللُّكنا", "ومُلْكُك", "أَسْلَفْتُكمْ"],
  "kaaf_nonJoin":    ["ذَكرناهم", "فاذْكُرْنا", "أَذْكُرُه", "وَأَكبَروا", "الرَكيكُ"],
  "belowmark_wawreh":["بِنُحُوسِها", "سَتُودِعُ", "عساكرِهِ", "خَنجَرِهِ", "وَرْدِي"],
  "clean":           ["بِسْمِ اللّٰهِ الرَّحْمٰنِ الرَّحِيْمِ", "الْحَمْدُ لِلّٰهِ رَبِّ الْعالَمِينَ"]
}
```

- [ ] **Step 2: Write the harness (one font per process)**

```python
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
    font = sys.argv[1] if len(sys.argv) > 1 else None
    fixture = os.path.join(os.path.dirname(__file__), "regression_words.json")
    print(json.dumps(run(font, fixture), ensure_ascii=False, indent=2))
```

- [ ] **Step 3: Run it on the shipped font to verify it produces counts**

Run: `. .venv/bin/activate && python3 qa/collision_regress.py fonts/FatemiMaqala-Regular.ttf`
Expected: JSON with non-zero `kaaf_above` under `kaaf_clearTop`/`kaaf_dotted`/`kaaf_longAsc`/`kaaf_nonJoin`, non-zero `belowmark_wawreh` under `belowmark_wawreh`, and `other`≈0 under `clean`.

- [ ] **Step 4: Commit**

```bash
git add qa/collision_regress.py qa/regression_words.json
git commit -m "test(qa): collision regression harness + corpus fixture words"
```

---

## Task 3: Capture the baseline (the "before" numbers to beat)

**Files:**
- Create: `qa/baseline.json` (generated)

- [ ] **Step 1: Build the current source font and record baseline**

Run:
```bash
. .venv/bin/activate
fontmake -u sources/FatemiMaqala-Regular.ufo -o ttf --output-path /tmp/fm_baseline.ttf
python3 qa/collision_regress.py /tmp/fm_baseline.ttf > qa/baseline.json
cat qa/baseline.json
```
Expected: same shape as Task 2 Step 3. This is the source-built baseline (use this, not the shipped TTF, so later comparisons are apples-to-apples).

- [ ] **Step 2: Sanity — built font matches shipped on the clean class**

Run: `python3 qa/collision_regress.py fonts/FatemiMaqala-Regular.ttf` and compare the `clean` block to `qa/baseline.json`'s `clean` block.
Expected: identical (both ≈0 collisions on basmala / fatiha line).

- [ ] **Step 3: Commit**

```bash
git add qa/baseline.json
git commit -m "test(qa): record source-built collision baseline"
```

---

## Task 4: Enumerate group classes from the font (blocker #2)

**Files:**
- Create: `qa/build_kaaf_classes.py`
- Create: `sources/FatemiMaqala-Regular.ufo/kaaf_classes.fea` (generated, then `include`d)
- Test: assertions inside `build_kaaf_classes.py` (`--check`)

- [ ] **Step 1: Write the enumerator**

```python
#!/usr/bin/env python3
"""build_kaaf_classes.py — enumerate ALL positional variants of each base letter
into GSUB glyph classes for the kaaf-collision rules, by scanning the font's
glyph names. Emits an includable .fea and self-checks membership + disjointness."""
import sys, os
from fontTools.ttLib import TTFont

FONT = os.path.join(os.path.dirname(__file__), "..", "fonts", "FatemiMaqala-Regular.ttf")

# Base letters per group -> the Unicode of the isolated form, used to find the
# init/medi/fina + .lowtop/.hightop/.lowbottom variants by Arabic-shaping name family.
# We match by the canonical FE/FB presentation-form ranges per letter.
CLEAR_TOP = {  # ب ج ح س ص ع ي م ه
    "beh":  ["uniFE8F","uniFE90","uniFE91","uniFE92"],
    "jeem": ["uniFE9D","uniFE9E","uniFE9F","uniFEA0"],
    "hah":  ["uniFEA1","uniFEA2","uniFEA3","uniFEA4"],
    "seen": ["uniFEB1","uniFEB2","uniFEB3","uniFEB4"],
    "sad":  ["uniFEB5","uniFEB6","uniFEB7","uniFEB8"],
    "ain":  ["uniFEC9","uniFECA","uniFECB","uniFECC"],
    "yeh":  ["uniFEF1","uniFEF2","uniFEF3","uniFEF4"],
    "meem": ["uniFEE1","uniFEE2","uniFEE3","uniFEE4"],
    "heh":  ["uniFEE9","uniFEEA","uniFEEB","uniFEEC"],
}
DOTTED = {  # ت ث خ ش ض غ ف ق ن
    "teh":  ["uniFE95","uniFE96","uniFE97","uniFE98"],
    "theh": ["uniFE99","uniFE9A","uniFE9B","uniFE9C"],
    "khah": ["uniFEA5","uniFEA6","uniFEA7","uniFEA8"],
    "sheen":["uniFEB5","uniFEB6","uniFEB7","uniFEB8"],  # NOTE: replace with sheen FEB9-FEBC
    "dad":  ["uniFEBD","uniFEBE","uniFEBF","uniFEC0"],
    "ghain":["uniFECD","uniFECE","uniFECF","uniFED0"],
    "feh":  ["uniFED1","uniFED2","uniFED3","uniFED4"],
    "qaf":  ["uniFED5","uniFED6","uniFED7","uniFED8"],
    "noon": ["uniFEE5","uniFEE6","uniFEE7","uniFEE8"],
}
LONG_ASC = {  # ل ط ظ + kaaf forms (kaaf-before-kaaf)
    "lam":  ["uniFEDD","uniFEDE","uniFEDF","uniFEE0"],
    "tah":  ["uniFEC1","uniFEC2","uniFEC3","uniFEC4"],
    "zah":  ["uniFEC5","uniFEC6","uniFEC7","uniFEC8"],
    "kaaf": ["uniFED9","uniFEDA","uniFEDB","uniFEDC"],
}
ABOVE_MARKS = ["uni064B","uni064C","uni064E","uni064F","uni0651","uni0652","uni0653","uni0670"]
# right-joining-only finals that yield an INITIAL kaaf after them
NONJOIN = ["uniFE8E","uniFEAE","uniFEEE","uniFEAA","uniFEAC","uniFEB0","uniFE82","uniFE84","uniFE88","uniFE8A"]

def variants(tt, seeds):
    """All glyph names that are `seed` or `seed.<suffix>` present in the font."""
    names = set(tt.getGlyphOrder())
    out = []
    for s in seeds:
        for n in names:
            if n == s or n.startswith(s + "."):
                out.append(n)
    return sorted(set(out))

def build(tt, groups):
    members = []
    for seeds in groups.values():
        members += variants(tt, seeds)
    return sorted(set(members))

def main():
    tt = TTFont(FONT)
    names = set(tt.getGlyphOrder())
    classes = {
        "kaafClearTop": build(tt, CLEAR_TOP),
        "kaafDotted":   build(tt, DOTTED),
        "kaafLongAsc":  build(tt, LONG_ASC),
        "aboveMarks":   [n for n in ABOVE_MARKS if n in names],
        "nonJoinFinals":[n for n in NONJOIN if n in names],
    }
    # self-checks
    for k, v in classes.items():
        assert v, f"class @{k} is empty"
        for g in v:
            assert g in names, f"@{k} references missing glyph {g}"
    # clearTop / dotted / longAsc must be disjoint
    ct, do, la = set(classes["kaafClearTop"]), set(classes["kaafDotted"]), set(classes["kaafLongAsc"])
    assert not (ct & do), f"clearTop∩dotted: {ct & do}"
    assert not (ct & la), f"clearTop∩longAsc: {ct & la}"
    assert not (do & la), f"dotted∩longAsc: {do & la}"
    if "--check" in sys.argv:
        print("classes OK:", {k: len(v) for k, v in classes.items()})
        return
    out = os.path.join(os.path.dirname(__file__), "..", "sources",
                       "FatemiMaqala-Regular.ufo", "kaaf_classes.fea")
    with open(out, "w") as f:
        f.write("# GENERATED by qa/build_kaaf_classes.py — do not edit by hand.\n")
        for k, v in classes.items():
            f.write(f"@{k} = [{' '.join(v)}];\n")
    print("wrote", out, {k: len(v) for k, v in classes.items()})

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the self-check; fix the seed lists until green**

Run: `. .venv/bin/activate && python3 qa/build_kaaf_classes.py --check`
Expected: `classes OK: {...}` with non-empty counts. **If it asserts** (missing glyph or `clearTop∩dotted` overlap — note the deliberate `sheen` bug placeholder in `DOTTED`), correct the seed list (sheen is `uniFEB9–uniFEBC`, not the sad range) and re-run until it prints OK. Verify a few names exist with: `python3 -c "from fontTools.ttLib import TTFont; go=set(TTFont('fonts/FatemiMaqala-Regular.ttf').getGlyphOrder()); print([n for n in go if n.startswith('uniFEE2')])"`.

- [ ] **Step 3: Generate the .fea and add the include**

Run: `python3 qa/build_kaaf_classes.py`
Then add near the top of `sources/FatemiMaqala-Regular.ufo/features.fea` (before the first `feature` block, after any existing class defs), the line:

```
include(kaaf_classes.fea);
```

- [ ] **Step 4: Verify the font still builds clean with the include**

Run: `. .venv/bin/activate && fontmake -u sources/FatemiMaqala-Regular.ufo -o ttf --output-path /tmp/fm_classes.ttf`
Expected: builds with no feaLib errors (warnings OK). Then `python3 qa/collision_regress.py /tmp/fm_classes.ttf` matches `qa/baseline.json` (classes alone change nothing).

- [ ] **Step 5: Commit**

```bash
git add qa/build_kaaf_classes.py sources/FatemiMaqala-Regular.ufo/kaaf_classes.fea sources/FatemiMaqala-Regular.ufo/features.fea
git commit -m "feat(fea): enumerate kaaf-collision group classes from the font"
```

---

## Task 5: Component B — wide tatweel before medial kaaf when marked

**Files:**
- Modify: `sources/FatemiMaqala-Regular.ufo/features.fea` (new lookups + `calt` wiring)

- [ ] **Step 1: Write the failing regression assertion**

Add to `qa/test_components.py` (create):

```python
import os, sys, json, subprocess
HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)

def build_and_regress(out="/tmp/fm_comp.ttf"):
    subprocess.run(["fontmake","-u",f"{ROOT}/sources/FatemiMaqala-Regular.ufo",
                    "-o","ttf","--output-path",out], check=True, capture_output=True)
    r = subprocess.run([sys.executable, f"{HERE}/collision_regress.py", out],
                       check=True, capture_output=True, text=True)
    return json.loads(r.stdout)

def test_componentB_connecting_kaaf_clears():
    res = build_and_regress()
    # clear-top, dotted, long-ascender connecting cases -> 0 kaaf_above
    assert res["kaaf_clearTop"]["kaaf_above"] == 0, res["kaaf_clearTop"]
    assert res["kaaf_dotted"]["kaaf_above"] == 0, res["kaaf_dotted"]
    assert res["kaaf_longAsc"]["kaaf_above"] == 0, res["kaaf_longAsc"]
    # clean text unchanged
    assert res["clean"]["kaaf_above"] == 0 and res["clean"]["belowmark_wawreh"] == 0
```

- [ ] **Step 2: Run to confirm it fails against the current font**

Run: `. .venv/bin/activate && python3 -m pytest qa/test_components.py::test_componentB_connecting_kaaf_clears -v`
Expected: FAIL — `kaaf_clearTop["kaaf_above"]` is the baseline non-zero count.

- [ ] **Step 3: Add the lookups to `features.fea`**

After the `longlaamContext` lookup block (around line 758), add:

```
lookup insertWideTatweelBeforeKaaf {
  lookupflag 0;
    sub uniFEDC by uni0640.3 uniFEDC ;
} insertWideTatweelBeforeKaaf;

lookup insertLittleTatweelBeforeKaaf {
  lookupflag 0;
    sub uniFEDC by uni0640.1 uniFEDC ;
} insertLittleTatweelBeforeKaaf;

# Marked: connecting base + above-mark + medial kaaf -> WIDE tatweel.
# Do NOT IgnoreMarks; the mark is matched explicitly, so unmarked words never widen.
lookup kaafCollideWideContext {
  lookupflag 0;
    sub [@kaafClearTop @kaafDotted @kaafLongAsc] @aboveMarks
        uniFEDC' lookup insertWideTatweelBeforeKaaf ;
} kaafCollideWideContext;

# Unmarked long-ascender before medial kaaf -> LITTLE tatweel ("as good as joined").
lookup kaafLongAscLittleContext {
  lookupflag IgnoreMarks;
    sub @kaafLongAsc uniFEDC' lookup insertLittleTatweelBeforeKaaf ;
} kaafLongAscLittleContext;
```

Then wire them into the **`calt`** feature. In the `calt` block (1610–1705), inside each `script`/`language` section that already lists `lookup longlaamContext;`, add **after** it:

```
      lookup kaafCollideWideContext;
      lookup kaafLongAscLittleContext;
```

(Order matters: the wide-marked rule first; the little-unmarked rule second. Both run because their match conditions are mutually exclusive — marked vs IgnoreMarks-but-no-mark-context.)

- [ ] **Step 4: Run the regression test to verify it passes**

Run: `. .venv/bin/activate && python3 -m pytest qa/test_components.py::test_componentB_connecting_kaaf_clears -v`
Expected: PASS. If a group still shows residual `kaaf_above`, the wide tatweel under-shoots for it → change that group's nested lookup to insert `uni0640.3` twice (`sub uniFEDC by uni0640.3 uni0640.3 uniFEDC;` in a group-specific insert lookup) and re-run. Record any residual in the spec.

**If ALL groups are unchanged from baseline** (the rule did not fire at all — the blocker-#1 failure mode, e.g. the mark is not where the backtrack expects at `calt` time): diagnose by dumping the shaped sequence of one fixture word against `/tmp/fm_comp.ttf` (`python3 -c "import uharfbuzz as hb; ... print([order[i.codepoint] for i in buf.glyph_infos])"`) to confirm the memory order is `base, mark, uniFEDC`. If the mark sits elsewhere, adjust the backtrack accordingly; if marks are dropped from the run, move the lookup earlier in `calt` (before any IgnoreMarks lookup repositions them). Do not proceed to Task 6 until the rule fires.

- [ ] **Step 5: Confirm no width regression on clean text**

Run: `python3 qa/collision_regress.py /tmp/fm_comp.ttf` and confirm `clean` is still all-zero, and `kaaf_nonJoin`/`belowmark_wawreh` are unchanged vs baseline (Component B must not touch them).

- [ ] **Step 6: Commit**

```bash
git add sources/FatemiMaqala-Regular.ufo/features.fea qa/test_components.py
git commit -m "feat(fea): wide-tatweel kaaf collision fix for connecting bases (Component B)"
```

---

## Task 6: Component C — kern before initial kaaf after a marked non-joining base

**Files:**
- Modify: `sources/FatemiMaqala-Regular.ufo/features.fea`

- [ ] **Step 1: Write the failing assertion**

Add to `qa/test_components.py`:

```python
def test_componentC_nonjoin_kaaf_clears():
    res = build_and_regress()
    assert res["kaaf_nonJoin"]["kaaf_above"] == 0, res["kaaf_nonJoin"]
    assert res["clean"]["kaaf_above"] == 0
```

- [ ] **Step 2: Run to confirm failure**

Run: `. .venv/bin/activate && python3 -m pytest qa/test_components.py::test_componentC_nonjoin_kaaf_clears -v`
Expected: FAIL (baseline non-zero `kaaf_nonJoin`).

- [ ] **Step 3: Add a contextual kern lookup and wire it into `kern`**

Add near `spaceBeforeAlefHamza` (≈line 7574):

```
lookup spaceBeforeInitKaaf {
    pos @nonJoinFinals @aboveMarks uniFEDB' 220 ;
} spaceBeforeInitKaaf;
```

In the `feature kern { ... }` block, add `lookup spaceBeforeInitKaaf;` immediately after `lookup spaceBeforeAlefHamza;`.

- [ ] **Step 4: Build, test, and tune the kern value**

Run: `. .venv/bin/activate && python3 -m pytest qa/test_components.py::test_componentC_nonjoin_kaaf_clears -v`
Expected: PASS. If still failing, raise `220` toward `400` and re-run.

**Fallback if the contextual kern does not fire at all** (the count is unchanged at every value — the blocker-#1 failure mode): replace with a GSUB approach. (a) Run `python3 qa/make_variant_glyphs.py --kaaf-sp` (Task 7's script, extended to copy `uniFEDB`→`uniFEDB.sp` with +220 right side-bearing). (b) Add `lookup subKaafSp { sub uniFEDB by uniFEDB.sp; } subKaafSp;` and `lookup kaafNonJoinContext { lookupflag 0; sub @nonJoinFinals @aboveMarks uniFEDB' lookup subKaafSp; } kaafNonJoinContext;` wired into `calt` after Component B. Re-run the test.

- [ ] **Step 5: Commit**

```bash
git add sources/FatemiMaqala-Regular.ufo/features.fea qa/test_components.py
git commit -m "feat(fea): kern (or GSUB) space before initial kaaf after marked non-joining base (Component C)"
```

---

## Task 7: Component D — below-mark vs following waw/reh (author glyph, prototype both, pick)

**Files:**
- Create: `qa/make_variant_glyphs.py`
- Modify: `sources/FatemiMaqala-Regular.ufo/...` (new glyph via script), `features.fea`
- Modify: the design spec (record the decision)

- [ ] **Step 1: Write the failing assertion**

Add to `qa/test_components.py`:

```python
def test_componentD_belowmark_clears():
    res = build_and_regress()
    assert res["belowmark_wawreh"]["belowmark_wawreh"] == 0, res["belowmark_wawreh"]
    assert res["clean"]["belowmark_wawreh"] == 0
```

- [ ] **Step 2: Run to confirm failure**

Run: `. .venv/bin/activate && python3 -m pytest qa/test_components.py::test_componentD_belowmark_clears -v`
Expected: FAIL (baseline non-zero).

- [ ] **Step 3: Write the glyph-authoring script (re-anchored kasra)**

```python
#!/usr/bin/env python3
"""make_variant_glyphs.py — add scripted glyph variants to the UFO (no manual draw).
--kasra-k : copy uni0650 -> uni0650.k and uni064D -> uni064D.k, identical outline,
            with their `belowSingle` anchor shifted right (+DX) and up (+DY) so the
            mark clears a following waw/reh bowl. The shift is applied to the glyph's
            mark anchor in the UFO; features re-anchor it via the existing markClass.
--kaaf-sp : copy uniFEDB -> uniFEDB.sp with +220 right side-bearing (Component C fallback)."""
import sys, os, defcon
UFO = os.path.join(os.path.dirname(__file__), "..", "sources", "FatemiMaqala-Regular.ufo")
DX, DY = 120, 90  # tune against the detector

def copy_glyph(font, src, dst):
    if dst in font: del font[dst]
    g = font[src]
    font.newGlyph(dst)
    ng = font[dst]
    ng.width = g.width
    pen = ng.getPen()
    g.draw(pen)
    for a in g.anchors:
        ng.appendAnchor({"name": a["name"], "x": a["x"], "y": a["y"]})
    return ng

def main():
    font = defcon.Font(UFO)
    if "--kasra-k" in sys.argv:
        for src, dst in [("uni0650", "uni0650.k"), ("uni064D", "uni064D.k")]:
            ng = copy_glyph(font, src, dst)
            for a in ng.anchors:
                if a["name"] in ("belowSingle", "_belowSingle", "below"):
                    a["x"] += DX; a["y"] += DY
        print("added uni0650.k, uni064D.k  (DX,DY=%d,%d)" % (DX, DY))
    if "--kaaf-sp" in sys.argv:
        ng = copy_glyph(font, "uniFEDB", "uniFEDB.sp")
        ng.width += 220
        print("added uniFEDB.sp (+220 width)")
    font.save()

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Author the kasra variants and register the markClass + GSUB**

Run: `. .venv/bin/activate && python3 qa/make_variant_glyphs.py --kasra-k`

In `features.fea`: (a) add the variants to the `belowSingle` markClass with the shifted anchor — find the lines `markClass [\uni064D ] <anchor 203 -640> @belowSingle;` / `markClass [\uni0650 ] <anchor 222 -659> @belowSingle;` and add after them:

```
  markClass [uni0650.k] <anchor 342 -569> @belowSingle;
  markClass [uni064D.k] <anchor 323 -550> @belowSingle;
```

(b) Add a contextual GSUB swapping the kasra for its variant before waw/reh and wire into `calt` after Component C:

```
lookup subKasraK { lookupflag 0;
    sub uni0650 by uni0650.k ;
    sub uni064D by uni064D.k ;
} subKasraK;
lookup belowMarkWawRehContext { lookupflag 0;
    sub [uni0650 uni064D]' lookup subKasraK
        [uniFEEE uni0648 uniFEAE uniFEAD uniFEAF uniFEB0 uni0631.alt uni0631 uniFE86] ;
} belowMarkWawRehContext;
```

- [ ] **Step 5: Build + test prototype 1 (shifted kasra)**

Run: `. .venv/bin/activate && python3 -m pytest qa/test_components.py::test_componentD_belowmark_clears -v`
Expected: PASS, or a reduced count. If reduced-but-not-zero, increase `DX/DY` in `make_variant_glyphs.py`, re-run `--kasra-k`, update the markClass anchors to match, rebuild. Record the residual.

- [ ] **Step 6: Prototype 2 (micro-kashida) and compare**

On a branch or stash of Step 4–5, instead insert `uni0640.1` between the marked letter and the waw/reh: `lookup belowMarkKashida { lookupflag 0; sub [uniFEEE uni0648 uniFEAE uniFEAD]' lookup <insert little tatweel before> ... }` (mirror Component B's insertion, lookahead = waw/reh). Build, run the same test, and record its residual + the added width. Choose the mechanism with the lower residual and lower visual/width cost.

- [ ] **Step 7: Record the decision in the spec and keep only the winner**

Edit `docs/superpowers/specs/2026-06-04-...-design.md` Component D section: state which mechanism shipped, the final `DX/DY` (or tatweel width), and the residual count. Remove the losing prototype's lookups from `features.fea`.

- [ ] **Step 8: Commit**

```bash
git add qa/make_variant_glyphs.py sources/FatemiMaqala-Regular.ufo qa/test_components.py docs/superpowers/specs/2026-06-04-kaaf-and-belowmark-collision-rules-design.md
git commit -m "feat: below-mark vs waw/reh fix (Component D) + decision recorded"
```

---

## Task 8: Full re-census + compile/render parity gate

**Files:**
- Create: `qa/collision_summary_after.json` (generated)

- [ ] **Step 1: Build the final font and run the full corpus census**

Run:
```bash
. .venv/bin/activate
fontmake -u sources/FatemiMaqala-Regular.ufo -o ttf --output-path /tmp/fm_final.ttf
python3 qa/collision_census_fast.py /Users/abdealikhurrum/Documents/apcd.csv \
    --column البيت --sample-words 150000 --same-marks --seed 1234 \
    --font /tmp/fm_final.ttf --out qa/collision_summary_after.json
```
Expected: `kaaf-above` aggregate and `below-mark vs waw/reh` aggregate both drop sharply vs the pre-fix `qa/collision_summary.json`; no new high-frequency glyph-pair appears.

- [ ] **Step 2: Compare before/after aggregates**

Run a short python compare (reuse the aggregation from the spec's evidence step) over `qa/collision_summary.json` (before) vs `qa/collision_summary_after.json` (after). Expected: in-scope classes down by the bulk of their count; out-of-scope classes (mark-vs-mark, descender near-misses) within ±5% (we did not touch them).

- [ ] **Step 3: Compile + render parity**

Run: `. .venv/bin/activate && python3 qa/collision_regress.py /tmp/fm_final.ttf` and confirm all in-scope classes are 0 (or the documented residual) and `clean` is 0. Then pixel-compare the basmala/fatiha rendering of `/tmp/fm_final.ttf` vs the shipped font visually (open both, or render to PNG) to confirm connected vocalised text is unchanged outside the intended kaaf/kasra adjustments.

- [ ] **Step 4: Ship the built font (optional, on request)**

Only if the user asks to update the shipping artifact: `fontmake ... --output-path fonts/FatemiMaqala-Regular.ttf` and commit `fonts/` separately.

- [ ] **Step 5: Commit the census evidence**

```bash
git add qa/collision_summary_after.json
git commit -m "test(qa): post-fix corpus census — in-scope collisions cleared"
```

---

## Self-review notes

- **Spec coverage:** Component A→Task 4; B→Task 5; C→Task 6; D→Task 7; build-loop/detector reliability→Tasks 1–3; full re-census + compile/render gate→Task 8. The blocker-#1 fallback (GSUB when contextual GPOS won't fire) is explicit in Task 6 Step 4. Blocker #2 (enumerate variants) is Task 4. Blocker #3 (wide vs little tatweel) is Task 5 Step 4 tuning.
- **Out of scope (unchanged by design):** mark-vs-mark shadda stacks, descender near-misses, alef-hamza blocker #4 — Task 8 Step 2 asserts these stay flat.
- **Known seed-list trap:** Task 4's `DOTTED["sheen"]` intentionally carries the wrong range so the disjointness self-check forces verification; fix to `uniFEB9–uniFEBC` (sheen) during Step 2.
- **Anchor numbers** in Task 7 Step 4 are starting estimates derived from the existing `belowSingle` anchors (`uni0650` 222/-659, `uni064D` 203/-640) plus `DX/DY`; they are tuned against the detector in Step 5, not assumed final.
