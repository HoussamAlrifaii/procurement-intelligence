"""Write a data profile: which fields exist, how complete they are, what they contain.

The report (reports/data_profile.md) is the evidence used to decide which fields
later phases can rely on. It contains aggregate statistics only. Most frequent
values are listed only for low-variety code columns, never for free text such
as names or addresses.
"""
from datetime import date

from procurement import config
from procurement.download import read_manifest
from procurement.sql_runner import run_sql_file, sql_string

LOW_VARIETY_LIMIT = 30   # columns with at most this many distinct values get a top-values list
TOP_VALUES_SHOWN = 5


def quoted(column_name):
    """Quote a column name for SQL, so names like "year" are always safe."""
    return '"' + column_name.replace('"', '""') + '"'


def list_columns(connection, table_name):
    rows = connection.sql(f"DESCRIBE {table_name}").fetchall()
    return [row[0] for row in rows]


def profile_column(connection, table_name, column_name):
    relation = run_sql_file(
        connection,
        config.PROFILE_SQL_DIR / "column_profile.sql",
        table_name=table_name,
        column=quoted(column_name),
        column_label=sql_string(column_name),
    )
    _, total_rows, filled_share, distinct_values = relation.fetchone()
    profile = {
        "column": column_name,
        "total_rows": total_rows,
        "filled_share": filled_share or 0.0,
        "distinct_values": distinct_values,
        "top_values": "",
    }
    if 0 < distinct_values <= LOW_VARIETY_LIMIT:
        profile["top_values"] = describe_top_values(connection, table_name, column_name, total_rows)
    return profile


def describe_top_values(connection, table_name, column_name, total_rows):
    relation = run_sql_file(
        connection,
        config.PROFILE_SQL_DIR / "top_values.sql",
        table_name=table_name,
        column=quoted(column_name),
        limit=TOP_VALUES_SHOWN,
    )
    parts = []
    for value, row_count in relation.fetchall():
        label = "(blank)" if value is None or value.strip() == "" else value
        parts.append(f"{label} {row_count / total_rows:.0%}")
    return ", ".join(parts)


def profile_table(connection, table_name):
    return [profile_column(connection, table_name, column) for column in list_columns(connection, table_name)]


def format_table_section(table_name, profiles):
    total_rows = profiles[0]["total_rows"] if profiles else 0
    lines = [
        f"## `{table_name}`",
        "",
        f"{total_rows:,} rows, {len(profiles)} columns.",
        "",
        "| Column | Filled | Distinct values | Most frequent values |",
        "|---|---:|---:|---|",
    ]
    for profile in profiles:
        top_values = profile["top_values"].replace("|", "/")
        lines.append(
            f"| `{profile['column']}` | {profile['filled_share']:.1%} "
            f"| {profile['distinct_values']:,} | {top_values} |"
        )
    lines.append("")
    return lines


def format_sources_section(manifest):
    lines = [
        "## Source files",
        "",
        "| File | Size (MB) | Downloaded (UTC) | SHA-256 (first 12) |",
        "|---|---:|---|---|",
    ]
    for file_name, details in sorted(manifest.items()):
        lines.append(
            f"| `{file_name}` | {details['bytes'] / 1e6:,.1f} "
            f"| {details['downloaded_at_utc']} | `{details['sha256'][:12]}` |"
        )
    lines.append("")
    return lines


def write_profile_report(connection, table_names, output_path=None):
    output_path = output_path or config.PROFILE_REPORT_PATH
    lines = [
        "# Raw data profile",
        "",
        f"Generated {date.today().isoformat()} by `python -m procurement.pipeline`. "
        "\"Filled\" means neither missing nor blank. All raw columns are stored as text.",
        "",
    ]
    manifest = read_manifest()
    if manifest:
        lines.extend(format_sources_section(manifest))
    for table_name in table_names:
        lines.extend(format_table_section(table_name, profile_table(connection, table_name)))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    return output_path
