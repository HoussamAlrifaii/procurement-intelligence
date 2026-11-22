"""Tests for the assistant: tools, agent loop and evaluation, with a scripted fake LLM."""
import duckdb
import numpy as np
import pandas as pd
import pytest

from procurement import features, price_features, tools
from procurement.assistant import ask, system_prompt
from procurement.evaluate_assistant import figures, score_case, ungrounded_figures
from procurement.llm import Reply, ToolCall


@pytest.fixture()
def connection():
    awards = pd.DataFrame({
        "award_id": [1, 2, 3, 4, 5],
        "notice_id": [10, 10, 11, 12, 13],
        "publication_date": pd.to_datetime(["2021-03-01", "2021-03-01", "2022-05-01", "2022-06-01", "2019-01-01"]),
        "award_status": ["awarded"] * 5,
        "cpv_code": ["45314300", "45314300", "32420000", "33600000", "45314300"],
        "buyer_country": ["PL", "PL", "PL", "PL", "PL"],
        "award_value_eur": [100_000.0, 300_000.0, 200_000.0, 50_000.0, 100_000.0],
        "award_value_quality": ["plausible"] * 5,
        "is_framework_agreement": [False, False, None, False, False],
        "is_competitive_procedure": [True, True, True, True, True],
        "is_single_bid": [1, 0, 0, 1, 1],
        "winner_name": ["Alpha", "Beta", "Alpha", "Gamma", "Alpha"],
        "winner_name_std": ["ALPHA", "BETA", "ALPHA", "GAMMA", "ALPHA"],
        "winner_country": ["PL"] * 5,
        "winner_is_sme": [True, False, True, True, True],
    })
    fact_award = pd.DataFrame({"award_id": [1, 2, 3, 4, 5], "buyer_key": [1, 1, 2, 2, 1]})
    dim_buyer = pd.DataFrame({"buyer_key": [1, 2], "buyer_name": ["City of Krakow", "University Hospital"],
                              "buyer_country": ["PL", "PL"]})
    with duckdb.connect() as in_memory:
        in_memory.register("ted_awards", awards)
        in_memory.register("fact_award", fact_award)
        in_memory.register("dim_buyer", dim_buyer)
        yield in_memory


class FakeLLM:
    """Replays scripted replies and records what it was sent."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.received = []

    def __call__(self, messages, tool_schemas):
        self.received.append([dict(message) for message in messages])
        return self.replies.pop(0)


def test_search_market_summarises_only_matching_recent_awards(connection):
    result = tools.search_market(connection, ["453", "324"], country="pl")
    # Award 4 is another sector and award 5 is from 2019: both excluded.
    assert result["contracts_awarded"] == "3"
    assert result["tenders"] == "2"
    assert result["buyers"] == "2"
    assert result["typical_award_value"] == "EUR 200,000"
    assert result["single_bid_rate"] == "33.3%"
    assert result["share_won_by_smes"] == "66.7%"
    assert result["top_winners"][0] == {"company": "Alpha", "country": "PL", "contracts": "2", "sme": True}
    assert result["top_buyers"][0]["buyer"] == "City of Krakow"


def test_search_market_value_range_filter(connection):
    result = tools.search_market(connection, ["453"], min_value=150_000)
    assert result["contracts_awarded"] == "1"


def test_invalid_arguments_come_back_as_errors_for_the_llm(connection):
    assert "Unknown CPV groups" in tools.run_tool(connection, "search_market", {"cpv_groups": ["999"]})["error"]
    assert "Unknown country" in tools.run_tool(connection, "search_market", {"cpv_groups": ["453"], "country": "XX"})["error"]
    assert "Unknown tool" in tools.run_tool(connection, "delete_everything", {})["error"]
    assert "error" in tools.run_tool(connection, "search_market", {"sectors": ["453"]})


def test_cpv_codes_are_cut_to_three_digit_groups(connection):
    assert tools.check_cpv_groups(connection, ["45314300", " 324 "]) == ["324", "453"]


def test_planned_tender_has_every_model_feature(monkeypatch):
    monkeypatch.setattr(tools, "unknown_buyer_single_bid_rate", lambda: 0.31)
    tender = tools.planned_tender("453", "PL", "Works", estimated_value=200_000, lots=2)
    assert set(features.FEATURES) <= set(tender.columns)
    assert set(price_features.FEATURES) <= set(tender.columns)
    assert tender["log_estimated_value"].iloc[0] == pytest.approx(np.log(200_000))
    assert tender["cpv_division"].iloc[0] == "45"
    assert np.isnan(tools.planned_tender("453", "PL", "Works", estimated_value=50)["log_estimated_value"].iloc[0])


def test_contract_type_is_checked():
    assert tools.check_contract_type("works") == "Works"
    with pytest.raises(tools.ToolError):
        tools.check_contract_type("goods")


def test_assistant_runs_the_requested_tool_and_returns_the_final_answer(connection):
    llm = FakeLLM([
        Reply(tool_calls=[ToolCall("call-1", "search_market", {"cpv_groups": ["453"], "country": "PL"})]),
        Reply(content="2 contracts were awarded, typical value EUR 200,000."),
    ])
    result = ask("We install cabling in Poland", llm, connection)

    assert result["answer"] == "2 contracts were awarded, typical value EUR 200,000."
    assert result["tool_calls"][0]["name"] == "search_market"
    assert result["tool_calls"][0]["result"]["contracts_awarded"] == "2"
    # The second LLM call received the tool result.
    last_message = llm.received[1][-1]
    assert last_message["role"] == "tool" and '"contracts_awarded": "2"' in last_message["content"]


def test_assistant_stops_after_the_step_limit(connection):
    endless = [Reply(tool_calls=[ToolCall(f"call-{i}", "search_market", {"cpv_groups": ["453"]})]) for i in range(3)]
    result = ask("question", FakeLLM(endless), connection, max_steps=3)
    assert len(result["tool_calls"]) == 3
    assert "could not finish" in result["answer"]


def test_system_prompt_lists_cpv_divisions():
    prompt = system_prompt()
    assert "45: Construction work" in prompt
    assert "Never estimate" in prompt


def test_figures_ignore_years_and_single_digits():
    assert figures("In 2021, 1,240 contracts at EUR 156,488 and 41.9% single-bid, 3 lots") == {"1,240", "156,488", "41.9"}


def test_ungrounded_figures_finds_invented_numbers():
    calls = [{"result": {"contracts_awarded": "1,240", "single_bid_rate": "41.9%"}}]
    answer = "1,240 contracts, 41.9% single-bid, your offer of 150,000 is fine, about 55% of buyers..."
    assert ungrounded_figures(answer, calls, question="We offer EUR 150,000") == ["55"]


def test_score_case():
    case = {"id": "x", "question": "IT company in Poland", "acceptable_cpv_divisions": ["72"],
            "country": "PL", "expected_tools": ["search_market"]}
    result = {"answer": "1,240 contracts.", "tool_calls": [
        {"name": "search_market", "arguments": {"cpv_groups": ["722"], "country": "pl"},
         "result": {"contracts_awarded": "1,240"}}]}
    score = score_case(case, result)
    assert score["tool"] and score["sector"] and score["country"] and score["grounded"]
