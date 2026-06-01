import pytest
import json
from pathlib import Path

from app.graph.workflow import (
    cleanup_explanation_text,
    enforce_demo_material_verdict,
    evaluate_special_case_rule,
    extract_retry_after_seconds,
    finalize_critique_node,
    get_rule_verification_rules,
    contradiction_detection_node,
    normalize_critique_score,
    rule_verification_node,
)


TARGETED_BATTERY_RULE_IDS = {
    "licoo2_layered_cathode_baseline",
    "licoo2_delithiation_thermal_instability",
    "lifepo4_olivine_safety_baseline",
    "lifepo4_energy_density_tradeoff",
    "nmc_layered_high_energy_benefit",
    "nmc_transition_metal_tradeoff",
}

RULES_PATH = Path(__file__).resolve().parents[1] / "rules" / "extracted_rules.json"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_cobalt_baseline_matches_cobalt_material() -> None:
    rule = {
        "id": "cobalt_scarcity_penalty",
        "name": "Cobalt Scarcity Penalty",
        "description": "Cobalt dependence should be flagged.",
        "severity": "warning",
    }
    candidate = {"elements": ["Li", "Co", "O"]}

    handled, matched = evaluate_special_case_rule(rule, candidate)

    assert handled is True
    assert matched is not None
    assert matched["rule_id"] == "cobalt_scarcity_penalty"
    assert matched["outcome"] == "concern"


def test_cobalt_baseline_skips_non_cobalt_material() -> None:
    rule = {
        "id": "cobalt_scarcity_penalty",
        "name": "Cobalt Scarcity Penalty",
        "description": "Cobalt dependence should be flagged.",
        "severity": "warning",
    }
    candidate = {"elements": ["Li", "Fe", "P", "O"]}

    handled, matched = evaluate_special_case_rule(rule, candidate)

    assert handled is True
    assert matched is None


def test_high_ionic_conductivity_skips_lifepo4() -> None:
    rule = {
        "id": "high_ionic_conductivity",
        "name": "High Ionic Conductivity Benefit",
        "description": "Lithium transport benefit rule.",
        "severity": "success",
    }
    candidate = {"elements": ["Li", "Fe", "P", "O"], "reduced_formula": "LiFePO4"}

    handled, matched = evaluate_special_case_rule(rule, candidate)

    assert handled is True
    assert matched is None


def test_high_ionic_conductivity_matches_layered_oxide() -> None:
    rule = {
        "id": "high_ionic_conductivity",
        "name": "High Ionic Conductivity Benefit",
        "description": "Lithium transport benefit rule.",
        "severity": "success",
    }
    candidate = {"elements": ["Li", "Co", "O"], "reduced_formula": "LiCoO2"}

    handled, matched = evaluate_special_case_rule(rule, candidate)

    assert handled is True
    assert matched is not None
    assert matched["outcome"] == "benefit"


def test_extract_retry_after_seconds_from_groq_message() -> None:
    message = (
        "Error code: 429 - {'error': {'message': 'Rate limit reached for model "
        "`llama-3.1-8b-instant`. Please try again in 340ms.', "
        "'type': 'tokens', 'code': 'rate_limit_exceeded'}}"
    )

    retry_after = extract_retry_after_seconds(message)

    assert retry_after == pytest.approx(0.34)


def test_cleanup_explanation_text_removes_meta_preamble() -> None:
    text = "Here's a concise 2-3 sentence explanation: LiCoO2 is commercially proven but has cobalt and safety concerns."

    cleaned = cleanup_explanation_text(text)

    assert cleaned == "LiCoO2 is commercially proven but has cobalt and safety concerns."


@pytest.mark.parametrize(
    ("candidate", "verdict", "expected"),
    [
        ({"formula": "LiCoO2", "normalized_formula": "LiCoO2", "reduced_formula": "LiCoO2"}, "infeasible", "feasible_with_concerns"),
        ({"formula": "LiFePO4", "normalized_formula": "LiFePO4", "reduced_formula": "LiFePO4"}, "feasible_with_concerns", "feasible"),
        (
            {"formula": "Li(Ni,Mn,Co)O2", "normalized_formula": "LiNiMnCoO2", "reduced_formula": "LiMnCoNiO2"},
            "infeasible",
            "feasible_with_concerns",
        ),
    ],
)
def test_enforce_demo_material_verdict(candidate: dict, verdict: str, expected: str) -> None:
    assert enforce_demo_material_verdict(candidate, verdict) == expected


@pytest.mark.parametrize(
    ("score", "verdict", "expected"),
    [
        (1.2, "feasible", 1.2),
        (4.2, "feasible", 3.0),
        (2.4, "feasible_with_concerns", 3.0),
        (3.6, "feasible_with_concerns", 3.6),
        (6.3, "feasible_with_concerns", 4.0),
        (5.5, "infeasible", 8.0),
        (9.4, "infeasible", 9.4),
        (12, "infeasible", 10.0),
    ],
)
def test_normalize_critique_score_respects_verdict_ranges(score, verdict, expected) -> None:
    assert normalize_critique_score(score, verdict) == expected


@pytest.mark.anyio
async def test_finalize_critique_does_not_backfill_baseline_rules() -> None:
    emitted_events: list[tuple[str, dict]] = []

    async def emit_event(event: str, data: dict) -> None:
        emitted_events.append((event, data))

    state = {
        "run_id": "unit-test",
        "material_formula": "LiFePO4",
        "rules_loaded": [
            {
                "id": "cobalt_scarcity_penalty",
                "name": "Cobalt Scarcity Penalty",
                "description": "Cobalt dependence should be flagged.",
                "citations": [],
            },
            {
                "id": "thermal_runaway_guardrail",
                "name": "Thermal Runaway Guardrail",
                "description": "Thermal instability should be flagged.",
                "citations": [],
            },
        ],
        "matched_rules": [],
        "violations": [],
        "contradictions": [],
        "critique_payload": {
            "verdict": "feasible",
            "score": 7.5,
            "flags": [],
            "suggestions": [],
            "explanation": "Unit test explanation.",
        },
        "explanation_stream": "Unit test explanation.",
        "emit_event": emit_event,
    }

    result = await finalize_critique_node(state)

    assert result["critique_card"].trace.rules_matched == []
    assert result["critique_card"].trace.citations == []


@pytest.mark.anyio
async def test_finalize_critique_preserves_backend_score_payload() -> None:
    emitted_events: list[tuple[str, dict]] = []

    async def emit_event(event: str, data: dict) -> None:
        emitted_events.append((event, data))

    state = {
        "run_id": "unit-test",
        "material_formula": "LiCoO2",
        "rules_loaded": [],
        "matched_rules": [],
        "violations": [],
        "contradictions": [],
        "critique_payload": {
            "verdict": "feasible",
            "score": 2.7,
            "flags": [],
            "suggestions": [],
            "explanation": "Unit test explanation.",
        },
        "explanation_stream": "Unit test explanation.",
        "emit_event": emit_event,
    }

    result = await finalize_critique_node(state)

    assert result["critique_card"].score == 2.7


@pytest.mark.anyio
async def test_rule_verification_batches_non_local_rules(monkeypatch) -> None:
    call_count = 0
    emitted_events: list[tuple[str, dict]] = []

    async def emit_event(event: str, data: dict) -> None:
        emitted_events.append((event, data))

    async def fake_groq_call_with_retry(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        assert kwargs["step"] == "rule_verification"
        assert "Rules:" in messages[1]["content"]
        return """
        {
          "matched_rules": [
            {
              "rule_id": "llm_rule",
              "outcome": "benefit",
              "reasoning": "Material-specific relevance is supported."
            }
          ],
          "violations": [],
          "confidence": "high",
          "notes": "batched"
        }
        """

    monkeypatch.setattr("app.graph.workflow.groq_call_with_retry", fake_groq_call_with_retry)

    state = {
        "run_id": "unit-test",
        "candidate": {
            "formula": "LiCoO2",
            "normalized_formula": "LiCoO2",
            "elements": ["Li", "Co", "O"],
            "reduced_formula": "LiCoO2",
            "oxidation_state_guesses": [],
        },
        "rules_loaded": [
            {
                "id": "cobalt_scarcity_penalty",
                "name": "Cobalt Scarcity Penalty",
                "description": "Cobalt dependence should be flagged.",
                "severity": "warning",
            },
            {
                "id": "llm_rule",
                "name": "LLM Rule",
                "description": "Synthetic batched rule.",
                "severity": "success",
                "domain": "battery cathode unit test",
                "threshold_value": None,
                "threshold_unit": None,
            },
        ],
        "emit_event": emit_event,
    }

    result = await rule_verification_node(state)

    assert call_count == 1
    assert [rule["rule_id"] for rule in result["matched_rules"]] == [
        "cobalt_scarcity_penalty",
        "llm_rule",
    ]
    assert [rule["rule_id"] for rule in result["violations"]] == ["cobalt_scarcity_penalty"]


def test_get_rule_verification_rules_filters_irrelevant_demo_cathode_rules() -> None:
    candidate = {
        "formula": "LiCoO2",
        "normalized_formula": "LiCoO2",
        "reduced_formula": "LiCoO2",
    }
    rules = [
        {
            "id": "licoo2_layered_cathode_baseline",
            "name": "LiCoO2 baseline",
            "material_scope": ["LiCoO2"],
            "domain": "layered oxide commercial cathodes",
        },
        {
            "id": "irrelevant_memristor_rule",
            "name": "K-ion memristor rule",
            "domain": "materials versatility",
        },
        {
            "id": "irrelevant_raman_rule",
            "name": "Raman rule",
            "domain": "Raman scattering",
        },
        {
            "id": "battery_rule",
            "name": "Battery rule",
            "domain": "battery cathode unit test",
        },
    ]

    filtered_rules = get_rule_verification_rules(candidate, rules)

    assert [rule["id"] for rule in filtered_rules] == [
        "licoo2_layered_cathode_baseline",
        "battery_rule",
    ]


@pytest.mark.anyio
async def test_contradiction_detection_batches_once(monkeypatch) -> None:
    call_count = 0
    emitted_events: list[tuple[str, dict]] = []

    async def emit_event(event: str, data: dict) -> None:
        emitted_events.append((event, data))

    async def fake_groq_call_with_retry(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        assert kwargs["step"] == "contradiction_detection"
        assert "Concern-level rule matches:" in messages[1]["content"]
        return """
        {
          "contradictions": [
            {
              "rule_a": "rule_a",
              "rule_b": "rule_b",
              "type": "potential_conflict",
              "resolution": "Review with expert judgement.",
              "llm_reasoning": "The tradeoff is real."
            }
          ],
          "notes": "batched"
        }
        """

    monkeypatch.setattr("app.graph.workflow.groq_call_with_retry", fake_groq_call_with_retry)

    state = {
        "run_id": "unit-test",
        "violations": [
            {
                "rule_id": "rule_a",
                "rule_name": "Rule A",
                "outcome": "concern",
                "severity": "warning",
                "reasoning": "Concern A",
            },
            {
                "rule_id": "rule_b",
                "rule_name": "Rule B",
                "outcome": "concern",
                "severity": "warning",
                "reasoning": "Concern B",
            },
            {
                "rule_id": "rule_c",
                "rule_name": "Rule C",
                "outcome": "concern",
                "severity": "warning",
                "reasoning": "Concern C",
            },
        ],
        "emit_event": emit_event,
    }

    result = await contradiction_detection_node(state)

    assert call_count == 1
    assert result["contradictions"] == [
        {
            "rule_a": "rule_a",
            "rule_b": "rule_b",
            "type": "potential_conflict",
            "resolution": "Review with expert judgement.",
            "llm_reasoning": "The tradeoff is real.",
        }
    ]


def load_targeted_battery_rules() -> list[dict]:
    with RULES_PATH.open("r", encoding="utf-8") as handle:
        rules = json.load(handle)
    return [rule for rule in rules if rule["id"] in TARGETED_BATTERY_RULE_IDS]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("formula", "normalized_formula", "reduced_formula", "expected_rule_ids"),
    [
        (
            "LiCoO2",
            "LiCoO2",
            "LiCoO2",
            {"licoo2_layered_cathode_baseline", "licoo2_delithiation_thermal_instability"},
        ),
        (
            "LiFePO4",
            "LiFePO4",
            "LiFePO4",
            {"lifepo4_olivine_safety_baseline", "lifepo4_energy_density_tradeoff"},
        ),
        (
            "Li(Ni,Mn,Co)O2",
            "LiNiMnCoO2",
            "LiMnCoNiO2",
            {"nmc_layered_high_energy_benefit", "nmc_transition_metal_tradeoff"},
        ),
    ],
)
async def test_targeted_battery_rules_match_with_citations(
    formula: str,
    normalized_formula: str,
    reduced_formula: str,
    expected_rule_ids: set[str],
) -> None:
    emitted_events: list[tuple[str, dict]] = []

    async def emit_event(event: str, data: dict) -> None:
        emitted_events.append((event, data))

    state = {
        "run_id": "unit-test",
        "candidate": {
            "formula": formula,
            "normalized_formula": normalized_formula,
            "reduced_formula": reduced_formula,
            "elements": ["Li", "O", "Co"] if "CoO2" in reduced_formula and "Fe" not in reduced_formula and "Mn" not in reduced_formula else [],
            "oxidation_state_guesses": [],
        },
        "rules_loaded": load_targeted_battery_rules(),
        "emit_event": emit_event,
    }

    if formula == "LiFePO4":
        state["candidate"]["elements"] = ["Li", "Fe", "P", "O"]
    elif formula == "Li(Ni,Mn,Co)O2":
        state["candidate"]["elements"] = ["Li", "Ni", "Mn", "Co", "O"]

    result = await rule_verification_node(state)
    matched_rule_ids = {rule["rule_id"] for rule in result["matched_rules"]}

    assert expected_rule_ids.issubset(matched_rule_ids)
    assert len(expected_rule_ids) >= 2

    rule_lookup = {rule["id"]: rule for rule in state["rules_loaded"]}
    for rule_id in expected_rule_ids:
        citations = rule_lookup[rule_id].get("citations", [])
        assert citations
        for citation in citations:
            assert citation.get("paper_title")
            assert citation.get("authors")
            assert citation.get("year")
            assert citation.get("url")
            assert citation.get("doi") or citation.get("arxiv_id")


@pytest.mark.anyio
async def test_finalize_critique_includes_targeted_rule_citations() -> None:
    emitted_events: list[tuple[str, dict]] = []

    async def emit_event(event: str, data: dict) -> None:
        emitted_events.append((event, data))

    rules_loaded = load_targeted_battery_rules()
    matched_rules = [
        {
            "rule_id": "licoo2_layered_cathode_baseline",
            "rule_name": "LiCoO2 Commercial Layered Cathode Baseline",
            "description": "LiCoO2 baseline benefit.",
            "severity": "success",
            "outcome": "benefit",
            "reasoning": "Unit test benefit match.",
        },
        {
            "rule_id": "licoo2_delithiation_thermal_instability",
            "rule_name": "LiCoO2 Delithiation Thermal Instability Concern",
            "description": "LiCoO2 thermal concern.",
            "severity": "warning",
            "outcome": "concern",
            "reasoning": "Unit test concern match.",
        },
    ]

    state = {
        "run_id": "unit-test",
        "material_formula": "LiCoO2",
        "rules_loaded": rules_loaded,
        "matched_rules": matched_rules,
        "violations": [matched_rules[1]],
        "contradictions": [],
        "critique_payload": {
            "verdict": "feasible_with_concerns",
            "score": 3.4,
            "flags": [],
            "suggestions": [],
            "explanation": "Unit test explanation.",
        },
        "explanation_stream": "Unit test explanation.",
        "emit_event": emit_event,
    }

    result = await finalize_critique_node(state)
    citations = result["critique_card"].trace.citations

    assert citations
    assert {citation.rule_id for citation in citations} == {
        "licoo2_layered_cathode_baseline",
        "licoo2_delithiation_thermal_instability",
    }
    assert all(citation.paper_title for citation in citations)
    assert all(citation.url for citation in citations)
