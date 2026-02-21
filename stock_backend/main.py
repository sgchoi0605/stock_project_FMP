from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FMP_API_KEY = "3DTD9chU2BpaqCprot3odMaHLsP6MaKb"
BASE_URL = "https://financialmodelingprep.com/stable"
V3_BASE_URL = "https://financialmodelingprep.com/api/v3"


def _first_row(payload):
    if isinstance(payload, list) and payload:
        row = payload[0]
        return row if isinstance(row, dict) else None
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list) and payload["data"]:
            row = payload["data"][0]
            return row if isinstance(row, dict) else None
        if payload.get("symbol"):
            return payload
    return None


def _fetch_quote_snapshot(symbol: str):
    upper_symbol = symbol.upper()
    snapshot = {
        "symbol": upper_symbol,
        "name": upper_symbol,
        "price": None,
        "changePercentage": None,
        "open": None,
        "dayHigh": None,
        "dayLow": None,
        "previousClose": None,
        "volume": None,
    }

    candidates = [
        (
            f"{BASE_URL}/quote",
            {"symbol": upper_symbol, "apikey": FMP_API_KEY},
        ),
        (
            f"{V3_BASE_URL}/quote/{upper_symbol}",
            {"apikey": FMP_API_KEY},
        ),
        (
            f"{V3_BASE_URL}/quote-short/{upper_symbol}",
            {"apikey": FMP_API_KEY},
        ),
    ]

    for url, params in candidates:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            continue

        row = _first_row(response.json())
        if not row:
            continue

        snapshot["name"] = row.get("name") or row.get("companyName") or snapshot["name"]
        snapshot["price"] = row.get("price") if row.get("price") is not None else snapshot["price"]
        snapshot["changePercentage"] = (
            row.get("changesPercentage")
            if row.get("changesPercentage") is not None
            else (row.get("changePercentage") if row.get("changePercentage") is not None else snapshot["changePercentage"])
        )
        snapshot["open"] = row.get("open") if row.get("open") is not None else snapshot["open"]
        snapshot["dayHigh"] = row.get("dayHigh") if row.get("dayHigh") is not None else snapshot["dayHigh"]
        snapshot["dayLow"] = row.get("dayLow") if row.get("dayLow") is not None else snapshot["dayLow"]
        snapshot["previousClose"] = (
            row.get("previousClose")
            if row.get("previousClose") is not None
            else snapshot["previousClose"]
        )
        snapshot["volume"] = row.get("volume") if row.get("volume") is not None else snapshot["volume"]

    if snapshot["name"] == upper_symbol:
        profile_resp = requests.get(
            f"{V3_BASE_URL}/profile/{upper_symbol}",
            params={"apikey": FMP_API_KEY},
            timeout=15,
        )
        if profile_resp.status_code == 200:
            profile = _first_row(profile_resp.json())
            if profile:
                snapshot["name"] = profile.get("companyName") or profile.get("name") or snapshot["name"]

    return snapshot


def _try_symbol_search(query: str, limit: int):
    candidates = [
        ("search-symbol", {"query": query, "limit": limit}),
        ("search-name", {"query": query, "limit": limit}),
        ("search-ticker", {"query": query, "limit": limit}),
    ]

    for path, params in candidates:
        response = requests.get(
            f"{BASE_URL}/{path}",
            params={**params, "apikey": FMP_API_KEY},
            timeout=15,
        )
        if response.status_code == 200:
            payload = response.json()
            if isinstance(payload, list):
                return payload
    return []


def _try_symbol_search_v3(query: str, limit: int):
    response = requests.get(
        f"{V3_BASE_URL}/search-ticker",
        params={"query": query, "limit": limit, "apikey": FMP_API_KEY},
        timeout=15,
    )
    if response.status_code != 200:
        return []

    payload = response.json()
    return payload if isinstance(payload, list) else []


def _is_us_listing(item: dict):
    country = (item.get("country") or "").strip().upper()
    if country in {"US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"}:
        return True

    exchange = (item.get("exchangeShortName") or item.get("exchange") or "").strip().upper()
    us_exchanges = {
        "NASDAQ",
        "NYSE",
        "AMEX",
        "ARCA",
        "BATS",
        "CBOE",
        "IEX",
    }
    return exchange in us_exchanges


def _fetch_quote_for_symbol(symbol: str):
    quote = _fetch_quote_snapshot(symbol)
    return {
        "price": quote.get("price"),
        "changePercentage": quote.get("changePercentage"),
    }


def _fetch_stock_detail(symbol: str):
    return _fetch_quote_snapshot(symbol)


@app.get("/financials/{symbol}")
def get_financials(symbol: str):
    url = f"{BASE_URL}/income-statement"
    params = {
        "symbol": symbol,
        "apikey": FMP_API_KEY,
        "limit": 5,
    }

    response = requests.get(url, params=params, timeout=15)

    if response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch data from FMP: {response.text}",
        )

    return response.json()


@app.get("/search-stocks/{query}")
def search_stocks(query: str, limit: int = 20):
    search_results = _try_symbol_search(query=query, limit=limit)
    if not search_results:
        search_results = _try_symbol_search_v3(query=query, limit=limit)
    if not search_results:
        return []

    seen = set()
    rows = []
    for item in search_results:
        if not _is_us_listing(item):
            continue
        symbol = (item.get("symbol") or item.get("ticker") or "").upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        rows.append(
            {
                "symbol": symbol,
                "name": item.get("name") or symbol,
            }
        )
        if len(rows) >= limit:
            break

    return rows


@app.get("/stock/{symbol}")
def get_stock(symbol: str):
    return _fetch_stock_detail(symbol)


#   실행 : cd stock_backend 후 uvicorn main:app --reload


