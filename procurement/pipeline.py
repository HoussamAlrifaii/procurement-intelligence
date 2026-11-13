"""Run the data pipeline: download -> Parquet -> raw views -> quality checks -> profile -> clean layer -> star schema.

Usage (from the project root):
    python -m procurement.pipeline                     # default years 2019-2022
    python -m procurement.pipeline --years 2021 2022   # a smaller, faster run
    python -m procurement.pipeline --skip-download     # reuse files already in data/raw

Every step can be re-run safely: files already downloaded or converted are reused.
Exits with code 1 if a critical quality rule fails.
"""
import argparse
import sys
import time

import duckdb

from procurement import config
from procurement.clean import build_clean_layer
from procurement.marts import build_marts
from procurement.download import download_sources, ted_zip_path, world_bank_csv_path
from procurement.load import load_ted, load_world_bank
from procurement.profile import write_profile_report
from procurement.quality import print_results, run_quality_checks


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(description="Build the raw procurement database.")
    parser.add_argument("--years", type=int, nargs="+", default=config.DEFAULT_YEARS,
                        help="TED publication years to include (default: 2019-2022)")
    parser.add_argument("--skip-download", action="store_true",
                        help="use files already in data/raw instead of downloading")
    return parser.parse_args(argv)


def local_source_paths(years):
    """Paths of files expected from a previous download, for --skip-download."""
    paths = {
        "ted_zips": [ted_zip_path(year) for year in years],
        "world_bank_csv": world_bank_csv_path(),
    }
    missing = [path for path in paths["ted_zips"] + [paths["world_bank_csv"]] if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing downloaded files: {missing}. Run without --skip-download.")
    return paths


def run_step(title, function, *args):
    """Run one pipeline step and print how long it took."""
    print(f"\n{title}")
    started = time.perf_counter()
    result = function(*args)
    print(f"  done in {time.perf_counter() - started:,.0f} s")
    return result


def main(argv=None):
    arguments = parse_arguments(argv)
    years = sorted(set(arguments.years))
    for folder in config.REQUIRED_FOLDERS:
        folder.mkdir(parents=True, exist_ok=True)

    if arguments.skip_download:
        sources = local_source_paths(years)
    else:
        sources = run_step(f"1/6 Downloading sources for {years}", download_sources, years)

    with duckdb.connect(str(config.DATABASE_PATH)) as connection:
        ted_rows = run_step("2/6 Loading TED", load_ted, connection,
                            sources["ted_zips"], config.PROCESSED_DATA_DIR)
        world_bank_rows = run_step("    Loading World Bank", load_world_bank, connection,
                                   sources["world_bank_csv"], config.PROCESSED_DATA_DIR, years)
        print(f"  {config.TED_TABLE}: {ted_rows:,} rows")
        print(f"  {config.WORLD_BANK_TABLE}: {world_bank_rows:,} rows")

        results = run_step("3/6 Running quality checks", run_quality_checks, connection, years)
        print_results(results)

        report = run_step("4/6 Writing data profile", write_profile_report, connection,
                          [config.TED_TABLE, config.WORLD_BANK_TABLE])
        print(f"  {report.relative_to(config.PROJECT_ROOT)}")

        # Stop before cleaning if the raw data cannot be trusted.
        blocking = [result.name for result in results if result.blocks_pipeline]
        if blocking:
            print(f"\nPipeline FAILED: critical quality rules failed: {blocking}")
            sys.exit(1)

        run_step("5/6 Building clean layer", build_clean_layer, connection)
        run_step("6/6 Building star schema", build_marts, connection)

    print("\nPipeline finished. Database:", config.DATABASE_PATH.relative_to(config.PROJECT_ROOT))


if __name__ == "__main__":
    main()
