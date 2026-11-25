# Phase 8: Automation

One command refreshes the whole project, from source files to an auditor's
red-flag report and a new app bundle, and Windows Task Scheduler runs it every
month.

## 1. How to run

```bash
python -m procurement.refresh                    # full monthly run, downloads the sources
python -m procurement.refresh --skip-download    # reuse the files in data/raw
python -m procurement.refresh --retrain          # also retrain both models
python -m procurement.red_flags                  # only the red-flag report
```

Schedule it once (Windows, from the project folder):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\schedule_refresh.ps1
schtasks /Run /TN "TenderLens monthly refresh"            # test it now
schtasks /Delete /TN "TenderLens monthly refresh" /F      # remove it
```

| File | Role |
|---|---|
| `procurement/refresh.py` | Runs the steps in order, logs each one, stops on the first failure |
| `procurement/red_flags.py` | Builds the red-flag report from the star schema and both models |
| `scripts/schedule_refresh.ps1` | Registers the monthly task (1st of each month, 07:00) |
| `tests/test_refresh.py` | Step order, stop on failure, logging, report rules |

## 2. What a refresh does

```
1. pipeline    download → load → quality checks → clean layer → star schema
                 ✗ critical quality rule fails → stop (exit code 1)
2. features    single-bid and price feature tables
3. models      kept, or retrained with --retrain
4. red flags   data/red_flags/red_flags.md (+ snapshot for the next comparison)
5. app bundle  data/app/procurement_app_bundle.zip, ready to publish as a new release
```

Every step is logged with its duration to `logs/refresh_<date>_<time>.log` and
to the console. A failed step stops the refresh, later steps keep their previous
outputs, and the process exits with code 1, which Task Scheduler records as a
failed run. A full run with `--skip-download` took 4 minutes on the development
machine: pipeline 64 s, features 3 s, red flags 147 s, bundle 6 s.

## 3. The red-flag report

What an auditor receives after each refresh:

| Section | Rule |
|---|---|
| Buyers to review | At least 100 labelled competitive awards and a single-bid rate of 80%+, or 20+ points above the buyer's country (reuses the Phase 3 query `02_buyer_red_flags.sql`) |
| Riskiest tenders | Highest single-bid risk in the latest year from the Phase 5 model, one row per tender, with the three features that raised the risk most (SHAP) and the actual outcome |
| Unusual prices | Awards more than twice the high end of the calibrated 80% price range, one row per tender, ranked by how far above; awards far below the range are counted (often data-entry errors) |
| Changes | Buyers flagged now that were not flagged in the previous report |

On the 2019-2022 data the first report flagged 497 buyers and 7,946 tenders with
an award far above the expected range in 2022. The report names public bodies
next to risk indicators, so, like the Phase 3 analysis results, it is written
to `data/red_flags/` and not committed. Every flag is an indicator for review,
not evidence of wrongdoing.

## 4. A data-quality bug found by the report

The first report's top "unusual prices" were awards of EUR 1,000,000,000: values
entered as 999,999,999.99. The Phase 2 rule that flags placeholder values made
of 9s converted values to integers before checking, which rounds 999,999.99 up
to 1,000,000 and let 111 such values pass as plausible. The rule now drops the
decimals first (`FLOOR`), the test fixture uses 999,999,999.99, and the test
fails with the old rule. The price feature table lost 89 rows (2,082,932 →
2,082,843). The models were trained before the fix; the 89 rows are 0.004% of
the price data, so they were not retrained.

## 5. Design decisions

- **Local scheduling.** GitHub Actions is disabled for this repository, so the
  refresh runs on the owner's computer with Windows Task Scheduler. The task
  starts as soon as possible after a missed run (computer off) and stops after
  three hours. The same command would run unchanged in a cloud scheduler or CI job.
- **No automatic retraining.** Models change only on request (`--retrain`), so a
  refresh cannot silently replace a validated model; retraining is followed by
  the Phase 5 evaluation.
- **Publishing stays manual.** The refresh builds the app bundle but does not
  upload it: a new release changes the live app, so a person checks the report
  and the log first.

## 6. Limits

- The source files for 2019-2022 no longer change; the refresh re-downloads and
  re-checks them. TED switched to the eForms format in 2023, so newer years need a
  new loader. The World Bank file is updated daily and is refreshed each run.
- The schedule only runs while the computer can start the task.
