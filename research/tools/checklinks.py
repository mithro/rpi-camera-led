# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
"""Check every http(s) link in the given markdown files.

Usage:
    uv run checklinks.py <file.md> [<file.md> ...]

Each unique URL is fetched with a browser User-Agent. Reports the HTTP
status, final URL after redirects, and content type. Links ending in .pdf
must actually serve a PDF (%PDF magic bytes) to count as OK — some hosts
soft-fail by serving an HTML error page with status 200.
"""

import re
import sys

import requests

UA = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
}

URL_RE = re.compile(r"https?://[^\s)\]>\"']+")

# These hosts block non-browser clients (nxp.com serves 404, the Amphenol CDN
# serves 403). Each URL below was verified in a real browser on 2026-09-01:
# HTTP 200, and the .pdf URLs served genuine application/pdf content.
BROWSER_VERIFIED = {
    "https://www.nxp.com/products/power-drivers/lighting-driver-and-controller-ics/led-drivers/16-channel-12-bit-pwm-fm-plus-ic-bus-led-driver:PCA9685",
    "https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf",
    "https://cdn.amphenol-cs.com/media/wysiwyg/files/documentation/datasheet/flex/flexconnectors_100mm_sfw_r.pdf",
    "https://cdn.amphenol-cs.com/media/wysiwyg/files/drawing/10172241.pdf",
}


def check(url):
    try:
        r = requests.get(url, headers=UA, timeout=30, allow_redirects=True, stream=True)
        head = next(r.iter_content(1024), b"")
        ctype = r.headers.get("content-type", "?").split(";")[0]
        ok = r.status_code == 200
        note = ""
        if url.lower().endswith(".pdf") or "pdf" in ctype:
            if not head.startswith(b"%PDF"):
                ok = False
                note = f"not-a-pdf ({ctype}, starts {head[:20]!r})"
        if r.url.rstrip("/") != url.rstrip("/"):
            note += f" redirected-> {r.url}"
        return ok, r.status_code, note
    except Exception as e:
        return False, None, f"{type(e).__name__}: {e}"


def main():
    urls = {}
    for path in sys.argv[1:]:
        for url in URL_RE.findall(open(path).read()):
            url = url.rstrip(".,;")
            urls.setdefault(url, []).append(path)
    good = bad = 0
    for url in sorted(urls):
        ok, status, note = check(url)
        if not ok and url in BROWSER_VERIFIED:
            ok, note = True, "bot-blocked; verified 200 in a real browser (see BROWSER_VERIFIED)"
        if ok:
            good += 1
            print(f"OK   {status} {url} {note}")
        else:
            bad += 1
            print(f"FAIL {status} {url} {note}  [{', '.join(sorted(set(urls[url])))}]")
    print(f"\n{good} ok, {bad} failed of {len(urls)} unique URLs")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
