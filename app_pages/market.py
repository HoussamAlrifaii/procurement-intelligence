"""Market explorer: who buys, who wins and at what price in a sector and country."""
import altair as alt
import pandas as pd
import streamlit as st

from app_pages.common import (DATA_NOTE, country_options, cursor, division_options, parse_codes, range_ends,
                              show_error)
from procurement import tools


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
                                           "Find codes on the CPV lookup page, or describe your company on the "
                                           "AI assistant page.")
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


market_explorer()
