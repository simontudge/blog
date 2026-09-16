# blog

Simon Tudge's blog — short stories, travel writing, and assorted posts. Built
as a static site with [Eleventy](https://www.11ty.dev/) and hosted on
Cloudflare Workers.

Live at **https://sjtudge.com**.

## Building locally

Node is installed self-contained at `~/.local/node` and is **not** on `PATH` by
default. Before running anything:

```sh
export PATH="$HOME/.local/node/bin:$PATH"
```

Then:

```sh
npm install
npm run serve   # preview with live reload
npm run build   # write the static site to _site/
```

`.node-version` pins the Node version so Cloudflare's build image matches local.

## Layout

| Path | What it is |
| --- | --- |
| `index.njk` | Home page; index pages are generated from the posts themselves |
| `short-stories/`, `travel-blog/`, `film/` | The posts, one directory per section |
| `_includes/` | Nunjucks layouts and partials |
| `site.css` | The site's styles |
| `style.css` | Old styles, used only by the unpublished film pages |
| `templates/` | Scratch templates from the hand-written days; not part of the site |
| `tools/` | One-off maintenance scripts (spelling fixes, image resizing, HTML→Markdown import) |
| `eleventy.config.js` | Eleventy configuration |
| `_site/` | Build output — generated, not committed |

`film/` is still in the repo but is no longer published.

## Deployment

Pushing to `master` triggers an automatic build and deploy on Cloudflare. There
is no deploy step to run by hand.

All the hosting configuration lives in the Cloudflare dashboard rather than in
this repo — there is no `wrangler.toml` and no CI workflow here, so the
dashboard is the only source of truth:

- **Worker:** `blog`, under Compute (Workers & Pages). Builds from the `master`
  branch of `github.com/simontudge/blog`.
- **Default URL:** `blog.sjtudge.workers.dev`, still live alongside the custom
  domain.
- **Custom domains:** `sjtudge.com` and `www.sjtudge.com`, added under the
  Worker's Settings → Domains & Routes. Cloudflare manages the DNS records and
  TLS certificates automatically.
- **Registrar:** Cloudflare Registrar, which auto-renews by default. The
  previous domain, `simontudge.com`, was lost to a missed renewal in 2026 and
  is now registered to someone else.

To move the site to a different domain: register or add the domain to the same
Cloudflare account, then add it as a Custom Domain on the `blog` Worker. No
changes are needed in this repo.
