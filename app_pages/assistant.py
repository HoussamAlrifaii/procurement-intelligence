"""AI assistant: questions in plain language, answered from the data and the models."""
import os

import streamlit as st

from app_pages.common import DATA_NOTE, cursor
from procurement import config
from procurement.assistant import ask


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
    # The placeholder must stay the same on every run: Streamlit identifies a widget by its
    # parameters, so a changing text (e.g. a counter) would create a new box and drop the question.
    question = st.chat_input("Describe your company or a tender") or example
    if not question:
        st.caption(f"{questions_left} of {config.APP_MAX_QUESTIONS} questions left in this session.")
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
    st.caption(f"{questions_left - 1} of {config.APP_MAX_QUESTIONS} questions left in this session.")


assistant()
