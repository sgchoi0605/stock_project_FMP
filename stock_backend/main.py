from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 출처 허용 (개발용)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FMP_API_KEY = "3DTD9chU2BpaqCprot3odMaHLsP6MaKb"
BASE_URL = "https://financialmodelingprep.com/stable"


@app.get("/financials/{symbol}")
def get_financials(symbol: str):
    url = f"{BASE_URL}/income-statement"
    params = {
        "symbol": symbol,
        "apikey": FMP_API_KEY,
        "limit": 5
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"FMP API Error: {response.status_code} - {response.text}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch data from FMP: {response.text}"
        )

    return response.json()

#   실행 : cd stock_backend 후 uvicorn main:app --reload
