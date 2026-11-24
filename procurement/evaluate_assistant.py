"""Evaluate the assistant on hand-written cases (evaluation/assistant_cases.json).

For each case it checks, from the tool calls and the answer:
  tool    - the assistant called at least one of the expected tools
  sector  - at least one CPV group it used falls in an acceptable CPV division
  country - it searched the expected country (or no country when none was given)
  grounded - every figure in the answer appears in the question, a tool call or a tool
             result, written the same way (no invented, rounded or derived numbers)

Every answer is saved to reports/assistant_answers.json for review.

Two case sets:
  development  evaluation/assistant_cases.json         20 cases, used while improving the assistant
  holdout      evaluation/assistant_cases_holdout.json 12 cases, written before the last changes and
                                                      never used to adjust the assistant: the fair score

Usage:
    python -m procurement.evaluate_assistant                      # development set (LLM_API_KEY in .env)
    python -m procurement.evaluate_assistant --set holdout        # held-out set
    python -m procurement.evaluate_assistant --rescore            # score saved answers again, no LLM calls
"""
import argparse
import json
import re

import duckdb

from procurement import config
from procurement.assistant import ask

# Figures such as 1,240 / 156,488 / 41.9 / EUR 2.07 m / 12.7k. Numbers written right after
# "ISO" or "CPV" are names of standards and codes, not figures, and are skipped.
# Thousands may be separated by commas or spaces ("156,488" or "156 488").
FIGURE = re.compile(r"(?<![\w.])(?<!ISO )(?<!CPV )(\d{1,3}(?:[, ]\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s?(bn|[kKmM])?(?![\w])")
MULTIPLIERS = {None: 1, "k": 1e3, "K": 1e3, "m": 1e6, "M": 1e6, "bn": 1e9}
YEARS = set(range(2015, 2031))
TOLERANCE = 0.05   # a rounded figure ("about 16%" for 16.5%) counts if within 5% of a source value


def figures(text):
    """Numeric values written in a text, with k/m/bn suffixes applied (years and values below 10 ignored)."""
    # Models often use no-break spaces inside numbers ("118\u202f330"); treat them as plain spaces.
    text = text.replace("\u202f", " ").replace("\u00a0", " ")
    values = set()
    for number, suffix in FIGURE.findall(text):
        value = float(number.replace(",", "").replace(" ", "")) * MULTIPLIERS[suffix or None]
        if value >= 10 and not (not suffix and value in YEARS):
            values.add(value)
    return values


def ungrounded_figures(answer, tool_calls, question=""):
    """Figures in the answer that match no figure in the question or the tool calls (arguments or results).

    Arguments count as sources because the assistant may mention the codes and value range
    it searched with. Rounding is accepted ("EUR 2.07 m" for EUR 2,070,415); a figure with
    no source value within 5% was calculated or invented by the model.
    """
    sources = figures(question + json.dumps(tool_calls, ensure_ascii=False, default=str))
    missing = []
    for value in figures(answer):
        if not any(abs(value - source) <= TOLERANCE * source for source in sources):
            missing.append(f"{value:,.10g}")
    return sorted(missing)


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


CASE_SETS = {
    "development": config.ASSISTANT_CASES_PATH,
    "holdout": config.ASSISTANT_HOLDOUT_CASES_PATH,
}


def output_paths(case_set):
    """reports/assistant_evaluation.md for the development set, ..._holdout.md for the held-out set."""
    suffix = "" if case_set == "development" else f"_{case_set}"
    report = config.REPORTS_DIR / f"assistant_evaluation{suffix}.md"
    answers = config.REPORTS_DIR / f"assistant_answers{suffix}.json"
    return report, answers


def write_report(scores, report_path, case_file):
    checks = ["tool", "sector", "country", "grounded"]
    lines = ["# Assistant evaluation", "",
             f"{len(scores)} hand-written cases from `evaluation/{case_file.name}`; "
             "full answers in the matching `assistant_answers*.json`.", "",
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
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def rescore(cases, answers_path):
    """Score answers saved by an earlier run, e.g. after a change to the scoring rules."""
    saved = json.loads(answers_path.read_text(encoding="utf-8"))
    by_id = {answer["id"]: answer for answer in saved}
    return [score_case(case, by_id[case["id"]]) for case in cases]


def print_score(score):
    print(f"{score['id']:<22} tool={score['tool']!s:<5} sector={score['sector']!s:<5} "
          f"country={score['country']!s:<5} grounded={score['grounded']!s:<5} {score['ungrounded']}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate the assistant on the hand-written cases.")
    parser.add_argument("--set", choices=sorted(CASE_SETS), default="development", help="which cases to run")
    parser.add_argument("--rescore", action="store_true", help="score the saved answers without calling the LLM")
    arguments = parser.parse_args()
    case_file = CASE_SETS[arguments.set]
    report_path, answers_path = output_paths(arguments.set)
    cases = json.loads(case_file.read_text(encoding="utf-8"))

    if arguments.rescore:
        scores = rescore(cases, answers_path)
        for score in scores:
            print_score(score)
        write_report(scores, report_path, case_file)
        print(f"\nSaved {report_path.relative_to(config.PROJECT_ROOT)}")
        return

    from procurement.llm import LLM
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
            print_score(scores[-1])
    write_report(scores, report_path, case_file)
    answers_path.write_text(json.dumps(answers, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nSaved {report_path.relative_to(config.PROJECT_ROOT)} and {answers_path.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
