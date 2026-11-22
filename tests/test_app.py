"""Tests for the app bundle loader, the REST API and the web app (small synthetic bundle)."""
import io
import zipfile

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from procurement import api, app_data, config
from procurement.app_bundle import AWARD_COLUMNS


@pytest.fixture()
def bundle(tmp_path, monkeypatch):
    """A tiny bundle folder with the same files and columns as the real one (no models)."""
    monkeypatch.setattr(config, "MODELS_DIR", config.MODELS_DIR)   # connect() changes it; restore afterwards
    awards = pd.DataFrame({
        "award_id": [1, 2, 3], "notice_id": [10, 10, 11],
        "publication_date": pd.to_datetime(["2021-03-01", "2021-03-01", "2022-05-01"]),
        "cpv_code": ["45314300", "45314300", "72000000"], "buyer_country": ["PL", "PL", "DE"],
        "award_status": ["awarded"] * 3, "award_value_eur": [100_000.0, 300_000.0, 200_000.0],
        "award_value_quality": ["plausible"] * 3, "is_framework_agreement": [False] * 3,
        "is_competitive_procedure": [True] * 3, "is_single_bid": [1, 0, 0],
        "winner_name": ["Alpha", "Beta", "Gamma"], "winner_name_std": ["ALPHA", "BETA", "GAMMA"],
        "winner_country": ["PL", "PL", "DE"], "winner_is_sme": [True, False, True], "buyer_key": [1, 1, 2],
    })
    assert set(AWARD_COLUMNS) <= set(awards.columns)
    awards.to_parquet(tmp_path / "awards.parquet")
    pd.DataFrame({"buyer_key": [1, 2], "buyer_name": ["City of Krakow", "Bund"],
                  "buyer_country": ["PL", "DE"]}).to_parquet(tmp_path / "dim_buyer.parquet")
    (tmp_path / "models").mkdir()
    return tmp_path


def test_connect_exposes_the_tables_the_tools_use(bundle):
    connection = app_data.connect(bundle)
    assert connection.sql("SELECT COUNT(*) FROM ted_awards").fetchone()[0] == 3
    assert connection.sql("SELECT COUNT(*) FROM fact_award").fetchone()[0] == 3
    assert connection.sql("SELECT buyer_name FROM dim_buyer WHERE buyer_key = 1").fetchone()[0] == "City of Krakow"
    assert config.MODELS_DIR == bundle / "models"


def test_download_bundle_unzips_once(tmp_path, monkeypatch):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("awards.parquet", b"placeholder")
    calls = []

    class Response:
        content = archive.getvalue()

        def raise_for_status(self):
            pass

    monkeypatch.setattr(app_data.requests, "get", lambda url, timeout: calls.append(url) or Response())
    target = tmp_path / "bundle"
    app_data.download_bundle("https://example.org/bundle.zip", target)
    app_data.download_bundle("https://example.org/bundle.zip", target)
    assert (target / "awards.parquet").exists()
    assert calls == ["https://example.org/bundle.zip"]   # the second call reuses the files


@pytest.fixture()
def client(bundle):
    connection = app_data.connect(bundle)
    api.app.dependency_overrides[api.get_cursor] = lambda: connection.cursor()
    yield TestClient(api.app)
    api.app.dependency_overrides.clear()


def test_api_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_api_market(client):
    response = client.post("/market", json={"cpv_codes": ["45314"], "country": "pl"})
    assert response.status_code == 200
    assert response.json()["contracts_awarded"] == "2"


def test_api_rejects_invalid_input(client):
    assert client.post("/market", json={"cpv_codes": ["999"]}).status_code == 422
    assert client.post("/market", json={"cpv_codes": []}).status_code == 422
    assert client.post("/price", json={"cpv_group": "453", "country": "PL", "contract_type": "Goods"}).status_code == 422


def test_web_app_market_page_runs(bundle, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(app_data, "download_bundle", lambda: bundle)
    app = AppTest.from_file(str(config.PROJECT_ROOT / "streamlit_app.py"), default_timeout=60)
    app.run()
    assert not app.exception
    assert app.title[0].value == "Market explorer"
    app.button[0].click().run()   # default search: IT services (72), all countries
    assert not app.exception
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Contracts awarded"] == "1"
