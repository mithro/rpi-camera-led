# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown"]
# ///
"""Render the project's markdown documents to styled HTML pages.

Usage:
    uv run research/tools/render_html.py

Renders README.md to index.html and each research/*.md next to its source,
rewriting .md links to the corresponding .html pages. Run from the repository
root. Re-run after editing any of the markdown sources.
"""

import re
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent.parent

# (markdown source, html output, nav label)
PAGES = [
    ("README.md", "index.html", "Overview"),
    ("research/i2c-rgb-leds.md", "research/i2c-rgb-leds.html", "I2C RGB LEDs"),
    ("research/i2c-gpio-expanders.md", "research/i2c-gpio-expanders.html", "GPIO expanders"),
    ("research/cheap-mcus.md", "research/cheap-mcus.html", "Cheap MCUs"),
    ("research/fpc-connectors.md", "research/fpc-connectors.html", "FPC connectors"),
]

FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Archivo:wght@500;600;700"
    "&family=Source+Sans+3:ital,wght@0,400;0,600;1,400"
    "&family=IBM+Plex+Mono:wght@400;500"
    "&display=swap"
)

STYLE = """
:root {
  --ground: #F7F5F1;
  --surface: #FFFFFF;
  --ink: #20262A;
  --muted: #66707A;
  --accent: #A85B28;
  --accent-ink: #8C4A1F;
  --line: #E2DDD4;
  --row: #FAF8F4;
  --warn: #8A5A00;
  --code-bg: #F0EDE7;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground: #181B1E;
    --surface: #20242A;
    --ink: #E9E6E0;
    --muted: #9AA3AB;
    --accent: #D68F52;
    --accent-ink: #E0A06E;
    --line: #333941;
    --row: #24282F;
    --warn: #E0B25E;
    --code-bg: #272C33;
  }
}
:root[data-theme="dark"] {
  --ground: #181B1E;
  --surface: #20242A;
  --ink: #E9E6E0;
  --muted: #9AA3AB;
  --accent: #D68F52;
  --accent-ink: #E0A06E;
  --line: #333941;
  --row: #24282F;
  --warn: #E0B25E;
  --code-bg: #272C33;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--ground);
  color: var(--ink);
  font-family: "Source Sans 3", "Segoe UI", system-ui, sans-serif;
  font-size: 17px;
  line-height: 1.6;
}
header.site {
  border-bottom: 2px solid var(--accent);
  background: var(--surface);
}
header.site .inner {
  padding: 20px 24px 14px;
}
header.site .kicker {
  font-family: Archivo, "Segoe UI", system-ui, sans-serif;
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
}
header.site .kicker a { color: inherit; text-decoration: none; }
header.site .kicker a:hover { text-decoration: underline; }
nav.pages {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 18px;
  margin-top: 8px;
  font-family: Archivo, "Segoe UI", system-ui, sans-serif;
  font-size: 14px;
  font-weight: 500;
}
nav.pages a { color: var(--muted); text-decoration: none; padding: 2px 0; }
nav.pages a:hover { color: var(--accent); }
nav.pages a[aria-current="page"] {
  color: var(--ink);
  font-weight: 600;
  border-bottom: 2px solid var(--accent);
}
main {
  padding: 12px 24px 64px;
}
h1, h2, h3 {
  font-family: Archivo, "Segoe UI", system-ui, sans-serif;
  line-height: 1.2;
  text-wrap: balance;
}
h1 { font-size: 30px; font-weight: 700; margin-block: 28px 10px; }
h2 {
  font-size: 21px;
  font-weight: 600;
  margin-block: 40px 10px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}
h3 { font-size: 17px; font-weight: 600; margin-block: 24px 8px; }
a { color: var(--accent-ink); text-decoration-thickness: 1px; text-underline-offset: 2px; }
a:hover { color: var(--accent); }
strong { font-weight: 600; }
code {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 0.86em;
  background: var(--code-bg);
  padding: 1px 5px;
  border-radius: 3px;
}
ul { padding-left: 22px; }
li { margin: 4px 0; }
.table-wrap { overflow-x: auto; margin-block: 18px; }
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  line-height: 1.45;
  font-variant-numeric: tabular-nums;
  min-width: 640px;
}
th, td {
  text-align: left;
  vertical-align: top;
  padding: 8px 14px 8px 0;
  border-bottom: 1px solid var(--line);
}
th {
  font-family: Archivo, "Segoe UI", system-ui, sans-serif;
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--muted);
  border-bottom: 2px solid var(--line);
  white-space: nowrap;
}
tbody tr:nth-child(even) td { background: var(--row); }
td:first-child, td:first-child a {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 13px;
  font-weight: 500;
}
td strong { color: var(--warn); }
footer.site {
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 13.5px;
  padding: 14px 24px 40px;
}
@media (prefers-reduced-motion: no-preference) {
  a { transition: color 120ms ease; }
}
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{fonts}">
<style>{style}</style>
</head>
<body>
<header class="site">
  <div class="inner">
    <div class="kicker"><a href="{home}">RPi Camera LED — part availability research</a></div>
    <nav class="pages">
{nav}
    </nav>
  </div>
</header>
<main>
{body}
</main>
<footer class="site">
  Data collected 2026-09-01 from jlcpcb.com and hqonline.com.
  Generated from <a href="{source}">{source_name}</a> by
  <code>research/tools/render_html.py</code>.
</footer>
</body>
</html>
"""


def wrap_tables(html):
    return html.replace("<table>", '<div class="table-wrap"><table>').replace(
        "</table>", "</table></div>"
    )


def rewrite_md_links(html, src_dir):
    """Point links at .md sources to their rendered .html siblings."""
    known = {str((ROOT / md).resolve()): out for md, out, _ in PAGES}

    def sub(m):
        href = m.group(1)
        if href.startswith(("http://", "https://", "#")) or not href.endswith(".md"):
            return m.group(0)
        target = str(((ROOT / src_dir) / href).resolve())
        if target in known:
            rel = Path(known[target])
            base = Path(src_dir)
            try:
                href = str(rel.relative_to(base))
            except ValueError:
                href = "../" * len(base.parts) + str(rel)
            return f'href="{href}"'
        return m.group(0)

    return re.sub(r'href="([^"]+)"', sub, html)


def main():
    md = markdown.Markdown(extensions=["tables", "fenced_code"])
    for src, out, label in PAGES:
        text = (ROOT / src).read_text()
        body = wrap_tables(md.reset().convert(text))
        body = rewrite_md_links(body, str(Path(src).parent))
        title_m = re.search(r"<h1>(.*?)</h1>", body, re.S)
        title = re.sub(r"<[^>]+>", "", title_m.group(1)) if title_m else label
        depth = len(Path(out).parts) - 1
        prefix = "../" * depth
        nav = "\n".join(
            f'      <a href="{prefix}{o}"'
            + (' aria-current="page"' if o == out else "")
            + f">{l}</a>"
            for _, o, l in PAGES
        )
        page = TEMPLATE.format(
            title=title,
            fonts=FONTS,
            style=STYLE,
            home=prefix + "index.html",
            nav=nav,
            body=body,
            source=prefix + src,
            source_name=src,
        )
        (ROOT / out).write_text(page)
        print(f"rendered {src} -> {out}")


if __name__ == "__main__":
    main()
