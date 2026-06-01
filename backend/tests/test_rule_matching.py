import pytest

from app.graph.workflow import (
    evaluate_special_case_rule,
    extract_retry_after_seconds,
    finalize_critique_node,
    contradiction_detection_node,
    normalize_critique_score,
    rule_verification_node,
)


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


@pytest.mark.parametrize(
    ("score", "verdict", "expected"),
    [
        (1.2, "feasible", 1.2),
        (4.2, "feasible", 3.0),
        (2.4, "feasible_with_concerns", 3.0),
        (4.6, "feasible_with_concerns", 4.6),
        (6.3, "feasible_with_concerns", 5.0),
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
                "domain": "unit test",
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
