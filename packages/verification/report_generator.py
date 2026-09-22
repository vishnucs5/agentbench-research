from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from packages.extraction.service import ExtractionService
from packages.synthesis.service import SynthesisService
from packages.verification.schemas import (
    BibliographyEntry,
    ReportRequest,
    ReportResponse,
    ReportSection,
    VerificationRequest,
)
from packages.verification.verifier import CitationVerificationService


class ReportGenerationService:
    def __init__(
        self,
        extraction_service: ExtractionService,
        synthesis_service: SynthesisService,
        verification_service: CitationVerificationService,
    ):
        self.extraction_service = extraction_service
        self.synthesis_service = synthesis_service
        self.verification_service = verification_service

    async def generate_report(self, request: ReportRequest) -> ReportResponse:
        synthesis = None
        # No persistent synthesis store exists (no synthesis table), so a
        # load-by-id path is unavailable. Attempt any opt-in cache exposed by
        # the synthesis service; otherwise re-run from paper_ids. The requested
        # synthesis_id is intentionally not stamped onto a fresh result.
        if request.synthesis_id is not None:
            synthesis = self._lookup_cached_synthesis(request.synthesis_id)
        if synthesis is None and (request.synthesis_id is not None or request.paper_ids):
            from packages.synthesis.schemas import SynthesisRequest

            synth_request = SynthesisRequest(
                project_id=request.project_id,
                paper_ids=request.paper_ids,
            )
            synthesis = await self.synthesis_service.run_synthesis(synth_request)

        sections = []
        citations = []
        all_evidence_ids = []

        if request.include_comparison_tables and synthesis:
            for table in synthesis.comparison_tables:
                section = self._build_comparison_section(table)
                sections.append(section)
                for row in table.rows:
                    for cell in row.cells:
                        all_evidence_ids.extend(cell.evidence_ids)

        if request.include_gaps and synthesis:
            gap_section = self._build_gaps_section(synthesis.gaps)
            sections.append(gap_section)

        if request.include_conflicts and synthesis:
            conflict_section = self._build_conflicts_section(synthesis.conflicts)
            sections.append(conflict_section)

        paper_claims = {}
        for pid in request.paper_ids:
            claims = await self.extraction_service.get_paper_claims(pid)
            paper_claims[pid] = claims

        exec_summary = self._generate_executive_summary(request.paper_ids, synthesis, paper_claims)
        exec_section = ReportSection(
            section_id="executive_summary",
            title="Executive Summary",
            content=exec_summary,
        )
        sections.insert(0, exec_section)

        uncertainty_text = None
        if request.include_uncertainty:
            uncertainty_text = self._generate_uncertainty_section(synthesis, paper_claims)
            if uncertainty_text:
                unc_section = ReportSection(
                    section_id="uncertainty",
                    title="Uncertainty and Limitations",
                    content=uncertainty_text,
                )
                sections.append(unc_section)

        bibliography = await self._build_bibliography(request.paper_ids)
        for entry in bibliography:
            citations.append(entry.formatted_citation)

        draft_text = "\n\n".join(f"## {s.title}\n\n{s.content}" for s in sections)

        verification_request = VerificationRequest(
            draft_text=draft_text if draft_text.strip() else "Empty report.",
            evidence_ids=list(set(all_evidence_ids)),
            paper_ids=request.paper_ids,
            strict_mode=False,
        )
        verification_result = await self.verification_service.verify_draft(verification_request)

        return ReportResponse(
            report_id=uuid.uuid4(),
            project_id=request.project_id,
            title=f"Literature Review: {request.paper_ids[0] if request.paper_ids else 'Multi-Paper'}",
            sections=sections,
            executive_summary=exec_summary,
            uncertainty_section=uncertainty_text,
            citations=citations,
            evidence_ids=list(set(all_evidence_ids)),
            verification_result=verification_result,
        )

    def _lookup_cached_synthesis(self, synthesis_id: UUID) -> Any | None:
        # Best-effort load-by-id: probe for an opt-in cache/store on the
        # synthesis service. No such store exists today, so this returns None
        # and the caller falls through to re-run.
        svc: Any = self.synthesis_service
        for attr in ("store", "_store", "cache", "_cache", "syntheses", "_syntheses"):
            candidate = getattr(svc, attr, None)
            if isinstance(candidate, dict) and synthesis_id in candidate:
                return candidate[synthesis_id]
            if isinstance(candidate, dict):
                key = str(synthesis_id)
                if key in candidate:
                    return candidate[key]
        get_by_id = getattr(svc, "get_synthesis", None) or getattr(svc, "get_by_id", None)
        if callable(get_by_id):
            try:
                import asyncio

                result = get_by_id(synthesis_id)
                if asyncio.iscoroutine(result):
                    # Caller is async but this helper is sync; no event loop
                    # juggling here — treat as unavailable and re-run.
                    return None
                return result
            except Exception:
                return None
        return None

    def _build_comparison_section(self, table) -> ReportSection:
        lines = [f"## {table.comparison_type.value.title()} Comparison"]
        lines.append("")
        lines.append(f"**Papers compared:** {len(table.paper_ids)}")
        lines.append("")

        for row in table.rows:
            lines.append(f"### {row.attribute}")
            lines.append("")
            for cell in row.cells:
                val = cell.value.value if cell.value.value else "Not reported"
                conf = (
                    f" (confidence: {cell.value.confidence:.0%})"
                    if cell.value.confidence > 0
                    else ""
                )
                lines.append(f"- **{cell.paper_title}**: {val}{conf}")
                if cell.evidence_ids:
                    lines.append(f"  *Evidence: {', '.join(cell.evidence_ids)}*")
            if row.has_conflicts:
                lines.append(f"  ⚠️ *Conflict detected: {row.conflict_details}*")
            lines.append("")

        return ReportSection(
            section_id=f"comparison_{table.comparison_type.value}",
            title=f"{table.comparison_type.value.title()} Comparison",
            content="\n".join(lines),
            evidence_ids=[
                eid for row in table.rows for cell in row.cells for eid in cell.evidence_ids
            ],
        )

    def _build_gaps_section(self, gaps) -> ReportSection:
        if not gaps:
            return ReportSection(
                section_id="gaps",
                title="Research Gaps",
                content="No significant research gaps identified.",
            )

        lines = ["## Identified Research Gaps", ""]
        for gap in gaps:
            lines.append(f"### {gap.gap_type.value.replace('_', ' ').title()}")
            lines.append(f"**Frequency:** {gap.frequency} papers")
            lines.append(f"**Severity:** {gap.severity}")
            lines.append(f"**Description:** {gap.description}")
            if gap.evidence_ids:
                lines.append(f"*Evidence: {', '.join(gap.evidence_ids)}*")
            lines.append("")

        return ReportSection(
            section_id="gaps",
            title="Research Gaps",
            content="\n".join(lines),
            evidence_ids=[eid for g in gaps for eid in g.evidence_ids],
        )

    def _build_conflicts_section(self, conflicts) -> ReportSection:
        if not conflicts:
            return ReportSection(
                section_id="conflicts",
                title="Conflicts and Inconsistencies",
                content="No significant conflicts identified.",
            )

        lines = ["## Conflicts and Inconsistencies", ""]
        for conflict in conflicts:
            lines.append(f"### {conflict.conflict_type.value.replace('_', ' ').title()}")
            lines.append(f"**Severity:** {conflict.severity}")
            lines.append(f"**Papers involved:** {len(conflict.paper_ids)}")
            lines.append(f"**Description:** {conflict.description}")
            if conflict.details:
                for key, val in conflict.details.items():
                    lines.append(f"  - {key}: {val}")
            lines.append("")

        return ReportSection(
            section_id="conflicts",
            title="Conflicts and Inconsistencies",
            content="\n".join(lines),
            evidence_ids=[eid for c in conflicts for eid in c.details.get("evidence_ids", [])],
        )

    def _generate_executive_summary(
        self,
        paper_ids: list[UUID],
        synthesis: Any | None,
        paper_claims: dict[UUID, list],
    ) -> str:
        lines = [
            f"This report analyzes {len(paper_ids)} research papers in the domain of network intrusion detection.",
            "",
            "## Key Findings",
            "",
        ]

        if synthesis:
            for table in synthesis.comparison_tables:
                lines.append(
                    f"- **{table.comparison_type.value.title()}**: Compared across {len(table.paper_ids)} papers"
                )

        if synthesis and synthesis.gaps:
            lines.append(f"- **Research Gaps**: {len(synthesis.gaps)} gaps identified")
        if synthesis and synthesis.conflicts:
            lines.append(f"- **Conflicts**: {len(synthesis.conflicts)} inconsistencies found")

        lines.extend(["", "## Methodology", ""])
        lines.append(
            "This analysis uses automated structured extraction, hybrid retrieval, and citation verification."
        )
        lines.append("All claims are verified against source evidence with page-level citations.")

        return "\n".join(lines)

    def _generate_uncertainty_section(
        self,
        synthesis: Any | None,
        paper_claims: dict[UUID, list],
    ) -> str:
        lines = ["## Uncertainty and Limitations", ""]

        lines.append("### Extraction Uncertainty")
        lines.append("Claims are extracted using LLMs with structured output validation. ")
        lines.append("Confidence scores reflect extraction reliability. ")

        lines.append("")
        lines.append("### Retrieval Uncertainty")
        lines.append("Hybrid search (BM25 + semantic) may miss relevant passages. ")
        lines.append("Score threshold of 0.3 used for 'not enough evidence' responses. ")

        lines.append("")
        lines.append("### Synthesis Uncertainty")
        lines.append("Comparison tables normalize model names, datasets, and metrics. ")
        lines.append("Normalization may introduce errors for ambiguous terms. ")

        lines.append("")
        lines.append("### Verification Uncertainty")
        lines.append("Citation verification uses LLM-based evidence matching. ")
        lines.append("Partially supported claims indicate mixed evidence. ")

        return "\n".join(lines)

    async def _build_bibliography(self, paper_ids: list[UUID]) -> list[BibliographyEntry]:
        from packages.domain.models import Paper

        entries: list[BibliographyEntry] = []
        for pid in paper_ids:
            claims = await self.extraction_service.get_paper_claims(pid)
            paper = None
            try:
                session = getattr(self.extraction_service, "_session", None)
                if session is not None and hasattr(session, "get"):
                    paper = await session.get(Paper, pid)
            except Exception:
                paper = None
            if paper is not None:
                raw_title = getattr(paper, "title", None)
                title = raw_title if isinstance(raw_title, str) and raw_title else "Unknown Title"
                raw_authors = getattr(paper, "authors_json", []) or []
                authors: list[str] = []
                for a in raw_authors:
                    if isinstance(a, dict):
                        authors.append(str(a.get("name", "")))
                    elif isinstance(a, str):
                        authors.append(a)
                raw_year = getattr(paper, "year", None)
                year = int(raw_year) if isinstance(raw_year, int) else None
                raw_doi = getattr(paper, "doi", None)
                doi = str(raw_doi) if isinstance(raw_doi, str) else None
            else:
                if not claims:
                    continue
                claim = claims[0]
                normalized = getattr(claim, "normalized_value", {}) or {}
                if not isinstance(normalized, dict):
                    normalized = {}
                title = str(normalized.get("title", "Unknown Title"))
                raw_authors = normalized.get("authors", [])
                authors = []
                if isinstance(raw_authors, list):
                    for a in raw_authors:
                        if isinstance(a, dict):
                            authors.append(str(a.get("name", "")))
                        elif isinstance(a, str):
                            authors.append(a)
                year = normalized.get("year")
                year = int(year) if isinstance(year, int) else None
                doi = normalized.get("doi")
                doi = str(doi) if isinstance(doi, str) else None

            author_str = ", ".join(authors) if authors else "Unknown"
            formatted = f"{author_str} ({year}). {title}."
            if doi:
                formatted += f" DOI: {doi}"

            entries.append(
                BibliographyEntry(
                    entry_id=str(uuid.uuid4()),
                    paper_id=pid,
                    formatted_citation=formatted,
                    paper_title=title,
                    authors=authors,
                    year=year,
                    doi=doi,
                )
            )

        return entries


_report_generation_service: Any | None = None


def get_report_generation_service(
    extraction_service: Any,
    synthesis_service: Any,
    verification_service: Any,
) -> ReportGenerationService:
    global _report_generation_service
    if _report_generation_service is None:
        _report_generation_service = ReportGenerationService(
            extraction_service=extraction_service,
            synthesis_service=synthesis_service,
            verification_service=verification_service,
        )
    return _report_generation_service
