"""REST API for the market search and the two models.

Endpoints (JSON in, JSON out):
  GET  /health   - is the service up
  POST /market   - market summary for CPV codes, a country and a value range
  POST /price    - expected award value and 80% range of a planned tender
  POST /risk     - single-bid risk of a planned tender

Run locally:  uvicorn procurement.api:app --reload    (interactive docs at /docs)
"""
from functools import lru_cache
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from procurement import app_data, tools

app = FastAPI(
    title="Procurement Intelligence API",
    description="Market statistics, expected award values and single-bid risk for EU public tenders (TED 2021-2022).",
    version="1.0.0",
)


class MarketQuery(BaseModel):
    cpv_codes: list[str] = Field(..., min_length=1, examples=[["45314", "3242", "72"]],
                                 description="CPV codes of 2 to 5 digits")
    country: str | None = Field(None, examples=["PL"], description="Two-letter buyer country code")
    min_value: float | None = Field(None, ge=0, examples=[50_000])
    max_value: float | None = Field(None, ge=0, examples=[500_000])


class Tender(BaseModel):
    cpv_group: str = Field(..., examples=["45314"], description="CPV code of at least 3 digits")
    country: str = Field(..., examples=["PL"])
    contract_type: Literal["Works", "Supplies", "Services"] = "Works"
    estimated_value: float | None = Field(None, ge=0, examples=[200_000])
    lots: int = Field(1, ge=1)


@lru_cache(maxsize=1)
def database():
    return app_data.connect()


def get_cursor():
    """One DuckDB cursor per request; the base connection is opened once."""
    cursor = database().cursor()
    try:
        yield cursor
    finally:
        cursor.close()


def run(tool, cursor, **arguments):
    try:
        return tool(cursor, **arguments)
    except tools.ToolError as problem:
        raise HTTPException(status_code=422, detail=str(problem)) from problem


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/market")
def market(query: MarketQuery, cursor=Depends(get_cursor)):
    return run(tools.search_market, cursor, cpv_groups=query.cpv_codes, country=query.country,
               min_value=query.min_value, max_value=query.max_value)


@app.post("/price")
def price(tender: Tender, cursor=Depends(get_cursor)):
    return run(tools.estimate_price, cursor, **tender.model_dump())


@app.post("/risk")
def risk(tender: Tender, cursor=Depends(get_cursor)):
    return run(tools.single_bid_risk, cursor, **tender.model_dump())
