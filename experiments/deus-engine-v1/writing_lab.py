#!/usr/bin/env python3
"""DEUS Engine v1 — literary stress-test harness.

Purpose: develop a distinctive, causally coherent literary voice and detect
model-generic habits. This is NOT an AI-detector bypass tool and should not be
used to misrepresent authorship where disclosure is required.
"""
from __future__ import annotations

import json
import math
import re
import statistics
from collections import Counter
from dataclasses import dataclass, asdict, field
from typing import Iterable, Sequence


SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+|\n+")
WORD_RE = re.compile(r"[A-Za-zÀ-ỹ0-9_'-]+", re.UNICODE)

# These are generic-writing habits, not evidence that a text was AI-generated.
GENERIC_MARKERS = (
    "nói cách khác",
    "điều này có nghĩa là",
    "tóm lại",
    "nhìn chung",
    "quan trọng hơn",
    "không chỉ",
    "mà còn",
    "có thể thấy rằng",
    "điều đáng chú ý là",
    "ở một khía cạnh khác",
    "cuối cùng",
)

OVEREXPLAIN_MARKERS = (
    "ý tôi là",
    "để hiểu rõ hơn",
    "cụ thể là",
    "nói một cách đơn giản",
    "điều này cho thấy",
    "điều đó chứng minh",
)


@dataclass(frozen=True)
class VoiceProfile:
    character: str
    preferred_terms: tuple[str, ...] = ()
    avoided_terms: tuple[str, ...] = ()
    max_mean_sentence_words: float | None = None
    min_mean_sentence_words: float | None = None


@dataclass(frozen=True)
class WritingCase:
    case_id: str
    text: str
    character: str | None = None
    required_memory_tokens: tuple[str, ...] = ()
    forbidden_exposition: tuple[str, ...] = ()
    preserve_ambiguity_terms: tuple[str, ...] = ()
    expected_callback_tokens: tuple[str, ...] = ()


@dataclass
class Check:
    name: str
    score: float
    evidence: dict = field(default_factory=dict)


@dataclass
class Report:
    case_id: str
    checks: list[Check]
    total: float
    notes: list[str]

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "total": round(self.total, 4),
            "checks": [asdict(x) for x in self.checks],
            "notes": self.notes,
        }


def sentences(text: str) -> list[str]:
    return [x.strip() for x in SENTENCE_RE.split(text.strip()) if x.strip()]


def words(text: str) -> list[str]:
    return [x.lower() for x in WORD_RE.findall(text)]


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _variation_score(values: Sequence[int]) -> float:
    if len(values) < 2:
        return 0.4
    mean = statistics.mean(values)
    if mean <= 0:
        return 0.0
    cv = statistics.pstdev(values) / mean
    # Literary prose usually benefits from some rhythm variation, but maximal
    # randomness is not the goal. Reward a broad middle band.
    return _clamp(1.0 - abs(cv - 0.55) / 0.70)


def rhythm_check(text: str) -> Check:
    sents = sentences(text)
    lengths = [len(words(s)) for s in sents]
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    para_lengths = [len(words(p)) for p in paragraphs]
    sentence_variation = _variation_score(lengths)
    paragraph_variation = _variation_score(para_lengths) if len(para_lengths) > 1 else 0.5
    score = 0.7 * sentence_variation + 0.3 * paragraph_variation
    return Check("RHYTHM_VARIATION", score, {
        "sentence_word_counts": lengths,
        "paragraph_word_counts": para_lengths,
    })


def generic_habit_check(text: str) -> Check:
    low = text.lower()
    hits = {m: low.count(m) for m in GENERIC_MARKERS if m in low}
    total_words = max(1, len(words(text)))
    density = sum(hits.values()) / total_words * 1000.0
    score = _clamp(1.0 - density / 14.0)
    return Check("NON_GENERIC_HABITS", score, {"marker_hits": hits, "per_1000_words": round(density, 3)})


def overexplanation_check(case: WritingCase) -> Check:
    low = case.text.lower()
    marker_hits = {m: low.count(m) for m in OVEREXPLAIN_MARKERS if m in low}
    explicit_hits = [x for x in case.forbidden_exposition if x.lower() in low]
    penalty = min(1.0, 0.10 * sum(marker_hits.values()) + 0.25 * len(explicit_hits))
    return Check("RESTRAINT", 1.0 - penalty, {
        "generic_exposition_hits": marker_hits,
        "forbidden_exposition_hits": explicit_hits,
    })


def repetition_check(text: str, n: int = 4) -> Check:
    toks = words(text)
    grams = [tuple(toks[i:i+n]) for i in range(max(0, len(toks) - n + 1))]
    counts = Counter(grams)
    repeated = {" ".join(g): c for g, c in counts.items() if c >= 2}
    repeats = sum(c - 1 for c in counts.values() if c >= 2)
    denom = max(1, len(grams))
    ratio = repeats / denom
    score = _clamp(1.0 - ratio * 8.0)
    return Check("PHRASE_REPETITION", score, {
        "repeat_ratio": round(ratio, 4),
        "top_repeated_ngrams": dict(sorted(repeated.items(), key=lambda x: -x[1])[:10]),
    })


def memory_check(case: WritingCase) -> Check:
    low = case.text.lower()
    required = list(case.required_memory_tokens) + list(case.expected_callback_tokens)
    missing = [x for x in required if x.lower() not in low]
    if not required:
        return Check("MEMORY_CALLBACK", 1.0, {"required": 0})
    score = 1.0 - len(missing) / len(required)
    return Check("MEMORY_CALLBACK", score, {"missing": missing, "required": required})


def ambiguity_check(case: WritingCase) -> Check:
    """Check that explicitly preserved ambiguities were not flattened away.

    This cannot judge ambiguity artistically; it only catches accidental loss of
    named unresolved terms in a benchmark case.
    """
    if not case.preserve_ambiguity_terms:
        return Check("AMBIGUITY_PRESERVATION", 1.0, {"tracked": 0})
    low = case.text.lower()
    retained = [x for x in case.preserve_ambiguity_terms if x.lower() in low]
    score = len(retained) / len(case.preserve_ambiguity_terms)
    return Check("AMBIGUITY_PRESERVATION", score, {
        "retained": retained,
        "tracked": list(case.preserve_ambiguity_terms),
    })


def voice_check(text: str, profile: VoiceProfile | None) -> Check:
    if profile is None:
        return Check("VOICE_PROFILE", 1.0, {"profile": None})
    low = text.lower()
    preferred_hits = [x for x in profile.preferred_terms if x.lower() in low]
    avoided_hits = [x for x in profile.avoided_terms if x.lower() in low]
    sents = sentences(text)
    mean_len = statistics.mean([len(words(s)) for s in sents]) if sents else 0.0

    score = 1.0
    if profile.preferred_terms:
        score *= 0.65 + 0.35 * (len(preferred_hits) / len(profile.preferred_terms))
    score -= min(0.6, 0.12 * len(avoided_hits))
    if profile.max_mean_sentence_words is not None and mean_len > profile.max_mean_sentence_words:
        score -= min(0.4, (mean_len - profile.max_mean_sentence_words) / 30.0)
    if profile.min_mean_sentence_words is not None and mean_len < profile.min_mean_sentence_words:
        score -= min(0.4, (profile.min_mean_sentence_words - mean_len) / 30.0)

    return Check("VOICE_PROFILE", _clamp(score), {
        "preferred_hits": preferred_hits,
        "avoided_hits": avoided_hits,
        "mean_sentence_words": round(mean_len, 2),
    })


def evaluate(case: WritingCase, profile: VoiceProfile | None = None) -> Report:
    checks = [
        rhythm_check(case.text),
        generic_habit_check(case.text),
        overexplanation_check(case),
        repetition_check(case.text),
        memory_check(case),
        ambiguity_check(case),
        voice_check(case.text, profile),
    ]
    # Equal weights intentionally keep the benchmark legible. Later versions may
    # use genre-specific profiles instead of one universal scalar.
    total = statistics.mean(x.score for x in checks)
    notes: list[str] = []
    if any(x.name == "NON_GENERIC_HABITS" and x.score < 0.7 for x in checks):
        notes.append("Too many generic connective/explanatory habits; rewrite by scene logic, not synonym substitution.")
    if any(x.name == "RESTRAINT" and x.score < 0.7 for x in checks):
        notes.append("The text may be explaining what the scene should demonstrate.")
    if any(x.name == "RHYTHM_VARIATION" and x.score < 0.55 for x in checks):
        notes.append("Rhythm is unusually uniform or chaotic; vary intentionally rather than randomly.")
    return Report(case.case_id, checks, total, notes)


TEST_BATTERY = (
    "T01_SAME_EVENT_THREE_CHARACTERS: same event, three incompatible causal histories; voices and choices must diverge.",
    "T02_CHARACTER_REFUSES_PLOT: planned plot demands A; character logic chooses B; rewrite plot without breaking world invariants.",
    "T03_LONG_CALLBACK: plant a harmless detail, delay payoff, preserve its causal route without overt reminders.",
    "T04_CONTROLLED_FORGETTING: allow a minor memory error while preserving the deep causal spine.",
    "T05_UNRESOLVED_CONTRADICTION: two explanations remain live; do not force premature closure.",
    "T06_BAD_ENDING_REGRESSION: start from an ending, regress necessary causes, then replay forward and see whether ending still emerges.",
    "T07_AUTHOR_BLINDNESS: remove author-only knowledge and verify a local character cannot infer unavailable facts.",
    "T08_FALSE_FORESHADOW: seed a plausible but non-canonical interpretation without lying about observed facts.",
    "T09_STYLE_PRESSURE: rewrite under speed/length constraints without collapsing into generic connective phrases.",
    "T10_DISCUSSION_HOOK: create a detail with at least two causally defensible interpretations, neither dependent on a continuity error.",
    "T11_WORLD_RULE_ATTACK: adversarially try to break one world rule; either survive or document the smallest repair.",
    "T12_REBIRTH_VARIANT: alter one childhood event and replay the same adult choice; measure whether personality changed plausibly.",
)


if __name__ == "__main__":
    sample = WritingCase(
        case_id="DEMO",
        text="Cô nhìn chiếc chìa khóa rất lâu. Ngoài cửa, mưa đã tạnh. Cô bỏ nó lại trên bàn rồi đi bằng cầu thang bộ. Không ai hỏi vì sao.",
        preserve_ambiguity_terms=("chìa khóa",),
    )
    print(json.dumps(evaluate(sample).to_dict(), ensure_ascii=False, indent=2))
    print("\n".join(TEST_BATTERY))
