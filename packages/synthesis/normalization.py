from __future__ import annotations

import re
from typing import Any

from packages.synthesis.schemas import NormalizedEntity

MODEL_ALIASES = {
    "bert": ["bert-base", "bert-large", "bert-base-uncased", "bert-large-uncased", "google/bert"],
    "roberta": ["roberta-base", "roberta-large", "facebook/roberta"],
    "distilbert": ["distilbert-base-uncased", "distilbert-base"],
    "xlnet": ["xlnet-base-cased", "xlnet-large-cased"],
    "gpt-2": ["gpt2", "gpt-2", "openai/gpt2"],
    "gpt-3": ["gpt3", "gpt-3", "text-davinci-003"],
    "t5": ["t5-base", "t5-large", "t5-small", "google/t5"],
    "bart": ["bart-base", "bart-large", "facebook/bart"],
    "electra": ["electra-base", "electra-small", "google/electra"],
    "deberta": ["deberta-base", "deberta-large", "microsoft/deberta"],
    "cnn": ["convolutional neural network", "convnet"],
    "rnn": ["recurrent neural network"],
    "lstm": ["long short-term memory"],
    "gru": ["gated recurrent unit"],
    "transformer": ["transformer model", "attention model"],
    "resnet": ["resnet50", "resnet101", "resnet152", "residual network"],
    "vgg": ["vgg16", "vgg19"],
    "efficientnet": ["efficientnet-b0", "efficientnet-b7"],
    "vit": ["vision transformer", "vit-base", "vit-large"],
    "swin": ["swin transformer", "swin-base", "swin-large"],
}

DATASET_ALIASES = {
    "cicids2017": ["cic-ids2017", "cic ids 2017", "canadian institute for cybersecurity ids 2017"],
    "cicids2018": ["cic-ids2018", "cic ids 2018"],
    "nsl-kdd": ["nsl kdd", "kdd cup 99", "kdd99"],
    "unsw-nb15": ["unsw nb15", "unsw-nb15"],
    "ton-iot": ["ton iot", "ton_iot"],
    "kitsune": ["kitsune network"],
    "mawilab": ["mawi lab"],
    "caida": ["caida dataset"],
    "iscx2012": ["iscx 2012", "iscx-2012"],
    "ctu-13": ["ctu 13", "ctu-13"],
    "bot-iot": ["bot iot", "bot_iot"],
    "nf-corpus": ["nf corpus", "nfcorpus"],
    "nf-stream": ["nf stream", "nfstream"],
}

METRIC_ALIASES = {
    "accuracy": ["acc", "classification accuracy"],
    "precision": ["prec", "positive predictive value"],
    "recall": ["rec", "sensitivity", "true positive rate", "tpr"],
    "f1": ["f1-score", "f1 score", "f-measure", "f measure"],
    "f1-macro": ["macro f1", "macro-f1"],
    "f1-micro": ["micro f1", "micro-f1"],
    "f1-weighted": ["weighted f1", "weighted-f1"],
    "auc": ["auroc", "area under roc curve", "roc auc"],
    "auc-pr": ["auprc", "area under pr curve", "pr auc"],
    "false positive rate": ["fpr", "fall-out"],
    "false negative rate": ["fnr", "miss rate"],
    "true negative rate": ["tnr", "specificity"],
    "matthews correlation coefficient": ["mcc", "matthews corrcoef"],
    "cohen kappa": ["kappa", "cohen's kappa"],
    "balanced accuracy": ["bal acc", "balanced acc"],
    "detection rate": ["dr", "detection accuracy"],
    "false alarm rate": ["far", "false alarm ratio"],
}

UNIT_NORMALIZATION = {
    "seconds": ["sec", "s", "second"],
    "milliseconds": ["ms", "millisecond"],
    "microseconds": ["us", "µs", "microsecond"],
    "megabytes": ["mb", "mbyte"],
    "gigabytes": ["gb", "gbyte"],
    "kilobytes": ["kb", "kbyte"],
    "samples": ["sample", "instances", "records"],
    "packets": ["packet", "pkts"],
    "flows": ["flow", "network flows"],
    "epochs": ["epoch", "ep"],
    "iterations": ["iter", "iteration"],
    "percentage": ["%", "percent", "pct"],
}


def normalize_model_name(name: str) -> NormalizedEntity:
    if not name:
        return NormalizedEntity(
            entity_type="model",
            original_value=name or "",
            normalized_value="",
            confidence=0.0,
        )

    lower = name.lower().strip()
    for canonical, aliases in MODEL_ALIASES.items():
        if lower == canonical or lower in aliases:
            return NormalizedEntity(
                entity_type="model",
                original_value=name,
                normalized_value=canonical,
                confidence=0.95,
                aliases=[canonical] + aliases,
            )

    for canonical, aliases in MODEL_ALIASES.items():
        for alias in aliases:
            if alias in lower or lower in alias:
                return NormalizedEntity(
                    entity_type="model",
                    original_value=name,
                    normalized_value=canonical,
                    confidence=0.7,
                    aliases=[canonical] + aliases,
                )

    return NormalizedEntity(
        entity_type="model",
        original_value=name,
        normalized_value=name,
        confidence=0.5,
        aliases=[],
    )


def normalize_dataset_name(name: str) -> NormalizedEntity:
    if not name:
        return NormalizedEntity(
            entity_type="dataset",
            original_value=name or "",
            normalized_value="",
            confidence=0.0,
        )

    lower = name.lower().strip().replace("-", "").replace("_", "").replace(" ", "")
    for canonical, aliases in DATASET_ALIASES.items():
        canonical_clean = canonical.replace("-", "").replace("_", "").replace(" ", "")
        if lower == canonical_clean:
            return NormalizedEntity(
                entity_type="dataset",
                original_value=name,
                normalized_value=canonical,
                confidence=0.95,
                aliases=[canonical] + aliases,
            )
        for alias in aliases:
            alias_clean = alias.replace("-", "").replace("_", "").replace(" ", "")
            if lower == alias_clean:
                return NormalizedEntity(
                    entity_type="dataset",
                    original_value=name,
                    normalized_value=canonical,
                    confidence=0.9,
                    aliases=[canonical] + aliases,
                )

    return NormalizedEntity(
        entity_type="dataset",
        original_value=name,
        normalized_value=name,
        confidence=0.5,
        aliases=[],
    )


def normalize_metric_name(name: str) -> NormalizedEntity:
    if not name:
        return NormalizedEntity(
            entity_type="metric",
            original_value=name or "",
            normalized_value="",
            confidence=0.0,
        )

    lower = name.lower().strip().replace("-", "").replace("_", "").replace(" ", "")
    for canonical, aliases in METRIC_ALIASES.items():
        canonical_clean = canonical.replace("-", "").replace("_", "").replace(" ", "")
        if lower == canonical_clean:
            return NormalizedEntity(
                entity_type="metric",
                original_value=name,
                normalized_value=canonical,
                confidence=0.95,
                aliases=[canonical] + aliases,
            )
        for alias in aliases:
            alias_clean = alias.replace("-", "").replace("_", "").replace(" ", "")
            if lower == alias_clean:
                return NormalizedEntity(
                    entity_type="metric",
                    original_value=name,
                    normalized_value=canonical,
                    confidence=0.9,
                    aliases=[canonical] + aliases,
                )

    return NormalizedEntity(
        entity_type="metric",
        original_value=name,
        normalized_value=name,
        confidence=0.5,
        aliases=[],
    )


def normalize_unit(value: str) -> NormalizedEntity:
    if not value:
        return NormalizedEntity(
            entity_type="unit",
            original_value=value or "",
            normalized_value="",
            confidence=0.0,
        )

    lower = value.lower().strip()
    for canonical, aliases in UNIT_NORMALIZATION.items():
        if lower == canonical or lower in aliases:
            return NormalizedEntity(
                entity_type="unit",
                original_value=value,
                normalized_value=canonical,
                confidence=0.95,
                aliases=[canonical] + aliases,
            )

    return NormalizedEntity(
        entity_type="unit",
        original_value=value,
        normalized_value=value,
        confidence=0.5,
        aliases=[],
    )


def normalize_numeric_value(value: Any, unit: str | None = None) -> tuple[float | None, str | None]:
    if value is None:
        return None, None

    if isinstance(value, (int, float)):
        return float(value), unit

    if isinstance(value, str):
        match = re.match(r"([\d.]+)\s*(%|percent|pct)?", value.strip())
        if match:
            num = float(match.group(1))
            if match.group(2) or "%" in value:
                return num / 100.0, "percentage"
            return num, unit or normalize_unit(value).normalized_value

    return None, None


class NormalizationService:
    def __init__(self):
        self.model_rules = MODEL_ALIASES
        self.dataset_rules = DATASET_ALIASES
        self.metric_rules = METRIC_ALIASES
        self.unit_rules = UNIT_NORMALIZATION

    def normalize_model(self, name: str) -> NormalizedEntity:
        return normalize_model_name(name)

    def normalize_dataset(self, name: str) -> NormalizedEntity:
        return normalize_dataset_name(name)

    def normalize_metric(self, name: str) -> NormalizedEntity:
        return normalize_metric_name(name)

    def normalize_unit(self, unit: str) -> NormalizedEntity:
        return normalize_unit(unit)

    def add_model_alias(self, canonical: str, alias: str) -> None:
        if canonical not in self.model_rules:
            self.model_rules[canonical] = []
        if alias not in self.model_rules[canonical]:
            self.model_rules[canonical].append(alias)

    def add_dataset_alias(self, canonical: str, alias: str) -> None:
        if canonical not in self.dataset_rules:
            self.dataset_rules[canonical] = []
        if alias not in self.dataset_rules[canonical]:
            self.dataset_rules[canonical].append(alias)

    def add_metric_alias(self, canonical: str, alias: str) -> None:
        if canonical not in self.metric_rules:
            self.metric_rules[canonical] = []
        if alias not in self.metric_rules[canonical]:
            self.metric_rules[canonical].append(alias)


_normalization_service: NormalizationService | None = None


def get_normalization_service() -> NormalizationService:
    global _normalization_service
    if _normalization_service is None:
        _normalization_service = NormalizationService()
    return _normalization_service
