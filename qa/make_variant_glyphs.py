#!/usr/bin/env python3
"""make_variant_glyphs.py — add scripted glyph variants to the UFO (no manual draw).
--kasra-k : copy uni0650 -> uni0650.k and uni064D -> uni064D.k (identical outline)
            so a contextual GSUB can swap to a re-anchored variant before waw/reh.
The re-anchoring is done in features.fea via a markClass with shifted anchor."""
import sys, os, defcon
UFO = os.path.join(os.path.dirname(__file__), "..", "sources", "FatemiMaqala-Regular.ufo")
def copy_glyph(font, src, dst):
    if dst in font: del font[dst]
    g = font[src]; font.newGlyph(dst); ng = font[dst]; ng.width = g.width
    g.draw(ng.getPen())
    for a in g.anchors: ng.appendAnchor({"name": a["name"], "x": a["x"], "y": a["y"]})
    return ng
def main():
    font = defcon.Font(UFO)
    if "--kasra-k" in sys.argv:
        for src, dst in [("uni0650","uni0650.k"), ("uni064D","uni064D.k")]:
            copy_glyph(font, src, dst)
        print("added uni0650.k, uni064D.k")
    font.save()
if __name__ == "__main__": main()
