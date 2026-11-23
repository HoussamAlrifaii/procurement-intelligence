"""Shared data access and formatting for the app pages."""
import pandas as pd
import streamlit as st

from procurement import app_data, config, tools


DATA_NOTE = (f"EU contract awards published on TED, {config.ASSISTANT_FIRST_YEAR}-{config.ASSISTANT_LAST_YEAR}. "
             "Single-bid rates and price ranges are indicators for review, not evidence of wrongdoing.")


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
