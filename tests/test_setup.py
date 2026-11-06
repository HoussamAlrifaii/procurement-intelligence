"""Tests for the Phase 0 setup.

📖 READ ONLY: pytest runs every function whose name starts with `test_`.
A test passes if no `assert` fails.
"""
from procurement import config
from procurement.check_setup import check_duckdb_sql, check_python_version


def test_python_version_is_supported():
    passed, _ = check_python_version()
    assert passed


def test_project_paths_are_inside_the_project():
    # 🎯 INTERVIEW FOCUS: guards against a config mistake that would make the
    # pipeline write data outside the repository.
    for folder in config.REQUIRED_FOLDERS:
        assert config.PROJECT_ROOT in folder.parents


def test_duckdb_can_query_pandas():
    passed, _ = check_duckdb_sql()
    assert passed
