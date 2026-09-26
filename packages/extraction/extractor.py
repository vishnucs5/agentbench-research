from __future__ import annotations

from dataclasses import dataclass

from packages.agent.providers import ModelProvider, ModelResponse
from packages.extraction.schemas import (
    CLAIM_SCHEMAS,
    ClaimType,
    DatasetClaim,
    FutureWorkClaim,
    LimitationClaim,
    MetricsClaim,
    ModelClaim,
    PreprocessingClaim,
    ResearchProblemClaim,
    ResultsClaim,
)
from pydantic import BaseModel


@dataclass
class ExtractionPrompt:
    system_prompt: str
    user_prompt_template: str
    output_schema: type[BaseModel]


EXTRACTION_PROMPTS = {
    ClaimType.RESEARCH_PROBLEM: ExtractionPrompt(
        system_prompt="""You are an expert research paper analyzer. Extract the research problem, motivation, hypotheses, research questions, and objectives from the given paper text. Be precise and cite specific passages.""",
        user_prompt_template="""Extract the research problem information from this paper text:

{paper_text}

Return a JSON object with these fields:
- problem_statement: The main problem being addressed
- motivation: Why this problem is important
- hypotheses: List of hypotheses (if stated)
- research_questions: List of research questions
- objectives: List of research objectives

If a field is not mentioned in the text, use null or empty list.""",
        output_schema=ResearchProblemClaim,
    ),
    ClaimType.DATASET: ExtractionPrompt(
        system_prompt="""You are an expert research paper analyzer. Extract all dataset information from the given paper text. Include dataset names, descriptions, sizes, splits, sources, and any statistics.""",
        user_prompt_template="""Extract dataset information from this paper text:

{paper_text}

Return a JSON object with these fields:
- name: Dataset name(s)
- description: Description of the dataset
- size: Size information (number of samples, files, etc.)
- splits: Train/val/test splits if mentioned
- source: Where the dataset comes from
- language: Language of the data
- domain: Domain/application area
- collection_method: How data was collected
- statistics: Any reported statistics

If a field is not mentioned, use null or empty.""",
        output_schema=DatasetClaim,
    ),
    ClaimType.PREPROCESSING: ExtractionPrompt(
        system_prompt="""You are an expert research paper analyzer. Extract all preprocessing steps, tools, and parameters from the given paper text.""",
        user_prompt_template="""Extract preprocessing information from this paper text:

{paper_text}

Return a JSON object with these fields:
- steps: List of preprocessing steps
- tools: Tools/libraries used
- parameters: Specific parameters mentioned
- tokenization: Tokenization method
- normalization: Normalization approach
- filtering_criteria: Any filtering applied

If a field is not mentioned, use null or empty.""",
        output_schema=PreprocessingClaim,
    ),
    ClaimType.MODEL: ExtractionPrompt(
        system_prompt="""You are an expert research paper analyzer. Extract all model architecture, training, and hyperparameter information from the given paper text.""",
        user_prompt_template="""Extract model information from this paper text:

{paper_text}

Return a JSON object with these fields:
- name: Model name
- architecture: Architecture description
- framework: Framework used (PyTorch, TensorFlow, etc.)
- parameters: Number of parameters
- training_details: Training procedure details
- hyperparameters: Key hyperparameters
- pretrained: Whether pretrained weights were used
- baseline_models: List of baseline models compared against

If a field is not mentioned, use null or empty.""",
        output_schema=ModelClaim,
    ),
    ClaimType.METRICS: ExtractionPrompt(
        system_prompt="""You are an expert research paper analyzer. Extract all evaluation metrics, their definitions, and evaluation protocols from the given paper text.""",
        user_prompt_template="""Extract metrics and evaluation information from this paper text:

{paper_text}

Return a JSON object with these fields:
- metrics: List of metrics used
- metric_definitions: Definitions of each metric
- evaluation_protocol: How evaluation was conducted
- significance_testing: Statistical significance testing methods

If a field is not mentioned, use null or empty.""",
        output_schema=MetricsClaim,
    ),
    ClaimType.RESULTS: ExtractionPrompt(
        system_prompt="""You are an expert research paper analyzer. Extract all quantitative results, comparisons, and qualitative findings from the given paper text.""",
        user_prompt_template="""Extract results from this paper text:

{paper_text}

Return a JSON object with these fields:
- metric_results: Dictionary mapping metric names to their values
- best_results: Best performing configurations/results
- statistical_significance: Significance test results
- comparison_results: Comparisons with baselines
- qualitative_findings: Key qualitative observations

If a field is not mentioned, use null or empty.""",
        output_schema=ResultsClaim,
    ),
    ClaimType.LIMITATIONS: ExtractionPrompt(
        system_prompt="""You are an expert research paper analyzer. Extract all stated limitations, their severity, and impact from the given paper text.""",
        user_prompt_template="""Extract limitations from this paper text:

{paper_text}

Return a JSON object with these fields:
- limitation_text: The limitation description
- severity: Severity level (high/medium/low)
- category: Type of limitation (data/method/evaluation/etc.)
- impact: Impact of this limitation
- mitigation: Suggested mitigations

If a field is not mentioned, use null.""",
        output_schema=LimitationClaim,
    ),
    ClaimType.FUTURE_WORK: ExtractionPrompt(
        system_prompt="""You are an expert research paper analyzer. Extract all future work suggestions from the given paper text.""",
        user_prompt_template="""Extract future work suggestions from this paper text:

{paper_text}

Return a JSON object with these fields:
- suggestion: The future work suggestion
- priority: Priority level (high/medium/low)
- category: Category of future work
- rationale: Why this is important

If a field is not mentioned, use null.""",
        output_schema=FutureWorkClaim,
    ),
}


def create_extraction_prompt(
    claim_type: ClaimType, paper_text: str
) -> tuple[str, str, type[BaseModel]]:
    prompt = EXTRACTION_PROMPTS.get(claim_type)
    if not prompt:
        raise ValueError(f"No extraction prompt for claim type: {claim_type}")
    user_prompt = prompt.user_prompt_template.format(paper_text=paper_text)
    return prompt.system_prompt, user_prompt, prompt.output_schema


async def extract_claim(
    provider: ModelProvider,
    claim_type: ClaimType,
    paper_text: str,
    temperature: float = 0.0,
) -> ModelResponse:
    system_prompt, user_prompt, output_schema = create_extraction_prompt(claim_type, paper_text)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    return await provider.complete(
        messages=messages,
        temperature=temperature,
        response_format=output_schema,
        max_tokens=4000,
    )


async def extract_all_claims(
    provider: ModelProvider,
    paper_text: str,
    claim_types: list[ClaimType] | None = None,
    temperature: float = 0.0,
) -> dict[ClaimType, ModelResponse]:
    if claim_types is None:
        claim_types = list(CLAIM_SCHEMAS.keys())

    results = {}
    for claim_type in claim_types:
        try:
            results[claim_type] = await extract_claim(provider, claim_type, paper_text, temperature)
        except Exception as e:
            results[claim_type] = ModelResponse(
                content=f"Extraction failed: {str(e)}",
                usage=None,
                model=None,
                finish_reason="error",
            )
    return results
