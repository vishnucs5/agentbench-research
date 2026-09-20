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
        if request.synthesis_id:
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

        bibliography = self._build_bibliography(request.paper_ids)
        for entry in bibliography:
            citations.append(entry.formatted_citation)

        draft_text = "\n\n".join(f"## {s.title}\n\n{s.content}" for s in sections)

        verification_request = type("VerificationRequest", (), {
            "draft_text": draft_text,
            "evidence_ids": list(set(all_evidence_ids)),
            "paper_ids": request.paper_ids,
            "strict_mode": False,
        })()
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
                conf = f" (confidence: {cell.value.confidence:.0%})" if cell.value.confidence > 0 else ""
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
            evidence_ids=[eid for row in table.rows for cell in row.cells for eid in cell.evidence_ids],
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
                lines.append(f"- **{table.comparison_type.value.title()}**: Compared across {len(table.paper_ids)} papers")

        if synthesis and synthesis.gaps:
            lines.append(f"- **Research Gaps**: {len(synthesis.gaps)} gaps identified")
        if synthesis and synthesis.conflicts:
            lines.append(f"- **Conflicts**: {len(synthesis.conflicts)} inconsistencies found")

        lines.extend(["", "## Methodology", ""])
        lines.append("This analysis uses automated structured extraction, hybrid retrieval, and citation verification.")
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

    def _build_bibliography(self, paper_ids: list[UUID]) -> list[BibliographyEntry]:
        entries = []
        for pid in paper_ids:
            claims = self.extraction_service.get_paper_claims(pid)
            if not claims:
                continue
            claim = claims[0]
            normalized = getattr(claim, "normalized_value", {})
            title = normalized.get("title", "Unknown Title")
            authors = normalized.get("authors", [])
            year = normalized.get("year")
            doi = normalized.get("doi")

            author_str = ", ".join([a.get("name", "") for a in authors]) if authors else "Unknown"
            formatted = f"{author_str} ({year}). {title}."
            if doi:
                formatted += f" DOI: {doi}"

            entries.append(BibliographyEntry(
                entry_id=str(uuid.uuid4()),
                paper_id=pid,
                formatted_citation=formatted,
                paper_title=title,
                authors=[a.get("name", "") for a in authors] if authors else [],
                year=year,
                doi=doi,
            ))

        return entries


_report_generation_service: Any | None = None


def get_report_generation_service(extraction_service, synthesis_service, verification_service):
    global _report_generation_service
    if _report_generation_service is None:
        _report_generation_service = ReportGenerationService(
            extraction_service=extraction_service,
            synthesis_service=synthesis_service,
            verification_service=verification_service,
        )
    return _report_generation_service
