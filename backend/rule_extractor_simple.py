import json
import os
import re
from pathlib import Path
from typing import Any

import groq
from groq import Groq


PAPERS_PATH = Path(__file__).resolve().parent / "data" / "arxiv_papers.json"
RULES_PATH = Path(__file__).resolve().parent / "rules" / "extracted_rules.json"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
MODEL_CANDIDATES = [
    "llama-3.2-90b-vision-preview",
    "llama-3.1-8b-instant",
]
MAX_NEW_RULES = 18
MAX_PAPERS_TO_PROCESS = 30

SYSTEM_PROMPT = """
You are a battery materials scientist extracting screening rules from paper abstracts.
Extract 1 or 2 quantitative or semi-quantitative battery material screening rules from the abstract.
Return strict JSON with this shape:
{
  "rules": [
    {
      "rule_text": "short rule sentence",
      "threshold": {"value": 0.001, "unit": "S/cm"},
      "domain": "ionic conductivity",
      "evidence_from_paper": "short supporting quote or paraphrase"
    }
  ]
}
Rules should be reusable for screening candidate materials.
If no meaningful rule is present, return {"rules": []}.
"""


def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key and ENV_PATH.exists():
        for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw_line.lstrip("\ufeff").strip()
            if line.startswith("GROQ_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not api_key:
        raise groq.GroqError("GROQ_API_KEY is not set.")
    return Groq(api_key=api_key, max_retries=0)


def parse_json_block(text: str) -> dict[str, Any]:
    payload = text.strip()
    if payload.startswith("```"):
        payload = payload.strip("`")
        payload = payload.replace("json", "", 1).strip()

    start = payload.find("{")
    end = payload.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"Could not parse JSON payload: {text}")
    return json.loads(payload[start : end + 1])


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized[:64] or "rule"


def load_existing_rules() -> list[dict[str, Any]]:
    with RULES_PATH.open("r", encoding="utf-8") as rules_file:
        rules = json.load(rules_file)

    for rule in rules:
        rule.setdefault("threshold_value", None)
        rule.setdefault("threshold_unit", None)
        rule.setdefault("citations", [])
        rule.setdefault("domain", "general screening")
        rule.setdefault("evidence_from_paper", "")

    return rules


def extract_rules_from_abstract(client: Groq, paper: dict[str, Any]) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for model_name in MODEL_CANDIDATES:
        try:
            response = client.chat.completions.create(
                model=model_name,
                temperature=0.1,
                stream=False,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Title: {paper['title']}\n"
                            f"Authors: {', '.join(paper['authors'])}\n"
                            f"Abstract: {paper['abstract']}\n"
                        ),
                    },
                ],
            )
            content = response.choices[0].message.content or '{"rules": []}'
            parsed = parse_json_block(content)
            rules = parsed.get("rules", [])
            return rules if isinstance(rules, list) else []
        except Exception as error:
            last_error = error
            if "model_decommissioned" in str(error):
                continue
            raise

    if last_error is not None:
        raise last_error

    return []


def build_rule_entry(rule_data: dict[str, Any], paper: dict[str, Any]) -> dict[str, Any]:
    threshold = rule_data.get("threshold") or {}
    rule_text = str(rule_data.get("rule_text", "")).strip()
    domain = str(rule_data.get("domain", "battery materials")).strip() or "battery materials"
    return {
        "id": slugify(rule_text or paper["title"]),
        "name": rule_text[:80] if rule_text else paper["title"][:80],
        "description": rule_text,
        "threshold_value": threshold.get("value"),
        "threshold_unit": threshold.get("unit"),
        "domain": domain,
        "evidence_from_paper": str(rule_data.get("evidence_from_paper", "")).strip(),
        "citations": [
            {
                "arxiv_id": paper["arxiv_id"],
                "paper_title": paper["title"],
                "authors": ", ".join(paper["authors"]),
                "year": paper["year"],
                "url": paper["url"],
            }
        ],
        "severity": "warning" if "risk" in domain.lower() else "success",
    }


def merge_rules(existing_rules: list[dict[str, Any]], extracted_rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {rule["id"]: rule for rule in existing_rules}

    for extracted in extracted_rules:
        existing = merged.get(extracted["id"])
        if existing is None:
            merged[extracted["id"]] = extracted
            continue

        existing_citations = existing.setdefault("citations", [])
        known_urls = {citation["url"] for citation in existing_citations if citation.get("url")}
        for citation in extracted.get("citations", []):
            if citation.get("url") not in known_urls:
                existing_citations.append(citation)

        if not existing.get("description"):
            existing["description"] = extracted.get("description", "")
        if existing.get("threshold_value") is None:
            existing["threshold_value"] = extracted.get("threshold_value")
        if not existing.get("threshold_unit"):
            existing["threshold_unit"] = extracted.get("threshold_unit")
        if not existing.get("domain"):
            existing["domain"] = extracted.get("domain")
        if not existing.get("evidence_from_paper"):
            existing["evidence_from_paper"] = extracted.get("evidence_from_paper", "")

    return list(merged.values())


def main() -> None:
    if not PAPERS_PATH.exists():
        raise FileNotFoundError(f"Missing paper data file: {PAPERS_PATH}")

    papers = json.loads(PAPERS_PATH.read_text(encoding="utf-8"))
    existing_rules = load_existing_rules()
    client = get_groq_client()

    extracted_rules: list[dict[str, Any]] = []
    for paper in papers[:MAX_PAPERS_TO_PROCESS]:
        try:
            rules = extract_rules_from_abstract(client, paper)
        except Exception as error:
            print(f"Skipping {paper['arxiv_id']}: {error}")
            continue

        for rule_data in rules:
            rule_text = str(rule_data.get("rule_text", "")).strip()
            if not rule_text:
                continue
            extracted_rules.append(build_rule_entry(rule_data, paper))
            if len(extracted_rules) >= MAX_NEW_RULES:
                break

        if len(extracted_rules) >= MAX_NEW_RULES:
            break

    merged_rules = merge_rules(existing_rules, extracted_rules)
    with RULES_PATH.open("w", encoding="utf-8") as rules_file:
        json.dump(merged_rules, rules_file, indent=2, ensure_ascii=False)

    print(f"Processed papers: {min(len(papers), MAX_PAPERS_TO_PROCESS)}")
    print(f"New extracted rules: {len(extracted_rules)}")
    print(f"Total rules after merge: {len(merged_rules)}")
    print(f"Saved merged rules to {RULES_PATH}")


if __name__ == "__main__":
    main()
