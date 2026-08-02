#!/usr/bin/env python3
r"""Build the public paper catalog from the survey's LaTeX sources.

The script recursively expands ``\input``/``\include`` directives so citations
inside tables and figures inherit their location in the manuscript. It writes
only references that are actually cited by the compiled paper.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote_plus

try:
    from pylatexenc.latex2text import LatexNodes2Text
except ImportError:  # pragma: no cover - optional convenience dependency
    LatexNodes2Text = None


SECTION_RE = re.compile(
    r"\\(?P<level>section|subsection|subsubsection|paragraph)\*?"
    r"(?:\[[^\]]*\])?\{(?P<title>(?:[^{}]|\{[^{}]*\})*)\}",
    re.DOTALL,
)
CITE_RE = re.compile(
    r"\\(?:[A-Za-z]*cite[A-Za-z]*|cite)\*?"
    r"(?:\[[^\]]*\]){0,2}\{(?P<keys>[^{}]+)\}",
    re.DOTALL,
)
EVENT_RE = re.compile(
    rf"(?P<section>{SECTION_RE.pattern})|(?P<cite>{CITE_RE.pattern})",
    re.DOTALL,
)
INCLUDE_RE = re.compile(r"\\(?:input|include)\{([^{}]+)\}")

OPERATION_BY_SECTION = {
    "Video Comprehension: Reading the World": "reading",
    "Video Generation: Writing the World": "writing",
    "Unified Video Models: Sharing the World": "sharing",
    "Video World Models: Interacting with the World": "interacting",
}

OPERATION_PRIORITY = {
    "reading": 0,
    "writing": 0,
    "sharing": 0,
    "interacting": 0,
    "foundations": 1,
    "frontiers": 2,
}

GRAPH_BRANCHES = {
    "Reading": "reading",
    "Writing": "writing",
    "Sharing": "sharing",
    "Interacting": "interacting",
}

URL_OVERRIDES = {
    "ren2024timechat": "https://openaccess.thecvf.com/content/CVPR2024/html/Ren_TimeChat_A_Time-sensitive_Multimodal_Large_Language_Model_for_Long_Video_CVPR_2024_paper.html",
    "onex2024worldmodel": "https://www.1x.tech/discover/1x-world-model",
    "yin2023nuwa": "https://aclanthology.org/2023.acl-long.73/",
}

VENUE_PATTERNS = (
    (r"Computer Vision and Pattern Recognition.*Workshop", "CVPRW"),
    (r"Computer Vision and Pattern Recognition", "CVPR"),
    (r"International Conference on Computer Vision", "ICCV"),
    (r"European Conference on Computer Vision", "ECCV"),
    (r"Neural Information Processing Systems", "NeurIPS"),
    (r"International Conference on Machine Learning", "ICML"),
    (r"International Conference on Learning Representations", "ICLR"),
    (r"Annual Meeting of the Association for Computational Linguistics", "ACL"),
    (r"Empirical Methods in Natural Language Processing", "EMNLP"),
    (r"ACM International Conference on Multimedia", "ACM MM"),
    (r"Special Interest Group on Computer Graphics and Interactive Techniques", "SIGGRAPH"),
    (r"SIGGRAPH Asia", "SIGGRAPH Asia"),
    (r"Conference on Language Modeling", "COLM"),
    (r"International Journal of Computer Vision", "IJCV"),
    (r"Transactions on Medical Imaging", "TMI"),
    (r"Computer Vision and Image Understanding", "CVIU"),
    (r"Transactions on Machine Learning Research", "TMLR"),
    (r"Pattern Analysis and Machine Intelligence", "TPAMI"),
    (r"International Conference on Acoustics.*Signal Processing", "ICASSP"),
    (r"International Conference on 3D Vision", "3DV"),
    (r"\bCVPR\b", "CVPR"),
    (r"\bICCV\b", "ICCV"),
    (r"\bECCV\b", "ECCV"),
    (r"\bNeurIPS\b", "NeurIPS"),
    (r"\bICML\b", "ICML"),
    (r"\bICLR\b", "ICLR"),
    (r"\bAAAI\b", "AAAI"),
    (r"\bIJCAI\b", "IJCAI"),
    (r"\bACL\b", "ACL"),
    (r"\bEMNLP\b", "EMNLP"),
    (r"\bNAACL\b", "NAACL"),
    (r"\bCOLM\b", "COLM"),
    (r"\bCoRL\b", "CoRL"),
    (r"\bIROS\b", "IROS"),
    (r"\bICRA\b", "ICRA"),
    (r"\bWACV\b", "WACV"),
    (r"\bACM MM\b", "ACM MM"),
    (r"\bT-PAMI\b|\bTPAMI\b", "TPAMI"),
    (r"\bTMLR\b", "TMLR"),
)


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%[^\n]*", "", text)


def expand_tex(path: Path, root: Path, stack: tuple[Path, ...] = ()) -> str:
    path = path.resolve()
    if path in stack:
        chain = " -> ".join(str(item) for item in (*stack, path))
        raise RuntimeError(f"Recursive LaTeX include: {chain}")
    text = strip_comments(path.read_text(encoding="utf-8"))

    def replace(match: re.Match[str]) -> str:
        target = match.group(1)
        include = Path(target)
        if include.suffix == "":
            include = include.with_suffix(".tex")
        candidates = (path.parent / include, root / include)
        found = next((item for item in candidates if item.exists()), None)
        if found is None:
            return match.group(0)
        return expand_tex(found, root, (*stack, path))

    return INCLUDE_RE.sub(replace, text)


def extract_bib_entries(text: str) -> tuple[dict[str, str], list[str]]:
    entries: dict[str, str] = {}
    order: list[str] = []
    start_re = re.compile(r"@([A-Za-z]+)\s*([\{\(])\s*([^,\s]+)\s*,")

    for match in start_re.finditer(text):
        key = match.group(3)
        opener = match.group(2)
        closer = "}" if opener == "{" else ")"
        depth = 0
        escaped = False
        end = None
        for index in range(match.start(), len(text)):
            char = text[index]
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            raise RuntimeError(f"Unclosed BibTeX entry: {key}")
        entries[key] = text[match.start() : end].strip()
        order.append(key)
    return entries, order


def parse_bib_fields(entry: str) -> dict[str, str]:
    head = re.match(r"@(?P<type>[A-Za-z]+)\s*[\{\(]\s*(?P<key>[^,\s]+)\s*,", entry)
    if head is None:
        raise ValueError("Invalid BibTeX entry")
    fields = {"ENTRYTYPE": head.group("type").lower(), "ID": head.group("key")}
    body = entry[head.end() : -1]
    field_re = re.compile(r"(?im)^\s*([A-Za-z][\w-]*)\s*=\s*")
    matches = list(field_re.finditer(body))
    for index, match in enumerate(matches):
        raw = body[match.end() : matches[index + 1].start() if index + 1 < len(matches) else len(body)]
        raw = raw.rstrip().rstrip(",").strip()
        if len(raw) >= 2 and raw[0] == "{" and raw[-1] == "}":
            raw = raw[1:-1]
        elif len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
            raw = raw[1:-1]
        fields[match.group(1).lower()] = raw.strip()
    return fields


def latex_to_text(value: str) -> str:
    value = value.replace("~", " ")
    if LatexNodes2Text is not None:
        converted = LatexNodes2Text().latex_to_text(value)
    else:
        accent_map = {
            "'": "\u0301",
            "`": "\u0300",
            '"': "\u0308",
            "^": "\u0302",
            "~": "\u0303",
            "c": "\u0327",
        }

        def accent(match: re.Match[str]) -> str:
            return unicodedata.normalize(
                "NFC", match.group(2) + accent_map.get(match.group(1), "")
            )

        converted = re.sub(r"\\([\'`\"\^~c])\{?([A-Za-z])\}?", accent, value)
        converted = re.sub(r"\\(?:textit|textbf|emph|mathrm|mathbf)\{([^{}]*)\}", r"\1", converted)
        converted = re.sub(r"\\[A-Za-z]+\*?", "", converted)
        converted = converted.replace(r"\&", "&").replace(r"\%", "%")
        converted = converted.replace("{", "").replace("}", "")
    converted = re.sub(r"\s+", " ", converted)
    return converted.strip()


def split_authors(raw: str) -> list[str]:
    authors = []
    for author in re.split(r"\s+and\s+", raw.strip()):
        clean = latex_to_text(author)
        if "," in clean:
            last, first = (part.strip() for part in clean.split(",", 1))
            clean = f"{first} {last}".strip()
        if clean:
            authors.append(clean)
    return authors


def short_authors(authors: list[str]) -> str:
    if not authors:
        return "Unknown authors"
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return f"{authors[0]} and {authors[1]}"
    return f"{authors[0]} et al."


def operation_for_section(section: str) -> str:
    if section in OPERATION_BY_SECTION:
        return OPERATION_BY_SECTION[section]
    if section in {"Open Challenges and Future Directions", "Conclusion"}:
        return "frontiers"
    return "foundations"


def parse_citation_contexts(tex: str) -> tuple[dict[str, list[dict]], list[str]]:
    hierarchy = {"section": "", "subsection": "", "subsubsection": "", "paragraph": ""}
    contexts: dict[str, list[dict]] = defaultdict(list)
    citation_order: list[str] = []

    for event in EVENT_RE.finditer(tex):
        if event.group("section"):
            level = event.group("level")
            title = latex_to_text(event.group("title"))
            hierarchy[level] = title
            if level == "section":
                hierarchy.update(subsection="", subsubsection="", paragraph="")
            elif level == "subsection":
                hierarchy.update(subsubsection="", paragraph="")
            elif level == "subsubsection":
                hierarchy["paragraph"] = ""
            continue

        keys = [key.strip() for key in event.group("keys").split(",") if key.strip()]
        path = [
            hierarchy[level]
            for level in ("section", "subsection", "subsubsection", "paragraph")
            if hierarchy[level]
        ]
        context = {
            "operation": operation_for_section(hierarchy["section"]),
            "section": hierarchy["section"] or "Front Matter",
            "subsection": hierarchy["subsection"],
            "subsubsection": hierarchy["subsubsection"],
            "paragraph": hierarchy["paragraph"],
            "path": path or ["Front Matter"],
        }
        for key in keys:
            contexts[key].append(context)
            if key not in citation_order:
                citation_order.append(key)
    return contexts, citation_order


def graph_contexts(path: Path) -> dict[str, list[dict]]:
    text = strip_comments(path.read_text(encoding="utf-8"))
    branch_re = re.compile(
        r"%\s*=+\s*(Reading|Writing|Sharing|Interacting)\s*=+\s*(.*?)(?=%\s*=+|\Z)",
        re.DOTALL,
    )
    result: dict[str, list[dict]] = defaultdict(list)
    for branch in branch_re.finditer(text):
        label = branch.group(1)
        operation = GRAPH_BRANCHES[label]
        for cite in CITE_RE.finditer(branch.group(2)):
            for key in (item.strip() for item in cite.group("keys").split(",")):
                if key:
                    result[key].append(
                        {
                            "operation": operation,
                            "section": f"{label} the World",
                            "subsection": "Knowledge Graph",
                            "subsubsection": "",
                            "paragraph": "",
                            "path": [f"{label} the World", "Knowledge Graph"],
                        }
                    )
    return result


def choose_primary(contexts: list[dict]) -> dict:
    operation_contexts = [
        item
        for item in contexts
        if item["operation"] in {"reading", "writing", "sharing", "interacting"}
    ]
    candidates = operation_contexts or contexts
    return min(
        candidates,
        key=lambda item: (
            OPERATION_PRIORITY[item["operation"]],
            -len(item["path"]),
            contexts.index(item),
        ),
    )


def venue_details(fields: dict[str, str]) -> tuple[str, str, str]:
    raw = fields.get("booktitle") or fields.get("journal") or fields.get("publisher") or ""
    venue = latex_to_text(raw)
    lower = venue.lower()
    url = fields.get("url", "").lower()
    archive = fields.get("archiveprefix", "").lower()
    if venue and "arxiv" not in lower:
        for pattern, short in VENUE_PATTERNS:
            if re.search(pattern, venue, re.IGNORECASE):
                return venue, short, "published"
    if "arxiv" in lower or "arxiv.org" in url or archive == "arxiv":
        return "arXiv", "arXiv", "preprint"
    for pattern, short in VENUE_PATTERNS:
        if re.search(pattern, venue, re.IGNORECASE):
            return venue, short, "published"
    parenthetical = re.findall(r"\(([A-Z][A-Z0-9-]{2,})\)", venue)
    short = parenthetical[-1] if parenthetical else venue
    if len(short) > 34:
        short = short[:31].rstrip() + "…"
    if venue:
        return venue, short, "published"
    if fields.get("url"):
        return "Official project page", "Project", "official"
    return "Preprint", "Preprint", "preprint"


def paper_url(fields: dict[str, str], title: str) -> tuple[str, str]:
    if fields["ID"] in URL_OVERRIDES:
        return URL_OVERRIDES[fields["ID"]], ""
    url = latex_to_text(fields.get("url", ""))
    eprint = latex_to_text(fields.get("eprint", ""))
    doi = latex_to_text(fields.get("doi", ""))
    arxiv = ""
    if eprint and re.fullmatch(r"\d{4}\.\d{4,5}(?:v\d+)?", eprint):
        arxiv = eprint
    elif "arxiv.org/abs/" in url:
        arxiv = url.split("arxiv.org/abs/", 1)[1].split("?", 1)[0].rstrip("/")
    if not arxiv:
        arxiv_text = " ".join(
            latex_to_text(fields.get(name, ""))
            for name in ("journal", "note", "howpublished")
        )
        match = re.search(r"arXiv\s*(?:preprint\s*)?(?:arXiv:)?\s*(\d{4}\.\d{4,5}(?:v\d+)?)", arxiv_text, re.IGNORECASE)
        if match:
            arxiv = match.group(1)
    if url:
        return url, arxiv
    if doi:
        return f"https://doi.org/{doi}", arxiv
    if arxiv:
        return f"https://arxiv.org/abs/{arxiv}", arxiv
    return f"https://scholar.google.com/scholar?q={quote_plus(title)}", ""


def unique_contexts(items: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for item in items:
        signature = tuple(item["path"])
        if signature not in seen:
            seen.add(signature)
            result.append(item)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="LaTeX project root")
    parser.add_argument("--output", type=Path, default=Path("data"), help="Output directory")
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    expanded = expand_tex(source / "main.tex", source)
    contexts, citation_order = parse_citation_contexts(expanded)
    graph = graph_contexts(source / "figures" / "F03_knowledge_graph.tex")
    for key, items in graph.items():
        contexts[key].extend(items)

    bib_text = (source / "paper.bib").read_text(encoding="utf-8")
    raw_entries, bib_order = extract_bib_entries(bib_text)
    missing = sorted(set(citation_order) - set(raw_entries))
    if missing:
        raise RuntimeError(f"Missing BibTeX entries: {', '.join(missing)}")

    papers = []
    for key in citation_order:
        fields = parse_bib_fields(raw_entries[key])
        title = latex_to_text(fields.get("title", key))
        authors = split_authors(fields.get("author", ""))
        venue, venue_short, record_type = venue_details(fields)
        url, arxiv = paper_url(fields, title)
        item_contexts = unique_contexts(contexts[key])
        primary = choose_primary(item_contexts)
        operations = list(
            dict.fromkeys(
                item["operation"]
                for item in item_contexts
                if item["operation"] in {"reading", "writing", "sharing", "interacting"}
            )
        )
        if not operations:
            operations = [primary["operation"]]

        papers.append(
            {
                "key": key,
                "title": title,
                "authors": authors,
                "authorsShort": short_authors(authors),
                "year": int(re.search(r"\d{4}", fields.get("year", "0")).group())
                if re.search(r"\d{4}", fields.get("year", ""))
                else None,
                "venue": venue,
                "venueShort": venue_short,
                "recordType": record_type,
                "url": url,
                "doi": latex_to_text(fields.get("doi", "")),
                "arxiv": arxiv,
                "operation": primary["operation"],
                "operations": operations,
                "primarySection": primary["subsection"] or primary["section"],
                "sectionPath": primary["path"],
                "sections": [item["path"] for item in item_contexts],
            }
        )

    operation_order = {
        "foundations": 0,
        "reading": 1,
        "writing": 2,
        "sharing": 3,
        "interacting": 4,
        "frontiers": 5,
    }
    papers.sort(
        key=lambda item: (
            operation_order[item["operation"]],
            item["primarySection"].lower(),
            -(item["year"] or 0),
            item["title"].lower(),
        )
    )

    payload = {
        "metadata": {
            "title": "Reading, Writing, Sharing, and Interacting with the World through Video",
            "subtitle": "A Survey of Video Foundation Models through the Lens of World Modeling",
            "authors": [
                "Meng Luo",
                "Shengqiong Wu",
                "Bobo Li",
                "Mong-Li Lee",
                "Wynne Hsu",
                "Ziwei Liu",
                "Shuicheng Yan",
                "Philip Torr",
                "Ming-Hsuan Yang",
                "Hao Fei",
            ],
            "updated": "2026-07-28",
            "paperCount": len(papers),
            "sourceBibEntryCount": len(raw_entries),
        },
        "papers": papers,
    }
    (output / "papers.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    cited = set(citation_order)
    selected = [raw_entries[key] for key in bib_order if key in cited]
    (output / "references.bib").write_text("\n\n".join(selected) + "\n", encoding="utf-8")

    counts = defaultdict(int)
    for paper in papers:
        counts[paper["operation"]] += 1
    print(f"Wrote {len(papers)} papers and {len(selected)} BibTeX entries")
    print(" | ".join(f"{key}: {counts[key]}" for key in operation_order))


if __name__ == "__main__":
    main()
