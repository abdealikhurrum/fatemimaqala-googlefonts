# gf-package — Google Fonts submission staging

This folder stages everything needed to onboard **Fatemi Maqala** to Google
Fonts. Nothing here is published until you act on it.

## Contents

- `fatemimaqala/` — mirrors the target directory `ofl/fatemimaqala/` in the
  [google/fonts](https://github.com/google/fonts) repo:
  - `FatemiMaqala-Regular.ttf` — the built font (FontBakery `check-googlefonts`:
    0 FAIL / 0 ERROR).
  - `OFL.txt` — license.
  - `METADATA.pb` — **draft** family metadata. GF's `gftools packager`
    regenerates this canonically from the `source { }` block; provided so
    reviewers can see intended values (category, subsets, primary_script: Arab).
  - `article/ARTICLE.en_us.html` — the family description shown on the GF
    specimen page.
  - `article/specimen.png` — rendered shaping sample.

- `ONBOARDING-ISSUE.md` — ready-to-paste text for the google/fonts onboarding
  issue, with the prefilled issue URL.

## How to submit (you do these — they are public actions)

1. **Sign the Google CLA** (individual): https://cla.developers.google.com/
   Every name in `AUTHORS.txt` must be covered.
2. **Open the onboarding issue** using `ONBOARDING-ISSUE.md`. This is the
   recommended path for a first family — the GF team drives the rest.
3. The GF team reviews design quality + licensing/provenance, runs FontBakery in
   their sandbox, and (when satisfied) generates the real METADATA.pb and opens
   the production PR. Respond to any review notes.

The upstream repo is the source of truth; the GF pipeline pulls from it via the
`source { }` block in METADATA.pb.
