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


def _fetch_quote_for_symbol(symbol: str):
    # Free plans may block bulk quote endpoints; fetch per-symbol and fallback.
    price = None
    change_pct = None

    short_resp = requests.get(
        f"{V3_BASE_URL}/quote-short/{symbol}",
        params={"apikey": FMP_API_KEY},
        timeout=15,
    )
    if short_resp.status_code == 200:
        short_payload = short_resp.json()
        if isinstance(short_payload, list) and short_payload:
            price = short_payload[0].get("price")

    quote_resp = requests.get(
        f"{V3_BASE_URL}/quote/{symbol}",
        params={"apikey": FMP_API_KEY},
        timeout=15,
    )
    if quote_resp.status_code == 200:
        quote_payload = quote_resp.json()
        if isinstance(quote_payload, list) and quote_payload:
            change_pct = quote_payload[0].get("changesPercentage")
            if price is None:
                price = quote_payload[0].get("price")

    return {
        "price": price,
        "changePercentage": change_pct,
    }


def _fetch_stock_detail(symbol: str):
    upper_symbol = symbol.upper()
    detail = {
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

    short_resp = requests.get(
        f"{V3_BASE_URL}/quote-short/{upper_symbol}",
        params={"apikey": FMP_API_KEY},
        timeout=15,
    )
    if short_resp.status_code == 200:
        short_payload = short_resp.json()
        if isinstance(short_payload, list) and short_payload:
            detail["price"] = short_payload[0].get("price")

    quote_resp = requests.get(
        f"{V3_BASE_URL}/quote/{upper_symbol}",
        params={"apikey": FMP_API_KEY},
        timeout=15,
    )
    if quote_resp.status_code == 200:
        quote_payload = quote_resp.json()
        if isinstance(quote_payload, list) and quote_payload:
            quote = quote_payload[0]
            detail["name"] = quote.get("name") or detail["name"]
            detail["price"] = quote.get("price") if quote.get("price") is not None else detail["price"]
            detail["changePercentage"] = quote.get("changesPercentage")
            detail["open"] = quote.get("open")
            detail["dayHigh"] = quote.get("dayHigh")
            detail["dayLow"] = quote.get("dayLow")
            detail["previousClose"] = quote.get("previousClose")
            detail["volume"] = quote.get("volume")

    return detail


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

    if not rows:
        return []

    merged = []
    for row in rows:
        q = _fetch_quote_for_symbol(row["symbol"])
        merged.append(
            {
                "symbol": row["symbol"],
                "name": row["name"],
                "price": q.get("price"),
                "changePercentage": q.get("changePercentage"),
            }
        )

    return merged


@app.get("/stock/{symbol}")
def get_stock(symbol: str):
    return _fetch_stock_detail(symbol)
