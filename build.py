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

Each file in articles/ (except ones starting with "_") is an article. It
becomes a tile wherever a page contains <!-- articles -->, newest first. An
article with body text also gets its own page at /articles/<file name>/; one
without body text links its tile straight to its "link".

Each folder in experiments/ is copied as-is to /experiments/<folder>/, with a
noindex tag added to its HTML. Folders starting with "_" are skipped.
"""
import datetime
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


# ---------- Articles ----------

ARTICLES = os.path.join(ROOT, "articles")
ARTICLE_FIELDS = {"title", "date", "summary", "image", "image_alt", "thumbnail", "link", "first_published_in", "published"}


def parse_article(path):
    text = read(path)
    m = re.match(r"---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if not m:
        sys.exit(f"{path}: must start with a --- block of fields")
    meta = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            sys.exit(f"{path}: can't read line '{line}' (expected 'field: value')")
        key, value = line.split(":", 1)
        key = key.strip()
        if key not in ARTICLE_FIELDS:
            sys.exit(f"{path}: unknown field '{key}'. Known fields: {', '.join(sorted(ARTICLE_FIELDS))}")
        meta[key] = value.strip()
    for key in ("title", "date", "summary"):
        if not meta.get(key):
            sys.exit(f"{path}: '{key}' is required")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["date"]):
        sys.exit(f"{path}: date must look like 2025-01-28")
    meta["published"] = meta.get("published", "true").lower() not in ("false", "no", "0")
    meta["body"] = text[m.end():].strip()
    return meta


def load_articles():
    if not os.path.isdir(ARTICLES):
        return []
    out = []
    for fn in sorted(os.listdir(ARTICLES)):
        if not fn.endswith(".md") or fn.startswith(("_", ".")):
            continue
        slug = fn[:-3]
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
            sys.exit(f"articles/{fn}: name files with lowercase letters, numbers and hyphens only")
        a = parse_article(os.path.join(ARTICLES, fn))
        a["slug"] = slug
        if a["published"]:
            if not a["body"] and not a.get("link"):
                sys.exit(f"articles/{fn}: needs either body text or a 'link'")
            out.append(a)
    out.sort(key=lambda a: a["date"], reverse=True)
    return out


def format_date(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    months = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
    return f"{d} {months[m - 1]} {y}"


def source_name(a):
    link = a.get("link", "")
    if "linkedin.com" in link or "lnkd.in" in link:
        return "LinkedIn"
    if a.get("first_published_in"):
        return a["first_published_in"]
    m = re.match(r"https?://(?:www\.)?([^/]+)", link)
    return m.group(1) if m else "the original site"


def md_inline(text):
    tokens = []

    def keep(fragment):
        tokens.append(fragment)
        return f"\x00{len(tokens) - 1}\x00"

    text = re.sub(r"`([^`]+)`", lambda m: keep(f"<code>{html.escape(m.group(1))}</code>"), text)
    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
                  lambda m: keep(f'<img src="{html.escape(m.group(2))}" alt="{html.escape(m.group(1))}" loading="lazy" decoding="async">'), text)

    def link(m):
        href = m.group(2)
        ext = ' target="_blank" rel="noopener"' if href.startswith("http") else ""
        return keep(f'<a href="{html.escape(href)}"{ext}>') + m.group(1) + keep("</a>")
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])", r"<em>\1</em>", text)
    while "\x00" in text:
        text = re.sub(r"\x00(\d+)\x00", lambda m: tokens[int(m.group(1))], text)
    return text


def md_to_html(md):
    """A small Markdown subset: headings, paragraphs, lists, quotes, images, rules, raw HTML."""
    out = []
    for block in re.split(r"\n\s*\n", md.strip()):
        lines = [l.rstrip() for l in block.strip("\n").splitlines()]
        first = lines[0].lstrip()
        if first.startswith("<"):
            out.append(block.strip())
        elif re.fullmatch(r"(-{3,}|\*{3,})", first) and len(lines) == 1:
            out.append("<hr>")
        elif m := re.match(r"(#{1,4})\s+(.*)", first):
            level = {1: 2, 2: 2, 3: 3, 4: 4}[len(m.group(1))]
            out.append(f"<h{level}>{md_inline(' '.join([m.group(2)] + lines[1:]))}</h{level}>")
        elif all(re.match(r"\s*[-*+]\s+", l) for l in lines):
            items = "".join(f"<li>{md_inline(re.sub(r'^\s*[-*+]\s+', '', l))}</li>" for l in lines)
            out.append(f"<ul>{items}</ul>")
        elif all(re.match(r"\s*\d+[.)]\s+", l) for l in lines):
            items = "".join(f"<li>{md_inline(re.sub(r'^\s*\d+[.)]\s+', '', l))}</li>" for l in lines)
            out.append(f"<ol>{items}</ol>")
        elif all(l.lstrip().startswith(">") for l in lines):
            inner = "\n".join(re.sub(r"^\s*>\s?", "", l) for l in lines)
            out.append(f"<blockquote>{md_to_html(inner)}</blockquote>")
        elif len(lines) == 1 and re.fullmatch(r"!\[[^\]]*\]\([^)\s]+\)", first):
            out.append(f"<figure>{md_inline(first)}</figure>")
        else:
            out.append(f"<p>{md_inline(' '.join(l.strip() for l in lines))}</p>")
    return "\n".join(out)


def article_href(a, prefix):
    return f"{prefix}articles/{a['slug']}/" if a["body"] else a["link"]


def article_title_html(a):
    t = html.escape(a["title"])
    if a.get("first_published_in"):
        t += f" <em>(first published in {html.escape(a['first_published_in'])})</em>"
    return t


def article_source_label(a):
    year = a["date"][:4]
    pub = a.get("first_published_in") or (source_name(a) if a.get("link") else "")
    return f"{pub} · {year}" if pub else year


def articles_section(articles, heading, prefix):
    cards = []
    for a in articles:
        href = html.escape(article_href(a, prefix))
        ext = "" if a["body"] else ' target="_blank" rel="noopener"'
        img = ""
        tile = a.get("thumbnail") or a.get("image")
        if tile:
            alt = "" if a.get("thumbnail") else a.get("image_alt", "")   # a thumbnail is decorative; the headline sits above it
            img = (f'<div class="wimg"><img src="{html.escape(tile)}" alt="{html.escape(alt)}" '
                   f'loading="lazy" decoding="async"></div>')
        cards.append(f'    <a class="wcard" href="{href}"{ext}>'
                     f'<div class="wmeta"><h3>{html.escape(a["title"])}</h3>'
                     f'<span class="src">{html.escape(article_source_label(a))}</span></div>'
                     f'{img}<p>{html.escape(a["summary"])}</p></a>')
    return (f'<section class="row wrap" id="writing">\n'
            f'  <div class="label"><h2>Writing</h2><p>{html.escape(heading)}</p></div>\n'
            f'  <div class="content writing">\n' + "\n".join(cards) + "\n  </div>\n</section>\n")


def article_page(a, prefix, home_url):
    side = [f'<a class="back" href="{home_url}#writing">All writing</a>', f"<p>{format_date(a['date'])}</p>"]
    if a.get("first_published_in"):
        side.append(f"<p>First published in {html.escape(a['first_published_in'])}</p>")
    hero = ""
    if a.get("image"):
        hero = f'<img class="article-hero" src="{html.escape(a["image"])}" alt="{html.escape(a.get("image_alt", ""))}">'
    source = ""
    if a.get("link"):
        source = (f'<p class="article-source">Originally published on '
                  f'<a href="{html.escape(a["link"])}" target="_blank" rel="noopener">{html.escape(source_name(a))}</a>.</p>')
    return (f'<article class="row wrap hero article-head">\n<div class="article-side">{"".join(side)}</div>\n'
            f'<div class="content">\n<h1 class="display"><span class="ink">{html.escape(a["title"])}</span></h1>\n{hero}\n'
            f'<div class="article-body">\n{md_to_html(a["body"])}\n</div>\n{source}\n</div>\n</article>\n')


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


# ---------- Case studies ----------

CASE_STUDIES = os.path.join(ROOT, "case-studies")
BLOCK_TYPES = {"text", "image", "images", "quote", "stats", "video"}


def load_case_studies():
    """Read case-studies/<slug>.json (files starting with "_" are skipped)."""
    if not os.path.isdir(CASE_STUDIES):
        return []
    out = []
    for fn in sorted(os.listdir(CASE_STUDIES)):
        if not fn.endswith(".json") or fn.startswith(("_", ".")):
            continue
        slug = fn[:-5]
        where = f"case-studies/{fn}"
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
            sys.exit(f"{where}: name files with lowercase letters, numbers and hyphens only")
        try:
            cs = json.loads(read(os.path.join(CASE_STUDIES, fn)))
        except json.JSONDecodeError as e:
            sys.exit(f"{where}: not valid JSON ({e})")
        for key in ("title", "cover"):
            if not cs.get(key):
                sys.exit(f"{where}: '{key}' is required")
        for i, b in enumerate(cs.get("blocks", [])):
            if b.get("type") not in BLOCK_TYPES:
                sys.exit(f"{where}: block {i + 1} has unknown type '{b.get('type')}'. Known: {', '.join(sorted(BLOCK_TYPES))}")
        cs["slug"] = slug
        out.append(cs)
    out.sort(key=lambda c: (c.get("order", 100), c["title"].lower()))
    return out


def work_meta(p):
    cs = p.get("case") or {}
    bits = [cs.get("discipline") or ", ".join(cs.get("services", [])[:2]), str(cs.get("year", ""))]
    return " · ".join(b for b in bits if b)


def work_cards(items, prefix_link=True):
    cards = []
    for p in items:
        cover = p.get("cover", "")
        img = (f'<div class="wimg"><img src="{html.escape(cover)}" alt="{html.escape(p.get("cover_alt", ""))}" '
               f'loading="lazy" decoding="async"></div>') if cover else ""
        cards.append(f'    <a class="wcard work" href="page:{p["id"]}">'
                     f'<div class="wmeta"><h3>{html.escape(p.get("label", p["id"]))}</h3>'
                     f'<span class="src">{html.escape(work_meta(p))}</span></div>{img}</a>')
    return "\n".join(cards)


def portfolio_children(page_id, pages, live):
    return [p for p in pages.values() if p.get("parent") == page_id and p["id"] in live and is_listed(p)]


def portfolio_index(page, pages, live):
    items = portfolio_children(page["id"], pages, live)
    return (f'<section class="row wrap hero">\n  <div class="label-spacer" aria-hidden="true"></div>\n'
            f'  <div class="content"><p class="status">Selected work</p>'
            f'<h1 class="display"><span class="ink">Case studies</span> in brand, experience and strategy.</h1></div>\n</section>\n'
            f'<section class="row wrap" id="work">\n  <div class="label"><h2>Projects</h2><p>{len(items)} case studies</p></div>\n'
            f'  <div class="content works">\n{work_cards(items)}\n  </div>\n</section>\n')


def work_section(pages, live, prefix):
    """Home page "Selected work": the first two case studies, if the portfolio is live."""
    if "portfolio" not in live:
        return ""
    items = portfolio_children("portfolio", pages, live)[:2]
    if not items:
        return ""
    return (f'<section class="row wrap" id="work">\n  <div class="label"><h2>Selected work</h2><p>The work I’m proud of</p></div>\n'
            f'  <div class="content works">\n{work_cards(items)}\n'
            f'    <a class="link-arrow" href="page:portfolio">See all projects</a>\n  </div>\n</section>\n')


def img_tag(src, alt, cls="", eager=False):
    c = f' class="{cls}"' if cls else ""
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    return f'<img{c} src="{html.escape(src)}" alt="{html.escape(alt or "")}" {load} decoding="async">'


def caption(text):
    return f"<figcaption>{md_inline(text)}</figcaption>" if text else ""


def render_block(b):
    t = b["type"]
    if t == "text":
        label = (f'<div class="label"><h2>{html.escape(b["heading"])}</h2>'
                 + (f'<p>{html.escape(b["subheading"])}</p>' if b.get("subheading") else "") + "</div>") \
            if b.get("heading") else '<div class="label-spacer" aria-hidden="true"></div>'
        return f'<section class="row wrap cs-text">{label}<div class="content prose-lg">{md_to_html(b.get("body", ""))}</div></section>'
    if t == "image":
        size = b.get("size", "full")
        fig = f'<figure class="cs-figure">{img_tag(b["src"], b.get("alt"))}{caption(b.get("caption"))}</figure>'
        if size == "wide":
            return f'<section class="wrap cs-media cs-split"><div class="label-spacer" aria-hidden="true"></div>{fig}</section>'
        return f'<section class="wrap cs-media">{fig}</section>'
    if t == "images":
        items = b.get("items", [])
        cols = b.get("columns") or (3 if len(items) % 3 == 0 and len(items) > 2 else 2)
        figs = "".join(f'<figure class="cs-figure">{img_tag(i["src"], i.get("alt"))}{caption(i.get("caption"))}</figure>' for i in items)
        return f'<section class="wrap cs-media"><div class="cs-grid cols-{int(cols)}">{figs}</div>{caption(b.get("caption"))}</section>'
    if t == "quote":
        who = f'<p class="cs-quote-by">{html.escape(b["attribution"])}</p>' if b.get("attribution") else ""
        return (f'<section class="row wrap cs-quote"><div class="label-spacer" aria-hidden="true"></div>'
                f'<blockquote class="content"><p class="lead"><span class="ink">{html.escape(b.get("text", ""))}</span></p>{who}</blockquote></section>')
    if t == "stats":
        cells = "".join(f'<div class="cs-stat"><p class="cs-stat-value">{html.escape(str(i.get("value", "")))}</p>'
                        f'<p class="muted">{html.escape(i.get("label", ""))}</p></div>' for i in b.get("items", []))
        label = f'<div class="label"><h2>{html.escape(b["heading"])}</h2></div>' if b.get("heading") else '<div class="label-spacer" aria-hidden="true"></div>'
        return f'<section class="row wrap cs-stats">{label}<div class="content cs-stat-grid">{cells}</div></section>'
    if t == "video":
        src = b.get("src", "")
        if re.match(r"https?://(www\.)?(youtube\.com|youtu\.be|vimeo\.com|player\.vimeo\.com)/", src):
            m = re.search(r"(?:v=|youtu\.be/|embed/)([\w-]{6,})", src)
            if "youtu" in src and m:
                embed = f"https://www.youtube-nocookie.com/embed/{m.group(1)}"
            else:
                m = re.search(r"vimeo\.com/(?:video/)?(\d+)", src)
                embed = f"https://player.vimeo.com/video/{m.group(1)}" if m else src
            media = f'<div class="cs-embed"><iframe src="{html.escape(embed)}" title="{html.escape(b.get("alt") or "Video")}" allow="fullscreen; picture-in-picture" loading="lazy"></iframe></div>'
        else:
            poster = f' poster="{html.escape(b["poster"])}"' if b.get("poster") else ""
            media = f'<video src="{html.escape(src)}"{poster} controls playsinline preload="metadata"></video>'
        return f'<section class="wrap cs-media"><figure class="cs-figure">{media}{caption(b.get("caption"))}</figure></section>'
    return ""


def case_study_page(page):
    cs = page["case"]
    status = " · ".join(x for x in [cs.get("client", ""), str(cs.get("year", ""))] if x)
    meta = []
    for label, key in (("Client", "client"), ("Year", "year"), ("Role", "role"), ("Services", "services")):
        v = cs.get(key)
        if v:
            v = ", ".join(v) if isinstance(v, list) else str(v)
            meta.append(f'<div><p class="muted">{label}</p><p>{html.escape(v)}</p></div>')
    intro = f'<p class="prose">{html.escape(cs["intro"])}</p>' if cs.get("intro") else ""
    head = (f'<section class="row wrap hero cs-head">\n  <div class="label-spacer" aria-hidden="true"></div>\n'
            f'  <div class="content">' + (f'<p class="status">{html.escape(status)}</p>' if status else "")
            + f'<h1 class="display"><span class="ink">{html.escape(cs["title"])}</span>'
            + (f' {html.escape(cs["headline"])}' if cs.get("headline") else "") + f'</h1>{intro}'
            + (f'<div class="cs-meta">{"".join(meta)}</div>' if meta else "") + '</div>\n</section>\n')
    cover = f'<section class="wrap cs-media cs-cover"><figure class="cs-figure">{img_tag(cs["cover"], cs.get("cover_alt"), eager=True)}</figure></section>\n'
    return head + cover + "\n".join(render_block(b) for b in cs.get("blocks", [])) + "\n"


def pagination(page, pages, live):
    siblings = portfolio_children(page.get("parent"), pages, live) if page.get("parent") else []
    if not page.get("parent") or not is_listed(page) or len(siblings) < 2:
        return ""
    i = [p["id"] for p in siblings].index(page["id"])
    prev_p = siblings[i - 1]
    next_p = siblings[(i + 1) % len(siblings)]
    return (f'<nav class="row wrap pager" aria-label="More case studies">'
            f'<div class="label"><h2>More work</h2><p><a href="page:{page["parent"]}">All projects</a></p></div>'
            f'<div class="content pager-links">'
            f'<a class="pager-link" href="page:{prev_p["id"]}"><span class="muted">Previous</span><span>{html.escape(prev_p.get("label", ""))}</span></a>'
            f'<a class="pager-link next" href="page:{next_p["id"]}"><span class="muted">Next</span><span>{html.escape(next_p.get("label", ""))}</span></a>'
            f'</div></nav>\n')


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
    articles = load_articles()
    for a in articles:
        if not a["body"]:
            continue
        if a["slug"] in pages:
            sys.exit(f"articles/{a['slug']}.md: name clashes with page id '{a['slug']}' in site.json")
        page = {"id": a["slug"], "path": "articles/" + a["slug"], "type": "article", "article": a,
                "title": f"{a['title']} — {cfg['site']['title']}", "published": True, "listed": False}
        pages[a["slug"]] = page
        cfg["pages"].append(page)
    for cs in load_case_studies():
        page = {"id": cs["slug"], "path": "portfolio/" + cs["slug"], "parent": "portfolio", "type": "case-study",
                "case": cs, "label": cs["title"], "cover": cs["cover"], "cover_alt": cs.get("cover_alt", ""),
                "title": f"{cs['title']} — {cfg['site']['title']}", "published": cs.get("published", True)}
        if cs["slug"] in pages:
            if pages[cs["slug"]].get("parent") != "portfolio":
                sys.exit(f"case-studies/{cs['slug']}.json: name clashes with page '{cs['slug']}' in site.json")
            cfg["pages"].remove(pages[cs["slug"]])   # the JSON version replaces an older hand-built page
        pages[cs["slug"]] = page
        cfg["pages"].append(page)
    # keep case studies in their own order after any older ones
    cfg["pages"].sort(key=lambda p: (p.get("type") == "case-study", p.get("case", {}).get("order", 100)))
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
        elif page.get("type") == "case-study":
            cs = page["case"]
            meta = {"description": cs.get("summary") or cs.get("intro", "")[:160]}
            body = case_study_page(page) + pagination(page, pages, live)
        elif page.get("type") == "article":
            a = page["article"]
            meta, body = {"description": a["summary"]}, article_page(a, prefix, prefix)
        else:
            meta, body = front_matter(read(os.path.join(SRC, page["source"])))
            body += pagination(page, pages, live)
            if "<!-- work -->" in body:
                body = body.replace("<!-- work -->", work_section(pages, live, prefix))
            if "<!-- articles -->" in body:
                heading = cfg.get("articles", {}).get("heading", "Writing")
                body = body.replace("<!-- articles -->", articles_section(articles, heading, prefix))
        source = page.get("source", pid)
        theme = header_theme(body)
        body = resolve_links(body, pages, live, prefix, warnings, source)
        foot = resolve_links(footer.replace("{{year}}", str(datetime.date.today().year))
                             .replace("{{nav}}", nav_html(cfg, pages, live, page, prefix)),
                             pages, live, prefix, warnings, "partials/footer.html")
        title = page.get("title") or meta.get("title") or cfg["site"]["title"]
        share = cfg["site"].get("share_image", "")
        if page.get("type") == "case-study":
            share = page["case"]["cover"]
            used.add(share)
        if page.get("type") == "article" and page["article"].get("image"):
            share = page["article"]["image"]
            used.add(share)
        desc = meta.get("description", "")
        # Pages still built from the old Squarespace-style sections need the old stylesheet.
        extra_css = '\n<link rel="stylesheet" href="assets/css/legacy.css">' if 'class="sec ' in body else ""
        if extra_css:
            used.add("assets/css/legacy.css")
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
               .replace("{{extra_css}}", extra_css)
               .replace("{{canonical}}", cfg["site"].get("url", "").rstrip("/") + "/" + (page["path"] + "/" if page["path"] else ""))
               .replace("{{share_image}}", cfg["site"].get("url", "").rstrip("/") + "/" + share))
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
    print(f"Articles: {len(articles)} ({sum(1 for a in articles if a['body'])} with their own page)")
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
