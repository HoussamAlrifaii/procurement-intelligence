"""Monthly refresh: one command from source files to red-flag report and app bundle.

Steps, each logged with its duration:
  1. pipeline        download -> load -> quality checks -> clean layer -> star schema
  2. features        single-bid and price feature tables
  3. models          retrain both models (only with --retrain)
  4. red flags       data/red_flags/red_flags.md
  5. app bundle      data/app/procurement_app_bundle.zip, ready to publish as a new release

If a step fails, for example a critical quality rule, the refresh stops: later
steps keep their previous outputs, and the exit code is 1 so a scheduler can
report the failure. Logs are written to logs/refresh_<date>.log.

Usage:
    python -m procurement.refresh                  # monthly run, with downloads
    python -m procurement.refresh --skip-download  # reuse the files in data/raw
    python -m procurement.refresh --retrain        # also retrain the two models
"""
import argparse
import logging
import sys
import time
from datetime import datetime

import duckdb

from procurement import app_bundle, config, pipeline, price_train, red_flags, train
from procurement.features import build_feature_table
from procurement.price_features import build_price_feature_table

log = logging.getLogger("refresh")


def run_pipeline(arguments):
    pipeline_arguments = ["--skip-download"] if arguments.skip_download else []
    pipeline.main(pipeline_arguments)


def build_features(arguments):
    with duckdb.connect(str(config.DATABASE_PATH), read_only=True) as connection:
        single_bid_rows = build_feature_table(connection)
        price_rows = build_price_feature_table(connection)
    log.info("feature tables: %s single-bid rows, %s price rows", f"{single_bid_rows:,}", f"{price_rows:,}")


def retrain_models(arguments):
    if not arguments.retrain:
        log.info("models kept (use --retrain to retrain them)")
        return
    train.main()
    price_train.main()


def write_red_flags(arguments):
    red_flags.main()


def build_app_bundle(arguments):
    app_bundle.main()


STEPS = [
    ("pipeline", run_pipeline),
    ("features", build_features),
    ("models", retrain_models),
    ("red flags", write_red_flags),
    ("app bundle", build_app_bundle),
]


def setup_logging(log_path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handlers = [logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler(sys.stdout)]
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers,
                        force=True)


def run_steps(arguments, steps=STEPS):
    """Run the steps in order; stop at the first failure. Returns 0 on success, 1 on failure."""
    started = time.perf_counter()
    for name, step in steps:
        log.info("start: %s", name)
        step_started = time.perf_counter()
        try:
            step(arguments)
        except SystemExit as stop:          # the pipeline exits with code 1 on a failed quality rule
            if stop.code not in (0, None):
                log.error("failed: %s (exit code %s); later steps were not run", name, stop.code)
                return 1
        except Exception:
            log.exception("failed: %s; later steps were not run", name)
            return 1
        log.info("done: %s in %.0f s", name, time.perf_counter() - step_started)
    log.info("refresh finished in %.0f min", (time.perf_counter() - started) / 60)
    return 0


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(description="Refresh data, red-flag report and app bundle.")
    parser.add_argument("--skip-download", action="store_true", help="reuse the files already in data/raw")
    parser.add_argument("--retrain", action="store_true", help="also retrain the single-bid and price models")
    return parser.parse_args(argv)


def main(argv=None):
    arguments = parse_arguments(argv)
    log_path = config.LOGS_DIR / f"refresh_{datetime.now():%Y-%m-%d_%H%M}.log"
    setup_logging(log_path)
    log.info("refresh started; log: %s", log_path.relative_to(config.PROJECT_ROOT))
    sys.exit(run_steps(arguments))


if __name__ == "__main__":
    main()
