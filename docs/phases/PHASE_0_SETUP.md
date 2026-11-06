# Phase 0: Project setup

**Goal:** a professional, reproducible project skeleton, so that every later
phase has a place to live, runs the same way on every computer, and is tested
automatically.

**Time for you:** about 1–2 hours (install, run, read this file).

---

## 1. What was built and why

| File / folder | What it is | Why it exists |
|---|---|---|
| `CLAUDE.md` | Rules Claude reads automatically in every session | Keeps the same way of working (🎯/📖 markers, simple style, a phase file each time) across sessions and tools: cloud, VS Code, anywhere |
| `README.md` | The project's front page | Recruiters spend about 30 seconds here, so it leads with the problem and solution |
| `requirements.txt` | Exact package versions | **Reproducibility:** the same versions on your laptop, in CI and in deployment |
| `.gitignore` | Files Git must never upload | Keeps data (large, re-creatable) and secrets (`.env`) out of GitHub |
| `.env.example` | Template for secret settings | Shows which secrets exist without exposing their values |
| `procurement/` | The Python package with all project code | Code in a package can be imported, tested and reused, which a notebook cannot do well |
| `procurement/config.py` | All paths in one place | Change a path once, and every script follows |
| `procurement/check_setup.py` | Environment checker | One command tells you whether your computer is ready |
| `tests/test_setup.py` | Automated tests | Proves the setup works |
| `pytest.ini` | pytest settings | Lets tests import `procurement` from the project root |
| `.github/workflows/tests.yml` | CI pipeline | GitHub runs the checks and tests on every push, on a clean machine |
| `.vscode/` | VS Code settings + recommended extensions | VS Code picks the right Python and runs tests automatically |
| `data/raw`, `data/processed` | Data folders (empty in Git) | Raw = downloaded and never edited by hand; processed = created by our code |
| `sql/`, `notebooks/`, `reports/` | Empty for now | Filled from Phase 1 onward |

### Key decisions

1. **A package (`procurement/`) instead of only notebooks.** Notebooks are
   great for exploring, but they are hard to test, reuse and deploy. EDA
   happens in notebooks; anything reusable moves into the package. *Interview
   phrasing:* "Notebooks for exploration, modules for production."
2. **DuckDB instead of PostgreSQL or MySQL.** It is a real SQL engine that runs
   inside Python and stores the database in one file, with no server to
   install. It handles millions of rows quickly on a laptop. The SQL you write
   is standard and transfers to PostgreSQL, Snowflake or BigQuery.
3. **Packages added per phase.** Phase 0 installs only what Phases 1–2 need.
   scikit-learn arrives in the ML phase, FastAPI in the API phase. Every package
   has a reason to be there.
4. **Pinned versions (`pandas==2.3.3`).** Without pins, installing next month
   could pull a new version that behaves differently. Pinning makes results
   reproducible.
5. **Data is never committed.** It is large and can be re-downloaded. The
   pipeline (Phase 1) re-creates it with one command, which itself shows
   reproducibility.

---

## 2. The code, explained

### `procurement/config.py`

```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
```
- `__file__` is the path of `config.py` itself.
- `.resolve()` turns it into a full absolute path.
- `.parents[0]` is the `procurement/` folder; `.parents[1]` is the project root.

🎯 **Why this matters:** paths are built from where the code lives, not from
where you happen to run it. `python -m procurement.check_setup` works from the
project root, from a notebook in `notebooks/`, and in CI.

### `procurement/check_setup.py`

Four checks, each returning `(passed, message)`:

1. `check_python_version()`: Python 3.12 or newer.
2. `check_packages()`: every package imports.
3. `check_folders()`: creates missing data folders.
4. 🎯 `check_duckdb_sql()`: runs real SQL on a pandas table:

```sql
SELECT
    country,
    COUNT(*) AS contracts,
    AVG(CASE WHEN number_of_bids = 1 THEN 1.0 ELSE 0.0 END) AS single_bid_rate
FROM contracts
GROUP BY country
```

**How the rate works:** `CASE WHEN` turns each contract into 1 (single bid) or
0 (competitive). The average of 1s and 0s is the share of 1s. For DE, (1 + 0) / 2
= 0.5, so 50% of German contracts in this toy example were single-bid. This
exact pattern becomes the project's main competition metric in SQL and in DAX.

**Why `sys.exit(1)` on failure:** programs report success with exit code 0
and failure with any other number. CI reads that code to decide whether a step
passed or failed.

### `tests/test_setup.py`
Three small tests. The useful one is
`test_project_paths_are_inside_the_project`, which protects against a config
change that would write data outside the repository.

---

## 3. Run it on your laptop (Windows, VS Code)

### One-time installs
1. **Python 3.12** from python.org. Tick **"Add python.exe to PATH"**.
2. **Git** from git-scm.com (default options).
3. **VS Code** + the **Claude Code** extension (done ✅). VS Code will offer the
   recommended Python and Jupyter extensions when you open the project; accept.
4. **Power BI Desktop** from the Microsoft Store (needed in Phase 4).

### Get the project
1. VS Code → `Ctrl+Shift+P` → **Git: Clone** →
   `https://github.com/HoussamAlrifaii/procurement-intelligence` → choose a
   folder → **Open**.
2. Open a terminal: **Terminal → New Terminal** (PowerShell).

### Create the environment and run the checks
```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m procurement.check_setup
python -m pytest -q
```

If PowerShell blocks `Activate.ps1` with a "running scripts is disabled"
error, run this once, then activate again:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**Expected result:** every line shows `[OK  ]`, then
`All checks passed`, then `3 passed`. If anything fails, copy the full output
to Claude.

Verified here: all 13 checks and 3 tests passed in Claude's Linux environment
(Python 3.13). Your Windows run is the real confirmation.

### Working with Claude in VS Code
Open the Claude Code panel in the project folder. It reads `CLAUDE.md`
automatically, so you can say *"Start Phase 1"* and it follows the same rules.
VS Code asks before Claude runs commands; it's safe to allow `git`, `pytest`
and `python -m procurement...` permanently.

---

## 4. Git workflow from now on

```
main ──────────────●────────────────●──────────
                    \              / (you merge the pull request)
phase-1-data         ●──●──●──●───●
```
- `main` always works.
- Each phase is built on its own branch, and Claude opens a pull request.
- **You review and merge.** A clean history of phases and pull requests is
  itself portfolio evidence.

---

## 5. What you must know from this phase

| Topic | Level |
|---|---|
| Why a package + notebooks instead of notebooks only | 🎯 Explain |
| Why pinned requirements and a virtual environment | 🎯 Explain |
| Why data and `.env` are git-ignored | 🎯 Explain |
| The `CASE WHEN` + `AVG` rate pattern | 🎯 Rebuild from scratch |
| Building paths from `__file__` | 🎯 Explain |
| CI YAML, `.vscode` settings, `pytest.ini` | 📖 Recognise |

## 6. Self-check questions (answer without looking, then check)

1. Why don't we commit the data to GitHub? How would someone else get it?
   <details><summary>Answer</summary>It's large and re-creatable; committing it bloats the repo and may break licence terms. The Phase 1 pipeline downloads and rebuilds it with one command.</details>
2. What happens if a teammate installs packages without a pinned `requirements.txt`?
   <details><summary>Answer</summary>They may get different versions, so results or behaviour can differ ("works on my machine"). Pinning makes environments identical.</details>
3. Write SQL that returns the share of contracts with more than 5 bids per country.
   <details><summary>Answer</summary>

   ```sql
   SELECT country,
          AVG(CASE WHEN number_of_bids > 5 THEN 1.0 ELSE 0.0 END) AS share_over_5
   FROM contracts
   GROUP BY country;
   ```
   </details>
4. Why does `check_setup.py` exit with code 1 when a check fails?
   <details><summary>Answer</summary>A non-zero exit code tells CI (and any script calling it) that the step failed, so the pipeline stops instead of continuing broken.</details>
5. Why DuckDB rather than installing PostgreSQL?
   <details><summary>Answer</summary>No server to set up, a single database file, fast analytics on millions of rows on a laptop, and standard SQL that transfers to other databases.</details>

## 7. Next: Phase 1, data sourcing

Download TED and World Bank contract award data for a subset of countries and
years, verify which fields really exist and how complete they are, and load
them into DuckDB with automatic quality checks. The data sites are blocked from
Claude's cloud session, so the download runs on your laptop.
