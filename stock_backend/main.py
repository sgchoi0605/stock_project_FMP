from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
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


def _to_number(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        normalized = value.replace(",", "").strip()
        try:
            return float(normalized)
        except ValueError:
            return None
    return None


def _first_numeric(value):
    if isinstance(value, list):
        for item in value:
            num = _to_number(item)
            if num is not None:
                return num
        return None
    return _to_number(value)


def _parse_fmp_date(raw):
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    for fmt in ("%b. %d, %Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


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


def _extract_income_row_from_report(report: dict):
    revenue = None
    gross_profit = None
    operating_income = None
    net_income = None
    report_date = None

    annual_mode = False

    # Prefer the primary statements-of-operations section to avoid YTD duplicates.
    target_section = None
    for key, value in report.items():
        if not isinstance(value, list):
            continue
        key_lower = str(key).lower()
        if "statemen" not in key_lower:
            continue
        if not any(isinstance(row, dict) for row in value):
            continue
        for row in value:
            if not isinstance(row, dict):
                continue
            row_key = str(next(iter(row.keys()), "")).lower()
            if "operations" in row_key:
                target_section = value
                break
        if target_section is not None:
            break

    sections = [target_section] if target_section is not None else [v for v in report.values() if isinstance(v, list)]

    for section in sections:
        for row in section:
            if not isinstance(row, dict):
                continue
            for key, raw_val in row.items():
                lowered = str(key).strip().lower()
                if lowered == "items" and isinstance(raw_val, list) and raw_val:
                    parsed_date = _parse_fmp_date(raw_val[0])
                    if parsed_date:
                        report_date = parsed_date
                    if len(raw_val) >= 3:
                        annual_mode = True
                    continue

                num = _first_numeric(raw_val)
                if num is None:
                    continue

                if revenue is None and ("net sales" in lowered or lowered in {"revenue", "total revenue"}):
                    revenue = num
                elif gross_profit is None and ("gross margin" in lowered or "gross profit" in lowered):
                    gross_profit = num
                elif operating_income is None and "operating income" in lowered:
                    operating_income = num
                elif net_income is None and lowered == "net income":
                    net_income = num

    if not report_date:
        year = str(report.get("year") or "").strip()
        period = str(report.get("period") or "").strip().upper()
        quarter_to_date = {
            "Q1": "-03-31",
            "Q2": "-06-30",
            "Q3": "-09-30",
            "Q4": "-12-31",
        }
        if year and period in quarter_to_date:
            report_date = f"{year}{quarter_to_date[period]}"

    if not report_date:
        return None, False

    if all(v is None for v in [revenue, gross_profit, operating_income, net_income]):
        return None, False

    return {
        "date": report_date,
        "calendarYear": report.get("year"),
        "period": report.get("period"),
        "revenue": revenue,
        "grossProfit": gross_profit,
        "operatingIncome": operating_income,
        "netIncome": net_income,
    }, annual_mode


def _fetch_financial_report_row(symbol: str, year: int, quarter: int):
    period = f"Q{quarter}"
    try:
        response = requests.get(
            f"{BASE_URL}/financial-reports-json",
            params={"symbol": symbol, "year": str(year), "period": period, "apikey": FMP_API_KEY},
            timeout=15,
        )
    except requests.RequestException:
        return None, False

    if response.status_code != 200:
        return None, False

    try:
        report = response.json()
    except ValueError:
        return None, False
    if not isinstance(report, dict):
        return None, False

    row, annual_mode = _extract_income_row_from_report(report)
    if not row:
        return None, False
    return _normalize_income_units(row), annual_mode


def _quarter_from_date(date_text: str):
    dt = datetime.strptime(date_text, "%Y-%m-%d")
    return dt.year, ((dt.month - 1) // 3) + 1


def _previous_quarter(year: int, quarter: int):
    if quarter == 1:
        return year - 1, 4
    return year, quarter - 1


def _build_missing_quarters(oldest_date: str, count: int):
    year, quarter = _quarter_from_date(oldest_date)
    out = []
    for _ in range(count):
        year, quarter = _previous_quarter(year, quarter)
        out.append((year, quarter))
    return out


def _period_to_quarter(period_value):
    text = str(period_value or "").strip().upper()
    if text in {"Q1", "Q2", "Q3", "Q4"}:
        return int(text[1])
    return None


def _build_missing_fiscal_quarters(calendar_year_value, period_value, count: int):
    try:
        year = int(str(calendar_year_value))
    except ValueError:
        return []
    quarter = _period_to_quarter(period_value)
    if quarter is None:
        return []

    out = []
    for _ in range(count):
        if quarter == 1:
            year -= 1
            quarter = 4
        else:
            quarter -= 1
        out.append((year, quarter))
    return out


def _normalize_income_units(row: dict):
    revenue = row.get("revenue")
    if revenue is None:
        return row
    # financial-reports-json is often in millions; stable income-statement is in full units.
    if abs(revenue) < 10_000_000:
        for key in ("revenue", "grossProfit", "operatingIncome", "netIncome"):
            value = row.get(key)
            if value is not None:
                row[key] = value * 1_000_000
    return row


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
        try:
            response = requests.get(url, params=params, timeout=15)
        except requests.RequestException:
            continue
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
        try:
            profile_resp = requests.get(
                f"{V3_BASE_URL}/profile/{upper_symbol}",
                params={"apikey": FMP_API_KEY},
                timeout=15,
            )
            if profile_resp.status_code == 200:
                profile = _first_row(profile_resp.json())
                if profile:
                    snapshot["name"] = profile.get("companyName") or profile.get("name") or snapshot["name"]
        except requests.RequestException:
            pass

    return snapshot


def _try_symbol_search(query: str, limit: int):
    candidates = [
        ("search-symbol", {"query": query, "limit": limit}),
        ("search-name", {"query": query, "limit": limit}),
        ("search-ticker", {"query": query, "limit": limit}),
    ]

    for path, params in candidates:
        try:
            response = requests.get(
                f"{BASE_URL}/{path}",
                params={**params, "apikey": FMP_API_KEY},
                timeout=15,
            )
        except requests.RequestException:
            continue
        if response.status_code == 200:
            payload = response.json()
            if isinstance(payload, list):
                return payload
    return []


def _try_symbol_search_v3(query: str, limit: int):
    try:
        response = requests.get(
            f"{V3_BASE_URL}/search-ticker",
            params={"query": query, "limit": limit, "apikey": FMP_API_KEY},
            timeout=15,
        )
    except requests.RequestException:
        return []
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


def _fetch_stock_detail(symbol: str):
    return _fetch_quote_snapshot(symbol)


@app.get("/financials/{symbol}")
def get_financials(symbol: str):
    upper_symbol = symbol.upper()
    rows = []
    report_cache = {}

    def fetch_report_cached(year: int, quarter: int):
        key = (year, quarter)
        if key not in report_cache:
            report_cache[key] = _fetch_financial_report_row(upper_symbol, year, quarter)
        return report_cache[key]

    try:
        response = requests.get(
            f"{BASE_URL}/income-statement",
            params={
                "symbol": upper_symbol,
                "period": "quarter",
                "limit": 5,
                "apikey": FMP_API_KEY,
            },
            timeout=15,
        )
        if response.status_code == 200:
            body = response.json()
            if isinstance(body, list):
                for item in body:
                    if not isinstance(item, dict):
                        continue
                    rows.append(
                        {
                            "date": item.get("date"),
                            "calendarYear": item.get("calendarYear") or item.get("fiscalYear"),
                            "period": item.get("period"),
                            "revenue": item.get("revenue"),
                            "grossProfit": item.get("grossProfit"),
                            "operatingIncome": item.get("operatingIncome"),
                            "netIncome": item.get("netIncome"),
                        }
                    )
    except requests.RequestException:
        pass

    rows = [row for row in rows if row.get("date")]
    rows.sort(key=lambda x: x["date"], reverse=True)
    dedup = {}
    for row in rows:
        dedup[row["date"]] = row
    rows = list(dedup.values())
    rows.sort(key=lambda x: x["date"], reverse=True)

    if rows and len(rows) < 8:
        existing_dates = {r["date"] for r in rows}
        missing_targets = _build_missing_fiscal_quarters(
            rows[-1].get("calendarYear"),
            rows[-1].get("period"),
            8 - len(rows),
        )
        if not missing_targets:
            missing_targets = _build_missing_quarters(rows[-1]["date"], 8 - len(rows))
        for target_year, target_quarter in missing_targets:
            extra_row, annual_mode = fetch_report_cached(target_year, target_quarter)
            if not extra_row:
                continue
            if extra_row.get("date") in existing_dates:
                continue

            if annual_mode and target_quarter == 4:
                q_rows = []
                for q in (1, 2, 3):
                    sub_row, _ = fetch_report_cached(target_year, q)
                    if not sub_row:
                        q_rows = []
                        break
                    q_rows.append(sub_row)
                if len(q_rows) == 3:
                    for metric in ("revenue", "grossProfit", "operatingIncome", "netIncome"):
                        annual_val = extra_row.get(metric)
                        if annual_val is None:
                            continue
                        parts = [q_row.get(metric) for q_row in q_rows]
                        if any(part is None for part in parts):
                            continue
                        extra_row[metric] = annual_val - sum(parts)

            rows.append(extra_row)
            existing_dates.add(extra_row["date"])

    rows.sort(key=lambda x: x["date"], reverse=True)
    return rows[:8]


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


# 실행 : cd stock_backend 후 uvicorn main:app --reload
