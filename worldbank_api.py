"""
World Bank Open Data API v2 모듈
https://api.worldbank.org/v2/

200+ 국가 거시·개발 데이터: GDP, CPI, 실업률, 인구, 무역, 재정 등
인증 불필요 (무료 공개)
"""

import requests
import pandas as pd
import time

BASE_URL = "https://api.worldbank.org/v2"

# ── 주요 국가 코드 (ISO 2자리) ────────────────────────────────────
COUNTRIES = {
    "KR": "한국",
    "US": "미국",
    "JP": "일본",
    "DE": "독일",
    "GB": "영국",
    "FR": "프랑스",
    "CN": "중국",
    "IT": "이탈리아",
    "CA": "캐나다",
    "AU": "호주",
    "MX": "멕시코",
    "BR": "브라질",
    "IN": "인도",
    "ID": "인도네시아",
    "TR": "튀르키예",
    "RU": "러시아",
    "ZA": "남아프리카",
    "SA": "사우디아라비아",
    "AR": "아르헨티나",
    "NG": "나이지리아",
}

# ── 주요 지표 코드 사전 ────────────────────────────────────────────
INDICATORS = {
    # ── GDP / 성장 ──
    "GDP_current_usd":         "NY.GDP.MKTP.CD",      # GDP (경상 US$)
    "GDP_growth":              "NY.GDP.MKTP.KD.ZG",    # GDP 성장률 (연간 %)
    "GDP_per_capita":          "NY.GDP.PCAP.CD",       # 1인당 GDP (경상 US$)
    "GDP_per_capita_ppp":      "NY.GDP.PCAP.PP.CD",    # 1인당 GDP PPP (경상 국제$)
    "GDP_ppp":                 "NY.GDP.MKTP.PP.CD",    # GDP PPP (경상 국제$)
    "GNI_per_capita":          "NY.GNP.PCAP.CD",       # 1인당 GNI (경상 US$)
    "GNI_per_capita_ppp":      "NY.GNP.PCAP.PP.CD",    # 1인당 GNI PPP

    # ── 물가 ──
    "CPI_inflation":           "FP.CPI.TOTL.ZG",       # 소비자물가 상승률 (연간 %)
    "GDP_deflator":            "NY.GDP.DEFL.KD.ZG",    # GDP 디플레이터 (연간 %)

    # ── 고용 ──
    "unemployment":            "SL.UEM.TOTL.ZS",       # 실업률 (ILO 기준, %)
    "unemployment_youth":      "SL.UEM.1524.ZS",       # 청년실업률 (15-24세, %)
    "labor_participation":     "SL.TLF.CACT.ZS",       # 경제활동참가율 (%)
    "employment_ratio":        "SL.EMP.TOTL.SP.ZS",    # 고용률 (15세 이상, %)

    # ── 인구 ──
    "population":              "SP.POP.TOTL",           # 총인구
    "population_growth":       "SP.POP.GROW",           # 인구증가율 (%)
    "urban_population_pct":    "SP.URB.TOTL.IN.ZS",    # 도시인구 비율 (%)
    "life_expectancy":         "SP.DYN.LE00.IN",        # 기대수명 (년)

    # ── 무역 / 국제수지 ──
    "trade_pct_gdp":           "NE.TRD.GNFS.ZS",       # 무역/GDP (%)
    "exports_pct_gdp":         "NE.EXP.GNFS.ZS",       # 수출/GDP (%)
    "imports_pct_gdp":         "NE.IMP.GNFS.ZS",       # 수입/GDP (%)
    "current_account_pct":     "BN.CAB.XOKA.GD.ZS",    # 경상수지/GDP (%)
    "fdi_net_inflows_pct":     "BX.KLT.DINV.WD.GD.ZS", # FDI 순유입/GDP (%)
    "remittances_pct_gdp":     "BX.TRF.PWKR.DT.GD.ZS", # 해외송금/GDP (%)

    # ── 재정 ──
    "govt_debt_pct_gdp":       "GC.DOD.TOTL.GD.ZS",    # 정부부채/GDP (%)
    "govt_revenue_pct_gdp":    "GC.REV.XGRT.GD.ZS",    # 정부수입/GDP (%)
    "govt_expense_pct_gdp":    "GC.XPN.TOTL.GD.ZS",    # 정부지출/GDP (%)
    "tax_revenue_pct_gdp":     "GC.TAX.TOTL.GD.ZS",    # 세수/GDP (%)

    # ── 금융 ──
    "broad_money_pct_gdp":     "FM.LBL.BMNY.GD.ZS",    # 광의통화(M2+)/GDP (%)
    "domestic_credit_pct_gdp": "FS.AST.DOMS.GD.ZS",    # 국내신용/GDP (%)
    "real_interest_rate":      "FR.INR.RINR",           # 실질금리 (%)
    "lending_interest_rate":   "FR.INR.LEND",           # 대출금리 (%)

    # ── 산업 / 구조 ──
    "industry_pct_gdp":        "NV.IND.TOTL.ZS",       # 제조업/GDP (%)
    "services_pct_gdp":        "NV.SRV.TOTL.ZS",       # 서비스업/GDP (%)
    "agriculture_pct_gdp":     "NV.AGR.TOTL.ZS",       # 농업/GDP (%)
    "high_tech_exports_pct":   "TX.VAL.TECH.MF.ZS",    # 하이테크 수출 비율 (%)

    # ── 기타 ──
    "co2_per_capita":          "EN.ATM.CO2E.PC",        # CO2 배출 (톤/인)
    "internet_users_pct":      "IT.NET.USER.ZS",        # 인터넷 이용률 (%)
    "gini_index":              "SI.POV.GINI",           # 지니계수
    "poverty_ratio":           "SI.POV.NAHC",           # 빈곤율 (국가기준, %)
}


def _get_json(url: str, params: dict = None) -> list:
    """World Bank API JSON 응답 파싱 (페이지네이션 처리)"""
    if params is None:
        params = {}
    params["format"] = "json"
    params.setdefault("per_page", 1000)

    all_data = []
    page = 1

    while True:
        params["page"] = page
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()

        result = resp.json()

        # World Bank API: [metadata, data] 형태
        if not isinstance(result, list) or len(result) < 2:
            break

        meta = result[0]
        data = result[1]

        if data is None:
            break

        all_data.extend(data)

        # 다음 페이지 확인
        total_pages = meta.get("pages", 1)
        if page >= total_pages:
            break
        page += 1

    return all_data


def get_indicator(indicator: str, countries: str = "all",
                  start_year: int = None, end_year: int = None) -> pd.DataFrame:
    """
    World Bank 지표 데이터 조회

    Parameters:
        indicator:   지표 코드 (예: "NY.GDP.MKTP.KD.ZG")
        countries:   국가 코드 (세미콜론 구분, ISO 2자리, 예: "KR;US;JP")
                     "all"이면 전체 국가
        start_year:  시작 연도
        end_year:    종료 연도

    Returns:
        DataFrame [country_id, country_name, indicator_id, indicator_name,
                   date, value]
    """
    url = f"{BASE_URL}/country/{countries}/indicator/{indicator}"
    params = {}
    if start_year and end_year:
        params["date"] = f"{start_year}:{end_year}"
    elif start_year:
        params["date"] = f"{start_year}:2030"
    elif end_year:
        params["date"] = f"1960:{end_year}"

    data = _get_json(url, params)
    if not data:
        return pd.DataFrame()

    rows = []
    for item in data:
        rows.append({
            "country_id": item.get("country", {}).get("id", ""),
            "country_name": item.get("country", {}).get("value", ""),
            "indicator_id": item.get("indicator", {}).get("id", ""),
            "indicator_name": item.get("indicator", {}).get("value", ""),
            "date": item.get("date", ""),
            "value": item.get("value"),
        })

    df = pd.DataFrame(rows)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = pd.to_numeric(df["date"], errors="coerce")
    df = df.sort_values(["country_id", "date"]).reset_index(drop=True)
    return df


def get_multi_indicators(indicators: list, countries: str = "all",
                         start_year: int = None, end_year: int = None,
                         delay: float = 0.3) -> pd.DataFrame:
    """
    여러 지표를 한번에 조회 → long format

    Returns:
        DataFrame [country_id, country_name, indicator_id, indicator_name,
                   date, value]
    """
    frames = []
    for ind in indicators:
        df = get_indicator(ind, countries, start_year, end_year)
        if not df.empty:
            frames.append(df)
        time.sleep(delay)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def get_indicator_wide(indicator: str, countries: str = "all",
                       start_year: int = None, end_year: int = None) -> pd.DataFrame:
    """
    단일 지표 → wide format (연도가 index, 국가가 컬럼)

    Returns:
        DataFrame (index=date, columns=country_id)
    """
    df = get_indicator(indicator, countries, start_year, end_year)
    if df.empty:
        return df
    wide = df.pivot(index="date", columns="country_id", values="value")
    wide.index.name = "year"
    return wide


# ── 편의 함수 ─────────────────────────────────────────────────────

def get_gdp_growth(countries: str = "KR;US;JP;DE;GB;FR;CN",
                   start_year: int = 2000) -> pd.DataFrame:
    """GDP 성장률 (연간 %)"""
    return get_indicator("NY.GDP.MKTP.KD.ZG", countries, start_year)


def get_gdp_current(countries: str = "KR;US;JP;DE;GB;FR;CN",
                    start_year: int = 2000) -> pd.DataFrame:
    """GDP (경상 US$)"""
    return get_indicator("NY.GDP.MKTP.CD", countries, start_year)


def get_gdp_per_capita(countries: str = "KR;US;JP;DE;GB;FR;CN",
                       start_year: int = 2000) -> pd.DataFrame:
    """1인당 GDP (경상 US$)"""
    return get_indicator("NY.GDP.PCAP.CD", countries, start_year)


def get_inflation(countries: str = "KR;US;JP;DE;GB;FR;CN",
                  start_year: int = 2000) -> pd.DataFrame:
    """소비자물가 상승률 (연간 %)"""
    return get_indicator("FP.CPI.TOTL.ZG", countries, start_year)


def get_unemployment(countries: str = "KR;US;JP;DE;GB;FR;CN",
                     start_year: int = 2000) -> pd.DataFrame:
    """실업률 (ILO 기준, %)"""
    return get_indicator("SL.UEM.TOTL.ZS", countries, start_year)


def get_population(countries: str = "KR;US;JP;DE;GB;FR;CN",
                   start_year: int = 2000) -> pd.DataFrame:
    """총인구"""
    return get_indicator("SP.POP.TOTL", countries, start_year)


def get_trade(countries: str = "KR;US;JP;DE;GB;FR;CN",
              start_year: int = 2000) -> pd.DataFrame:
    """무역/GDP (%)"""
    return get_indicator("NE.TRD.GNFS.ZS", countries, start_year)


def get_current_account(countries: str = "KR;US;JP;DE;GB;FR;CN",
                        start_year: int = 2000) -> pd.DataFrame:
    """경상수지/GDP (%)"""
    return get_indicator("BN.CAB.XOKA.GD.ZS", countries, start_year)


def get_govt_debt(countries: str = "KR;US;JP;DE;GB;FR;CN",
                  start_year: int = 2000) -> pd.DataFrame:
    """정부부채/GDP (%)"""
    return get_indicator("GC.DOD.TOTL.GD.ZS", countries, start_year)


# ── 유틸리티 ──────────────────────────────────────────────────────

def search_indicators(keyword: str, per_page: int = 50) -> pd.DataFrame:
    """지표 키워드 검색"""
    url = f"{BASE_URL}/indicator"
    params = {"format": "json", "per_page": per_page}

    data = _get_json(url, params)
    if not data:
        return pd.DataFrame()

    rows = []
    for item in data:
        name = item.get("name", "")
        if keyword.lower() in name.lower():
            rows.append({
                "id": item.get("id", ""),
                "name": name,
                "source": item.get("source", {}).get("value", ""),
            })

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def list_countries() -> pd.DataFrame:
    """사용 가능한 국가 목록"""
    url = f"{BASE_URL}/country"
    data = _get_json(url, {"per_page": 500})
    if not data:
        return pd.DataFrame()

    rows = []
    for item in data:
        rows.append({
            "id": item.get("id", ""),
            "name": item.get("name", ""),
            "region": item.get("region", {}).get("value", ""),
            "income_level": item.get("incomeLevel", {}).get("value", ""),
            "capital": item.get("capitalCity", ""),
        })

    return pd.DataFrame(rows)


def get_country_snapshot(country: str = "KR", start_year: int = 2015) -> pd.DataFrame:
    """
    국가별 주요 지표 한눈에 보기

    Returns:
        DataFrame [indicator, date, value]
    """
    key_indicators = [
        "NY.GDP.MKTP.CD",       # GDP
        "NY.GDP.MKTP.KD.ZG",    # GDP 성장률
        "NY.GDP.PCAP.CD",       # 1인당 GDP
        "FP.CPI.TOTL.ZG",       # 인플레이션
        "SL.UEM.TOTL.ZS",       # 실업률
        "SP.POP.TOTL",           # 인구
        "NE.TRD.GNFS.ZS",       # 무역/GDP
        "BN.CAB.XOKA.GD.ZS",    # 경상수지/GDP
        "GC.DOD.TOTL.GD.ZS",    # 정부부채/GDP
    ]

    df = get_multi_indicators(key_indicators, country, start_year)
    if df.empty:
        return df
    return df[["indicator_name", "date", "value"]].reset_index(drop=True)


if __name__ == "__main__":
    print("=" * 60)
    print("World Bank API 테스트")
    print("=" * 60)

    # 1) GDP 성장률
    print("\n[1] GDP 성장률 (한·미·일, 2020~)")
    df = get_gdp_growth("KR;US;JP", start_year=2020)
    if not df.empty:
        print(df[["country_id", "date", "value"]].to_string(index=False))

    # 2) 인플레이션
    print("\n[2] CPI 인플레이션 (한·미·일, 2020~)")
    df = get_inflation("KR;US;JP", start_year=2020)
    if not df.empty:
        print(df[["country_id", "date", "value"]].to_string(index=False))

    # 3) 실업률
    print("\n[3] 실업률 (한·미·일, 2020~)")
    df = get_unemployment("KR;US;JP", start_year=2020)
    if not df.empty:
        print(df[["country_id", "date", "value"]].to_string(index=False))

    print("\n" + "=" * 60)
    print("사용 예시:")
    print("  from worldbank_api import get_gdp_growth, get_inflation, INDICATORS")
    print('  df = get_gdp_growth("KR;US;JP;DE", 2010)')
    print('  df = get_indicator("NY.GDP.MKTP.CD", "KR;US", 2000, 2024)')
    print('  wide = get_indicator_wide("FP.CPI.TOTL.ZG", "KR;US;JP", 2010)')
    print("=" * 60)
