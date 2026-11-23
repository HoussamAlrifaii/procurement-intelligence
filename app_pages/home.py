"""Home page: what TenderLens does and how to use it."""
import streamlit as st


def feature_card(column, page_file, title, icon, text):
    with column.container(border=True):
        st.markdown(f"#### {icon} {title}")
        st.write(text)
        st.page_link(page_file, label=f"Open {title}", icon="➡️")


def home():
    st.title("🔍 TenderLens")
    st.subheader("See clearly into EU public tenders.")
    st.write(
        "Governments in Europe award hundreds of billions of euros in public contracts every year. TenderLens turns "
        "3.56 million of these awards (TED, 2019-2022, 33 countries) into answers for small businesses and auditors: "
        "**where the market is, who buys and who wins, what a contract is likely to cost, and how much competition to expect.**"
    )

    st.markdown("### What you can do")
    top = st.columns(2)
    feature_card(top[0], "app_pages/assistant.py", "AI assistant", "💬",
                 "Describe your company or a tender in your own words, in any language. An AI assistant finds your "
                 "sector, searches the data and runs the models for you.")
    feature_card(top[1], "app_pages/market.py", "Market explorer", "🔎",
                 "Choose a sector, country and contract size. See how many contracts are awarded, the typical value, "
                 "the main buyers, the most frequent winners and how often only one company bids.")
    bottom = st.columns(2)
    feature_card(bottom[0], "app_pages/tender.py", "Tender check", "💶",
                 "Planning or bidding for a tender? Get the expected award value, the usual price range and the risk "
                 "of a single bid, and check whether your offer is in line.")
    feature_card(bottom[1], "app_pages/cpv.py", "CPV lookup", "📖",
                 "Every tender has a CPV code describing what is bought. Type what you sell to find your codes and "
                 "how often buyers use them.")

    st.markdown("### How to use it")
    steps = st.columns(3)
    steps[0].markdown("**1. Find your codes**  \nNot sure how your products are classified? Start with **CPV lookup**, "
                      "or simply ask the **AI assistant**.")
    steps[1].markdown("**2. Explore your market**  \nUse **Market explorer** to see buyers, competitors, prices "
                      "and competition in your countries.")
    steps[2].markdown("**3. Check a tender**  \nBefore bidding, use **Tender check** to compare your offer with "
                      "the expected price range.")

    st.markdown("### Key numbers")
    numbers = st.columns(4)
    numbers[0].metric("Contract awards analysed", "3.56 M", help="TED contract award notices, 2019-2022")
    numbers[1].metric("Risk model: lift in top 10%", "2.4x", help="The riskiest 10% of 2022 tenders it flags received a single "
                                                       "bid 2.4 times as often as average (ROC-AUC 0.76)")
    numbers[2].metric("Price model: typical error", "26%", help="Typical error of the expected award value when the buyer "
                                                 "publishes an estimate (2022 test year)")
    numbers[3].metric("Assistant answers grounded", "18 / 20", help="Hand-written test questions whose answers "
                                                                   "used only figures from the data and models")

    st.divider()
    st.caption("Data: TED (Tenders Electronic Daily) contract award notices published by the EU. The app searches "
               "awards from 2021-2022; the models were trained on 2019-2020 and tested on 2022. Single-bid rates, "
               "price ranges and flags are indicators for review, not evidence of wrongdoing. "
               "[Methods, code and evaluation on GitHub](https://github.com/HoussamAlrifaii/procurement-intelligence).")


home()
