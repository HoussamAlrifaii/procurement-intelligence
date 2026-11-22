"""Evaluate the assistant on hand-written cases (evaluation/assistant_cases.json).

For each case it checks, from the tool calls and the answer:
  tool    - the assistant called at least one of the expected tools
  sector  - at least one CPV group it used falls in an acceptable CPV division
  country - it searched the expected country (or no country when none was given)
  grounded - every figure in the answer appears in the question, a tool call or a tool
             result, written the same way (no invented, rounded or derived numbers)

Every answer is saved to reports/assistant_answers.json for review.

Usage (needs LLM_API_KEY in .env; about 20 LLM calls):
    python -m procurement.evaluate_assistant
"""
import json
import re

import duckdb

from procurement import config
from procurement.assistant import ask

# Figures such as 1,240 / 156,488 / 41.9 / 30.9% (years and single digits are ignored).
FIGURE = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d{2,}")
YEARS = {str(year) for year in range(2015, 2031)}


def figures(text):
    return {match for match in FIGURE.findall(text) if match not in YEARS}


def ungrounded_figures(answer, tool_calls, question=""):
    """Figures in the answer found neither in the question nor in any tool call (arguments or result).

    Arguments count as sources because the assistant may mention the codes and
    value range it searched with.
    """
    sources = question + json.dumps(tool_calls, ensure_ascii=False, default=str)
    return sorted(figure for figure in figures(answer) if figure not in sources)


def used_values(tool_calls, argument):
    values = set()
    for call in tool_calls:
        value = call["arguments"].get(argument)
        if isinstance(value, list):
            values.update(str(item) for item in value)
        elif value is not None:
            values.add(str(value))
    return values


def score_case(case, result):
    calls = result["tool_calls"]
    groups = used_values(calls, "cpv_groups") | used_values(calls, "cpv_group")
    countries = {value.upper() for value in used_values(calls, "country")}
    expected_country = {case["country"]} if case["country"] else set()
    missing = ungrounded_figures(result["answer"], calls, case["question"])
    return {
        "id": case["id"],
        "tool": any(call["name"] in case["expected_tools"] for call in calls),
        "sector": any(group[:2] in case["acceptable_cpv_divisions"] for group in groups),
        "country": countries == expected_country,
        "grounded": not missing,
        "cpv_groups": sorted(groups),
        "ungrounded": missing,
        "tool_calls": len(calls),
    }


def write_report(scores):
    checks = ["tool", "sector", "country", "grounded"]
    lines = ["# Assistant evaluation", "",
             f"{len(scores)} hand-written cases from `evaluation/assistant_cases.json`; "
             "full answers in `assistant_answers.json`.", "",
             "| Check | Passed |", "|---|---|"]
    for check in checks:
        passed = sum(score[check] for score in scores)
        lines.append(f"| {check} | {passed}/{len(scores)} ({passed / len(scores):.0%}) |")
    lines += ["", "| Case | Tool | Sector | Country | Grounded | CPV groups used | Figures not found in tools |",
              "|---|---|---|---|---|---|---|"]
    for score in scores:
        marks = ["yes" if score[check] else "**no**" for check in checks]
        lines.append(f"| {score['id']} | " + " | ".join(marks) +
                     f" | {', '.join(score['cpv_groups'])} | {', '.join(score['ungrounded'])} |")
    config.ASSISTANT_EVALUATION_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    from procurement.llm import LLM

    cases = json.loads(config.ASSISTANT_CASES_PATH.read_text(encoding="utf-8"))
    llm = LLM()
    scores = []
    answers = []
    with duckdb.connect(str(config.DATABASE_PATH), read_only=True) as connection:
        for case in cases:
            try:
                result = ask(case["question"], llm, connection)
            except Exception as problem:   # e.g. the provider rejects a malformed tool call
                result = {"answer": f"ERROR: {problem}", "tool_calls": []}
            scores.append(score_case(case, result))
            answers.append({"id": case["id"], "question": case["question"], **result})
            score = scores[-1]
            print(f"{case['id']:<22} tool={score['tool']!s:<5} sector={score['sector']!s:<5} "
                  f"country={score['country']!s:<5} grounded={score['grounded']!s:<5} {score['ungrounded']}")
    write_report(scores)
    config.ASSISTANT_ANSWERS_PATH.write_text(json.dumps(answers, indent=2, ensure_ascii=False, default=str),
                                             encoding="utf-8")
    print(f"\nSaved {config.ASSISTANT_EVALUATION_PATH.relative_to(config.PROJECT_ROOT)} and "
          f"{config.ASSISTANT_ANSWERS_PATH.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
