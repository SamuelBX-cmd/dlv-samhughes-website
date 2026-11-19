# samhughes.com.au

Static rebuild of Sam Hughes's personal website, matching the current Squarespace site, with each page switched on or off from one file.

- **Owner:** Sam Hughes
- **Status:** Draft. Home and Contact are published; the Portfolio and its case studies are built but hidden.
- **Live URL:** https://samuelbx-cmd.github.io/dlv-samhughes-website/

## Turning pages on and off

Every page is listed in [`site.json`](site.json) with a `"published"` flag.

1. Set `"published": true` or `false` on the page.
2. Commit on a branch, open a PR, merge. The site redeploys on merge to `main`.

A hidden page is not built at all. It gets no URL, its nav link and prev/next links disappear, and its images are not deployed. Case studies sit under the Portfolio page, so a case study only goes live when both it and `portfolio` are published. To hide one case study, set only that case study to `false`.

The page source and images stay in this repository either way, and the repository is public. Hiding a page keeps it off the website, not out of GitHub.

## Working on it locally

```bash
python3 build.py --serve          # build the published pages, open http://localhost:8000
python3 build.py --all --serve    # preview with hidden pages included (never deploy this)
```

Python 3 is the only requirement. The deploy runs `python3 build.py` in GitHub Actions and publishes `_site/`.

## Where things are

| Path | What it is |
|---|---|
| `site.json` | Page list: paths, nav labels, published flags, portfolio covers |
| `src/layout.html` | Shared page shell: head, header, mobile menu, footer slot |
| `src/partials/footer.html` | Footer used on every page |
| `src/pages/` | One file per page, written as sections of blocks |
| `assets/css/site.css` | Theme colours, type scale, grid, components |
| `assets/js/site.js` | Header offset, mobile menu, portfolio hover covers |
| `assets/img/`, `assets/video/` | Images and video, one folder per page |
| `build.py` | Builds `_site/` from the above |

### Page sources

Each page is a list of `<section>` elements. A section's class sets its theme (`t-bright`, `t-light-bold`, `t-white-bold` and so on) and minimum height (`h-small`, `h-medium`, `h-large`, `h-custom`). Inside, blocks sit on the same grid Squarespace uses: 24 columns on desktop and 8 on mobile. Each block's `--d` (desktop) and `--m` (mobile) values are CSS `grid-area` positions: `row-start / column-start / row-end / column-end`.

Link to another page with `href="page:<id>"`, for example `href="page:contact"`. The build turns it into the right relative URL, or into plain text if that page is hidden.

## Moving the domain

The site currently runs at the GitHub Pages address above. To serve it from samhughes.com.au, set `site.url` in `site.json`, add the custom domain under Settings → Pages, and update DNS at the registrar. Squarespace keeps serving the domain until DNS is moved.
