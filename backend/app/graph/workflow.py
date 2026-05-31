import asyncio
import json
import os
from itertools import combinations
from pathlib import Path
from typing import Any

import groq
from groq import Groq
from langgraph.graph import END, START, StateGraph
from pymatgen.core import Composition

from app.graph.state import ScreeningState
from app.schemas.critique import CritiqueCard


MODEL_NAME = "llama-3.1-8b-instant"
RULES_PATH = Path(__file__).resolve().parents[2] / "rules" / "extracted_rules.json"
ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
SYSTEM_PROMPT_RULE = (
    "You are a materials chemistry expert. Verify if this material violates this rule. "
    "Respond: YES (violated) or NO (compliant). Brief reasoning."
)
SYSTEM_PROMPT_CONTRADICTION = (
    "Do these two rules conflict? Answer YES or NO first, then give a concise explanation."
)
SYSTEM_PROMPT_CRITIQUE = (
    "You are a battery materials expert. Given this candidate, rule set, violations, and contradictions, "
    "generate strict JSON with keys verdict, score, flags, suggestions, explanation. "
    "Verdict must be one of feasible, feasible_with_concerns, infeasible. "
    "Flags must be a list of objects with icon, text, severity. "
    "Suggestions must be a list of objects with text and rationale."
)
SYSTEM_PROMPT_EXPLANATION = (
    "You are a battery materials expert. Write a concise 2-3 sentence explanation for the critique. "
    "Focus on the most important benefits, violations, and contradictions."
)


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
    await emit_event(
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


def format_candidate_for_prompt(candidate: dict[str, Any]) -> str:
    return json.dumps(candidate, indent=2, default=str)


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
    max_retries: int = 1,
) -> str | list[str]:
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            if stream:
                return await asyncio.to_thread(_run_streaming_completion, messages)
            return await asyncio.to_thread(_run_non_streaming_completion, messages)
        except (groq.APIError, groq.APITimeoutError, groq.APIConnectionError) as error:
            last_error = error
            if attempt >= max_retries:
                raise
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

    composition = Composition(state["material_formula"])
    oxidation_guesses = composition.oxi_state_guesses()
    candidate = {
        "formula": state["material_formula"],
        "reduced_formula": composition.reduced_formula,
        "elements": [str(element) for element in composition.elements],
        "num_atoms": composition.num_atoms,
        "fractional_composition": composition.fractional_composition.as_dict(),
        "oxidation_state_guesses": oxidation_guesses[:3],
    }

    return {"candidate": candidate}


async def rule_verification_node(state: ScreeningState) -> dict[str, Any]:
    await emit_step_event(state, "rule_verification", "Verifying candidate against domain rules...")

    candidate_text = format_candidate_for_prompt(state["candidate"])
    violations: list[dict[str, Any]] = []

    for rule in state["rules_loaded"]:
        compact_rule = {
            "id": rule["id"],
            "name": rule.get("name"),
            "description": rule.get("description"),
            "domain": rule.get("domain"),
            "threshold_value": rule.get("threshold_value"),
            "threshold_unit": rule.get("threshold_unit"),
            "severity": rule.get("severity"),
        }
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_RULE},
            {
                "role": "user",
                "content": (
                    f"Candidate:\n{candidate_text}\n\n"
                    f"Rule:\n{json.dumps(compact_rule, indent=2)}\n\n"
                    "Does the candidate violate the rule?"
                ),
            },
        ]

        response_text = await groq_call_with_retry(messages, stream=False, max_retries=1)
        normalized = response_text.strip().upper()
        reasoning = response_text.strip()
        is_violated = normalized.startswith("YES")

        if is_violated:
            violations.append(
                {
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "description": rule["description"],
                    "severity": rule.get("severity", "warning"),
                    "reasoning": reasoning,
                }
            )

    return {"violations": violations}


async def contradiction_detection_node(state: ScreeningState) -> dict[str, Any]:
    await emit_step_event(state, "contradiction_detection", "Checking contradiction reasoning...")

    contradictions: list[dict[str, Any]] = []
    for violation_a, violation_b in combinations(state["violations"], 2):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_CONTRADICTION},
            {
                "role": "user",
                "content": (
                    f"Violation A:\n{json.dumps(violation_a, indent=2)}\n\n"
                    f"Violation B:\n{json.dumps(violation_b, indent=2)}"
                ),
            },
        ]

        response_text = await groq_call_with_retry(messages, stream=False, max_retries=1)
        normalized = response_text.strip().upper()
        if normalized.startswith("YES"):
            contradictions.append(
                {
                    "rule_a": violation_a["rule_id"],
                    "rule_b": violation_b["rule_id"],
                    "type": "potential_conflict",
                    "resolution": "Review with expert judgement.",
                    "llm_reasoning": response_text.strip(),
                }
            )

    return {"contradictions": contradictions}


async def critique_generation_node(state: ScreeningState) -> dict[str, Any]:
    await emit_step_event(state, "critique_generation", "Running critique...")

    candidate_text = format_candidate_for_prompt(state["candidate"])
    violation_text = json.dumps(state["violations"], indent=2)
    contradiction_text = json.dumps(state["contradictions"], indent=2)

    critique_messages = [
        {"role": "system", "content": SYSTEM_PROMPT_CRITIQUE},
        {
            "role": "user",
            "content": (
                f"Candidate:\n{candidate_text}\n\n"
                f"Violations:\n{violation_text}\n\n"
                f"Contradictions:\n{contradiction_text}\n\n"
                "Return strict JSON only."
            ),
        },
    ]
    critique_text = await groq_call_with_retry(critique_messages, stream=False, max_retries=1)
    critique_payload = parse_json_block(critique_text)

    explanation_messages = [
        {"role": "system", "content": SYSTEM_PROMPT_EXPLANATION},
        {
            "role": "user",
            "content": (
                f"Candidate:\n{candidate_text}\n\n"
                f"Violations:\n{violation_text}\n\n"
                f"Contradictions:\n{contradiction_text}\n\n"
                f"Verdict summary:\n{json.dumps(critique_payload, indent=2)}"
            ),
        },
    ]
    explanation_chunks = await groq_call_with_retry(explanation_messages, stream=True, max_retries=1)

    explanation_stream = ""
    for chunk in explanation_chunks:
        explanation_stream += chunk
        await state["emit_event"]("text.delta", {"delta": chunk})

    critique_payload["explanation"] = explanation_stream.strip()
    return {
        "critique_payload": critique_payload,
        "explanation_stream": explanation_stream.strip(),
    }


async def finalize_critique_node(state: ScreeningState) -> dict[str, Any]:
    await emit_step_event(state, "finalize_critique", "Finalizing critique card...")

    payload = state["critique_payload"]
    rule_lookup = {rule["id"]: rule for rule in state["rules_loaded"]}
    matched_rule_ids = [violation["rule_id"] for violation in state["violations"]]
    if not matched_rule_ids:
        matched_rule_ids = [rule["id"] for rule in state["rules_loaded"][:3]]

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

    if not citations:
        citation_rule_ids = []
        for rule in state["rules_loaded"]:
            if not rule.get("citations"):
                continue
            citation_rule_ids.append(rule["id"])
            append_rule_citations(rule["id"])
            if len(citation_rule_ids) >= 3:
                break

    display_rule_ids = list(dict.fromkeys(matched_rule_ids + citation_rule_ids))
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
        "violations": [],
        "contradictions": [],
        "explanation_stream": "",
        "emit_event": emit_event,
    }

    return await graph.ainvoke(initial_state)
