# Contributing

Thank you for helping keep this survey accurate and current. We welcome:

- representative papers that materially extend one of the survey directions;
- corrections to titles, authors, venues, years, links, or BibTeX metadata;
- clearer placement within Reading, Writing, Sharing, or Interacting;
- fixes to the website, figures, or repository documentation.

## Suggesting a paper

Please use the **New paper suggestion** issue form and provide:

1. the exact paper title and a stable paper or project URL;
2. its publication venue or arXiv identifier;
3. the most relevant survey operation and technical topic;
4. one or two sentences explaining its distinct contribution.

The collection is curated rather than exhaustive. A submission should be technically
relevant, sufficiently representative of its direction, and non-duplicative of work
already listed. Closely related versions of the same project are normally represented
by the most complete or authoritative record.

## Correcting an existing entry

Open a regular issue with the citation key shown in the README or submit a pull
request. For bibliographic corrections, please prefer the published Google Scholar
record when available; otherwise use the export provided by arXiv.

## Updating the generated catalog

The website and README share `data/papers.json` as their source of truth. Maintainers
can synchronize it from the survey LaTeX project with:

```bash
python scripts/sync_catalog.py --source /path/to/Video_Survey_Overleaf
python scripts/build_readme.py
```

The synchronization script recursively follows LaTeX `\input` and `\include`
directives, keeps only references cited by the manuscript, and records the section
context in which each citation appears.

## Pull requests

Keep changes focused and describe the reason for each addition or correction. Before
opening a pull request:

```bash
python -m json.tool data/papers.json >/dev/null
python scripts/build_readme.py
```

For website changes, also test `index.html` through a local HTTP server at desktop and
mobile widths.
