# Contributing

Thank you for helping improve **Awesome Video World Models**. We welcome new
paper suggestions, metadata corrections, and clearer category placement.

## Before suggesting a paper

A paper should be relevant to video foundation models or video world models,
technically substantive, and not already present in the list. Closely related
versions of one project are normally represented by the most complete or
authoritative record.

Please search the [current list](README.md#literature) first, then use the
[paper suggestion form](https://github.com/Eurekaleo/Awesome-Video-World-Model/issues/new?template=new-paper.yml).

Provide:

1. the exact paper title;
2. a stable paper, publisher, or official project URL;
3. venue and year;
4. the best matching category;
5. a short explanation of why the work is representative.

## Categories

- **Foundations and Background** — core concepts, general-purpose models,
  representation learning, and surveys.
- **Video Understanding** — perception, language understanding, temporal or
  physical reasoning, datasets, and evaluation.
- **Video Generation** — generative modeling, representations, conditioning,
  controllable generation, and evaluation.
- **Unified Video Models** — models and learning strategies shared across
  understanding and generation.
- **Interactive Video World Models** — simulation, planning, robotics, games,
  driving, and other work centered on world dynamics.

These are broad browsing categories. They do not reproduce the structure of
the manuscript in preparation.

## Pull requests

Use one bullet per paper in the following format:

```markdown
- [Paper title](https://paper-or-project-url) — Author et al. *Venue, year*.
```

Keep pull requests focused. Prefer a DOI landing page, publisher page, ACL
Anthology, OpenReview, arXiv abstract page, or official project page over a
search-results URL. Preserve the year recorded by the cited version and explain
any ambiguous metadata in the pull-request description.

The maintainers update `references.bib`; contributors only need to propose the
README entry and supporting metadata.
