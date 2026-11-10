"""Run the data quality rules in sql/quality/.

Each rule is a .sql file that returns one number, `failing_rows`: how many rows
break the rule. A header comment sets its severity:

    critical  the pipeline stops if any row fails (the data cannot be trusted)
    warning   failures are reported for investigation in the cleaning phase
    info      counts reported for context only
"""
from dataclasses import dataclass
from pathlib import Path

import duckdb

from procurement import config
from procurement.sql_runner import read_sql, sql_list


@dataclass
class RuleResult:
    name: str
    severity: str
    description: str
    failing_rows: int
    error: str = ""

    @property
    def passed(self):
        # A rule that could not run (e.g. a missing column) counts as a failure.
        return self.failing_rows == 0 and not self.error

    @property
    def blocks_pipeline(self):
        return self.severity == "critical" and not self.passed


def read_header_value(sql_text, key):
    """Return the value of a `-- key: value` header line in a .sql file."""
    prefix = f"-- {key}:"
    for line in sql_text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    raise ValueError(f"Quality rule is missing its '{key}' header")


def run_rule(connection, rule_path, parameters):
    sql_text = read_sql(rule_path, **parameters)
    severity = read_header_value(sql_text, "severity")
    description = read_header_value(sql_text, "rule")
    try:
        failing_rows = connection.sql(sql_text).fetchone()[0]
        return RuleResult(Path(rule_path).stem, severity, description, failing_rows)
    except duckdb.Error as error:
        return RuleResult(Path(rule_path).stem, severity, description, -1, str(error))


def run_quality_checks(connection, years, rules_dir=None):
    """Run every rule and return a list of RuleResult."""
    rules_dir = Path(rules_dir or config.QUALITY_SQL_DIR)
    parameters = {
        "ted_table": config.TED_TABLE,
        "world_bank_table": config.WORLD_BANK_TABLE,
        "year_list": sql_list(years),
    }
    rule_paths = sorted(rules_dir.glob("*.sql"))
    return [run_rule(connection, rule_path, parameters) for rule_path in rule_paths]


def print_results(results):
    for result in results:
        if result.error:
            status = "ERROR"
        elif result.passed:
            status = "PASS"
        else:
            status = result.severity.upper()
        detail = result.error if result.error else f"{result.failing_rows:,} rows"
        print(f"  [{status:8s}] {result.name}: {detail}")
