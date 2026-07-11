# Perseus Ontology Editor Manual

A bilingual (English / French) user manual for the ontology editing UI in
[Lettria Perseus](https://app.perseus.lettria.net), published as a single self-contained
web page and as PDFs.

**Read it:** https://jalakoo.github.io/perseus-ontology-manual/
*(after GitHub Pages is enabled — see [Publishing to GitHub Pages](#publishing-to-github-pages))*

---

## Table of Contents

- [What's in here](#whats-in-here)
- [Repository layout](#repository-layout)
- [Requirements](#requirements)
- [Building](#building)
- [Editing the manual](#editing-the-manual)
    - [Text](#text)
    - [Keeping the two languages in sync](#keeping-the-two-languages-in-sync)
    - [Headings, the TOC, and anchors](#headings-the-toc-and-anchors)
    - [Figures](#figures)
- [Publishing to GitHub Pages](#publishing-to-github-pages)
    - [One-time setup](#one-time-setup)
    - [Publishing an update](#publishing-an-update)
    - [Troubleshooting](#troubleshooting)
- [How the build works](#how-the-build-works)

---

## What's in here

The manual covers the Perseus ontology editor for developers: the Classes / Properties /
Individuals tabs, domain and range, annotations, individuals and identity, the version
history, the keyboard shortcuts, and a worked example — plus a glossary of the graph and
OWL/RDF terminology the UI assumes.

The built page has a left-hand contents drawer, a language toggle (🇬🇧 / 🇫🇷), and a
**Save as PDF** button. Every screenshot is embedded in the HTML, so the page is a single
file with no external requests.

## Repository layout

| Path | What it is |
| --- | --- |
| `manual.md` | English source. **Edit this.** |
| `manual.fr.md` | French source. **Edit this.** |
| `manual_assets/` | The 28 figures, cropped and sized for the manual. |
| `build_manual.py` | Build script: Markdown → the published site. |
| `docs/` | **Build output — do not hand-edit.** What GitHub Pages serves. |
| `docs/index.html` | The manual: self-contained, bilingual, ~3.9 MB. |
| `docs/manual.pdf`, `docs/manual.fr.pdf` | One PDF per language. |
| `screengrabs/` | Original untouched screenshots, kept as the source for `manual_assets/`. |
| `ttl_references/` | Example `.ttl` files, kept as evidence for the simple-vs-advanced card menu explanation in §3. |

The screen recording the figures were captured from is **not** committed (see
`.gitignore`) — it is 13 MB and every frame the manual uses has already been extracted
into `manual_assets/`.

## Requirements

- **Python 3** with [`markdown`](https://pypi.org/project/Markdown/):
  ```sh
  pip3 install markdown
  ```
- **Google Chrome or Chromium** — only for `--pdf`. Without it the HTML still builds, and
  you can export a PDF from the page's own **Save as PDF** button.

## Building

```sh
python3 build_manual.py          # writes docs/index.html
python3 build_manual.py --pdf    # also writes docs/manual.pdf and docs/manual.fr.pdf
```

Open `docs/index.html` in a browser to read it locally — no server needed.

Watch the build output. It checks every internal link on every run:

```
internal links OK (84 anchors resolve)
wrote docs/index.html  (3,872 KB, 28 figures, langs: en, fr)
```

If a link breaks, it tells you exactly which, and you should fix it before committing:

```
!! broken internal links (anchor has no matching heading):
   #domain-and-range
```

It also warns about missing image files. Don't ignore either warning.

## Editing the manual

### Text

Edit `manual.md` (and `manual.fr.md`), then rebuild. **Never edit `docs/index.html`** — the
next build overwrites it.

### Keeping the two languages in sync

The two files must stay **structurally parallel**: same headings, in the same order, with
the same figures in the same positions. The language toggle swaps between them, so a
section added to one and not the other silently disappears for that language's readers.
Nothing enforces this, so if you add a section to `manual.md`, add it to `manual.fr.md`.

UI labels are deliberately left in English in the French text (`Add Class`, `Save`,
`Domain`), because the Perseus interface itself is in English — a French reader still has
to find an English button.

### Headings, the TOC, and anchors

The contents drawer is generated from the headings, so a new `##` or `###` appears in it
automatically.

The Table of Contents block at the top of each Markdown file is **separate**. It exists so
the files read well on GitHub, and the build strips it out of the HTML. A new section
therefore needs its TOC entry added by hand, with an anchor that matches GitHub's slug
rules: lowercase, punctuation stripped, spaces to hyphens — and **runs of spaces are not
collapsed**, so `URI / IRI` becomes `#uri--iri`, with two hyphens. Sub-entries are indented
four spaces. The link check will catch you if you get it wrong.

### Figures

Put the image in `manual_assets/` and reference it normally. The alt text becomes the
caption:

```markdown
![The Save ontology dialog](manual_assets/fig-14-save-dialog.png)
```

Images are inlined at build time, so the page stays self-contained.

If you add a **small crop** (a menu, a dropdown — anything under roughly 600px wide), add
its filename stem to the `NATURAL` set near the top of `build_manual.py`. That renders it at
its native size instead of stretching it across the column, where a 1x capture just looks
blurry.

To pull a new frame from a screen recording:

```sh
ffmpeg -ss 126 -i recording.mp4 -frames:v 1 frame.png          # grab at 126 seconds
ffmpeg -i frame.png -vf "crop=W:H:X:Y" manual_assets/fig-NN.png # trim to the panel
```

## Publishing to GitHub Pages

Pushing to the repo is **not** enough on its own — Pages has to be switched on once, and
told which folder to serve. After that, every push republishes automatically.

### One-time setup

1. Push the repo, including the `docs/` folder:
   ```sh
   git add .
   git commit -m "Add Perseus ontology editor manual"
   git push -u origin main
   ```
2. On GitHub, go to the repo → **Settings** → **Pages** (left sidebar).
3. Under **Build and deployment**:
   - **Source:** `Deploy from a branch`
   - **Branch:** `main`, folder `/docs`
   - Click **Save**.
4. Wait a minute or two for the first deploy — the Pages section shows a green banner with
   the live URL, and the **Actions** tab shows a `pages build and deployment` run.
5. The manual is then at `https://<user>.github.io/<repo>/` — for this repo,
   **https://jalakoo.github.io/perseus-ontology-manual/**

The site is public even if the repository is private, unless you are on a plan with private
Pages. If the repo is private and the manual should stay internal, check that before
enabling.

### Publishing an update

```sh
python3 build_manual.py --pdf
git add -A
git commit -m "Describe the change"
git push
```

Pages redeploys on its own within a minute or so. **The `docs/` folder must be committed** —
GitHub Pages serves files from the repository and does not run the build script. If you
forget to rebuild before committing, the site will keep showing the previous version even
though the Markdown changed.

### Troubleshooting

| Symptom | Cause |
| --- | --- |
| 404 at the Pages URL | Pages not enabled yet, or the branch/folder is set to something other than `main` + `/docs`. |
| Site shows an old version | `docs/` wasn't rebuilt, or wasn't committed, before the push. |
| Page loads but the screenshots are missing | JavaScript is disabled in the browser. The images are applied from an inlined JS map at load time. |
| Content is there but unstyled or the drawer is missing | Deployment served the raw Markdown rather than `docs/index.html` — re-check the folder setting is `/docs`. |

`docs/.nojekyll` is committed on purpose: it stops GitHub from running the folder through
Jekyll, which would ignore files beginning with an underscore. Leave it in place.

## How the build works

`build_manual.py` renders both Markdown files with `python-markdown`, then assembles one
HTML document containing both languages:

- **Images are embedded once.** Each figure becomes a base64 data URI in a single JS map,
  and both language copies point at the same entry. Inlining them per-language would double
  the file size for no benefit — the tradeoff is that the screenshots need JavaScript.
- **French ids and anchors are namespaced** with an `fr-` prefix, so the two copies can live
  in one document without duplicate `id`s (both languages have a `### Types`, for example).
- **The language choice persists** in `localStorage`, can be forced with `?lang=fr`, and
  falls back to the browser's preferred language on a first visit.
- **The PDFs are printed from the same HTML** by headless Chrome, one per language, using
  the same print stylesheet as the in-page **Save as PDF** button — so the button and the
  committed PDFs produce the same document.
