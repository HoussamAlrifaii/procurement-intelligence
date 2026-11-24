"""TenderLens: the Procurement Intelligence web app (entry point).

Pages live in app_pages/ and use the same tools as the AI assistant (procurement/tools.py):
  Home            - what the app does and how to use it
  AI assistant    - questions in plain language, answered from the data and the models
  Market explorer - who buys, who wins and at what price in a sector and country
  Tender check    - expected award value, price range and single-bid risk of a planned tender
  CPV lookup      - find the procurement codes for a product or service

Run locally:  streamlit run streamlit_app.py
"""
import streamlit as st

st.set_page_config(page_title="TenderLens", page_icon="🔍", layout="wide")

with st.sidebar:
    st.markdown("### 🔍 TenderLens")
    st.markdown("See clearly into EU public tenders: markets, prices and competition from 3.56 million contract awards.")
    st.markdown("[Source code and documentation](https://github.com/HoussamAlrifaii/procurement-intelligence)")

st.navigation([
    st.Page("app_pages/home.py", title="Home", icon="🏠", default=True),
    st.Page("app_pages/assistant.py", title="AI assistant", icon="💬"),
    st.Page("app_pages/market.py", title="Market explorer", icon="🔎"),
    st.Page("app_pages/tender.py", title="Tender check", icon="💶"),
    st.Page("app_pages/cpv.py", title="CPV lookup", icon="📖"),
]).run()
