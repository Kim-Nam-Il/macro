"""
FRED (Federal Reserve Economic Data) API 모듈
https://fred.stlouisfed.org/docs/api/fred/

미국 중심 거시경제 데이터: GDP, CPI, 고용, 금리 등
"""

import requests
import pandas as pd
import time

import os as _os
API_KEY = _os.environ.get("FRED_API_KEY", "")
# 키 파일 자동 로드
_key_file = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "fred_api_key.txt")
if not API_KEY and _os.path.exists(_key_file):
    API_KEY = open(_key_file).read().strip()
BASE_URL = "https://api.stlouisfed.org/fred"


def set_api_key(key: str):
    """FRED API 키 설정"""
    global API_KEY
    API_KEY = key


def _get(endpoint: str, params: dict = None) -> dict:
    """FRED API 기본 요청"""
    if params is None:
        params = {}
    params["api_key"] = API_KEY
    params["file_type"] = "json"

    url = f"{BASE_URL}/{endpoint}"
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "error_code" in data:
        raise Exception(f"[FRED {data['error_code']}] {data.get('error_message', '')}")

    return data


# ── 시계열 데이터 조회 ────────────────────────────────────────────

def get_series(series_id: str, start_date: str = None, end_date: str = None,
               frequency: str = None, units: str = None,
               sort_order: str = "asc") -> pd.DataFrame:
    """
    FRED 시계열 데이터 조회

    Parameters:
        series_id:   시리즈 ID (예: "GDP", "CPIAUCSL", "UNRATE")
        start_date:  시작일 (YYYY-MM-DD)
        end_date:    종료일 (YYYY-MM-DD)
        frequency:   주기 변환 (d/w/bw/m/q/sa/a)
        units:       단위 변환 (lin/chg/ch1/pch/pc1/pca/cch/cca/log)
                     lin=원본, chg=전기차, pch=전기비(%), pc1=전년비(%), pca=연율(%)
        sort_order:  정렬 (asc/desc)

    Returns:
        DataFrame [date, value, series_id]
    """
    params = {
        "series_id": series_id,
        "sort_order": sort_order,
    }
    if start_date:
        params["observation_start"] = start_date
    if end_date:
        params["observation_end"] = end_date
    if frequency:
        params["frequency"] = frequency
    if units:
        params["units"] = units

    data = _get("series/observations", params)
    obs = data.get("observations", [])
    if not obs:
        return pd.DataFrame()

    df = pd.DataFrame(obs)
    df = df[["date", "value"]].copy()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    df["series_id"] = series_id
    return df


def get_series_info(series_id: str) -> dict:
    """시리즈 메타데이터 조회"""
    data = _get("series", {"series_id": series_id})
    seriess = data.get("seriess", [])
    return seriess[0] if seriess else {}


def search_series(search_text: str, limit: int = 20) -> pd.DataFrame:
    """시리즈 키워드 검색"""
    data = _get("series/search", {
        "search_text": search_text,
        "limit": limit,
        "order_by": "popularity",
        "sort_order": "desc",
    })
    seriess = data.get("seriess", [])
    if not seriess:
        return pd.DataFrame()
    df = pd.DataFrame(seriess)
    cols = ["id", "title", "frequency_short", "units_short",
            "observation_start", "observation_end", "popularity"]
    return df[[c for c in cols if c in df.columns]]


def get_multi_series(series_ids: list, start_date: str = None,
                     end_date: str = None, frequency: str = None,
                     delay: float = 0.2) -> pd.DataFrame:
    """
    여러 시리즈를 한번에 조회 → long format DataFrame

    Returns:
        DataFrame [date, value, series_id]
    """
    frames = []
    for sid in series_ids:
        df = get_series(sid, start_date, end_date, frequency)
        if not df.empty:
            frames.append(df)
        time.sleep(delay)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def get_multi_series_wide(series_ids: list, start_date: str = None,
                          end_date: str = None, frequency: str = None,
                          delay: float = 0.2) -> pd.DataFrame:
    """
    여러 시리즈 → wide format (date를 index, 각 시리즈가 컬럼)
    """
    long = get_multi_series(series_ids, start_date, end_date, frequency, delay)
    if long.empty:
        return pd.DataFrame()
    wide = long.pivot(index="date", columns="series_id", values="value")
    wide = wide[series_ids]  # 원래 순서 유지
    return wide


# ── 주요 시리즈 ID 사전 ──────────────────────────────────────────

SERIES = {
    # ── GDP / 성장 ──
    "GDP_nominal":          "GDP",         # 명목 GDP (분기, 연율, 십억달러)
    "GDP_real":             "GDPC1",       # 실질 GDP (분기, 연율, 2017=100)
    "GDP_growth_rate":      "A191RL1Q225SBEA",  # 실질 GDP 성장률 (분기, 연율, %)
    "GDP_deflator":         "GDPDEF",      # GDP 디플레이터

    # ── 물가 ──
    "CPI_all":              "CPIAUCSL",    # CPI 전체 (월별, 계절조정)
    "CPI_core":             "CPILFESL",    # Core CPI (식품·에너지 제외, 월별)
    "CPI_yoy":              "CPIAUCSL",    # CPI (전년비는 units="pc1"로 요청)
    "PCE_deflator":         "PCEPI",       # PCE 물가지수 (월별)
    "PCE_core":             "PCEPILFE",    # Core PCE (월별)
    "PPI_all":              "PPIACO",      # 생산자물가 전체 (월별)

    # ── 고용 ──
    "unemployment_rate":    "UNRATE",      # 실업률 (월별, %)
    "nonfarm_payrolls":     "PAYEMS",      # 비농업 고용자 수 (월별, 천명)
    "labor_force_rate":     "CIVPART",     # 경제활동참가율 (월별, %)
    "avg_hourly_earnings":  "CES0500000003",  # 평균 시급 (월별)
    "initial_claims":       "ICSA",        # 신규 실업수당 청구 (주별)
    "job_openings":         "JTSJOL",      # 구인건수 JOLTS (월별, 천건)

    # ── 금리 ──
    "fed_funds_rate":       "FEDFUNDS",    # 연방기금금리 (월별)
    "fed_funds_effective":  "DFF",         # 연방기금 실효금리 (일별)
    "treasury_10y":         "DGS10",       # 10년물 국채수익률 (일별)
    "treasury_2y":          "DGS2",        # 2년물 국채수익률 (일별)
    "treasury_3m":          "DTB3",        # 3개월물 T-Bill (일별)
    "term_spread_10y2y":    "T10Y2Y",      # 장단기 스프레드 10Y-2Y (일별)

    # ── 통화/금융 ──
    "m2":                   "M2SL",        # M2 통화량 (월별)
    "monetary_base":        "BOGMBASE",    # 본원통화 (월별)
    "sp500":                "SP500",       # S&P 500 (일별)
    "vix":                  "VIXCLS",      # VIX (일별)

    # ── 기타 거시 ──
    "industrial_production": "INDPRO",     # 산업생산지수 (월별)
    "retail_sales":          "RSXFS",      # 소매판매 (월별, 식품서비스 제외)
    "housing_starts":        "HOUST",      # 주택착공 (월별)
    "trade_balance":         "BOPGSTB",    # 무역수지 (월별)
    "consumer_sentiment":    "UMCSENT",    # 미시건 소비자심리지수 (월별)
    "leading_index":         "USSLIND",    # 경기선행지수 (월별)
}


if __name__ == "__main__":
    print("=" * 60)
    print("FRED API 테스트")
    print("=" * 60)

    if API_KEY == "YOUR_FRED_API_KEY":
        print("\n[!] API 키를 설정하세요:")
        print("    from fred_api import set_api_key")
        print('    set_api_key("YOUR_KEY_HERE")')
        print("\n    무료 발급: https://fred.stlouisfed.org/docs/api/api_key.html")
    else:
        # 실질 GDP 성장률
        print("\n[1] 실질 GDP 성장률 (분기, 2020~)")
        df = get_series("A191RL1Q225SBEA", "2020-01-01")
        if not df.empty:
            print(df.tail(10).to_string(index=False))

        # CPI 전년비
        print("\n[2] CPI 전년동월비 (2020~)")
        df = get_series("CPIAUCSL", "2020-01-01", units="pc1")
        if not df.empty:
            print(df.tail(12).to_string(index=False))

        # 실업률
        print("\n[3] 실업률 (2020~)")
        df = get_series("UNRATE", "2020-01-01")
        if not df.empty:
            print(df.tail(12).to_string(index=False))

    print("\n" + "=" * 60)
    print("사용 예시:")
    print("  from fred_api import get_series, get_multi_series_wide, SERIES")
    print('  set_api_key("YOUR_KEY")')
    print('  df = get_series("GDPC1", "2020-01-01")')
    print('  panel = get_multi_series_wide(["GDPC1","CPIAUCSL","UNRATE"], "2020-01-01")')
    print("=" * 60)
