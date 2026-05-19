# Building the documentation site

The documentation under `docs/` is rendered by [MkDocs](https://www.mkdocs.org/)
with the [Material](https://squidfunk.github.io/mkdocs-material/) theme into
a static site under `site/`. Source of truth is the `docs/` directory plus
`mkdocs.yml` at the repo root.

## One-shot setup

```bash
pip install -r requirements-dev.txt
# or, if you only want the docs toolchain:
pip install "mkdocs>=1.6" "mkdocs-material>=9.5"
```

## Local preview

```bash
mkdocs serve
```

Opens a live-reloading server on `http://127.0.0.1:8000/`. Editing any
`docs/*.md` or `mkdocs.yml` re-renders the affected page within a second.

## Production build

```bash
mkdocs build --strict
```

The `--strict` flag is what CI uses (see `.github/workflows/ci.yml` → `docs`
job). It turns every warning into an error — broken internal links,
files in `docs/` missing from the `nav`, undefined references, etc.
`make docs` runs the same command.

Output ends up in `site/` (gitignored). The directory is regenerated from
scratch on every build, so don't edit anything in it.

## Deploying to GitHub Pages

```bash
mkdocs gh-deploy --force
```

That command builds the site and pushes it to the `gh-pages` branch of the
repo's `origin` remote. GitHub Pages serves whatever is on `gh-pages` at
`https://wachawo.github.io/pydantic-ai-toolbox/` (matches the `site_url`
in `mkdocs.yml`). The current setup expects you to run this manually after
a release; there is no scheduled or post-publish workflow that does it
automatically.

## File naming and nav

- **`docs/index.md` must stay lowercase.** MkDocs maps it to the site
  root URL (`/`). Renaming it to `INDEX.md` would move the homepage to
  `/INDEX/` and break every link to the root.
- Every other `docs/*.md` file is uppercase by project convention
  (`INSTALL.md`, `FILESYSTEM.md`, `CUSTOM.md`, …) and is listed
  explicitly in the `nav:` block of `mkdocs.yml`.
- `--strict` will fail the build if a file exists under `docs/` but
  isn't referenced from `nav`. To intentionally hide a file from the
  sidebar, delete it or move it outside `docs/`.
- `docs/CHANGELOG.md` is a symlink to the repo-root `CHANGELOG.md` so
  the changelog has a single source of truth. Edit the root file; the
  doc page picks up the change automatically.

## Adding a new page

1. Drop a new `docs/NEW.md`.
2. Add a `- Label: NEW.md` line to the relevant section in `mkdocs.yml`
   `nav:`.
3. Run `mkdocs build --strict` locally to confirm there are no broken
   links and no orphan-file warnings.

## Adding a new toolset page

When you add a toolset, the page goes under the existing `Toolsets:`
group:

```yaml
nav:
  - Toolsets:
      - Filesystem: FILESYSTEM.md
      - SQL: SQL.md
      - …
      - NewKit: NEWKIT.md          # add here
```

The contribution checklist in `AGENTS.md` already includes "add a page
under `docs/`".

## Theme customisation

Theme is configured under `theme:` in `mkdocs.yml`:

- `name: material` — the Material theme.
- `features:` — enables sidebar sections, expanded nav, back-to-top
  button, copy-to-clipboard on code blocks, and code annotations.
- `palette:` — single light scheme with indigo as primary and accent.

The Material project's "MkDocs 2.0" warning printed during `mkdocs build`
is unrelated to this project — it is an upstream announcement and can
be ignored.

## Markdown extensions enabled

Configured under `markdown_extensions:` in `mkdocs.yml`:

| Extension                 | What it gives you                             |
|---------------------------|-----------------------------------------------|
| `admonition`              | `!!! note "..."` callouts                     |
| `attr_list`               | `{#id .class}` attributes on any element      |
| `pymdownx.details`        | Collapsible `???`-style admonitions           |
| `pymdownx.highlight`      | Syntax highlighting for fenced code blocks    |
| `pymdownx.superfences`    | Nested code blocks and custom fences          |
| `pymdownx.tabbed`         | Tabbed content (`=== "Tab name"`)             |
| `toc` (permalink)         | Anchor links next to every heading            |
