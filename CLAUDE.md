# CLAUDE.md — project rules for Claude

This file is read automatically by Claude Code at the start of every session in
this repository. It records how we work, so every session follows the same rules.

## Project

**Procurement Intelligence**: an end-to-end data project on public procurement
data (EU TED contract awards as the main source, World Bank contract awards for
global coverage). It solves three problems:

1. **Weak competition:** predict, before publication, the risk that a tender
   receives only one bid, and explain why.
2. **Hidden patterns:** SQL + Power BI show where competition is weak, which
   vendors dominate which buyers, and which award prices are unusual.
3. **Access for small businesses:** an AI assistant matches a company
   description to relevant tenders and past winners and prices.

Full plan: `docs/PROJECT_PLAN.md`. One explanation file per phase lives in `docs/phases/`.

## Who the owner is

The owner is a certified data scientist (CS degree) moving from business
development into data roles: Data Analyst, Data Scientist, ML Engineer and
AI Engineer. Strong in Python and ML/DL theory, comfortable with Power BI;
growing on engineering, deployment and AI systems. Do not explain basic Python
syntax. Do explain library-specific or advanced features.

## How we work (every phase)

1. **Plan:** explain what will be built and why; wait for approval.
2. **Build:** write code, SQL and tests.
3. **Explain:** write `docs/phases/PHASE_N_<NAME>.md`, covering logic,
   decisions, alternatives rejected, how to run it, and interview questions
   with answers.
4. **Run:** the owner runs it locally and checks the outputs.
5. **Learn:** quiz the owner on the 🎯 parts; for SQL phases, give 3–5
   exercises to solve without AI.
6. **Ship:** one branch per phase (`phase-N-short-name`), then a pull request
   that the owner reviews and merges.

## Code style (non-negotiable)

- Simple and readable. Small functions with clear names. One step per line.
- No clever one-liners, no semicolon-chained statements, no single-letter
  variable names (except `i` in short loops).
- Every block is commented with one of these markers:
  - `# 🎯 INTERVIEW FOCUS:` logic the owner must explain AND rebuild from
    scratch (cleaning rules, SQL logic, splits, features, evaluation).
  - `# 📖 READ ONLY:` boilerplate to recognise, not memorise (setup,
    configuration, logging, API/Docker/CI plumbing).
- SQL lives in `.sql` files under `sql/`, not hidden in Python strings, so it
  can be read and practised on its own.
- All paths come from `procurement/config.py`. Never hard-code paths.
- Prefer pandas + DuckDB + scikit-learn. Add a library only when it clearly
  earns its place, and say why in the phase explanation file.
- Add packages to `requirements.txt` only in the phase that first needs them,
  with exact pinned versions.

## Honesty rules

- Never fabricate data, results, metrics or screenshots. If something was not
  run, say so.
- Report metrics with their evaluation setup. Never tune on the test set.
- Describe what the data can and cannot show (e.g. single-bid is a risk
  indicator, not proof of corruption).

## Data and secrets

- Raw and processed data are NOT committed (`data/` is git-ignored except
  `.gitkeep`). Pipelines must be able to re-create them.
- Secrets (e.g. `ANTHROPIC_API_KEY`) go in `.env` (git-ignored). Commit only
  `.env.example`.

## Commands

```bash
python -m procurement.check_setup   # verify the environment
python -m pytest -q                 # run tests
```
