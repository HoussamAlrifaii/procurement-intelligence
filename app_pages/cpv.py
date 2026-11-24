"""CPV lookup: find the procurement codes for a product or service."""
import pandas as pd
import streamlit as st

from app_pages.common import cursor, show_error
from procurement import tools


def cpv_lookup():
    st.title("CPV lookup")
    st.caption("Every EU tender is labelled with a CPV code from the official Common Procurement Vocabulary "
               "(9,454 codes). Type what you sell in English to find its codes, then use them in Market explorer "
               "or Tender check. Codes used by many contracts come first.")
    keywords = st.text_input("What do you sell?", placeholder="e.g. bread, office cleaning, network cabling")
    if not keywords:
        st.markdown("Codes are hierarchical: each extra digit narrows the market, e.g. "
                    "**33** medical equipment and pharmaceuticals → **331** medical equipment → "
                    "**3314** medical consumables.")
        return
    result = tools.run_tool(cursor(), "find_cpv_codes", {"keywords": keywords, "limit": 15})
    if show_error(result):
        return
    if not result["codes"]:
        st.info(result["note"])
        return
    table = pd.DataFrame(result["codes"]).rename(columns={
        "cpv_code": "CPV code", "name": "Name", "contracts_2021_2022": "Contracts 2021-2022"})
    st.dataframe(table, hide_index=True, width="stretch")


cpv_lookup()
