"""
BIS (Bank for International Settlements) SDMX v2 REST API 모듈
https://stats.bis.org/api-doc/v2/

글로벌 금융·거시 데이터: CPI, 정책금리, 신용, 부동산, 실효환율, DSR 등
인증 불필요 (무료 공개)
"""

import requests
import pandas as pd
import io
import time

BASE_URL = "https://stats.bis.org/api/v2"

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
}


def _fetch_csv(url: str, params: dict = None) -> pd.DataFrame:
    """BIS API CSV 응답을 DataFrame으로 변환"""
    if params is None:
        params = {}
    params["format"] = "csv"
    params["detail"] = "dataonly"

    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()

    text = resp.text.strip()
    if not text:
        return pd.DataFrame()

    df = pd.read_csv(io.StringIO(text))
    if "OBS_VALUE" in df.columns:
        df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
    return df


def _build_url(dataflow: str, version: str, key: str = "") -> str:
    """BIS SDMX v2 데이터 URL 생성"""
    url = f"{BASE_URL}/data/dataflow/BIS/{dataflow}/{version}"
    if key:
        url += f"/{key}"
    return url


def get_data(dataflow: str, version: str, key: str = "",
             start_period: str = None, end_period: str = None) -> pd.DataFrame:
    """
    BIS SDMX 데이터 조회 (범용)

    Parameters:
        dataflow:     데이터플로우 ID (예: "WS_LONG_CPI")
        version:      버전 (예: "1.0")
        key:          차원 필터 (예: "M.KR+US")
        start_period: 시작기간 (예: "2020-01")
        end_period:   종료기간

    Returns:
        DataFrame (CSV 파싱 결과)
    """
    url = _build_url(dataflow, version, key)
    params = {}
    if start_period:
        params["startPeriod"] = start_period
    if end_period:
        params["endPeriod"] = end_period

    return _fetch_csv(url, params)


# ── 편의 함수: 소비자물가 (CPI) ────────────────────────────────────

def get_cpi(countries: str = "KR+US+JP+DE+GB+FR",
            start: str = "2007-01", end: str = None,
            unit: str = None) -> pd.DataFrame:
    """
    소비자물가지수 (Long Consumer Prices)

    UNIT_MEASURE:
        628 = Index (2010=100)
        771 = Year-on-year changes (%)

    Parameters:
        countries: 국가 코드 (+로 연결, ISO 2자리)
        start:     시작기간 (YYYY-MM)
        end:       종료기간
        unit:      "628" (지수) 또는 "771" (전년비%). None이면 둘 다.

    Returns:
        DataFrame [FREQ, REF_AREA, UNIT_MEASURE, TIME_PERIOD, OBS_VALUE]
    """
    if unit:
        key = f"M.{countries}.{unit}"
    else:
        key = f"M.{countries}"
    return get_data("WS_LONG_CPI", "1.0", key, start, end)


def get_cpi_yoy(countries: str = "KR+US+JP+DE+GB+FR",
                start: str = "2007-01", end: str = None) -> pd.DataFrame:
    """CPI 전년동월비 (%) 전용"""
    return get_cpi(countries, start, end, unit="771")


def get_cpi_index(countries: str = "KR+US+JP+DE+GB+FR",
                  start: str = "2007-01", end: str = None) -> pd.DataFrame:
    """CPI 지수 (2010=100) 전용"""
    return get_cpi(countries, start, end, unit="628")


# ── 편의 함수: 정책금리 ───────────────────────────────────────────

def get_policy_rate(countries: str = "KR+US+JP+DE+GB+FR",
                    start: str = "2007-01", end: str = None) -> pd.DataFrame:
    """
    중앙은행 정책금리 (Central Bank Policy Rates)

    Returns:
        DataFrame [FREQ, REF_AREA, TIME_PERIOD, OBS_VALUE]
    """
    key = f"M.{countries}"
    return get_data("WS_CBPOL", "1.0", key, start, end)


# ── 편의 함수: 총 신용 ────────────────────────────────────────────

def get_total_credit(countries: str = "KR+US+JP+DE+GB+FR",
                     start: str = "2007-Q1", end: str = None,
                     borrower: str = "P",
                     unit: str = "770") -> pd.DataFrame:
    """
    총 신용 (Total Credit to the Non-Financial Sector)

    Parameters:
        borrower: 차입자 구분
            P = 민간 비금융부문 전체
            H = 가계
            N = 비금융기업
            G = 정부
            C = 핵심 부채 (P+G)
        unit: 단위
            770 = GDP 대비 (%)
            XDC = 현지통화 (십억)
            USD = 미달러 (십억)

    Returns:
        DataFrame [FREQ, BORROWERS_CTY, TC_BORROWERS, TC_LENDERS, VALUATION,
                   UNIT_TYPE, TC_ADJUST, TIME_PERIOD, OBS_VALUE]
    """
    key = f"Q.{countries}.{borrower}.A.M.{unit}.A"
    return get_data("WS_TC", "2.0", key, start, end)


def get_credit_to_gdp(countries: str = "KR+US+JP+DE+GB+FR",
                      start: str = "2007-Q1", end: str = None,
                      borrower: str = "P") -> pd.DataFrame:
    """민간 신용/GDP (%) 전용"""
    return get_total_credit(countries, start, end, borrower, unit="770")


# ── 편의 함수: 신용/GDP 갭 ────────────────────────────────────────

def get_credit_gap(countries: str = "KR+US+JP+DE+GB+FR",
                   start: str = "2007-Q1", end: str = None) -> pd.DataFrame:
    """
    신용/GDP 갭 (Credit-to-GDP Gap)
    - 바젤III 경기대응완충자본 기준 지표

    CG_DTYPE:
        A = 신용/GDP 비율 (추세)
        B = 신용/GDP 비율 (실제)
        C = 갭 (실제 - 추세, %p)

    Returns:
        DataFrame [FREQ, BORROWERS_CTY, TC_BORROWERS, TC_LENDERS,
                   CG_DTYPE, TIME_PERIOD, OBS_VALUE]
    """
    key = f"Q.{countries}"
    return get_data("WS_CREDIT_GAP", "1.0", key, start, end)


# ── 편의 함수: 부동산 가격 ────────────────────────────────────────

def get_property_prices(countries: str = "KR+US+JP+DE+GB+FR",
                        start: str = "2007-Q1", end: str = None,
                        value_type: str = None) -> pd.DataFrame:
    """
    주택가격지수 (Selected Property Prices)

    VALUE:
        R = 실질 (Real)
        N = 명목 (Nominal)

    UNIT_MEASURE:
        628 = Index (2010=100)
        771 = Year-on-year changes (%)

    Returns:
        DataFrame [FREQ, REF_AREA, VALUE, UNIT_MEASURE, TIME_PERIOD, OBS_VALUE]
    """
    if value_type:
        key = f"Q.{countries}.{value_type}"
    else:
        key = f"Q.{countries}"
    return get_data("WS_SPP", "1.0", key, start, end)


# ── 편의 함수: 실효환율 ───────────────────────────────────────────

def get_effective_exchange_rate(countries: str = "KR+US+JP+DE+GB+FR",
                                start: str = "2007-01",
                                end: str = None,
                                eer_type: str = None) -> pd.DataFrame:
    """
    실효환율 (Effective Exchange Rates)

    EER_TYPE:
        R = 실질실효환율 (Real)
        N = 명목실효환율 (Nominal)

    Returns:
        DataFrame [FREQ, EER_TYPE, EER_BASKET, REF_AREA, TIME_PERIOD, OBS_VALUE]
    """
    if eer_type:
        key = f"M.{eer_type}.N.{countries}"
    else:
        key = f"M..N.{countries}"
    return get_data("WS_EER", "1.0", key, start, end)


# ── 편의 함수: 원리금상환비율 (DSR) ────────────────────────────────

def get_debt_service_ratio(countries: str = "KR+US+JP+DE+GB+FR",
                           start: str = "2007-Q1",
                           end: str = None) -> pd.DataFrame:
    """
    원리금상환비율 (Debt Service Ratios)

    DSR_BORROWERS:
        P = 민간 비금융부문
        H = 가계
        N = 비금융기업

    Returns:
        DataFrame [FREQ, BORROWERS_CTY, DSR_BORROWERS, TIME_PERIOD, OBS_VALUE]
    """
    key = f"Q.{countries}"
    return get_data("WS_DSR", "1.0", key, start, end)


# ── 데이터플로우 목록 사전 ─────────────────────────────────────────

DATAFLOWS = {
    "CPI":                ("WS_LONG_CPI",    "1.0", "소비자물가지수"),
    "policy_rate":        ("WS_CBPOL",       "1.0", "중앙은행 정책금리"),
    "total_credit":       ("WS_TC",          "2.0", "비금융부문 총 신용"),
    "credit_gap":         ("WS_CREDIT_GAP",  "1.0", "신용/GDP 갭"),
    "property_prices":    ("WS_SPP",         "1.0", "주택가격지수"),
    "effective_fx":       ("WS_EER",         "1.0", "실효환율"),
    "debt_service_ratio": ("WS_DSR",         "1.0", "원리금상환비율"),
}


def list_dataflows() -> pd.DataFrame:
    """사용 가능한 데이터플로우 목록"""
    rows = []
    for name, (df_id, ver, desc) in DATAFLOWS.items():
        rows.append({"name": name, "dataflow": df_id, "version": ver, "description": desc})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("=" * 60)
    print("BIS SDMX API 테스트")
    print("=" * 60)

    # 1) CPI 전년비
    print("\n[1] CPI 전년비 (한·미·일, 2023~)")
    try:
        df = get_cpi_yoy("KR+US+JP", start="2023-01")
        if not df.empty:
            cols = [c for c in ["REF_AREA", "TIME_PERIOD", "OBS_VALUE"] if c in df.columns]
            print(df[cols].tail(12).to_string(index=False))
        else:
            print("  >> 데이터 없음")
    except Exception as e:
        print(f"  >> 오류: {e}")

    # 2) 정책금리
    print("\n[2] 중앙은행 정책금리 (한·미·일, 2023~)")
    try:
        df = get_policy_rate("KR+US+JP", start="2023-01")
        if not df.empty:
            cols = [c for c in ["REF_AREA", "TIME_PERIOD", "OBS_VALUE"] if c in df.columns]
            print(df[cols].tail(12).to_string(index=False))
        else:
            print("  >> 데이터 없음")
    except Exception as e:
        print(f"  >> 오류: {e}")

    # 3) 민간 신용/GDP
    print("\n[3] 민간 신용/GDP (한·미·일, 2023~)")
    try:
        df = get_credit_to_gdp("KR+US+JP", start="2023-Q1")
        if not df.empty:
            cols = [c for c in ["BORROWERS_CTY", "TIME_PERIOD", "OBS_VALUE"] if c in df.columns]
            print(df[cols].tail(12).to_string(index=False))
        else:
            print("  >> 데이터 없음")
    except Exception as e:
        print(f"  >> 오류: {e}")

    # 4) 주택가격
    print("\n[4] 주택가격지수 실질 (한·미·일, 2023~)")
    try:
        df = get_property_prices("KR+US+JP", start="2023-Q1", value_type="R")
        if not df.empty:
            cols = [c for c in ["REF_AREA", "UNIT_MEASURE", "TIME_PERIOD", "OBS_VALUE"]
                    if c in df.columns]
            print(df[cols].tail(12).to_string(index=False))
        else:
            print("  >> 데이터 없음")
    except Exception as e:
        print(f"  >> 오류: {e}")

    print("\n" + "=" * 60)
    print("사용 예시:")
    print("  from bis_api import get_cpi_yoy, get_policy_rate, get_credit_to_gdp")
    print('  df = get_cpi_yoy("KR+US+JP+DE", "2020-01")')
    print('  df = get_policy_rate("KR+US", "2020-01")')
    print('  df = get_credit_to_gdp("KR+US+CN", "2015-Q1")')
    print("=" * 60)
