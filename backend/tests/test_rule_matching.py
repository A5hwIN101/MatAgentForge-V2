import pytest

from app.graph.workflow import evaluate_special_case_rule, finalize_critique_node


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
