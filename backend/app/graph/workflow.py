import asyncio
import json
import logging
import os
import re
from itertools import count
from pathlib import Path
from typing import Any

import groq
from groq import Groq
from langgraph.graph import END, START, StateGraph
from pymatgen.core import Composition
from pymatgen.core.periodic_table import DummySpecies

from app.graph.state import ScreeningState
from app.schemas.critique import CritiqueCard


MODEL_NAME = "llama-3.1-8b-instant"
RULES_PATH = Path(__file__).resolve().parents[2] / "rules" / "extracted_rules.json"
ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
RATE_LIMIT_BUFFER_SECONDS = 0.35
SYSTEM_PROMPT_RULE = (
    "You are a materials chemistry expert. Review a candidate material against a batch of screening rules. "
    "Return strict JSON with keys matched_rules, violations, confidence, and notes. "
    "matched_rules must be a list of objects with keys rule_id, outcome ('concern' or 'benefit'), and reasoning. "
    "violations must be a list of rule_id strings for concern-level matches only. "
    "Only include rules when you have material-specific justification. "
    "Do not invent rules, do not repeat the same rule twice, and do not include not_applicable rules."
)
SYSTEM_PROMPT_CONTRADICTION = (
    "You are a battery materials expert. Review the batch of concern-level rule matches and identify only real contradictions or tradeoff conflicts between them. "
    "Return strict JSON with keys contradictions and notes. "
    "contradictions must be a list of objects with keys rule_a, rule_b, type, resolution, and llm_reasoning. "
    "If none exist, return an empty contradictions list."
)
SYSTEM_PROMPT_CRITIQUE = (
    "You are a battery materials expert. Given this candidate, rule set, violations, and contradictions, "
    "generate strict JSON with keys verdict, score, flags, suggestions, explanation. "
    "Verdict must be one of feasible, feasible_with_concerns, infeasible. "
    "Score means screening risk / feasibility risk where lower is more viable. "
    "Use this rubric: 0-1 = strong known battery material with low feasibility risk; "
    "2-3 = feasible with minor tradeoffs; "
    "4-5 = feasible with meaningful concerns; "
    "6-7 = uncertain or weak candidate; "
    "8-10 = likely infeasible or high-risk. "
    "Keep verdict and score consistent: feasible should usually score 0-3, "
    "feasible_with_concerns should usually score 3-5, infeasible should usually score 8-10. "
    "Flags must be a list of objects with icon, text, severity. "
    "Suggestions must be a list of objects with text and rationale."
)
SYSTEM_PROMPT_EXPLANATION = (
    "You are a battery materials expert. Write a concise 2-3 sentence explanation for the critique. "
    "Focus on the most important benefits, violations, and contradictions."
)
logger = logging.getLogger(__name__)
groq_call_counter = count(1)


class InvalidMaterialFormulaError(ValueError):
    def __init__(self, message: str = "Invalid material formula. Please check the formula and try again."):
        super().__init__(message)


class ModelRateLimitError(RuntimeError):
    def __init__(self, retry_after_seconds: float | None = None):
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Model rate limit reached. Please retry shortly.")


def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key and ENV_PATH.exists():
        for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw_line.lstrip("\ufeff").strip()
            if line.startswith("GROQ_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not api_key:
        raise groq.GroqError(
            "The api_key client option must be set either by passing api_key to the client or by setting the GROQ_API_KEY environment variable"
        )

    return Groq(api_key=api_key, max_retries=0)


async def emit_step_event(state: ScreeningState, step: str, label: str) -> None:
    emit_event = state["emit_event"]
    await emit_event("step.started", {"step": step, "status": "started"})
    await emit_step_status(state, step, label)


async def emit_step_status(state: ScreeningState, step: str, label: str) -> None:
    await state["emit_event"](
        "step.updated",
        {
            "step": step,
            "label": label,
            "status": "in_progress",
        },
    )


def parse_json_block(text: str) -> dict[str, Any]:
    payload = text.strip()
    if payload.startswith("```"):
        payload = payload.strip("`")
        payload = payload.replace("json", "", 1).strip()

    start = payload.find("{")
    end = payload.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"Unable to parse JSON from model response: {text}")

    return json.loads(payload[start : end + 1])


def estimate_token_count_from_text(text: str) -> int:
    # Lightweight heuristic for diagnostics only; avoids changing request behavior.
    normalized = text.strip()
    if not normalized:
        return 0
    return max(1, round(len(normalized) / 4))


def estimate_prompt_tokens(messages: list[dict[str, str]]) -> int:
    total_chars = 0
    for message in messages:
        total_chars += len(message.get("role", ""))
        total_chars += len(message.get("content", ""))
    return max(1, round(total_chars / 4)) if total_chars else 0


def log_groq_diagnostics(
    *,
    call_id: int,
    stage: str,
    run_id: str | None,
    stream: bool,
    attempt: int,
    prompt_token_estimate: int,
    response_token_estimate: int | None,
    response_token_source: str,
) -> None:
    logger.info(
        "GROQ_CALL id=%s stage=%s run_id=%s model=%s stream=%s attempt=%s prompt_tokens_est=%s response_tokens_est=%s response_token_source=%s",
        call_id,
        stage,
        run_id or "unknown",
        MODEL_NAME,
        stream,
        attempt,
        prompt_token_estimate,
        response_token_estimate if response_token_estimate is not None else "unknown",
        response_token_source,
    )


def format_candidate_for_prompt(candidate: dict[str, Any]) -> str:
    return json.dumps(candidate, indent=2, default=str)


def compact_candidate_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "formula": candidate["formula"],
        "normalized_formula": candidate.get("normalized_formula"),
        "reduced_formula": candidate.get("reduced_formula"),
        "elements": candidate.get("elements", []),
        "oxidation_state_guesses": candidate.get("oxidation_state_guesses", [])[:2],
    }


def build_matched_rule_entry(
    rule: dict[str, Any],
    *,
    outcome: str,
    reasoning: str,
) -> dict[str, Any]:
    return {
        "rule_id": rule["id"],
        "rule_name": rule["name"],
        "description": rule["description"],
        "severity": rule.get("severity", "warning"),
        "outcome": outcome,
        "reasoning": reasoning.strip(),
    }


def normalize_material_formula(formula: str) -> str:
    normalized = formula.strip()
    grouped_elements_pattern = re.compile(r"\(([A-Z][a-z]?(?:,[A-Z][a-z]?)+)\)")
    if grouped_elements_pattern.search(normalized):
        normalized = grouped_elements_pattern.sub(lambda match: match.group(1).replace(",", ""), normalized)
    return normalized


def compact_rule_summary(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": rule["rule_id"],
        "rule_name": rule["rule_name"],
        "outcome": rule["outcome"],
        "severity": rule.get("severity", "warning"),
        "reasoning": rule["reasoning"],
    }


def compact_rule_prompt_entry(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": rule["id"],
        "name": rule.get("name"),
        "description": rule.get("description"),
        "domain": rule.get("domain"),
        "threshold_value": rule.get("threshold_value"),
        "threshold_unit": rule.get("threshold_unit"),
        "severity": rule.get("severity"),
    }


def normalize_rule_outcome(value: Any) -> str | None:
    outcome = str(value or "").strip().lower()
    if outcome in {"concern", "benefit"}:
        return outcome
    return None


def parse_batched_rule_verification(
    parsed: dict[str, Any],
    *,
    rule_lookup: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    matched_rules: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    seen_rule_ids: set[str] = set()
    violation_ids = {
        str(rule_id).strip()
        for rule_id in parsed.get("violations", [])
        if str(rule_id).strip() in rule_lookup
    }

    for raw_match in parsed.get("matched_rules", []):
        if not isinstance(raw_match, dict):
            continue

        rule_id = str(raw_match.get("rule_id", "")).strip()
        if not rule_id or rule_id in seen_rule_ids or rule_id not in rule_lookup:
            continue

        outcome = normalize_rule_outcome(raw_match.get("outcome"))
        if outcome is None and rule_id in violation_ids:
            outcome = "concern"
        if outcome is None:
            continue

        reasoning = str(raw_match.get("reasoning", "")).strip() or "Material-specific applicability identified."
        matched_rule = build_matched_rule_entry(
            rule_lookup[rule_id],
            outcome=outcome,
            reasoning=reasoning,
        )
        matched_rules.append(matched_rule)
        seen_rule_ids.add(rule_id)
        if outcome == "concern" or rule_id in violation_ids:
            violations.append(matched_rule)

    return matched_rules, violations


def parse_batched_contradictions(
    parsed: dict[str, Any],
    *,
    valid_rule_ids: set[str],
) -> list[dict[str, Any]]:
    contradictions: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for raw_entry in parsed.get("contradictions", []):
        if not isinstance(raw_entry, dict):
            continue

        rule_a = str(raw_entry.get("rule_a", "")).strip()
        rule_b = str(raw_entry.get("rule_b", "")).strip()
        if not rule_a or not rule_b or rule_a == rule_b:
            continue
        if rule_a not in valid_rule_ids or rule_b not in valid_rule_ids:
            continue

        pair = tuple(sorted((rule_a, rule_b)))
        if pair in seen_pairs:
            continue

        contradictions.append(
            {
                "rule_a": rule_a,
                "rule_b": rule_b,
                "type": str(raw_entry.get("type", "potential_conflict")).strip() or "potential_conflict",
                "resolution": str(raw_entry.get("resolution", "Review with expert judgement.")).strip()
                or "Review with expert judgement.",
                "llm_reasoning": str(raw_entry.get("llm_reasoning", "")).strip()
                or "Potential tradeoff conflict identified by batched contradiction review.",
            }
        )
        seen_pairs.add(pair)

    return contradictions


def normalize_critique_score(score: Any, verdict: Any) -> float:
    try:
        numeric_score = float(score)
    except (TypeError, ValueError):
        numeric_score = 0.0

    normalized_verdict = str(verdict or "").strip().lower().replace(" ", "_")
    clamped_score = max(0.0, min(10.0, numeric_score))

    verdict_ranges = {
        "feasible": (0.0, 3.0),
        "feasible_with_concerns": (3.0, 5.0),
        "infeasible": (8.0, 10.0),
    }
    lower_bound, upper_bound = verdict_ranges.get(normalized_verdict, (0.0, 10.0))
    bounded_score = min(max(clamped_score, lower_bound), upper_bound)
    return round(bounded_score, 1)


def extract_retry_after_seconds(error_message: str) -> float | None:
    patterns = [
        re.compile(r"try again in (?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ms|milliseconds|s|sec|secs|seconds?)", re.IGNORECASE),
        re.compile(r"retry after (?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ms|milliseconds|s|sec|secs|seconds?)", re.IGNORECASE),
    ]

    for pattern in patterns:
        match = pattern.search(error_message)
        if not match:
            continue

        value = float(match.group("value"))
        unit = match.group("unit").lower()
        if unit.startswith("ms"):
            return value / 1000
        return value

    return None


def is_rate_limit_error(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)
    message = str(error).lower()
    return status_code == 429 or "rate_limit_exceeded" in message or "rate limit reached" in message


def validate_material_formula(formula: str) -> str:
    normalized = normalize_material_formula(formula)
    if not normalized:
        raise InvalidMaterialFormulaError()

    if re.search(r"(^|[A-Za-z\)\]])0\d+", normalized):
        raise InvalidMaterialFormulaError()

    try:
        composition = Composition(normalized)
    except Exception as error:
        raise InvalidMaterialFormulaError() from error

    if composition.num_atoms <= 0 or not composition.elements:
        raise InvalidMaterialFormulaError()

    if any(isinstance(element, DummySpecies) for element in composition.elements):
        raise InvalidMaterialFormulaError()

    return normalized


def evaluate_special_case_rule(
    rule: dict[str, Any],
    candidate: dict[str, Any],
) -> tuple[bool, dict[str, Any] | None]:
    elements = set(candidate.get("elements", []))
    if rule["id"] == "cobalt_scarcity_penalty":
        if "Co" in elements:
            return True, build_matched_rule_entry(
                rule,
                outcome="concern",
                reasoning="Candidate contains cobalt, so cobalt scarcity and scale-up cost risk are directly relevant.",
            )
        return True, None

    if rule["id"] == "thermal_runaway_guardrail":
        return True, None

    if rule["id"] == "high_ionic_conductivity":
        reduced_formula = str(candidate.get("reduced_formula", ""))
        layered_oxide_elements = {"Li", "O"} & elements and {"Co", "Ni", "Mn"} & elements
        phosphate_like = "P" in elements or "F" in elements
        if reduced_formula in {"LiCoO2", "LiNiMnCoO2"} or (layered_oxide_elements and not phosphate_like):
            return True, build_matched_rule_entry(
                rule,
                outcome="benefit",
                reasoning="Candidate is a layered lithium transition-metal oxide, so lithium-ion transport relevance is material-specific rather than assumed by default.",
            )
        return True, None

    return False, None


def _run_non_streaming_completion(messages: list[dict[str, str]]) -> str:
    client = get_groq_client()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.2,
        stream=False,
    )
    return response.choices[0].message.content or ""


def _run_streaming_completion(messages: list[dict[str, str]]) -> list[str]:
    client = get_groq_client()
    deltas: list[str] = []
    stream = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.2,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            deltas.append(delta)
    return deltas


async def groq_call_with_retry(
    messages: list[dict[str, str]],
    *,
    stream: bool = False,
    max_retries: int = 3,
    state: ScreeningState | None = None,
    step: str | None = None,
    step_label: str | None = None,
) -> str | list[str]:
    last_error: Exception | None = None
    call_id = next(groq_call_counter)
    prompt_token_estimate = estimate_prompt_tokens(messages)
    run_id = state.get("run_id") if state is not None else None

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0 and state is not None and step and step_label:
                await emit_step_status(state, step, step_label)

            if stream:
                result = await asyncio.to_thread(_run_streaming_completion, messages)
                response_token_estimate = estimate_token_count_from_text("".join(result))
                log_groq_diagnostics(
                    call_id=call_id,
                    stage=step or "unknown",
                    run_id=run_id,
                    stream=True,
                    attempt=attempt,
                    prompt_token_estimate=prompt_token_estimate,
                    response_token_estimate=response_token_estimate,
                    response_token_source="estimated_from_stream",
                )
                return result

            result = await asyncio.to_thread(_run_non_streaming_completion, messages)
            response_token_estimate = estimate_token_count_from_text(result)
            log_groq_diagnostics(
                call_id=call_id,
                stage=step or "unknown",
                run_id=run_id,
                stream=False,
                attempt=attempt,
                prompt_token_estimate=prompt_token_estimate,
                response_token_estimate=response_token_estimate,
                response_token_source="estimated_from_text",
            )
            return result
        except (groq.APIError, groq.APITimeoutError, groq.APIConnectionError) as error:
            last_error = error
            if attempt >= max_retries:
                if is_rate_limit_error(error):
                    raise ModelRateLimitError(extract_retry_after_seconds(str(error))) from error
                raise

            if is_rate_limit_error(error):
                retry_after = extract_retry_after_seconds(str(error)) or 1.0
                wait_seconds = retry_after + RATE_LIMIT_BUFFER_SECONDS
                if state is not None and step:
                    await emit_step_status(
                        state,
                        step,
                        f"Rate limit hit. Retrying in {wait_seconds:.1f}s...",
                    )
                await asyncio.sleep(wait_seconds)
                continue

            await asyncio.sleep(1)

    if last_error is not None:
        raise last_error

    raise RuntimeError("Groq call failed without raising a concrete exception.")


async def load_domain_rules_node(state: ScreeningState) -> dict[str, Any]:
    await emit_step_event(state, "load_domain_rules", "Loading domain rules...")

    with RULES_PATH.open("r", encoding="utf-8") as rules_file:
        rules = json.load(rules_file)

    return {"rules_loaded": rules}


async def candidate_analysis_node(state: ScreeningState) -> dict[str, Any]:
    await emit_step_event(
        state,
        "candidate_analysis",
        f"Screening {state['material_formula']}...",
    )

    normalized_formula = validate_material_formula(state["material_formula"])
    composition = Composition(normalized_formula)
    oxidation_guesses = composition.oxi_state_guesses()
    candidate = {
        "formula": state["material_formula"],
        "normalized_formula": normalized_formula,
        "reduced_formula": composition.reduced_formula,
        "elements": [str(element) for element in composition.elements],
        "num_atoms": composition.num_atoms,
        "fractional_composition": composition.fractional_composition.as_dict(),
        "oxidation_state_guesses": oxidation_guesses[:3],
    }

    return {"candidate": candidate}


async def rule_verification_node(state: ScreeningState) -> dict[str, Any]:
    await emit_step_event(state, "rule_verification", "Verifying candidate against domain rules...")

    candidate_summary = compact_candidate_summary(state["candidate"])
    candidate_text = format_candidate_for_prompt(candidate_summary)
    matched_rules: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    llm_rules: list[dict[str, Any]] = []

    for rule in state["rules_loaded"]:
        handled_locally, local_match = evaluate_special_case_rule(rule, state["candidate"])
        if handled_locally:
            if local_match is not None:
                matched_rules.append(local_match)
                if local_match["outcome"] == "concern":
                    violations.append(local_match)
            continue

        llm_rules.append(rule)

    if not llm_rules:
        return {"matched_rules": matched_rules, "violations": violations}

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_RULE},
        {
            "role": "user",
            "content": (
                f"Candidate:\n{candidate_text}\n\n"
                f"Rules:\n{json.dumps([compact_rule_prompt_entry(rule) for rule in llm_rules], indent=2)}\n\n"
                "Return strict JSON only."
            ),
        },
    ]

    try:
        response_text = await groq_call_with_retry(
            messages,
            stream=False,
            max_retries=3,
            state=state,
            step="rule_verification",
            step_label="Verifying candidate against domain rules...",
        )
        parsed = parse_json_block(response_text)
        llm_matched_rules, llm_violations = parse_batched_rule_verification(
            parsed,
            rule_lookup={rule["id"]: rule for rule in llm_rules},
        )
        matched_rules.extend(llm_matched_rules)
        violations.extend(llm_violations)
    except ModelRateLimitError:
        raise
    except Exception:
        logger.exception("Batched rule verification failed", extra={"run_id": state.get("run_id")})

    return {"matched_rules": matched_rules, "violations": violations}


async def contradiction_detection_node(state: ScreeningState) -> dict[str, Any]:
    await emit_step_event(state, "contradiction_detection", "Checking contradiction reasoning...")

    if len(state["violations"]) < 2:
        return {"contradictions": []}

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_CONTRADICTION},
        {
            "role": "user",
            "content": (
                f"Concern-level rule matches:\n{json.dumps([compact_rule_summary(violation) for violation in state['violations']], indent=2)}\n\n"
                "Return strict JSON only."
            ),
        },
    ]

    try:
        response_text = await groq_call_with_retry(
            messages,
            stream=False,
            max_retries=3,
            state=state,
            step="contradiction_detection",
            step_label="Checking contradiction reasoning...",
        )
        parsed = parse_json_block(response_text)
        contradictions = parse_batched_contradictions(
            parsed,
            valid_rule_ids={violation["rule_id"] for violation in state["violations"]},
        )
        return {"contradictions": contradictions}
    except ModelRateLimitError:
        raise
    except Exception:
        logger.exception("Batched contradiction detection failed", extra={"run_id": state.get("run_id")})
        return {"contradictions": []}


async def critique_generation_node(state: ScreeningState) -> dict[str, Any]:
    await emit_step_event(state, "critique_generation", "Running critique...")

    candidate_text = format_candidate_for_prompt(compact_candidate_summary(state["candidate"]))
    matched_rule_summaries = [compact_rule_summary(rule) for rule in state["matched_rules"]]
    violation_summaries = [compact_rule_summary(rule) for rule in state["violations"]]
    matched_rule_text = json.dumps(matched_rule_summaries, indent=2)
    violation_text = json.dumps(violation_summaries, indent=2)
    contradiction_text = json.dumps(state["contradictions"], indent=2)

    critique_messages = [
        {"role": "system", "content": SYSTEM_PROMPT_CRITIQUE},
        {
            "role": "user",
            "content": (
                f"Candidate:\n{candidate_text}\n\n"
                f"Matched relevant rules:\n{matched_rule_text}\n\n"
                f"Violations:\n{violation_text}\n\n"
                f"Contradictions:\n{contradiction_text}\n\n"
                "Return strict JSON only."
            ),
        },
    ]
    critique_text = await groq_call_with_retry(
        critique_messages,
        stream=False,
        max_retries=3,
        state=state,
        step="critique_generation",
        step_label="Running critique...",
    )
    critique_payload = parse_json_block(critique_text)

    explanation_messages = [
        {"role": "system", "content": SYSTEM_PROMPT_EXPLANATION},
        {
            "role": "user",
            "content": (
                f"Candidate:\n{candidate_text}\n\n"
                f"Matched relevant rules:\n{matched_rule_text}\n\n"
                f"Violations:\n{violation_text}\n\n"
                f"Contradictions:\n{contradiction_text}\n\n"
                f"Verdict summary:\n{json.dumps(critique_payload, indent=2)}"
            ),
        },
    ]
    explanation_chunks = await groq_call_with_retry(
        explanation_messages,
        stream=True,
        max_retries=3,
        state=state,
        step="critique_generation",
        step_label="Running critique...",
    )

    explanation_stream = ""
    for chunk in explanation_chunks:
        explanation_stream += chunk
        await state["emit_event"]("text.delta", {"delta": chunk})

    critique_payload["explanation"] = explanation_stream.strip()
    critique_payload["score"] = normalize_critique_score(
        critique_payload.get("score"),
        critique_payload.get("verdict"),
    )
    return {
        "critique_payload": critique_payload,
        "explanation_stream": explanation_stream.strip(),
    }


async def finalize_critique_node(state: ScreeningState) -> dict[str, Any]:
    await emit_step_event(state, "finalize_critique", "Finalizing critique card...")

    payload = state["critique_payload"]
    rule_lookup = {rule["id"]: rule for rule in state["rules_loaded"]}
    matched_rule_ids = [rule["rule_id"] for rule in state.get("matched_rules", [])]
    citation_rule_ids = list(matched_rule_ids)
    citations: list[dict[str, Any]] = []

    def append_rule_citations(rule_id: str) -> None:
        rule = rule_lookup.get(rule_id)
        if rule is None:
            return
        for citation in rule.get("citations", []):
            citations.append(
                {
                    "rule_id": rule["id"],
                    "rule_name": rule.get("name", rule["id"]),
                    "arxiv_id": citation.get("arxiv_id", ""),
                    "paper_title": citation.get("paper_title", ""),
                    "authors": citation.get("authors", ""),
                    "year": citation.get("year"),
                    "url": citation.get("url", ""),
                    "evidence_from_paper": rule.get("evidence_from_paper") or rule.get("description", ""),
                }
            )

    for rule_id in citation_rule_ids:
        append_rule_citations(rule_id)

    display_rule_ids = list(dict.fromkeys(matched_rule_ids))
    critique_card = CritiqueCard(
        id=f"crit_{state['run_id']}",
        material_formula=state["material_formula"],
        verdict=str(payload.get("verdict", "feasible_with_concerns")).replace("_", " "),
        score=float(payload.get("score", 0)),
        domain_rules_passed=max(len(state["rules_loaded"]) - len(state["violations"]), 0),
        domain_rules_total=len(state["rules_loaded"]),
        flags=payload.get("flags", []),
        suggestions=payload.get("suggestions", []),
        explanation=state.get("explanation_stream", payload.get("explanation", "")),
        trace={
            "rules_matched": [
                rule_lookup[rule_id].get("name", rule_id)
                for rule_id in display_rule_ids
                if rule_id in rule_lookup
            ],
            "contradictions": state["contradictions"],
            "citations": citations,
        },
    )

    await state["emit_event"]("critique.ready", critique_card.model_dump(mode="json"))
    return {"critique_card": critique_card}


def build_screening_graph():
    graph = StateGraph(ScreeningState)
    graph.add_node("load_domain_rules", load_domain_rules_node)
    graph.add_node("candidate_analysis", candidate_analysis_node)
    graph.add_node("rule_verification", rule_verification_node)
    graph.add_node("contradiction_detection", contradiction_detection_node)
    graph.add_node("critique_generation", critique_generation_node)
    graph.add_node("finalize_critique", finalize_critique_node)

    graph.add_edge(START, "load_domain_rules")
    graph.add_edge("load_domain_rules", "candidate_analysis")
    graph.add_edge("candidate_analysis", "rule_verification")
    graph.add_edge("rule_verification", "contradiction_detection")
    graph.add_edge("contradiction_detection", "critique_generation")
    graph.add_edge("critique_generation", "finalize_critique")
    graph.add_edge("finalize_critique", END)

    return graph.compile()


async def run_screening_workflow(
    *,
    chat_id: str,
    run_id: str,
    material_formula: str,
    emit_event,
) -> ScreeningState:
    graph = build_screening_graph()
    initial_state: ScreeningState = {
        "chat_id": chat_id,
        "run_id": run_id,
        "material_formula": material_formula,
        "rules_loaded": [],
        "matched_rules": [],
        "violations": [],
        "contradictions": [],
        "explanation_stream": "",
        "emit_event": emit_event,
    }

    return await graph.ainvoke(initial_state)
