#!/usr/bin/env python3
"""Build a standalone, bilingual HTML manual from manual.md + manual.fr.md.

Output is a single self-contained file: images are inlined as base64, the table of
contents becomes a left-hand drawer, and a flag toggle switches the whole document
between English and French. No external requests, no build step to view it.

    python3 build_manual.py          # writes docs/index.html
    python3 build_manual.py --pdf    # also writes the two PDFs (headless Chrome)

Everything is written to docs/, which is what GitHub Pages serves. Open
docs/index.html directly in a browser to read it locally — it needs no server.

Each image is embedded ONCE, into a JS map, and applied to both language copies at
load time — inlining twice would double the file size for no benefit.
"""

import base64
import mimetypes
import pathlib
import re
import sys

try:
    import markdown
except ImportError:
    sys.exit("python-markdown is required:  pip3 install markdown")

ROOT = pathlib.Path(__file__).parent
SITE = ROOT / "docs"          # GitHub Pages serves this folder
OUT = SITE / "index.html"

# Where readers' edits and suggestions go. The "Edit this page" links point at the
# Markdown SOURCE (manual.md / manual.fr.md), never the generated docs/index.html.
REPO = "https://github.com/jalakoo/perseus-ontology-manual"
BRANCH = "main"
ISSUE_TEMPLATE = "suggest-change.yml"   # see .github/ISSUE_TEMPLATE/

LANGS = {
    "en": {
        "src": ROOT / "manual.md",
        "label": "English",
        "toc_heading": "Table of Contents",
        "pdf": "Save as PDF",
        "contents": "Contents",
        "bar_edit": "Edit",
        "bar_suggest": "Suggest",
        "edit_title": "Edit this page on GitHub",
        "suggest_title": "Suggest a change",
    },
    "fr": {
        "src": ROOT / "manual.fr.md",
        "label": "Français",
        "toc_heading": "Table des matières",
        "pdf": "Enregistrer en PDF",
        "contents": "Sommaire",
        "bar_edit": "Modifier",
        "bar_suggest": "Suggérer",
        "edit_title": "Modifier cette page sur GitHub",
        "suggest_title": "Suggérer une modification",
    },
}

# Small 1x UI crops: show at native size rather than stretching to the column width.
NATURAL = {
    "fig-02-card-menu", "fig-17-resource-menu", "fig-12-property-tabs",
    "fig-12b-individuals-list", "fig-10-parents-dropdown",
    "fig-09-relationships-dropdown", "fig-15-version-history",
    "fig-14-save-dialog", "fig-19-card-menu-advanced",
}

FLAG_EN = (
    '<svg viewBox="0 0 60 30" aria-hidden="true">'
    '<clipPath id="uk-c"><path d="M0,0 v30 h60 v-30 z"/></clipPath>'
    '<rect width="60" height="30" fill="#012169"/>'
    '<path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/>'
    '<path d="M0,0 L60,30 M60,0 L0,30" stroke="#C8102E" stroke-width="4" clip-path="url(#uk-c)"/>'
    '<path d="M30,0 v30 M0,15 h60" stroke="#fff" stroke-width="10"/>'
    '<path d="M30,0 v30 M0,15 h60" stroke="#C8102E" stroke-width="6"/></svg>'
)
FLAG_FR = (
    '<svg viewBox="0 0 60 30" aria-hidden="true">'
    '<rect width="20" height="30" x="0" fill="#0055A4"/>'
    '<rect width="20" height="30" x="20" fill="#fff"/>'
    '<rect width="20" height="30" x="40" fill="#EF4135"/></svg>'
)

CSS = """
:root {
  --fg: #1c1e21;
  --muted: #5c6570;
  --rule: #e3e6ea;
  --accent: #5b4bd6;
  --code-bg: #f5f6f8;
  --figure-bg: #0e0e10;
  --drawer-w: 290px;
  --bar-h: 36px;          /* shared height for every topbar control */
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 24px; }
body {
  margin: 0;
  font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Helvetica, Arial, sans-serif;
  color: var(--fg);
  background: #fff;
}
[hidden] { display: none !important; }

/* ---------- top bar ---------- */
.topbar {
  position: fixed; top: 0; right: 0; z-index: 30;
  display: flex; align-items: center; gap: 8px;
  padding: 14px 18px;
}
.langgroup { display: flex; align-items: center; gap: 4px; height: var(--bar-h); padding: 3px; background: #eceef1; border-radius: 9px; }
.langbtn {
  display: grid; place-items: center; width: 38px; height: 30px; padding: 0;
  border: 0; border-radius: 6px; background: transparent; cursor: pointer;
  opacity: .5; transition: opacity .12s, background .12s;
}
.langbtn:hover { opacity: .85; }
.langbtn[aria-pressed="true"] { opacity: 1; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.14); }
.langbtn svg { width: 24px; height: 16px; border-radius: 2px; display: block; }
.pdfbtn {
  display: inline-flex; align-items: center; justify-content: center;
  height: var(--bar-h); font: 600 .85rem/1 inherit; color: #fff; background: var(--accent);
  border: 0; border-radius: 8px; padding: 0 15px; cursor: pointer;
  box-shadow: 0 2px 10px rgba(0,0,0,.16); white-space: nowrap;
}
.pdfbtn:hover { filter: brightness(1.08); }
/* "Edit" / "Suggest" links — ghost buttons that sit beside the language and PDF controls. */
.linkbtn {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  height: var(--bar-h); font: 600 .85rem/1 inherit; color: var(--fg);
  background: #fff; border: 1px solid var(--rule); border-radius: 8px;
  padding: 0 12px; text-decoration: none; white-space: nowrap;
  box-shadow: 0 2px 10px rgba(0,0,0,.10);
}
.linkbtn:hover { text-decoration: none; border-color: var(--accent); color: var(--accent); }
.linkbtn .ico { font-size: .95rem; line-height: 1; }
/* Below this width the topbar gets crowded, so the link buttons collapse to their icons. */
@media (max-width: 860px) {
  .linkbtn .lbl { display: none; }
  .linkbtn { padding: 0 10px; }
}

/* ---------- drawer ---------- */
.drawer {
  position: fixed; top: 0; left: 0; bottom: 0; width: var(--drawer-w); z-index: 20;
  padding: 26px 14px 40px 22px; overflow-y: auto;
  border-right: 1px solid var(--rule); background: #fbfbfc;
}
.drawer h2 {
  margin: 0 0 12px; font-size: .72rem; font-weight: 700; letter-spacing: .09em;
  text-transform: uppercase; color: var(--muted);
}
.drawer ul { list-style: none; margin: 0; padding: 0; }
.drawer li { margin: 0; }
.drawer > nav > ul > li > a { font-weight: 600; }
.drawer ul ul { margin: 2px 0 6px; padding-left: 12px; border-left: 1px solid var(--rule); }
.drawer ul ul a { font-size: .85rem; color: var(--muted); font-weight: 400; }
.drawer a {
  display: block; padding: 4px 8px; margin: 1px 0; border-radius: 6px;
  font-size: .89rem; line-height: 1.35; color: var(--fg); text-decoration: none;
}
.drawer a:hover { background: #eef0f3; }
.drawer a.active { background: #eeebfd; color: var(--accent); font-weight: 600; }
.drawertoggle {
  display: none; position: fixed; top: 14px; left: 14px; z-index: 31;
  width: 40px; height: 40px; padding: 0; font-size: 1.1rem;
  border: 1px solid var(--rule); border-radius: 9px; background: #fff; cursor: pointer;
  box-shadow: 0 2px 10px rgba(0,0,0,.10);
}
.scrim { display: none; position: fixed; inset: 0; z-index: 19; background: rgba(0,0,0,.35); }

/* ---------- article ---------- */
main { margin-left: var(--drawer-w); }
.page { max-width: 800px; margin: 0 auto; padding: 60px 28px 140px; }

h1 { font-size: 2.05rem; line-height: 1.2; margin: 0 0 .4em; letter-spacing: -.02em; }
h2 {
  font-size: 1.45rem; margin: 2.6em 0 .7em; padding-top: .7em;
  border-top: 1px solid var(--rule); letter-spacing: -.01em;
}
h3 { font-size: 1.12rem; margin: 2em 0 .5em; }
h1 + p, h2 + p { margin-top: 0; }
/* The Markdown uses --- between sections; on screen the h2 rule already does that job. */
.page hr { display: none; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

code {
  font: 0.875em/1.5 ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  background: var(--code-bg); padding: .12em .38em; border-radius: 4px;
}
pre {
  background: var(--code-bg); border: 1px solid var(--rule); border-radius: 8px;
  padding: 14px 16px; overflow-x: auto;
}
pre code { background: none; padding: 0; font-size: .84rem; }

table { border-collapse: collapse; width: 100%; margin: 1.4em 0; font-size: .93rem; }
th, td { border: 1px solid var(--rule); padding: 9px 12px; text-align: left; vertical-align: top; }
th { background: var(--code-bg); font-weight: 600; }

blockquote {
  margin: 1.4em 0; padding: .6em 1.1em; border-left: 3px solid var(--accent);
  background: #f7f6fd; color: var(--muted);
}
blockquote p { margin: .3em 0; }

figure {
  margin: 1.8em 0; padding: 12px; background: var(--figure-bg);
  border: 1px solid var(--rule); border-radius: 10px;
}
figure img { display: block; width: 100%; height: auto; border-radius: 5px; }
/* Small UI crops are 1x captures — upscaling them just makes them blurry. */
figure.natural { width: fit-content; max-width: 100%; }
figure.natural img { width: auto; max-width: 100%; }
figcaption {
  margin-top: 10px; padding: 0 2px; font-size: .82rem; line-height: 1.45;
  color: #9aa2ad;
}
figcaption code { background: #24262b; color: #d6d9de; }

/* ---------- narrow screens ---------- */
@media (max-width: 1100px) {
  main { margin-left: 0; }
  .page { padding-top: 74px; }
  .drawertoggle { display: block; }
  .drawer { transform: translateX(-100%); transition: transform .18s ease; box-shadow: 0 0 30px rgba(0,0,0,.16); }
  body.drawer-open .drawer { transform: none; }
  body.drawer-open .scrim { display: block; }
}

/* ---------- print ---------- */
@media print {
  @page { size: A4; margin: 16mm 14mm; }
  body { font-size: 10.5pt; }
  .topbar, .drawer, .drawertoggle, .scrim { display: none !important; }
  main { margin-left: 0; }
  .page { max-width: none; padding: 0; }
  a { color: var(--fg); text-decoration: none; }
  h2 { break-before: page; page-break-before: always; border-top: 0; }
  h2:first-of-type { break-before: auto; page-break-before: auto; }
  h2, h3 { break-after: avoid; page-break-after: avoid; }
  figure, pre, table, blockquote { break-inside: avoid; page-break-inside: avoid; }
  figure { max-width: 100%; }
  img { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
"""

JS = """
(function () {
  // Images are stored once and applied to every copy that references them, so the
  // two language versions don't each carry their own base64 payload.
  document.querySelectorAll('img[data-fig]').forEach(function (img) {
    var src = FIGS[img.getAttribute('data-fig')];
    if (src) img.src = src;
  });

  var LANGS = ['en', 'fr'];
  var body = document.body;

  function available(lang) {
    return !!document.querySelector('.lang[data-lang="' + lang + '"]');
  }

  function setLang(lang) {
    if (!available(lang)) lang = 'en';
    document.documentElement.lang = lang;
    LANGS.forEach(function (l) {
      document.querySelectorAll('[data-lang="' + l + '"]').forEach(function (el) {
        el.hidden = (l !== lang);
      });
      var btn = document.querySelector('.langbtn[data-set-lang="' + l + '"]');
      if (btn) btn.setAttribute('aria-pressed', String(l === lang));
    });
    var pdf = document.querySelector('.pdfbtn');
    if (pdf) pdf.textContent = pdf.getAttribute('data-label-' + lang) || pdf.textContent;
    try { localStorage.setItem('perseus-manual-lang', lang); } catch (e) {}
    syncActive();
  }

  document.querySelectorAll('.langbtn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      setLang(btn.getAttribute('data-set-lang'));
      window.scrollTo({ top: 0 });
    });
  });

  // Initial language: ?lang= wins, then last choice, then browser preference.
  var initial = new URLSearchParams(location.search).get('lang');
  if (!initial) { try { initial = localStorage.getItem('perseus-manual-lang'); } catch (e) {} }
  if (!initial) initial = (navigator.language || 'en').toLowerCase().startsWith('fr') ? 'fr' : 'en';
  setLang(initial);

  // Drawer (narrow screens only; it is always open on wide ones).
  var toggle = document.querySelector('.drawertoggle');
  var scrim = document.querySelector('.scrim');
  function closeDrawer() { body.classList.remove('drawer-open'); }
  if (toggle) toggle.addEventListener('click', function () { body.classList.toggle('drawer-open'); });
  if (scrim) scrim.addEventListener('click', closeDrawer);
  document.querySelectorAll('.drawer a').forEach(function (a) {
    a.addEventListener('click', closeDrawer);
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeDrawer(); });

  // Highlight the section currently on screen in the drawer.
  var links = {}, observer = null;
  function syncActive() {
    if (observer) observer.disconnect();
    links = {};
    var nav = document.querySelector('.drawer nav:not([hidden])');
    var article = document.querySelector('.lang:not([hidden])');
    if (!nav || !article) return;
    nav.querySelectorAll('a[href^="#"]').forEach(function (a) {
      links[decodeURIComponent(a.getAttribute('href').slice(1))] = a;
    });
    var seen = [];
    observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        var id = en.target.id;
        if (en.isIntersecting) { if (seen.indexOf(id) < 0) seen.push(id); }
        else { seen = seen.filter(function (s) { return s !== id; }); }
      });
      var current = seen[0];
      if (!current) return;
      Object.keys(links).forEach(function (id) { links[id].classList.toggle('active', id === current); });
    }, { rootMargin: '0px 0px -70% 0px' });
    article.querySelectorAll('h2[id], h3[id]').forEach(function (h) { observer.observe(h); });
  }
})();
"""


def main() -> None:
    langs = {k: v for k, v in LANGS.items() if v["src"].is_file()}
    if "en" not in langs:
        sys.exit("manual.md not found")
    for code in LANGS:
        if code not in langs:
            print(f"!! {LANGS[code]['src'].name} missing — building without {code}")

    figures: dict[str, str] = {}   # fig key -> data URI, emitted once
    articles, navs, missing = [], [], []

    for code, cfg in langs.items():
        text = strip_toc_section(cfg["src"].read_text(), cfg["toc_heading"])

        md = markdown.Markdown(
            extensions=["tables", "fenced_code", "toc", "attr_list", "sane_lists"],
            extension_configs={"toc": {"slugify": github_slugify, "toc_depth": "2-3"}},
        )
        html = md.convert(text)
        html = re.sub(
            r'<p><img alt="(?P<alt>[^"]*)" src="(?P<src>[^"]+)"\s*/?></p>',
            lambda m: figure_html(m, figures, missing),
            html,
        )
        toc = md.toc

        # Namespace the French ids/anchors so the two copies can coexist in one
        # document without duplicate ids (e.g. "### Types" exists in both).
        if code != "en":
            html = prefix_anchors(html, code)
            toc = prefix_anchors(toc, code)

        articles.append(f'<article class="lang page" data-lang="{code}">\n{html}\n</article>')
        navs.append(
            f'<nav data-lang="{code}"><h2>{cfg["contents"]}</h2>\n{toc}\n</nav>'
        )

    if missing:
        print("!! missing images:", *sorted(set(missing)), sep="\n   ")

    figs_js = "var FIGS = {\n" + ",\n".join(
        f'  "{k}": "{v}"' for k, v in sorted(figures.items())
    ) + "\n};"

    en, fr = LANGS["en"], LANGS["fr"]
    topbar = (
        '<div class="topbar">'
        '<div class="langgroup">'
        f'<button class="langbtn" data-set-lang="en" aria-pressed="true" '
        f'title="{en["label"]}" aria-label="{en["label"]}">{FLAG_EN}</button>'
        f'<button class="langbtn" data-set-lang="fr" aria-pressed="false" '
        f'title="{fr["label"]}" aria-label="{fr["label"]}">{FLAG_FR}</button>'
        "</div>"
        f"{bar_links(en, fr)}"
        f'<button class="pdfbtn" data-label-en="{en["pdf"]}" data-label-fr="{fr["pdf"]}" '
        f'onclick="window.print()">{en["pdf"]}</button>'
        "</div>"
    )

    page = (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Lettria Perseus — Ontology Editor Manual</title>\n"
        f"<style>{CSS}</style>\n</head>\n<body>\n"
        f"{topbar}\n"
        '<button class="drawertoggle" aria-label="Contents">&#9776;</button>\n'
        '<div class="scrim"></div>\n'
        f'<aside class="drawer">\n{chr(10).join(navs)}\n</aside>\n'
        f"<main>\n{chr(10).join(articles)}\n</main>\n"
        f"<script>{figs_js}\n{JS}</script>\n"
        "</body>\n</html>\n"
    )

    check_anchors(page)
    SITE.mkdir(exist_ok=True)
    # Tells GitHub Pages to serve the folder as-is instead of running it through Jekyll,
    # which would otherwise ignore any file or folder whose name starts with an underscore.
    (SITE / ".nojekyll").write_text("")
    OUT.write_text(page)
    print(
        f"wrote {OUT.relative_to(ROOT)}  ({len(page.encode()) / 1024:,.0f} KB, "
        f"{len(figures)} figures, langs: {', '.join(langs)})"
    )

    if "--pdf" in sys.argv:
        export_pdf()


def bar_links(en: dict, fr: dict) -> str:
    """The "Edit" and "Suggest" topbar buttons, one <a> per language.

    Both target the Markdown SOURCE — "Edit" opens GitHub's web editor on
    manual.md / manual.fr.md (auto-forks and files a PR), "Suggest" opens a
    pre-filled issue. They deliberately never link docs/index.html, which is this
    generated file. The two language copies coexist and the existing setLang()
    show/hide (it toggles every [data-lang] element) swaps between them; the
    French copies start hidden so the default English view has no flash.
    """
    issue_url = f"{REPO}/issues/new?template={ISSUE_TEMPLATE}"

    def link(href: str, icon: str, label: str, title: str, code: str) -> str:
        hide = " hidden" if code != "en" else ""
        return (
            f'<a class="linkbtn" data-lang="{code}"{hide} href="{href}" '
            f'title="{escape_attr(title)}" aria-label="{escape_attr(title)}">'
            f'<span class="ico" aria-hidden="true">{icon}</span>'
            f'<span class="lbl">{escape_attr(label)}</span></a>'
        )

    out = []
    for code, cfg in (("en", en), ("fr", fr)):
        edit_url = f"{REPO}/edit/{BRANCH}/{cfg['src'].name}"
        out.append(link(edit_url, "✏️", cfg["bar_edit"], cfg["edit_title"], code))
    for code, cfg in (("en", en), ("fr", fr)):
        out.append(link(issue_url, "💬", cfg["bar_suggest"], cfg["suggest_title"], code))
    return "".join(out)


def strip_toc_section(text: str, heading: str) -> str:
    """Drop the hand-written TOC — in HTML it lives in the drawer instead.

    It stays in the Markdown because that is what makes the file navigable on GitHub.
    """
    lines = text.splitlines()
    start = next(
        (i for i, ln in enumerate(lines) if ln.startswith("## ") and heading.lower() in ln.lower()),
        None,
    )
    if start is None:
        return text
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() == "---"), len(lines))
    del lines[start:end + 1]
    return "\n".join(lines)


def figure_html(m: re.Match, figures: dict, missing: list) -> str:
    alt, src = m.group("alt"), m.group("src")
    path = (ROOT / src).resolve()
    if not path.is_file():
        missing.append(src)
        return m.group(0)
    key = path.stem
    if key not in figures:
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        figures[key] = f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"
    cls = ' class="natural"' if key in NATURAL else ""
    return (
        f'<figure{cls}><img alt="{escape_attr(alt)}" data-fig="{key}" loading="lazy">'
        f"<figcaption>{md_inline(alt)}</figcaption></figure>"
    )


def prefix_anchors(html: str, code: str) -> str:
    html = re.sub(r'id="([^"]+)"', lambda m: f'id="{code}-{m.group(1)}"', html)
    return re.sub(r'href="#([^"]+)"', lambda m: f'href="#{code}-{m.group(1)}"', html)


def md_inline(text: str) -> str:
    # `text` is an alt attribute, so Markdown has already entity-escaped it. Escaping
    # again would render the entity itself ("&quot;" instead of a quote mark).
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return re.sub(r"\*([^*]+)\*", r"<em>\1</em>", out)


def escape_attr(text: str, quotes: bool = True) -> str:
    out = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return out.replace('"', "&quot;") if quotes else out


def github_slugify(value: str, separator: str = "-") -> str:
    """Match GitHub's heading-anchor rules so hand-written TOC links resolve.

    GitHub strips punctuation, then maps each remaining whitespace character to a
    separator without collapsing runs — so "URI / IRI" becomes "uri--iri", with two
    hyphens. Do not "tidy" that up: it would silently break every anchor that works
    when the Markdown is viewed on GitHub.
    """
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    return re.sub(r"\s", separator, value)


def check_anchors(html: str) -> None:
    ids = set(re.findall(r'id="([^"]+)"', html))
    links = set(re.findall(r'href="#([^"]+)"', html))
    broken = sorted(links - ids)
    if broken:
        print("!! broken internal links (anchor has no matching heading):")
        for b in broken:
            print(f"   #{b}")
    else:
        print(f"internal links OK ({len(links)} anchors resolve)")


def export_pdf() -> None:
    """Render manual.html to manual.pdf via headless Chrome.

    Same print path as the in-page button, so the two produce the same document.
    Prints whichever language the page loads with, i.e. English by default.
    """
    import shutil
    import subprocess

    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
    ]
    chrome = next((c for c in candidates if c and pathlib.Path(c).is_file()), None)
    if not chrome:
        print("!! Chrome not found — open manual.html and use the Save as PDF button")
        return

    for code in ("en", "fr"):
        if not LANGS[code]["src"].is_file():
            continue
        pdf = SITE / ("manual.pdf" if code == "en" else f"manual.{code}.pdf")
        subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={pdf}", OUT.resolve().as_uri() + f"?lang={code}"],
            check=True, capture_output=True,
        )
        print(f"wrote {pdf.relative_to(ROOT)}  ({pdf.stat().st_size / 1024:,.0f} KB)")


if __name__ == "__main__":
    main()
