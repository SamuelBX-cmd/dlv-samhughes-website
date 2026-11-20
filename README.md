# samhughes.com.au

Static rebuild of Sam Hughes's personal website, matching the current Squarespace site, with each page switched on or off from one file.

- **Owner:** Sam Hughes
- **Status:** Draft. Home and Contact are published; the Portfolio and its case studies are built but hidden.
- **Live URL:** https://www.samhughes.com.au/

## Turning pages on and off

Every page is listed in [`site.json`](site.json) with a `"published"` flag.

1. Set `"published": true` or `false` on the page.
2. Commit on a branch, open a PR, merge. The site redeploys on merge to `main`.

A hidden page is not built at all. It gets no URL, its nav link and prev/next links disappear, and its images are not deployed. Case studies sit under the Portfolio page, so a case study only goes live when both it and `portfolio` are published. To hide one case study, set only that case study to `false`.

The page source and images stay in this repository either way, and the repository is public. Hiding a page keeps it off the website, not out of GitHub.

## Site editor

Articles and case studies can be drafted in the site editor, a private claude.ai page: https://claude.ai/artifact/NsXTyBPSNffoEZPzaV153t

- **Articles:** headline, date, summary, original link, tile image and the article text in Markdown.
- **Case studies:** project details, a cover image, then page blocks (text, full-width or column image, 2- or 3-across image grid, quote, numbers, video), reordered with the arrows. The editor builds the page; the copy is yours.
- **Images** are resized in the browser before upload: 2400px wide for covers and full-width images, 1800px for column images, 1600px for article images and 2-across grids, 1200px for 3-across grids, saved as WebP (JPEG in Safari).

When a draft is marked **Ready to publish**, ask Claude to "publish my website drafts". Claude reads the ready drafts and downloads their images, runs `tools/import_draft.py` to write `articles/<name>.md` or `case-studies/<name>.json` plus images, builds, opens a PR and merges it, then marks the drafts Published in the editor.

## Case studies

Each case study is one file, `case-studies/<name>.json`, published at `/portfolio/<name>/`. `case-studies/_example.json` shows every field and block type. A case study only goes live when the `portfolio` page in `site.json` is published, and when it is, the first two also appear as "Selected work" on the home page. A JSON case study with the same name as an older hand-built page in `site.json` replaces it.

## Adding an article

Articles are tiles in the "Some things that I’ve written" section on the home page, newest first. Each article is one file in [`articles/`](articles/).

1. Copy `articles/_template.md` to `articles/<short-name>.md`, using lowercase letters, numbers and hyphens. The file name becomes the address: `/articles/<short-name>/`.
2. Fill in the fields at the top:

   | Field | What it does |
   |---|---|
   | `title` | Headline on the tile and the article page (required) |
   | `date` | `YYYY-MM-DD`; sets the order, newest first (required) |
   | `summary` | One or two sentences on the tile (required) |
   | `image` | Tile and header image, e.g. `assets/img/articles/<short-name>.webp` |
   | `image_alt` | Description of the image for screen readers |
   | `link` | Where it was first posted, e.g. the LinkedIn URL |
   | `first_published_in` | Optional; adds "(first published in …)" to the tile |
   | `published` | `false` hides it without deleting the file |

3. Put the image in `assets/img/articles/`.
4. Below the `---` line, paste the article in Markdown: `## Subheading`, `**bold**`, `*italic*`, `[link text](url)`, `- bullets`, `> quote` and `![description](assets/img/articles/picture.webp)` all work.
5. Commit on a branch, open a PR, merge. The tile appears on the home page and the article gets its own page.

If you leave the body empty, there is no article page and the tile links straight to `link`. That is how the six existing articles work today, so each one can be brought onto the site later by pasting its text into its file.

## Unlinked experiments

There are two ways to put something on the site without linking to it from anywhere. Both pages are reachable only by someone who has the URL, and both tell search engines not to index them.

**A standalone experiment** (its own HTML, CSS and JS, for example a prototype or an exported artifact):

1. Copy `experiments/_example/` to `experiments/<name>/`, using lowercase letters, numbers and hyphens.
2. Put the experiment's files in that folder, with `index.html` as the entry page.
3. Commit on a branch, open a PR, merge. It goes live at `https://www.samhughes.com.au/experiments/<name>/`.

The folder is copied as it is. The build only adds a `noindex` tag to each HTML file. To take an experiment down, delete its folder or rename it to start with `_`. Folders starting with `_` are never deployed.

**A page in the site's own design** (header, footer, fonts): add it to `site.json` with `"listed": false`:

```json
{ "id": "idea", "path": "lab/idea", "source": "pages/lab/idea.html", "listed": false, "published": true }
```

An unlisted page is built like any other but stays out of the nav, the portfolio index and prev/next links.

Unlinked is not private. The repository is public, so anyone browsing it on GitHub can find these files.

## Working on it locally

```bash
python3 build.py --serve          # build the published pages, open http://localhost:8000
python3 build.py --all --serve    # preview with hidden pages included (never deploy this)
```

Python 3 is the only requirement. The deploy runs `python3 build.py` in GitHub Actions and publishes `_site/`.

## Where things are

| Path | What it is |
|---|---|
| `site.json` | Page list: paths, nav labels, published and listed flags, portfolio covers |
| `src/layout.html` | Shared page shell: head, header, mobile menu, footer slot |
| `src/partials/footer.html` | Footer used on every page |
| `src/pages/` | One file per page, written as sections of blocks |
| `assets/css/site.css` | Current design: type, layout, header, sections, article cards, footer |
| `assets/css/legacy.css` | Old Squarespace-style grid, loaded only by pages still built from `<section class="sec">` blocks (the hidden portfolio pages) |
| `assets/js/site.js` | Header offset, mobile menu, portfolio hover covers |
| `assets/img/`, `assets/video/` | Images and video, one folder per page |
| `articles/` | One Markdown file per article; `_template.md` is the starting point |
| `case-studies/` | One JSON file per case study; `_example.json` shows every block |
| `tools/import_draft.py` | Turns a draft from the site editor into the files above |
| `experiments/` | Standalone unlinked experiments, one folder each |
| `build.py` | Builds `_site/` from the above |

### Page sources

Each page is a list of `<section>` elements. A section's class sets its theme (`t-bright`, `t-light-bold`, `t-white-bold` and so on) and minimum height (`h-small`, `h-medium`, `h-large`, `h-custom`). Inside, blocks sit on the same grid Squarespace uses: 24 columns on desktop and 8 on mobile. Each block's `--d` (desktop) and `--m` (mobile) values are CSS `grid-area` positions: `row-start / column-start / row-end / column-end`.

Link to another page with `href="page:<id>"`, for example `href="page:contact"`. The build turns it into the right relative URL, or into plain text if that page is hidden.

## Domain

`www.samhughes.com.au` is served by GitHub Pages (custom domain set under Settings → Pages; `samhughes.com.au` redirects to `www`). DNS is at GoDaddy: four `@` A records to `185.199.108.153`–`185.199.111.153` and a `www` CNAME to `samuelbx-cmd.github.io`. The domain is verified on the GitHub account through a `_github-pages-challenge-SamuelBX-cmd` TXT record, which should stay in place.
