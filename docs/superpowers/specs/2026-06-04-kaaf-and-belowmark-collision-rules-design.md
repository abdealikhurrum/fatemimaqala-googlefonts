# Programmatic collision correction — kaaf-adjacency + below-mark — design

Date: 2026-06-04
Supersedes the open questions in `qa/collision-rules-design.md` with corpus-measured
decisions. Builds on `REHAB.md` (feature-file rehab) and the validated detector
`qa/collision_check.py`.

## Goal

Reduce inter-character diacritic collisions in `FatemiMaqala-Regular` by editing
the font's OpenType layout (`sources/FatemiMaqala-Regular.ufo/features.fea`) plus a
small number of new mark glyphs in the UFO — no outline reshaping of existing
letters. Correctness is judged objectively by the pixel collision detector at full
600px resolution; no regression in already-clean text (basmala, connected vocalised
text) is acceptable.

## Evidence base (APCD corpus, `/Users/abdealikhurrum/Documents/apcd.csv`, column البيت)

Measured with the new parallel, raster-cached census `qa/collision_census_fast.py`
(gid-cached render + multiprocessing; px=200 for ranking) over a 150k random sample
of unique marked words (and focused 100–120k scans per class). Detector fidelity:
ranking at px=200, all final validation at px=600.

Collision classes by real-world frequency:

| Class | Count (150k sample) | Disposition |
|---|---|---|
| **Kaaf-above** (above-mark ↔ `uniFEDB`/`uniFEDC` arm) | 1466 | **In scope** — dominant single-letter cause |
| Below-mark ↔ following waw/reh | 3538 | **In scope** (added) — 76% hard overlaps, real |
| Mark-vs-mark shadda stacks | 1699 | Out of scope — mostly normal stacking; visual review later |
| Below-mark near-misses (descenders) | — | Out of scope — margin artifacts |
| alef-hamza (shadda ↔ `uniFE83.short`) | ~150 | Out of scope this pass (blocker #4) |

Kaaf-above sub-structure (focused 120k-word scan, 11,760 collisions):
- **49%** connecting base → **medial** kaaf `uniFEDC` — tatweel insertion works.
- **30%** non-joining preceding letter (ا ر و د ز …) → **initial** kaaf `uniFEDB` —
  letters do not join the kaaf, so a tatweel cannot bridge them; but the natural gap
  means **kerning works**.
- **20%** already carry the little tatweel `uni0640.1` (270u) and still collide —
  proof the marked case needs the **wide** tatweel `uni0640.3` (890u).
- Kaaf forms: `uniFEDC` (medial) 8172, `uniFEDB` (initial) 3588. Marks by frequency:
  fatḥa > ḍamma > shadda > sukūn; tanwīn negligible.

Below-mark sub-structure (focused 100k-word scan, 3887 collisions):
- **100%** the waw/reh **follows** the marked letter and is **connected** to it.
- **76%** hard overlaps (>50px; median 89px, max 646px) — a genuine collision, not a
  near-miss. Top pairs: `uni0650↔uniFEEE` (waw), `uni0650↔uni0648`,
  `uni0650↔uniFEAE` (reh), `uni0650↔uniFEAD`, `uni064D↔…`.

Confirmed font facts: `uni0640.1` adv 270 ("little"), `uni0640.3` adv 890 ("wide");
`uniFEDB` adv 580, `uniFEDC` adv 788; `@aboveSingle`/`@belowSingle` mark classes
defined at features.fea ~4662–4681; `spaceBeforeAlefHamza` is a working simple kern
pair (~7574) that adds space before `uni0625` after non-joining descenders.

## Principle

For every class the fix is **move the offending glyph away from the mark**, choosing
the mechanism the corpus says will actually work for that sub-case. "Only when
marked" is achieved by **matching the mark explicitly in the GSUB backtrack** (no mark
⇒ pattern does not match ⇒ no widening) — this side-steps blocker #1 (contextual GPOS
on marks would not fire with a backtrack in the `mark` feature; GSUB chaining does
fire, as the existing `*Context` lookups prove).

## Design

### Component A — class definitions (blocker #2)

Build three GSUB glyph classes of **preceding bases**, enumerated by scanning the
font's glyph names for *all* positional variants of each base letter (init/medi/fina
and `.lowtop`/`.hightop`/`.lowbottom` etc.), not hand-listed frames:

- `@kaafClearTop` — ب ج ح س ص ع ي م ه (+ variants)
- `@kaafDotted` — ت ث خ ش ض غ ف ق ن (+ variants)
- `@kaafLongAsc` — ل ط ظ (+ variants) and the kaaf forms themselves (kaaf-before-kaaf)

Plus:
- `@aboveMarks` — a plain GSUB class mirroring `@aboveSingle`'s members
  (`uni064B uni064C uni064E uni064F uni0651 uni0652 uni0653 …`), for use in backtracks.
- `@kaafInit` = `[uniFEDB]`, `@kaafMedi` = `[uniFEDC]` (extend with kaaf/gaaf doubles
  only if the corpus shows them; it currently does not).
- `@nonJoinFinals` — the right-joining-only letters that produce an *initial* kaaf:
  alef/reh/waw/dal/zay families (`uniFE8E uniFEAE uniFEEE uniFEAA uniFEB0 …`), enumerated.

A self-test (`qa/build_kaaf_classes.py`, also reusable as the enumerator) asserts each
class's members all exist in the font and that the classes are disjoint.

### Component B — kaaf, connecting base, marked → wide tatweel (GSUB, `calt`)

New lookups modeled on the `longlaamContext`→`longlaamkaafs` convention, but the
above-mark is matched in the backtrack so they fire **only when marked**:

```
lookup insertWideTatweelBeforeKaaf {           # one-to-many insertion
    sub uniFEDC by uni0640.3 uniFEDC ;
} insertWideTatweelBeforeKaaf;

lookup kaafCollideWideContext {
    # memory order: base, mark, kaaf  → insert wide tatweel before the kaaf
    sub [@kaafClearTop @kaafDotted @kaafLongAsc] @aboveMarks
        [uniFEDC]' lookup insertWideTatweelBeforeKaaf ;
} kaafCollideWideContext;
```

Component B targets only the **medial** kaaf `uniFEDC`: a *connecting* preceding base
always yields the medial form. The **initial** kaaf `uniFEDB` only follows a
non-joining base (or word start), so it is handled entirely by Component C.

Group differentiation:
- **clear-top** and **dotted**: wide tatweel **only when marked** (rule above).
- **long-ascender**: wide tatweel when marked (rule above) **and** a *little* tatweel
  when unmarked ("as good as joined") — a second rule with the same backtrack but
  *no* `@aboveMarks` and inserting `uni0640.1`, ordered after the marked rule.

Width is the tunable knob (blocker #3): start at `uni0640.3` (890u) for marked; if the
detector shows it over/under-shoots for a group, the only change is which tatweel glyph
the nested lookup inserts. The existing always-on little-tatweel behaviour for the
*unmarked* long-ascender case is preserved; the existing `longlaamContext` (a different
purpose — kaaf→lam elongation) is left untouched.

### Component C — kaaf, non-joining preceding letter, marked → kern space

The preceding letter does not join the initial kaaf, so widen the gap instead:

```
lookup spaceBeforeInitKaaf {
    # contextual: only when the non-joining base carries an above-mark
    pos @nonJoinFinals @aboveMarks uniFEDB' <space>;
}
```

Primary attempt: contextual GPOS in the **kern** feature (where `spaceBeforeAlefHamza`
lives and fires). **Fallback if it will not fire** (mirroring blocker #1): a GSUB
`uniFEDB → uniFEDB.sp` substitution gated by `@nonJoinFinals @aboveMarks` in the
backtrack, where `uniFEDB.sp` is a new UFO glyph identical to `uniFEDB` but with extra
right side-bearing. The detector decides which path ships.

### Component D — below-mark ↔ following waw/reh → measure two, then decide

Two prototypes, both validated on the real example words, pick the winner (fewer
residual collisions, least width/visual cost):

1. **GSUB shifted-kasra variant** — new UFO glyphs `uni0650.k` / `uni064D.k`
   (kasra / kasratan re-anchored slightly right and/or down, away from the following
   waw/reh bowl), contextually substituted before `[uniFEEE uni0648 uniFEAE uniFEAD …]`.
   GSUB chaining is the proven-to-fire path; no widening.
2. **Micro-kashida** — insert a small tatweel between the marked letter and the
   waw/reh to push the bowl off the kasra. Reuses Component B's mechanism; risk: extra
   mid-word width and unusual kashida placement.

Decision recorded in this doc after the prototype measurement.

## Build sequence (each step is test-first against the detector)

1. **Tooling** — `collision_census_fast.py` (done). Add `build_kaaf_classes.py`
   (enumerate + assert classes). Add a small regression harness
   `qa/collision_regress.py` that runs the 600px detector over a fixed list of
   real example words per class and asserts collision counts.
2. **Component A** — classes + class self-test green.
3. **Component B** — wide-tatweel rule; regression set for clear-top/dotted/long-asc
   goes from N collisions → 0 (or documented residual), basmala/clean text unchanged.
4. **Component C** — non-joining kern (or GSUB fallback); regression green.
5. **Component D** — prototype both, measure, ship the winner; regression green.
6. **Full re-census** — re-run `collision_census_fast.py` on the built TTF; confirm
   the kaaf-above and below-mark totals drop and nothing new appears.
7. **Compile + render check** — `feaLib` compiles clean (per REHAB reproduce step);
   pixel-compare basmala and a connected-text sample against the current font.

## Risks / mitigations

- **Contextual rule won't fire** (blocker #1 recurrence) → every GPOS-contextual step
  has a GSUB-variant fallback; the detector is the gate, not assumption.
- **Wide tatweel over-widens** → width is a single-glyph knob per group, tuned to the
  detector + visual review.
- **New marked glyphs break mark attachment** → new variants get their own anchors in
  the same mark lookups; verified by rendering the example words.
- **Census px=200 mis-ranks** → ranking only; all accept/reject decisions use 600px.
- **Cross-word collisions** not covered — out of scope by construction (intra-word
  problem); matches existing tooling.

## Out of scope (this pass)

Mark-vs-mark shadda stacks; below-mark near-misses against descenders; alef-hamza
short-form firing (blocker #4); any outline reshaping; non-Arabic/Latin features.
