"""Procurement Intelligence web app.

Three pages built on the same tools as the AI assistant (procurement/tools.py):
  Market explorer - who buys, who wins and at what price in a sector and country
  Tender check    - expected award value, price range and single-bid risk of a planned tender
  AI assistant    - questions in plain language, answered from the tools

Run locally:  streamlit run streamlit_app.py
"""
import os

import altair as alt
import pandas as pd
import streamlit as st

from procurement import app_data, config, tools
from procurement.assistant import ask

st.set_page_config(page_title="Procurement Intelligence", page_icon="📊", layout="wide")

DATA_NOTE = (f"EU contract awards published on TED, {config.ASSISTANT_FIRST_YEAR}-{config.ASSISTANT_LAST_YEAR}. "
             "Single-bid rates and price ranges are indicators for review, not evidence of wrongdoing.")


# --- Shared resources -------------------------------------------------------------

@st.cache_resource(show_spinner="Loading data and models (first visit only)...")
def database():
    return app_data.connect()


def cursor():
    """Each page run gets its own cursor: DuckDB connections are not shared between threads."""
    return database().cursor()


@st.cache_data
def division_options():
    return {code: f"{code} · {name}" for code, name in tools.cpv_division_names().items()}


@st.cache_data
def country_options():
    names = pd.read_csv(config.COUNTRIES_PATH, dtype=str).set_index("country_code")["country_name"]
    present = sorted(tools.known_values(cursor(), "SELECT DISTINCT buyer_country FROM ted_awards"))
    return {code: names.get(code, code) for code in present}


def parse_codes(text):
    return [code.strip() for code in text.replace(";", ",").split(",") if code.strip()]


def range_ends(text):
    """'EUR 1 to EUR 2' -> ('EUR 1', 'EUR 2'); shown as two short metrics instead of one long one."""
    if " to " not in text:
        return text, text
    low, high = text.split(" to ")
    return low, high


def euro_amount(text):
    return float(text.replace("EUR", "").replace(",", ""))


def show_error(result):
    if "error" in result:
        st.error(result["error"])
        return True
    return False


# --- Page 1: market explorer -----------------------------------------------------------

COLUMN_NAMES = {"buyer": "Buyer", "company": "Company", "country": "Country", "contracts": "Contracts",
                "typical_value": "Typical value", "sme": "SME"}


def contracts_chart(buyers):
    """Top buyers by number of contracts, largest first."""
    data = buyers.assign(Contracts=buyers["Contracts"].str.replace(",", "").astype(int))
    return (
        alt.Chart(data, title="Contracts awarded by the top buyers")
        .mark_bar(color="#2B8DE0")
        .encode(
            x=alt.X("Contracts:Q", title=None),
            y=alt.Y("Buyer:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320)),
            tooltip=["Buyer", "Country", "Contracts", "Typical value"],
        )
        .properties(height=220)
    )

def market_explorer():
    st.title("Market explorer")
    st.caption("Who buys, who wins and at what price, by sector and country. " + DATA_NOTE)

    divisions = division_options()
    countries = country_options()
    with st.form("market"):
        left, right = st.columns(2)
        chosen_divisions = left.multiselect("Sectors (CPV divisions)", list(divisions), default=["72"],
                                            format_func=divisions.get)
        extra_codes = left.text_input("More specific CPV codes (optional, 3-5 digits, comma-separated)",
                                      placeholder="e.g. 45314, 3242",
                                      help="Searched together with the sectors above. Codes are hierarchical: "
                                           "33 medical, 331 medical equipment, 3314 medical consumables. "
                                           "Not sure which codes fit? Describe your company on the AI assistant page.")
        country = right.selectbox("Buyer country", [None] + list(countries),
                                  format_func=lambda code: "All countries" if code is None else countries[code])
        low, high = right.columns(2)
        min_value = low.number_input("Minimum value (EUR)", min_value=0, value=0, step=10_000)
        max_value = high.number_input("Maximum value (EUR, 0 = no limit)", min_value=0, value=0, step=10_000)
        submitted = st.form_submit_button("Search", type="primary")

    if not submitted:
        return
    codes = chosen_divisions + parse_codes(extra_codes)
    if not codes:
        st.warning("Choose at least one sector or type a CPV code. "
                   "Not sure which ones fit? Describe your company on the AI assistant page.")
        return
    result = tools.run_tool(cursor(), "search_market", {
        "cpv_groups": codes, "country": country,
        "min_value": min_value or None, "max_value": max_value or None,
    })
    if show_error(result):
        return
    if "note" in result:
        st.info(result["note"])

    first = st.columns(4)
    first[0].metric("Contracts awarded", result["contracts_awarded"])
    first[1].metric("Typical award value", result["typical_award_value"])
    first[2].metric("Single-bid rate", result["single_bid_rate"], help="Competitive procedures with one offer")
    first[3].metric("Won by SMEs", result["share_won_by_smes"], help="Self-reported in the award notices")
    low, high = range_ends(result["usual_value_range"])
    second = st.columns(4)
    second[0].metric("Tenders", result["tenders"])
    second[1].metric("Buyers", result["buyers"])
    second[2].metric("Low end of usual values", low, help="10% of awards are below this value")
    second[3].metric("High end of usual values", high, help="10% of awards are above this value")

    buyers = pd.DataFrame(result["top_buyers"]).rename(columns=COLUMN_NAMES)
    winners = pd.DataFrame(result["top_winners"]).rename(columns=COLUMN_NAMES)
    left, right = st.columns(2)
    left.subheader("Top buyers")
    left.dataframe(buyers, hide_index=True, width="stretch")
    right.subheader("Most frequent winners")
    right.dataframe(winners, hide_index=True, width="stretch")
    if not buyers.empty:
        st.altair_chart(contracts_chart(buyers), width="stretch")


# --- Page 2: tender check -------------------------------------------------------------

def tender_check():
    st.title("Tender check")
    st.caption("Expected award value and single-bid risk of a planned tender, from the two models "
               "trained on 2019-2020 and tested on 2022. " + DATA_NOTE)

    countries = country_options()
    with st.form("tender"):
        left, right = st.columns(2)
        cpv_code = left.text_input("CPV code (at least 3 digits)", value="45314",
                                   help="e.g. 45314 telecom installation, 336 pharmaceuticals, 9091 cleaning")
        country = left.selectbox("Buyer country", list(countries), index=list(countries).index("PL"),
                                 format_func=countries.get)
        contract_type = left.radio("Contract type", tools.CONTRACT_TYPES, horizontal=True)
        estimate = right.number_input("Buyer's estimate (EUR, 0 = not published)", min_value=0, value=200_000,
                                      step=10_000)
        lots = right.number_input("Lots in the tender", min_value=1, value=1)
        offer = right.number_input("Your planned offer (EUR, optional)", min_value=0, value=0, step=10_000)
        submitted = st.form_submit_button("Check", type="primary")

    if not submitted:
        return
    tender = {"cpv_group": cpv_code, "country": country, "contract_type": contract_type,
              "estimated_value": estimate or None, "lots": lots}
    price = tools.run_tool(cursor(), "estimate_price", tender)
    risk = tools.run_tool(cursor(), "single_bid_risk", tender)
    if show_error(price) or show_error(risk):
        return

    low, high = range_ends(price["range_80_percent"])
    columns = st.columns(4)
    columns[0].metric("Expected award value", price["expected_award_value"])
    columns[1].metric("Low end (80% range)", low, help="10% of similar contracts are awarded below this")
    columns[2].metric("High end (80% range)", high, help="10% of similar contracts are awarded above this")
    columns[3].metric("Single-bid risk", risk["single_bid_risk"],
                      help=f"Average across all tenders: {risk['average_risk_all_tenders']}")
    if offer:
        low, high = euro_amount(low), euro_amount(high)
        if offer < low:
            st.warning(f"Your offer of EUR {offer:,.0f} is below the usual range for similar contracts.")
        elif offer > high:
            st.warning(f"Your offer of EUR {offer:,.0f} is above the usual range for similar contracts.")
        else:
            st.success(f"Your offer of EUR {offer:,.0f} is within the usual range for similar contracts.")
    st.caption(price["note"] + " Predictions assume a typical buyer with an open procedure.")


# --- Page 3: AI assistant -------------------------------------------------------------

EXAMPLES = [
    "We are a 20-person IT company in Poland. We install computer networks and cabling. Projects are usually EUR 50k-500k.",
    "Small family bakery in Slovenia, we deliver bread and pastries. Which public buyers could we supply?",
    "A Romanian hospital tenders pharmaceutical supplies, 3 lots, estimated at EUR 62,000. What price should we expect?",
]


def llm_key_available():
    # Streamlit Cloud keeps the key in the app's secrets; locally it comes from .env.
    try:
        if "LLM_API_KEY" in st.secrets:
            os.environ["LLM_API_KEY"] = st.secrets["LLM_API_KEY"]
    except FileNotFoundError:
        pass
    from dotenv import load_dotenv
    load_dotenv(config.PROJECT_ROOT / ".env")
    return bool(os.getenv("LLM_API_KEY"))


def show_tool_calls(tool_calls):
    if not tool_calls:
        return
    with st.expander("How this answer was made"):
        for call in tool_calls:
            st.markdown(f"**{call['name']}**")
            st.json({"arguments": call["arguments"], "result": call["result"]}, expanded=False)


def assistant():
    st.title("AI assistant")
    st.caption("Describe your company or a tender in any language. An LLM picks the sector codes and calls the "
               "market search and the models; every figure comes from them. " + DATA_NOTE)

    if not llm_key_available():
        st.info("The assistant needs an LLM API key (LLM_API_KEY). The other pages work without it.")
        return

    history = st.session_state.setdefault("history", [])
    for message in history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            show_tool_calls(message.get("tool_calls"))

    questions_left = config.APP_MAX_QUESTIONS - sum(message["role"] == "user" for message in history)
    if questions_left <= 0:
        st.info("You have reached the question limit for this session. Market explorer and Tender check remain available.")
        return

    example = None
    if not history:
        st.write("Try an example:")
        for index, text in enumerate(EXAMPLES):
            if st.button(text, key=f"example-{index}"):
                example = text
    question = st.chat_input(f"Describe your company or tender ({questions_left} questions left)") or example
    if not question:
        return

    history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Searching the data..."):
            from procurement.llm import LLM
            try:
                result = ask(question, LLM(), cursor())
            except Exception as problem:   # provider limits or network errors: keep the page usable
                result = {"answer": f"The assistant is unavailable right now ({type(problem).__name__}). "
                                    "Please try again later.", "tool_calls": []}
        st.markdown(result["answer"])
        show_tool_calls(result["tool_calls"])
    history.append({"role": "assistant", "content": result["answer"], "tool_calls": result["tool_calls"]})


# --- Navigation -------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Procurement Intelligence")
    st.markdown("Public procurement analytics on 3.5 million EU contract awards: competition, prices and markets.")
    st.markdown("[Source code and documentation](https://github.com/HoussamAlrifaii/procurement-intelligence)")

pages = st.navigation([
    st.Page(market_explorer, title="Market explorer", icon="🔎", url_path="market"),
    st.Page(tender_check, title="Tender check", icon="💶", url_path="tender"),
    st.Page(assistant, title="AI assistant", icon="💬", url_path="assistant"),
])
pages.run()
