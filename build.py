#!/usr/bin/env python3
"""Build the static site into _site/ from site.json and src/.

    python3 build.py            build into _site/
    python3 build.py --serve    build, then serve _site/ on http://localhost:8000
    python3 build.py --all      preview: build hidden pages too (never deploy this)

Only pages marked "published": true in site.json are built. A page whose parent
is unpublished is skipped too. Links to unbuilt pages are turned into plain
text, and only the images that built pages actually use are copied, so nothing
from a hidden page reaches the live site.

A page with "listed": false is built but kept out of the nav, the portfolio
index and prev/next links, and asks search engines not to index it.

Each folder in experiments/ is copied as-is to /experiments/<folder>/, with a
noindex tag added to its HTML. Folders starting with "_" are skipped.
"""
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "_site")


def load_config():
    with open(os.path.join(ROOT, "site.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    pages = {p["id"]: p for p in cfg["pages"]}
    for p in cfg["pages"]:
        if p.get("parent") and p["parent"] not in pages:
            sys.exit(f"site.json: page '{p['id']}' has unknown parent '{p['parent']}'")
    return cfg, pages


def is_live(page, pages):
    while page:
        if not page.get("published", False):
            return False
        page = pages.get(page.get("parent"))
    return True


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def front_matter(text):
    m = re.match(r"\s*<!--\s*(\{.*?\})\s*-->\s*", text, re.S)
    if not m:
        return {}, text
    return json.loads(m.group(1)), text[m.end():]


def url_for(page, prefix):
    return prefix + (page["path"] + "/" if page["path"] else "")


NOINDEX = '<meta name="robots" content="noindex, nofollow">'


def is_listed(page):
    return page.get("listed", True)


def resolve_links(body, pages, live, prefix, warnings, source):
    # Button blocks pointing at hidden pages are dropped entirely.
    def drop_button(m):
        pid = m.group(1)
        if pid in live:
            return m.group(0)
        warnings.append(f"{source}: removed button to hidden page '{pid}'")
        return ""
    body = re.sub(r'<div class="b b-button[^"]*"[^>]*><a class="btn[^"]*" href="page:([a-z0-9_-]+)"[^>]*>.*?</a></div>',
                  drop_button, body, flags=re.S)

    # Other links to hidden pages keep their text but lose the link.
    def link(m):
        pid, attrs_before, attrs_after, inner = m.group(2), m.group(1), m.group(3), m.group(4)
        if pid not in pages:
            sys.exit(f"{source}: link to unknown page '{pid}'")
        if pid in live:
            return f'<a{attrs_before}href="{url_for(pages[pid], prefix)}"{attrs_after}>{inner}</a>'
        warnings.append(f"{source}: unlinked text pointing at hidden page '{pid}'")
        return inner
    body = re.sub(r'<a([^>]*?\s)href="page:([a-z0-9_-]+)"([^>]*)>(.*?)</a>', link, body, flags=re.S)
    return body


def rewrite_assets(body, prefix, used):
    def sub(m):
        used.add(m.group(2))
        return m.group(1) + prefix + m.group(2)
    return re.sub(r'((?:src|href|poster)=")(assets/[^"]+)', sub, body)


def header_theme(body):
    m = re.search(r'<section class="sec t-([a-z-]+)', body)
    return m.group(1) if m else "white"


def portfolio_index(page, pages, live):
    items = [p for p in pages.values() if p.get("parent") == page["id"] and p["id"] in live and is_listed(p)]
    out = []
    for i, p in enumerate(items):
        delim = '<span class="pf-delim" aria-hidden="true">—</span>' if i < len(items) - 1 else ""
        out.append(f'<a class="pf-item" href="page:{p["id"]}" data-id="{p["id"]}">'
                   f'<span class="pf-title">{html.escape(p.get("label", p["id"]))}</span>{delim}</a>')
    covers = "".join(f'<img src="{html.escape(p["cover"])}" alt="" data-for="{p["id"]}">' for p in items if p.get("cover"))
    return (f'<section class="sec t-light-bold h-large sec-portfolio">\n'
            f'  <div class="pf-covers" aria-hidden="true">{covers}</div>\n'
            f'  <nav class="pf-list" aria-label="Case studies">{"".join(out)}</nav>\n</section>\n')


def pagination(page, pages, live):
    siblings = [p for p in pages.values() if p.get("parent") == page.get("parent") and p["id"] in live and is_listed(p)]
    if not page.get("parent") or not is_listed(page) or len(siblings) < 2:
        return ""
    i = [p["id"] for p in siblings].index(page["id"])
    prev_p = siblings[i - 1] if i > 0 else None
    next_p = siblings[i + 1] if i + 1 < len(siblings) else None
    arrow_l = '<svg viewBox="0 0 44 18" aria-hidden="true"><path d="M9.9 17 1.4 9l8.5-8M1.4 9H44"/></svg>'
    arrow_r = '<svg viewBox="0 0 44 18" aria-hidden="true"><path d="m34.1 1 8.5 8-8.5 8M42.6 9H0"/></svg>'
    left = (f'<a class="pg-link pg-prev" href="page:{prev_p["id"]}">{arrow_l}<span class="sr">Previous</span>'
            f'<span class="pg-title">{html.escape(prev_p.get("label", ""))}</span></a>') if prev_p else "<span></span>"
    right = (f'<a class="pg-link pg-next" href="page:{next_p["id"]}"><span class="sr">Next</span>'
             f'<span class="pg-title">{html.escape(next_p.get("label", ""))}</span>{arrow_r}</a>') if next_p else ""
    return f'<nav class="pagination" aria-label="More case studies">{left}{right}</nav>\n'


def nav_html(cfg, pages, live, current, prefix):
    items = []
    for p in cfg["pages"]:
        if p.get("nav") and p["id"] in live and is_listed(p):
            active = current["id"] == p["id"] or current.get("parent") == p["id"]
            cls = ' class="active" aria-current="page"' if active else ""
            items.append(f'<a href="{url_for(p, prefix)}"{cls}>{html.escape(p["nav"])}</a>')
    return "".join(items)


def copy_experiments():
    """Copy each experiments/<name>/ folder verbatim, adding noindex to its HTML."""
    src_dir = os.path.join(ROOT, "experiments")
    if not os.path.isdir(src_dir):
        return []
    names = sorted(n for n in os.listdir(src_dir)
                   if os.path.isdir(os.path.join(src_dir, n)) and not n.startswith((".", "_")))
    for name in names:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
            sys.exit(f"experiments/{name}: use lowercase letters, numbers and hyphens only")
        dst = os.path.join(OUT, "experiments", name)
        shutil.copytree(os.path.join(src_dir, name), dst,
                        ignore=shutil.ignore_patterns(".*"))
        if not os.path.isfile(os.path.join(dst, "index.html")):
            print(f"note: experiments/{name} has no index.html, so /experiments/{name}/ will 404")
        for dirpath, _, files in os.walk(dst):
            for fn in files:
                if fn.lower().endswith((".html", ".htm")):
                    fp = os.path.join(dirpath, fn)
                    with open(fp, encoding="utf-8", errors="surrogateescape") as f:
                        text = f.read()
                    if 'name="robots"' in text:
                        continue
                    text, n = re.subn(r"(<head[^>]*>)", lambda m: m.group(1) + NOINDEX, text, count=1, flags=re.I)
                    if not n:
                        text = NOINDEX + "\n" + text
                    with open(fp, "w", encoding="utf-8", errors="surrogateescape") as f:
                        f.write(text)
    return names


def build():
    cfg, pages = load_config()
    if "--all" in sys.argv:
        for p in pages.values():
            p["published"] = True
        print("PREVIEW: --all builds hidden pages too. Do not deploy this output.")
    live = {pid for pid, p in pages.items() if is_live(p, pages)}
    layout = read(os.path.join(SRC, "layout.html"))
    footer = read(os.path.join(SRC, "partials", "footer.html"))
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    used, warnings, built = set(), [], []

    for pid in [p["id"] for p in cfg["pages"]]:
        page = pages[pid]
        if pid not in live:
            continue
        depth = len(page["path"].split("/")) if page["path"] else 0
        prefix = "../" * depth or "./"
        if page.get("type") == "portfolio-index":
            meta, body = {"title": page.get("title", cfg["site"]["title"])}, portfolio_index(page, pages, live)
        else:
            meta, body = front_matter(read(os.path.join(SRC, page["source"])))
            body += pagination(page, pages, live)
        source = page.get("source", pid)
        theme = header_theme(body)
        body = resolve_links(body, pages, live, prefix, warnings, source)
        foot = resolve_links(footer, pages, live, prefix, warnings, "partials/footer.html")
        title = page.get("title") or meta.get("title") or cfg["site"]["title"]
        desc = meta.get("description", "")
        doc = (layout
               .replace("{{lang}}", cfg["site"].get("lang", "en"))
               .replace("{{title}}", html.escape(title))
               .replace("{{description}}", html.escape(desc))
               .replace("{{site_title}}", html.escape(cfg["site"]["title"]))
               .replace("{{home}}", prefix)
               .replace("{{header_theme}}", theme)
               .replace("{{nav}}", nav_html(cfg, pages, live, page, prefix))
               .replace("{{content}}", body)
               .replace("{{footer}}", foot)
               .replace("{{robots}}", "" if is_listed(page) else "\n" + NOINDEX)
               .replace("{{page_id}}", pid)
               .replace("{{canonical}}", cfg["site"].get("url", "").rstrip("/") + "/" + (page["path"] + "/" if page["path"] else ""))
               .replace("{{share_image}}", cfg["site"].get("url", "").rstrip("/") + "/" + cfg["site"].get("share_image", "")))
        doc = rewrite_assets(doc, prefix, used)
        dest = os.path.join(OUT, page["path"], "index.html")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(doc)
        built.append("/" + page["path"] + ("" if is_listed(page) else " (unlisted)"))
        for alias in page.get("aliases", []):
            a_prefix = "../" * len(alias.split("/"))
            target = url_for(page, a_prefix)
            a_dest = os.path.join(OUT, alias, "index.html")
            os.makedirs(os.path.dirname(a_dest), exist_ok=True)
            with open(a_dest, "w", encoding="utf-8") as f:
                f.write(f'<!doctype html><meta charset="utf-8"><title>{html.escape(title)}</title>'
                        f'<link rel="canonical" href="{target}"><meta http-equiv="refresh" content="0; url={target}">'
                        f'<a href="{target}">Continue</a>\n')

    if cfg["site"].get("share_image"):
        used.add(cfg["site"]["share_image"])

    # Copy only the assets that built pages reference, plus css/js.
    for rel in sorted(used):
        src = os.path.join(ROOT, rel)
        if not os.path.isfile(src):
            sys.exit(f"missing asset: {rel}")
        dst = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    experiments = copy_experiments()

    hidden = sorted(set(pages) - live)
    print(f"Built {len(built)} page(s): {', '.join(built)}")
    print(f"Hidden: {', '.join(hidden) if hidden else 'none'}")
    print(f"Copied {len(used)} asset file(s)")
    print(f"Experiments: {', '.join('/experiments/' + e + '/' for e in experiments) if experiments else 'none'}")
    for w in warnings:
        print("note:", w)


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        import functools
        import http.server
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=OUT)
        print("Serving http://localhost:8000  (Ctrl-C to stop)")
        http.server.ThreadingHTTPServer(("127.0.0.1", 8000), handler).serve_forever()
