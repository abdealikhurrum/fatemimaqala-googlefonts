# Google Fonts onboarding issue — copy/paste into google/fonts

Open at: https://github.com/google/fonts/issues/new?assignees=&labels=II+New+Font%2C+%3E+Submission&template=1_add-font.md&title=Add+Fatemi+Maqala

Search existing issues for "Fatemi Maqala" first to avoid a duplicate.

---

**Title:** Add Fatemi Maqala

**Body:**

### Font project

- **Family name:** Fatemi Maqala
- **Upstream repository:** https://github.com/abdealikhurrum/fatemimaqala-googlefonts
- **Built font files:** `fonts/FatemiMaqala-Regular.ttf` (also staged for the GF
  entry under `gf-package/fatemimaqala/`)
- **Sources:** UFO (`sources/FatemiMaqala-Regular.ufo`) + `features.fea`, built
  with `gftools builder sources/config.yaml`
- **Designer:** Abdeali Khurrum
- **Scripts / subsets:** Arabic (primary) + Latin (GF Latin Core) + menu
- **Styles:** Regular (single weight, static)
- **Category:** Serif (Naskh)

### Licensing

- Licensed wholly under the **SIL Open Font License 1.1** (`OFL.txt`).
- **No Reserved Font Name** is declared.
- No proprietary version of this family is distributed elsewhere.
- I am the author/copyright holder and will sign the Google Contributor License
  Agreement; `AUTHORS.txt` lists all copyright holders.

### Provenance / right to release

Fatemi Maqala is an original retracing and extension, by the submitter, of the
Lisan ud Dawat Naskh manuscript hand. The outlines were substantially redrawn;
this OFL release covers the submitter's own font software. The originating
tradition (Aljamea-tus-Saifiyah / the Dawoodi Bohra community) is acknowledged
in `AUTHORS.txt` and `OFL.txt`. Some Arabic glyphs derive from Amiri and the
Latin from Crimson Text / Crimson Pro — all OFL; their copyright is preserved in
`OFL.txt`.

### Quality

- **FontBakery `check-googlefonts`: 0 FAIL, 0 ERROR** (108 PASS, 17 WARN).
  Remaining WARNs are documented in `qa/fontbakery-summary.md` — intentional
  (width-preserved honorific marks), inherent to the retraced/Crimson outlines,
  or onboarding-time items (article image, METADATA subsetting, vendor ID).
- Vertical metrics: GF-compliant (USE_TYPO_METRICS, typo/hhea 2500/-1400).
- Latin trimmed to exactly GF Latin Core; tabular figures.

### Anything else

This is a community-significant script; I'm happy to provide additional
provenance detail or design-review materials on request.
