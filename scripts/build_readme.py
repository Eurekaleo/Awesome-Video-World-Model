#!/usr/bin/env python3
"""Regenerate README.md from data/papers.json."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "papers.json"
README = ROOT / "README.md"

OPERATIONS = [
    (
        "foundations",
        "Foundations",
        "Definitions, scenarios, generative foundations, and the Type A/B/C world-model taxonomy.",
    ),
    (
        "reading",
        "Reading the World",
        "Video understanding, transferable representations, multimodal models, agents, and applications.",
    ),
    (
        "writing",
        "Writing the World",
        "Video generation tasks, latent representations, generative paradigms, control, and applications.",
    ),
    (
        "sharing",
        "Sharing the World",
        "Architectures, objectives, and evaluations that connect video understanding and generation.",
    ),
    (
        "interacting",
        "Interacting with the World",
        "Online, open-loop, and latent-state world models, together with their challenges and benchmarks.",
    ),
    (
        "frontiers",
        "Open Frontiers",
        "Generalization, stochastic futures, efficiency, memory, and reliable evaluation.",
    ),
]


def anchor(value: str) -> str:
    return (
        value.lower()
        .replace(" ", "-")
        .replace("/", "")
        .replace(":", "")
        .replace(",", "")
        .replace("&", "")
    )


def paper_line(paper: dict) -> str:
    year = paper["year"] or "n.d."
    venue = paper["venueShort"]
    authors = paper["authorsShort"]
    return (
        f"- **[{paper['title']}]({paper['url']})** · {authors} · "
        f"*{venue}, {year}* · `{paper['key']}`"
    )


def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    papers = payload["papers"]
    metadata = payload["metadata"]
    grouped: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for paper in papers:
        grouped[paper["operation"]][paper["primarySection"]].append(paper)

    lines = [
        '<div align="center">',
        "",
        "# Reading, Writing, Sharing, and Interacting with the World through Video",
        "",
        "### A Survey of Video Foundation Models through the Lens of World Modeling",
        "",
        "**Meng Luo · Shengqiong Wu · Bobo Li · Hao Fei**",
        "",
        "[![Project Website](https://img.shields.io/badge/Project-Website-18232a?style=flat-square)](https://eurekaleo.github.io/Awesome-Video-World-Model/)",
        f"[![Paper Collection](https://img.shields.io/badge/Papers-{metadata['paperCount']}-1c7ea6?style=flat-square)](#paper-collection)",
        f"[![BibTeX](https://img.shields.io/badge/BibTeX-{metadata['paperCount']}-cf5b2b?style=flat-square)](data/references.bib)",
        "[![Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-198974?style=flat-square)](CONTRIBUTING.md)",
        "",
        "</div>",
        "",
        '<p align="center">',
        '  <img src="assets/figures/four-operations.png" width="96%" alt="The video-world lens and its four operations: reading, writing, sharing, and interacting.">',
        "</p>",
        "",
        "This repository accompanies our survey of video foundation models through a unified",
        "**video-world lens**. We organize the field around four operations on the relation",
        "between an observed video trace and its latent world: **Reading**, **Writing**,",
        "**Sharing**, and **Interacting**.",
        "",
        f"The catalog contains **{metadata['paperCount']} references actually cited by the manuscript**.",
        "Every entry is assigned from its location in the LaTeX source, and papers used across",
        "multiple themes remain cross-indexed in the [interactive explorer](https://eurekaleo.github.io/Awesome-Video-World-Model/#papers).",
        "",
        "## News",
        "",
        f"- **{metadata['updated']}** · Repository and searchable survey website released.",
        "- **Preprint forthcoming** · The public paper link and formal citation will be added here.",
        "",
        "## World-Modeling Lens",
        "",
        "| Operation | Core question | Survey scope |",
        "|:--|:--|:--|",
        "| **Reading** | What world structure can be inferred from video? | Understanding, representation learning, multimodal reasoning, and video agents |",
        "| **Writing** | How can a coherent video trace be generated? | Latent representations, generation paradigms, conditioning, control, and editing |",
        "| **Sharing** | What can understanding and generation share? | Tokens, latent spaces, modules, training objectives, and tool-level orchestration |",
        "| **Interacting** | How does the world evolve under actions or conditions? | Online rollout, open-loop prediction, latent-state dynamics, memory, and planning |",
        "",
        '<p align="center">',
        '  <img src="assets/figures/field-timeline.png" width="92%" alt="Evolution of video foundation models across the four survey operations.">',
        "</p>",
        "",
        "## Contents",
        "",
        "- [Explore the collection](https://eurekaleo.github.io/Awesome-Video-World-Model/#papers)",
        "- [Download the complete BibTeX file](data/references.bib)",
    ]
    for _, label, _ in OPERATIONS:
        lines.append(f"- [{label}](#{anchor(label)})")
    lines.extend(
        [
            "- [Contributing](#contributing)",
            "",
            "## Paper Collection",
            "",
            "> The list below gives each paper one primary location for readability. The website",
            "> exposes every cross-listing recorded in the survey.",
            "",
        ]
    )

    for operation, label, description in OPERATIONS:
        operation_papers = [paper for paper in papers if paper["operation"] == operation]
        lines.extend(
            [
                f'<a id="{anchor(label)}"></a>',
                f"### {label} ({len(operation_papers)})",
                "",
                description,
                "",
            ]
        )
        sections = grouped[operation]
        for section in sorted(sections, key=str.casefold):
            section_papers = sorted(
                sections[section],
                key=lambda paper: (-(paper["year"] or 0), paper["title"].casefold()),
            )
            lines.extend([f"#### {section} ({len(section_papers)})", ""])
            lines.extend(paper_line(paper) for paper in section_papers)
            lines.append("")

    lines.extend(
        [
            "## Contributing",
            "",
            "Suggestions are welcome when a work is both technically relevant and sufficiently",
            "representative of its direction. Please read [CONTRIBUTING.md](CONTRIBUTING.md)",
            "and use the paper-suggestion issue form. Corrections to titles, venues, links,",
            "classification, or BibTeX metadata are equally valuable.",
            "",
            "## Citation",
            "",
            "The manuscript is being prepared for public release. Its formal BibTeX citation",
            "will be added here when the preprint becomes available.",
            "",
            "## Acknowledgements",
            "",
            "We thank the authors of the papers, datasets, benchmarks, and open-source systems",
            "that make this survey possible.",
            "",
        ]
    )
    README.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {README} with {len(papers)} papers")


if __name__ == "__main__":
    main()
