# Phase 6: AI assistant

A small business describes itself, or a tender it is considering, in plain
language. The assistant turns that into a search of 2021-2022 EU contract
awards and calls the Phase 5 models, then explains the results. The LLM
interprets the question and writes the answer; **every figure comes from SQL or
the models**.

## 1. How to run

```bash
pip install -r requirements.txt     # adds the openai client (works with Groq and Gemini too)
cp .env.example .env                # Windows: Copy-Item .env.example .env, then add LLM_API_KEY
python -m procurement.assistant --trace "We are a 20-person IT company in Poland. We install computer networks and cabling. Projects are usually EUR 50k-500k."
python -m procurement.evaluate_assistant            # 20 test cases (~20 LLM calls)
python -m procurement.evaluate_assistant --rescore  # score saved answers again, no LLM calls
python -m pytest -q
```

Requires the star schema (Phase 3) and the trained models (Phase 5). The LLM
provider is set in `.env`: `LLM_API_KEY` (a free Groq key by default), and
optionally `LLM_BASE_URL` and `LLM_MODEL`. Any provider with an
OpenAI-compatible API works without code changes.

| File | Role |
|---|---|
| `procurement/assistant.py` | Instructions (system prompt) and the agent loop `ask()` |
| `procurement/tools.py` | The three tools, input checks and tool descriptions for the LLM |
| `procurement/llm.py` | LLM client; returns either text or tool calls |
| `sql/assistant/*.sql` | Matching awards, market summary, top buyers, top winners |
| `procurement/evaluate_assistant.py` | Evaluation: runs the cases, scores them, writes the report |
| `evaluation/assistant_cases.json` | 20 hand-written questions with the expected tools, sectors and country |

## 2. How it works

```
question ──▶ LLM (instructions + question + tool descriptions)
                │ tool call, e.g. search_market(cpv_groups=["45314","3242","72"], country="PL", ...)
                ▼
          tools.py: check inputs ──▶ SQL on DuckDB / Phase 5 model ──▶ result (formatted figures)
                │ result sent back to the LLM
                ▼
          LLM: another tool call, or the final answer (at most 6 rounds)
```

| Tool | Source | Returns |
|---|---|---|
| `search_market` | SQL over awards published 2021-2022 | Contracts, tenders, buyers, winners, typical value and range, single-bid rate, SME win share, top 5 buyers and winners |
| `estimate_price` | Fair price model (three quantile models + conformal margin) | Expected award value and 80% range |
| `single_bid_risk` | Single-bid risk model | Probability of a single offer |

**Example** (from the evaluation run). *"We are a 20-person IT company in Poland.
We install computer networks and cabling. Projects are usually EUR 50k-500k."*
The assistant searched CPV 45314 (telecommunications installation), 3242
(network equipment) and 72 (IT services) in Poland, EUR 50k-500k, and answered
with 1,156 awards, a typical value of EUR 194,206, a single-bid rate of 57.5%,
an SME win share of 70.7%, the top buyers (e.g. Centrum e-Zdrowia, City of
Warsaw) and the most frequent winners (e.g. Asseco Poland, Comtegra, Exatel).

## 3. Design decisions

**Search by CPV code, not by title text.** Titles are written in 24 languages;
CPV codes are the same in every country. The LLM's main job is to translate a
description in any language into CPV codes, a country and a value range. Codes
of 2 to 5 digits are accepted (division `45`, group `453`, class `4531`,
category `45314`), so the LLM can be as specific as it is sure.

**Search related codes together.** Buyers code similar work differently: in
Poland only 2 awards use 45314 (telecommunications installation), while network
projects are usually coded as network equipment (3242) or IT services (72).
The instructions ask for installation, equipment and service codes in one
search, and a search returning fewer than 30 awards adds a note suggesting
related or broader codes. The answer must say when a search was widened.

**The LLM never computes figures.** Tools return figures already formatted
(`EUR 156,488`, `41.9%`) and the instructions forbid estimating, rounding or
deriving new figures. This is checked automatically (section 4).

**Checked inputs, safe SQL.** CPV codes, countries and contract types are
validated against the data; invalid input returns an error message that the
LLM reads and corrects (in testing it fixed `"71"` and `"51"` this way). Values
chosen by the LLM reach DuckDB as bound parameters (`$country`), never as text
inside the query.

**Predictions for a typical buyer.** The models need every training feature.
Details the user does not give take neutral defaults (open procedure, buyer type
not reported, no buyer history), so price and risk describe a typical buyer in
that market. Model files and the conformal margin come from Phase 5; nothing is
retrained.

**No fine-tuning or retrieval over text.** The questions are about counts,
prices and rates, which SQL answers exactly; the pre-trained model already
understands the descriptions and only needs instructions and tools.

**Provider-neutral and free.** The OpenAI-compatible client works with Groq
(free tier, default) and Google Gemini; the model is set in `.env`
(default `openai/gpt-oss-120b` on Groq), with `temperature=0` for repeatable answers.

## 4. Evaluation

`evaluation/assistant_cases.json` holds 20 questions written before testing,
with the correct answers: 14 market questions (including one in French and one
in Polish) and 6 questions about a specific tender's price or competition. Each
answer is scored on four checks:

| Check | Passes when |
|---|---|
| tool | The assistant called at least one expected tool |
| sector | A CPV code it used falls in an acceptable CPV division |
| country | It searched the expected country (or none when none was given) |
| grounded | Every figure in the answer matches, within 5%, a figure in the question or a tool call |

The grounding check reads figures written as `1,240`, `118 330`, `EUR 2.07 m` or
`16.5%`; it accepts rounding ("about 16%" for 16.5%) but flags any figure with no
matching source. Numbers that are names (`ISO 27001`, `CPV 1512`) are skipped.

**Results (one run, Groq `openai/gpt-oss-120b`):**

| Check | Passed |
|---|---|
| tool | 20/20 |
| sector | 20/20 |
| country | 20/20 |
| grounded | **18/20** |

Full report: [`reports/assistant_evaluation.md`](../../reports/assistant_evaluation.md);
every answer and tool call: [`reports/assistant_answers.json`](../../reports/assistant_answers.json).

**The two failures** are invented figures in the "practical tip" at the end of
an answer, not in the reported market data:
- *translation-eu*: "tailor proposals to the common contract size (EUR 100-300k)";
  the tool reported a typical value of EUR 183k and a range of EUR 4k to EUR 803k.
- *price-medicines-ro*: "an offer near the lower end of the range (about EUR 7k-15k)";
  no tool produced this range.

The first version of the grounding check reported 8/20: it also flagged
certification names, numbers written with spaces and rounded values. The check
was corrected and the **same saved answers** were scored again
(`--rescore`); the assistant itself was not changed after seeing the results,
so the cases remain a fair test. Instructions that forbid suggested prices are
the next improvement and should be measured on new cases.

## 5. Limits

- **Past awards, not open tenders.** The data shows where a market is, who buys
  and at what price in 2021-2022; it does not list tenders open today.
- **LLM output varies.** Results are from one run; answers and tool choices can
  change slightly between runs even at temperature 0.
- **SME flag.** Winners' SME status is self-reported in TED notices and is
  sometimes wrong for local subsidiaries of large groups.
- **Buyer names.** Buyers are grouped by standardised name; spellings differing
  by one letter (e.g. "ł" and "l") remain separate.
- **Typical buyer.** Price and risk do not use the buyer's own history, the
  second strongest single-bid driver.
- **Privacy.** Questions are sent to the LLM provider, whose free tier may use
  them to improve its service; confidential company details should not be entered.

## 6. Tests

`tests/test_assistant.py` (16 tests) runs without a key or network: a fake LLM
replays scripted replies. It covers the market search on synthetic data (filters,
value range, divisions and 5-digit codes, small-market note), input checks and
error messages, null optional inputs, the model input row, the agent loop and its
step limit, the instructions, and the grounding and scoring rules.
