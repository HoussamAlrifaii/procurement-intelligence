"""Helpers for running the project's .sql files with DuckDB."""
from pathlib import Path


def sql_string(value):
    """Format a value as a SQL string literal.

    Paths use forward slashes (DuckDB accepts them on Windows too), and single
    quotes are doubled so a folder name such as "O'Brien" cannot break the query.
    """
    if isinstance(value, Path):
        value = value.as_posix()
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def sql_list(values):
    """Format Python values as a comma-separated SQL list, e.g. 2019, 2020."""
    return ", ".join(str(value) for value in values)


def read_sql(path, **parameters):
    """Read a .sql file and fill its {placeholders}.

    Placeholders are filled only with values created by the pipeline itself
    (file paths, table names, years), never with external input.
    """
    template = Path(path).read_text()
    return template.format(**parameters)


def run_sql_file(connection, path, **parameters):
    """Run a .sql file on a DuckDB connection and return the relation, if any."""
    return connection.sql(read_sql(path, **parameters))
