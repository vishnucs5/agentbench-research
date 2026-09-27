from __future__ import annotations

import re
from typing import Any


def _make_cite_key(paper: Any) -> str:
    """Generate a valid, deterministic BibTeX citation key."""
    author_str = ""
    authors = getattr(paper, "authors_json", None) or getattr(paper, "authors", None)
    if isinstance(authors, list) and authors:
        first = str(authors[0])
        # Extract last name
        parts = first.strip().split()
        if parts:
            author_str = re.sub(r"[^a-zA-Z]", "", parts[-1]).lower()
    if not author_str:
        title = getattr(paper, "title", "paper") or "paper"
        first_word = title.strip().split()[0] if title.strip() else "paper"
        author_str = re.sub(r"[^a-zA-Z]", "", first_word).lower() or "paper"

    year = getattr(paper, "year", None) or getattr(paper, "publication_year", None) or 2024
    paper_id_short = str(getattr(paper, "id", ""))[:4]
    return f"{author_str}{year}_{paper_id_short}" if paper_id_short else f"{author_str}{year}"


def _format_authors(authors: Any) -> str:
    if isinstance(authors, list) and authors:
        return " and ".join(str(a).strip() for a in authors if a)
    if isinstance(authors, str) and authors:
        return authors.strip()
    return "Unknown Author"


def generate_bibtex(papers: list[Any]) -> str:
    """Generate RFC-compliant BibTeX bibliography entries for a list of papers."""
    if not papers:
        return "% No papers indexed in project bibliography.\n"

    entries: list[str] = [
        "% ==========================================================================",
        "% Auto-generated BibTeX Bibliography from AgentBench-Research",
        f"% Total references: {len(papers)}",
        "% ==========================================================================\n",
    ]

    for p in papers:
        key = _make_cite_key(p)
        title = getattr(p, "title", "Untitled") or "Untitled"
        authors = _format_authors(getattr(p, "authors_json", None) or getattr(p, "authors", None))
        year = getattr(p, "year", None) or getattr(p, "publication_year", None) or 2024
        venue = (
            getattr(p, "journal_or_conference", None)
            or getattr(p, "source_url", None)
            or "arXiv preprint"
        )
        doi = getattr(p, "doi", None)
        abstract = getattr(p, "abstract", None)

        entry_type = (
            "inproceedings"
            if "conference" in venue.lower() or "symposium" in venue.lower()
            else "article"
        )

        fields = [
            f"@{entry_type}{{{key},",
            f"  title = {{{{{title}}}}},",
            f"  author = {{{authors}}},",
            f"  year = {{{year}}},",
            f"  journal = {{{venue}}},"
            if entry_type == "article"
            else f"  booktitle = {{{venue}}},",
        ]

        if doi:
            fields.append(f"  doi = {{{doi}}},")
        if abstract:
            clean_abstract = abstract.strip().replace("\n", " ")
            if len(clean_abstract) > 300:
                clean_abstract = clean_abstract[:297] + "..."
            fields.append(f"  abstract = {{{{{clean_abstract}}}}},")

        fields.append("}\n")
        entries.append("\n".join(fields))

    return "\n".join(entries)
