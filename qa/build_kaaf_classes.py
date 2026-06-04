#!/usr/bin/env python3
"""build_kaaf_classes.py — enumerate ALL positional variants of each base letter
into GSUB glyph classes for the kaaf-collision rules, by scanning the font's
glyph names. Emits an includable .fea and self-checks membership + disjointness."""
import sys, os
from fontTools.ttLib import TTFont

FONT = os.path.join(os.path.dirname(__file__), "..", "fonts", "FatemiMaqala-Regular.ttf")

CLEAR_TOP = {  # ب ج ح س ص ع ي م ه
    "beh":       ["uniFE8F","uniFE90","uniFE91","uniFE92"],
    "beh_named": ["dlbeh","behChashm"],           # dotless beh, chashm-beh variants
    "jeem":      ["uniFE9D","uniFE9E","uniFE9F","uniFEA0"],
    "hah":       ["uniFEA1","uniFEA2","uniFEA3","uniFEA4"],
    "seen":      ["uniFEB1","uniFEB2","uniFEB3","uniFEB4"],
    "seen_named":["seenDouble"],                  # double-eye seen variant
    "sad":       ["uniFEB5","uniFEB6","uniFEB7","uniFEB8"],
    "ain":       ["uniFEC9","uniFECA","uniFECB","uniFECC"],
    "yeh":       ["uniFEF1","uniFEF2","uniFEF3","uniFEF4"],
    "yeh_named": ["yehChashm"],                   # chashm-yeh variant
    "meem":      ["uniFEE1","uniFEE2","uniFEE3","uniFEE4"],
    "heh":       ["uniFEE9","uniFEEA","uniFEEB","uniFEEC"],
}
DOTTED = {  # ت ث خ ش ض غ ف ق ن
    "teh":        ["uniFE95","uniFE96","uniFE97","uniFE98"],
    "theh":       ["uniFE99","uniFE9A","uniFE9B","uniFE9C"],
    "theh_named": ["thehDouble"],                 # double-dot theh variant
    "khah":       ["uniFEA5","uniFEA6","uniFEA7","uniFEA8"],
    "sheen":      ["uniFEB9","uniFEBA","uniFEBB","uniFEBC"],
    "dad":        ["uniFEBD","uniFEBE","uniFEBF","uniFEC0"],
    "ghain":      ["uniFECD","uniFECE","uniFECF","uniFED0"],
    "feh":        ["uniFED1","uniFED2","uniFED3","uniFED4"],
    "feh_named":  ["dotlessfeh"],                 # dotless feh (seen in Urdu fonts)
    "qaf":        ["uniFED5","uniFED6","uniFED7","uniFED8"],
    "noon":       ["uniFEE5","uniFEE6","uniFEE7","uniFEE8"],
    "noon_named": ["noonChashm"],                 # chashm-noon variant
}
LONG_ASC = {  # ل ط ظ + kaaf forms (kaaf-before-kaaf)
    "lam":        ["uniFEDD","uniFEDE","uniFEDF","uniFEE0"],
    "tah":        ["uniFEC1","uniFEC2","uniFEC3","uniFEC4"],
    "zah":        ["uniFEC5","uniFEC6","uniFEC7","uniFEC8"],
    "kaaf":       ["uniFED9","uniFEDA","uniFEDB","uniFEDC"],
    "kaaf_named": ["kaafDouble"],                 # double-story kaaf variant
}
ABOVE_MARKS = ["uni064B","uni064C","uni064E","uni064F","uni0651","uni0652","uni0653","uni0670"]
NONJOIN = [
    # Arabic Presentation Forms — final and isolated forms of non-joining letters
    # alef family
    "uniFE8E","uniFE8D","uniFE8C","uniFE8B","uniFE8A","uniFE89",
    "uniFE88","uniFE87","uniFE86","uniFE85","uniFE84","uniFE83","uniFE82","uniFE81",
    # waw family
    "uniFEEE","uniFEED",
    # dal / dhal / thal
    "uniFEAA","uniFEA9","uniFEAC","uniFEAB",
    # reh / zay
    "uniFEAE","uniFEAD","uniFEB0","uniFEAF",
    # Base Unicode forms (produced by HarfBuzz Arabic shaping for non-joining chars)
    "uni0627","uni0622","uni0623","uni0625","uni0671",  # alef forms
    "uni0648","uni0624",                                 # waw
    "uni062F","uni0630",                                 # dal / thal
    "uni0631","uni0632","uni0691","uni0698",             # reh / zay variants
    "uni06D2","uni06D3",                                 # yeh barree
    # Ligature finals that end with a non-joining form (reh/waw/dal side)
    # Covers: hamza+reh/zay, beh+reh/zay, teh+reh/zay, theh+reh/zay,
    #         noon+reh/zay, yeh+reh/zay, etc.
    "uniFC6A","uniFC6B","uniFC64","uniFC65","uniFC70","uniFC71","uniFC76","uniFC77",
    "uniFC8A","uniFC8B","uniFC91","uniFC92",
]

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
        "nonJoinFinals": variants(tt, NONJOIN),  # also picks up .short/.alt variants
    }
    for k, v in classes.items():
        assert v, f"class @{k} is empty"
        for g in v:
            assert g in names, f"@{k} references missing glyph {g}"
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
