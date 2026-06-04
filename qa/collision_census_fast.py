#!/usr/bin/env python3
"""
collision_census_fast.py — parallel, raster-cached census over a large corpus.

Same idea and output format as collision_census.py, but built to run over big
corpora (e.g. APCD, ~1.8M rows) in minutes instead of days:

  1. gid -> bitmap cache: a glyph's outline is context-free (HarfBuzz shaping
     resolves all ligatures / contextual variants / mark anchoring into final
     (gid, offset) pairs BEFORE rasterisation), so each gid is rendered once
     and reused across every word it appears in.
  2. multiprocessing across all cores but two.
  3. px=200 by default (vs 600) — enough to RANK colliding glyph-pairs; use the
     full-res collision_check.py for final per-string validation.

Correctness note: caching memoises only the render, never a shaping decision —
context (ligatures, .lowtop/.hightop variants, mark combos) is fully handled by
hb.shape() per word, upstream of the cache. Results are the same as the
un-cached detector at the same px.

Usage:
    python3 collision_census_fast.py CORPUS.csv --column البيت [options]

Options mirror collision_census.py, plus:
    --sample-words N   randomly sample N unique marked words from the corpus
                       (0 = use all)                              [default: 150000]
    --px N             raster resolution for ranking              [default: 200]
    --workers N        process pool size           [default: cpu_count - 2]
    --seed N           RNG seed for the random sample             [default: 1234]

Deps: same as collision_check.py (uharfbuzz, freetype-py, numpy, pillow, fonttools)
"""
import sys, os, csv, json, argparse, collections, random, time, multiprocessing as mp
import uharfbuzz as hb, freetype, numpy as np
from PIL import Image, ImageFilter
from fontTools.ttLib import TTFont

sys.path.insert(0, os.path.dirname(__file__))
from collision_check import DEFAULT_FONT


def has_mark(tok):
    return any(0x064B <= ord(c) <= 0x065F or ord(c) == 0x0670 for c in tok)


# ---- per-worker state (built once per process via the pool initializer) ----
_W = {}


def _init(font_path, px, margin_units, min_pixels, same_marks):
    tt = TTFont(font_path)
    upm = tt["head"].unitsPerEm
    order = tt.getGlyphOrder()
    n2g = {n: i for i, n in enumerate(order)}
    marks = set()
    gd = tt["GDEF"].table.GlyphClassDef if "GDEF" in tt else None
    if gd:
        marks = {n2g[g] for g, c in gd.classDefs.items() if c == 3}
    data = open(font_path, "rb").read()
    ft = freetype.Face(font_path)
    ft.set_char_size(int(px * 64))
    _W.update(
        path=font_path, upm=upm, order=order, marks=marks,
        face=hb.Face(data), ft=ft, px=px,
        sc=px / upm, base_y=px * 2.0,
        k=max(1, int(round(margin_units * px / upm))),
        min_pixels=min_pixels, same_marks=same_marks,
        raster={},   # gid -> (mask_bool, w, h, left, top)
        dilate={},   # mark gid -> dilated bool mask (with k-border)
    )


def _raster(gid):
    c = _W["raster"].get(gid)
    if c is None:
        ft = _W["ft"]
        ft.load_glyph(gid, freetype.FT_LOAD_RENDER)
        b = ft.glyph.bitmap
        w, h = b.width, b.rows
        mask = (np.frombuffer(bytes(b.buffer), dtype=np.uint8).reshape(h, w) > 40
                ) if (w and h) else np.zeros((0, 0), bool)
        c = (mask, w, h, ft.glyph.bitmap_left, ft.glyph.bitmap_top)
        _W["raster"][gid] = c
    return c


def _dilated(gid, mask, w, h):
    d = _W["dilate"].get(gid)
    if d is None:
        k = _W["k"]
        gm = Image.fromarray((mask * 255).astype("uint8"))
        gm = gm.crop((-k, -k, w + k, h + k)).filter(ImageFilter.MaxFilter(2 * k + 1))
        d = np.array(gm) > 0
        _W["dilate"][gid] = d
    return d


def _collisions(text):
    fnt = hb.Font(_W["face"]); fnt.scale = (_W["upm"], _W["upm"])
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    hb.shape(fnt, buf, {})
    sc, base_y, k = _W["sc"], _W["base_y"], _W["k"]
    glyphs = []; penx = 0.0
    for i, p in zip(buf.glyph_infos, buf.glyph_positions):
        mask, w, h, left, top = _raster(i.codepoint)
        x = penx + p.x_offset * sc + left
        y = base_y - p.y_offset * sc - top
        glyphs.append(dict(gid=i.codepoint, cl=i.cluster, x=int(round(x)),
                           y=int(round(y)), w=w, h=h, mask=mask,
                           ismark=i.codepoint in _W["marks"]))
        penx += p.x_advance * sc
    hits = []
    for m in glyphs:
        if not m["ismark"] or m["w"] == 0:
            continue
        gmask = _dilated(m["gid"], m["mask"], m["w"], m["h"])
        gx, gy = m["x"] - k, m["y"] - k; gh, gw = gmask.shape
        for o in glyphs:
            if o is m or o["w"] == 0:
                continue
            same = o["cl"] == m["cl"]
            if same and not (_W["same_marks"] and o["ismark"]):
                continue
            if same and o["gid"] == m["gid"]:
                continue
            ox0 = max(gx, o["x"]); oy0 = max(gy, o["y"])
            ox1 = min(gx + gw, o["x"] + o["w"]); oy1 = min(gy + gh, o["y"] + o["h"])
            if ox1 <= ox0 or oy1 <= oy0:
                continue
            mm = gmask[oy0 - gy:oy1 - gy, ox0 - gx:ox1 - gx]
            oo = o["mask"][oy0 - o["y"]:oy1 - o["y"], ox0 - o["x"]:ox1 - o["x"]]
            inter = int(np.logical_and(mm, oo).sum())
            if inter >= _W["min_pixels"]:
                hits.append((_W["order"][m["gid"]], _W["order"][o["gid"]], inter))
    return hits


def _process_chunk(words):
    pairs = collections.Counter()
    examples = collections.defaultdict(list)
    for tok in words:
        for ma, ob, px in _collisions(tok):
            key = f"{ma}|{ob}"
            pairs[key] += 1
            if len(examples[key]) < 6:
                examples[key].append(tok)
    return pairs, examples


def collect_words(corpus, column, sample_words, seed, limit):
    """Read the corpus once, return a (possibly random-sampled) list of unique
    marked words."""
    csv.field_size_limit(10 ** 7)
    seen = set(); n_rows = 0
    t0 = time.time()
    with open(corpus, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        if column not in rd.fieldnames:
            sys.exit(f"column '{column}' not in CSV. columns: {rd.fieldnames}")
        for row in rd:
            n_rows += 1
            if limit and n_rows > limit:
                break
            for tok in (row.get(column) or "").split():
                if has_mark(tok):
                    seen.add(tok)
            if n_rows % 200000 == 0:
                print(f"  read {n_rows} rows, {len(seen)} unique marked words "
                      f"({time.time()-t0:.0f}s)", flush=True)
    words = list(seen)
    if sample_words and len(words) > sample_words:
        random.seed(seed)
        words = random.sample(words, sample_words)
    return words, n_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus")
    ap.add_argument("--column", required=True)
    ap.add_argument("--font", default=DEFAULT_FONT)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sample-words", type=int, default=150000)
    ap.add_argument("--margin", type=int, default=35)
    ap.add_argument("--min-pixels", type=int, default=4)
    ap.add_argument("--same-marks", action="store_true")
    ap.add_argument("--px", type=int, default=200)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--examples", type=int, default=4)
    ap.add_argument("--out", default="collision_summary.json")
    a = ap.parse_args()

    print(f"reading corpus + collecting unique marked words ...", flush=True)
    words, n_rows = collect_words(a.corpus, a.column, a.sample_words, a.seed, a.limit)
    print(f"testing {len(words)} unique marked words on {a.workers} workers "
          f"(px={a.px}) ...", flush=True)

    n = max(1, a.workers)
    chunks = [words[i::n * 4] for i in range(n * 4)]   # 4 chunks/worker for balance
    chunks = [c for c in chunks if c]

    pairs = collections.Counter()
    examples = collections.defaultdict(list)
    t0 = time.time()
    with mp.Pool(n, initializer=_init,
                 initargs=(a.font, a.px, a.margin, a.min_pixels, a.same_marks)) as pool:
        done = 0
        for cp, cex in pool.imap_unordered(_process_chunk, chunks):
            pairs.update(cp)
            for k, ex in cex.items():
                for e in ex:
                    if len(examples[k]) < a.examples:
                        examples[k].append(e)
            done += 1
            print(f"  {done}/{len(chunks)} chunks ({time.time()-t0:.0f}s)", flush=True)

    summary = {
        "font": os.path.basename(a.font),
        "rows_scanned": n_rows,
        "px": a.px,
        "unique_marked_words": len(words),
        "sample_words": a.sample_words,
        "seed": a.seed,
        "margin_units": a.margin,
        "same_cluster_marks": a.same_marks,
        "total_collisions": sum(pairs.values()),
        "by_glyph_pair": [
            {"mark": k.split("|")[0], "neighbor": k.split("|")[1],
             "count": c, "examples": examples[k][:a.examples]}
            for k, c in pairs.most_common()
        ],
    }
    with open(a.out, "w", encoding="utf-8") as o:
        json.dump(summary, o, ensure_ascii=False, indent=2)
    print(f"\nscanned {len(words)} unique marked words across {n_rows} rows in "
          f"{time.time()-t0:.0f}s")
    print(f"{summary['total_collisions']} collisions across {len(pairs)} glyph-pairs")
    print(f"-> {a.out}")
    for e in summary["by_glyph_pair"][:20]:
        print(f"   {e['count']:7}  {e['mark']} ↔ {e['neighbor']}   e.g. {' '.join(e['examples'])}")


if __name__ == "__main__":
    main()
