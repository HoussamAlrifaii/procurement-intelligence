"""Tender check: expected award value, price range and single-bid risk of a planned tender."""
import streamlit as st

from app_pages.common import DATA_NOTE, country_options, cursor, euro_amount, range_ends, show_error
from procurement import tools


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


tender_check()
