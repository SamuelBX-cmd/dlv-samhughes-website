#!/usr/bin/env python3
"""Turn a draft from the site editor artifact into site files.

    python3 tools/import_draft.py <draft.json> <asset-dir>

<draft.json> is one document from the editor's "drafts" collection (the
document body, or the {"id", "data": {...}} wrapper a database read returns).
<asset-dir> holds the draft's uploaded images, each saved under its asset id
(e.g. 3f2a....webp, any extension).

Articles become articles/<slug>.md plus assets/img/articles/<slug>.<ext>.
Case studies become case-studies/<slug>.json plus assets/img/<slug>/... and
assets/video/<slug>-N.<ext>. Existing files for the same slug are replaced.
Prints the files written.
"""
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def slugify(s):
    s = re.sub(r"[’'\"]", "", str(s or "").lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]


def find_asset(asset_dir, asset_id):
    for fn in os.listdir(asset_dir):
        if fn.split(".")[0] == asset_id:
            return os.path.join(asset_dir, fn)
    sys.exit(f"asset {asset_id} not found in {asset_dir}")


class Writer:
    def __init__(self, asset_dir):
        self.asset_dir = asset_dir
        self.written = []

    def copy(self, ref, dest_rel):
        """Copy an uploaded asset ({"asset", "ext"}) to dest_rel (extension added). Returns the site path."""
        src = find_asset(self.asset_dir, ref["asset"])
        ext = ref.get("ext") or os.path.splitext(src)[1].lstrip(".") or "webp"
        rel = f"{dest_rel}.{ext}"
        dst = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        self.written.append(rel)
        return rel

    def text(self, rel, content):
        dst = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(content)
        self.written.append(rel)


def one_line(v):
    return re.sub(r"\s+", " ", str(v or "")).strip()


def import_article(doc, w):
    x = doc["data"]
    slug = doc.get("slug") or slugify(x["title"])
    fields = [("title", x["title"]), ("date", x["date"]), ("summary", x["summary"])]
    if x.get("image"):
        fields.append(("image", w.copy(x["image"], f"assets/img/articles/{slug}")))
        fields.append(("image_alt", x.get("image_alt", "")))
    if x.get("link"):
        fields.append(("link", x["link"]))
    if x.get("first_published_in"):
        fields.append(("first_published_in", x["first_published_in"]))
    head = "\n".join(f"{k}: {one_line(v)}" for k, v in fields)
    body = (x.get("body") or "").strip()
    w.text(f"articles/{slug}.md", f"---\n{head}\n---\n" + (f"\n{body}\n" if body else ""))
    return slug


def import_case(doc, w):
    x = doc["data"]
    slug = doc.get("slug") or slugify(x["title"])
    img_dir = f"assets/img/{slug}"
    if os.path.isdir(os.path.join(ROOT, img_dir)):
        shutil.rmtree(os.path.join(ROOT, img_dir))   # replace the previous version's images
    n = 0

    def next_name():
        nonlocal n
        n += 1
        return f"{img_dir}/{n:02d}"

    services = [s.strip() for s in str(x.get("services") or "").split(",") if s.strip()]
    out = {k: x[k] for k in ("title", "headline", "client", "year", "role", "discipline", "intro", "summary", "order") if x.get(k) not in (None, "")}
    if services:
        out["services"] = services
    out["cover"] = w.copy(x["cover"], f"{img_dir}/cover")
    out["cover_alt"] = x.get("cover_alt", "")
    blocks = []
    videos = 0
    for b in x.get("blocks", []):
        t = b["type"]
        if t == "text":
            blocks.append({k: b[k] for k in ("type", "heading", "subheading", "body") if b.get(k)})
        elif t == "image":
            if not b.get("img"):
                continue
            blocks.append({"type": "image", "size": b.get("size", "full"), "src": w.copy(b["img"], next_name()),
                           "alt": b.get("alt", ""), "caption": b.get("caption", "")})
        elif t == "images":
            items = [{"src": w.copy(it["img"], next_name()), "alt": it.get("alt", "")} for it in b.get("items", []) if it.get("img")]
            if items:
                blocks.append({"type": "images", "columns": b.get("columns", 2), "items": items, "caption": b.get("caption", "")})
        elif t == "quote":
            blocks.append({"type": "quote", "text": b.get("text", ""), "attribution": b.get("attribution", "")})
        elif t == "stats":
            items = [i for i in b.get("items", []) if str(i.get("value", "")).strip()]
            blocks.append({"type": "stats", "heading": b.get("heading", ""), "items": items})
        elif t == "video":
            if b.get("src"):
                blocks.append({"type": "video", "src": b["src"], "caption": b.get("caption", "")})
            elif b.get("file"):
                videos += 1
                blocks.append({"type": "video", "src": w.copy(b["file"], f"assets/video/{slug}-{videos}"), "caption": b.get("caption", "")})
    out["blocks"] = blocks
    w.text(f"case-studies/{slug}.json", json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    return slug


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        doc = json.load(f)
    if "kind" not in doc and isinstance(doc.get("data"), dict) and "kind" in doc["data"]:
        doc = doc["data"]          # a database read wraps the body as {"id", "data", "version"}
    w = Writer(sys.argv[2])
    slug = import_article(doc, w) if doc["kind"] == "article" else import_case(doc, w)
    print(f"{doc['kind']} {slug}")
    for rel in w.written:
        print("  wrote", rel)


if __name__ == "__main__":
    main()
