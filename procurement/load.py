"""Convert downloaded files to Parquet and expose them as DuckDB raw views.

Raw layer rule: values are stored exactly as published (as text). No rows are
cleaned or corrected here, so every cleaning decision in the next phase is
explicit and reviewable.
"""
import tempfile
import zipfile
from pathlib import Path

from procurement import config
from procurement.sql_runner import run_sql_file, sql_list, sql_string


def parquet_path_for(source_path, output_dir):
    return Path(output_dir) / (Path(source_path).stem + ".parquet")


def is_up_to_date(output_path, source_path):
    """True if the output exists and was written after its source file."""
    if not output_path.exists():
        return False
    return output_path.stat().st_mtime >= Path(source_path).stat().st_mtime


def extract_single_csv(zip_path, target_dir):
    """Extract the one CSV inside a TED zip archive and return its path."""
    with zipfile.ZipFile(zip_path) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"Expected one CSV in {zip_path}, found {csv_names}")
        extracted_path = archive.extract(csv_names[0], path=target_dir)
    return Path(extracted_path)


def ted_zip_to_parquet(connection, zip_path, output_dir):
    """Convert one TED yearly zip to Parquet; skip if already converted.

    The CSV (about 700 MB per year) is extracted to a temporary folder that is
    deleted right after conversion. Only the original zip and the much smaller
    Parquet file stay on disk.
    """
    parquet_path = parquet_path_for(zip_path, output_dir)
    if is_up_to_date(parquet_path, zip_path):
        return parquet_path

    with tempfile.TemporaryDirectory() as temp_dir:
        csv_path = extract_single_csv(zip_path, temp_dir)
        run_sql_file(
            connection,
            config.LOAD_SQL_DIR / "ted_csv_to_parquet.sql",
            csv_path=sql_string(csv_path),
            parquet_path=sql_string(parquet_path),
            source_file=sql_string(Path(zip_path).name),
        )
    return parquet_path


def world_bank_csv_to_parquet(connection, csv_path, output_dir):
    parquet_path = parquet_path_for(csv_path, output_dir)
    if is_up_to_date(parquet_path, csv_path):
        return parquet_path

    run_sql_file(
        connection,
        config.LOAD_SQL_DIR / "world_bank_csv_to_parquet.sql",
        csv_path=sql_string(csv_path),
        parquet_path=sql_string(parquet_path),
        source_file=sql_string(Path(csv_path).name),
    )
    return parquet_path


def load_ted(connection, zip_paths, output_dir):
    """Convert every TED year to Parquet, then create the raw TED view over them."""
    parquet_paths = []
    for zip_path in zip_paths:
        print(f"  converting {Path(zip_path).name}")
        parquet_paths.append(ted_zip_to_parquet(connection, zip_path, output_dir))

    path_list = "[" + sql_list(sql_string(path) for path in parquet_paths) + "]"
    run_sql_file(
        connection,
        config.LOAD_SQL_DIR / "create_raw_ted_awards.sql",
        table_name=config.TED_TABLE,
        parquet_paths=path_list,
    )
    return count_rows(connection, config.TED_TABLE)


def load_world_bank(connection, csv_path, output_dir, years):
    print(f"  converting {Path(csv_path).name}")
    parquet_path = world_bank_csv_to_parquet(connection, csv_path, output_dir)
    run_sql_file(
        connection,
        config.LOAD_SQL_DIR / "create_raw_world_bank_awards.sql",
        table_name=config.WORLD_BANK_TABLE,
        parquet_path=sql_string(parquet_path),
        year_list=sql_list(years),
    )
    return count_rows(connection, config.WORLD_BANK_TABLE)


def count_rows(connection, table_name):
    return connection.sql(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
