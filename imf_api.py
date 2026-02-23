"""
IMF DataMapper API 모듈
https://www.imf.org/external/datamapper/api/v1/

WEO(World Economic Outlook) 데이터: GDP, 인플레이션, 실업률, 재정, 경상수지 등
인증 불필요 (무료 공개, 연간 데이터)

국가 코드: ISO 3자리 (USA, KOR, JPN, DEU, GBR, FRA, CHN 등)
"""

import requests
import pandas as pd
import time

BASE_URL = "https://www.imf.org/external/datamapper/api/v1"

# ── 주요 국가 코드 (ISO 3자리) ────────────────────────────────────
COUNTRIES = {
    "KOR": "한국",
    "USA": "미국",
    "JPN": "일본",
    "DEU": "독일",
    "GBR": "영국",
    "FRA": "프랑스",
    "CHN": "중국",
    "ITA": "이탈리아",
    "CAN": "캐나다",
    "AUS": "호주",
    "MEX": "멕시코",
    "BRA": "브라질",
    "IND": "인도",
    "IDN": "인도네시아",
    "TUR": "튀르키예",
    "RUS": "러시아",
    "ZAF": "남아프리카",
    "SAU": "사우디아라비아",
    "ARG": "아르헨티나",
    "NGA": "나이지리아",
    "ESP": "스페인",
    "NLD": "네덜란드",
    "CHE": "스위스",
    "SWE": "스웨덴",
    "NOR": "노르웨이",
    "POL": "폴란드",
    "THA": "태국",
    "VNM": "베트남",
    "PHL": "필리핀",
    "MYS": "말레이시아",
    "TWN": "대만",
}

# ISO 2자리 → 3자리 변환
ISO2_TO_ISO3 = {
    "KR": "KOR", "US": "USA", "JP": "JPN", "DE": "DEU", "GB": "GBR",
    "FR": "FRA", "CN": "CHN", "IT": "ITA", "CA": "CAN", "AU": "AUS",
    "MX": "MEX", "BR": "BRA", "IN": "IND", "ID": "IDN", "TR": "TUR",
    "RU": "RUS", "ZA": "ZAF", "SA": "SAU", "AR": "ARG", "NG": "NGA",
    "ES": "ESP", "NL": "NLD", "CH": "CHE", "SE": "SWE", "NO": "NOR",
    "PL": "POL", "TH": "THA", "VN": "VNM", "PH": "PHL", "MY": "MYS",
    "TW": "TWN",
}

# ── 주요 지표 코드 ────────────────────────────────────────────────
INDICATORS = {
    # ── 성장 ──
    "NGDP_RPCH":    "실질 GDP 성장률 (%)",
    "NGDPD":        "명목 GDP (십억 USD)",
    "NGDPDPC":      "1인당 GDP (USD)",
    "PPPGDP":       "GDP PPP (십억 국제달러)",
    "PPPPC":        "1인당 GDP PPP (국제달러)",

    # ── 물가 ──
    "PCPIPCH":      "CPI 인플레이션 (%, 연평균)",
    "PCPIEPCH":     "CPI 인플레이션 (%, 기말)",

    # ── 고용 ──
    "LUR":          "실업률 (%)",
    "LP":           "인구 (백만명)",

    # ── 재정 ──
    "GGXWDG_NGDP":  "정부 총부채/GDP (%)",
    "GGXCNL_NGDP":  "재정수지/GDP (%)",

    # ── 대외 ──
    "BCA_NGDPD":    "경상수지/GDP (%)",
}

# 지표 그룹
INDICATOR_GROUPS = {
    "growth":   ["NGDP_RPCH", "NGDPD", "NGDPDPC", "PPPGDP", "PPPPC"],
    "price":    ["PCPIPCH", "PCPIEPCH"],
    "labor":    ["LUR", "LP"],
    "fiscal":   ["GGXWDG_NGDP", "GGXCNL_NGDP", "GGR_NGDP", "GGX_NGDP"],
    "external": ["BCA_NGDPD", "TM_RPCH", "TX_RPCH"],
}

# 지역 그룹 코드
GROUPS = {
    "ADVEC":  "선진국",
    "OEMDC":  "신흥시장·개도국",
    "WEOWORLD": "세계",
}


def _normalize_country(code: str) -> str:
    """ISO 2자리 → 3자리 자동 변환"""
    upper = code.upper()
    if len(upper) == 2 and upper in ISO2_TO_ISO3:
        return ISO2_TO_ISO3[upper]
    return upper


def _normalize_countries(countries: str) -> str:
    """국가 코드 문자열 정규화 (/, +, ; 구분자 지원)"""
    # 구분자 통일
    for sep in ["+", ";", ","]:
        countries = countries.replace(sep, "/")
    codes = [_normalize_country(c.strip()) for c in countries.split("/") if c.strip()]
    return "/".join(codes)


def get_indicator(indicator: str,
                  countries: str = None,
                  start_year: int = None,
                  end_year: int = None) -> pd.DataFrame:
    """
    IMF DataMapper 지표 데이터 조회

    Parameters:
        indicator:   지표 코드 (예: "NGDP_RPCH")
        countries:   국가 코드 (/로 연결, ISO 2자리 또는 3자리)
                     예: "USA/KOR/JPN" 또는 "US/KR/JP"
                     None이면 전체 국가
        start_year:  시작 연도 (None이면 전체)
        end_year:    종료 연도

    Returns:
        DataFrame [country, year, value, indicator]
    """
    url = f"{BASE_URL}/{indicator}"
    if countries:
        url += f"/{_normalize_countries(countries)}"

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    values = data.get("values", {}).get(indicator, {})
    if not values:
        return pd.DataFrame()

    rows = []
    for country, year_vals in values.items():
        for year_str, val in year_vals.items():
            try:
                year = int(year_str)
            except ValueError:
                continue
            if start_year and year < start_year:
                continue
            if end_year and year > end_year:
                continue
            rows.append({
                "country": country,
                "year": year,
                "value": val,
                "indicator": indicator,
            })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.sort_values(["country", "year"]).reset_index(drop=True)


def get_indicator_wide(indicator: str,
                       countries: str = None,
                       start_year: int = None,
                       end_year: int = None) -> pd.DataFrame:
    """
    지표 데이터를 wide 포맷으로 (연도 × 국가)

    Returns:
        DataFrame (index=year, columns=국가코드)
    """
    df = get_indicator(indicator, countries, start_year, end_year)
    if df.empty:
        return pd.DataFrame()
    return df.pivot(index="year", columns="country", values="value")


def get_multi_indicator(indicators: list,
                        countries: str = None,
                        start_year: int = None,
                        end_year: int = None,
                        delay: float = 0.3) -> pd.DataFrame:
    """
    여러 지표를 한번에 조회

    Parameters:
        indicators: 지표 코드 리스트
        countries:  국가 코드 문자열
        start_year: 시작 연도
        end_year:   종료 연도
        delay:      요청 간 대기 (초)

    Returns:
        DataFrame [country, year, indicator, value]
    """
    all_dfs = []
    for ind in indicators:
        try:
            df = get_indicator(ind, countries, start_year, end_year)
            if not df.empty:
                all_dfs.append(df)
        except Exception as e:
            print(f"  [{ind}] 오류: {e}")
        if delay > 0:
            time.sleep(delay)

    if not all_dfs:
        return pd.DataFrame()
    return pd.concat(all_dfs, ignore_index=True)


# ── 편의 함수: 성장 ──────────────────────────────────────────────

def get_gdp_growth(countries: str = "USA/KOR/JPN/DEU/GBR/FRA/CHN",
                   start_year: int = 2007) -> pd.DataFrame:
    """실질 GDP 성장률 (%, 연간)"""
    return get_indicator("NGDP_RPCH", countries, start_year)


def get_gdp_nominal(countries: str = "USA/KOR/JPN/DEU/GBR/FRA/CHN",
                    start_year: int = 2007) -> pd.DataFrame:
    """명목 GDP (십억 USD, 연간)"""
    return get_indicator("NGDPD", countries, start_year)


def get_gdp_per_capita(countries: str = "USA/KOR/JPN/DEU/GBR/FRA/CHN",
                       start_year: int = 2007) -> pd.DataFrame:
    """1인당 GDP (USD, 연간)"""
    return get_indicator("NGDPDPC", countries, start_year)


def get_gdp_ppp(countries: str = "USA/KOR/JPN/DEU/GBR/FRA/CHN",
                start_year: int = 2007) -> pd.DataFrame:
    """GDP PPP (십억 국제달러, 연간)"""
    return get_indicator("PPPGDP", countries, start_year)


# ── 편의 함수: 물가 ──────────────────────────────────────────────

def get_inflation(countries: str = "USA/KOR/JPN/DEU/GBR/FRA/CHN",
                  start_year: int = 2007) -> pd.DataFrame:
    """CPI 인플레이션 (%, 연평균)"""
    return get_indicator("PCPIPCH", countries, start_year)


# ── 편의 함수: 고용 ──────────────────────────────────────────────

def get_unemployment(countries: str = "USA/KOR/JPN/DEU/GBR/FRA/CHN",
                     start_year: int = 2007) -> pd.DataFrame:
    """실업률 (%, 연간)"""
    return get_indicator("LUR", countries, start_year)


def get_population(countries: str = "USA/KOR/JPN/DEU/GBR/FRA/CHN",
                   start_year: int = 2007) -> pd.DataFrame:
    """인구 (백만명, 연간)"""
    return get_indicator("LP", countries, start_year)


# ── 편의 함수: 재정 ──────────────────────────────────────────────

def get_govt_debt(countries: str = "USA/KOR/JPN/DEU/GBR/FRA/CHN",
                  start_year: int = 2007) -> pd.DataFrame:
    """정부 총부채/GDP (%, 연간)"""
    return get_indicator("GGXWDG_NGDP", countries, start_year)


def get_fiscal_balance(countries: str = "USA/KOR/JPN/DEU/GBR/FRA/CHN",
                       start_year: int = 2007) -> pd.DataFrame:
    """재정수지/GDP (%, 연간)"""
    return get_indicator("GGXCNL_NGDP", countries, start_year)


# ── 편의 함수: 대외 ──────────────────────────────────────────────

def get_current_account(countries: str = "USA/KOR/JPN/DEU/GBR/FRA/CHN",
                        start_year: int = 2007) -> pd.DataFrame:
    """경상수지/GDP (%, 연간)"""
    return get_indicator("BCA_NGDPD", countries, start_year)


# ── 편의 함수: 국가 스냅샷 ────────────────────────────────────────

def get_country_snapshot(country: str,
                         start_year: int = 2020) -> pd.DataFrame:
    """
    단일 국가 주요 지표 종합 (연간)

    Returns:
        DataFrame [year, indicator, value, description]
    """
    key_indicators = [
        "NGDP_RPCH", "NGDPDPC", "PCPIPCH", "LUR",
        "GGXWDG_NGDP", "GGXCNL_NGDP", "BCA_NGDPD",
    ]
    df = get_multi_indicator(key_indicators, country, start_year)
    if not df.empty:
        df["description"] = df["indicator"].map(INDICATORS)
    return df


# ── 그룹 데이터 ──────────────────────────────────────────────────

def get_group_data(indicator: str,
                   group: str = "ADVEC",
                   start_year: int = 2007) -> pd.DataFrame:
    """
    지역 그룹 집계 데이터 (선진국/신흥시장/세계)

    Parameters:
        indicator: 지표 코드
        group:     ADVEC (선진국), OEMDC (신흥시장), WEOWORLD (세계)

    Returns:
        DataFrame [country, year, value, indicator]
    """
    return get_indicator(indicator, group, start_year)


if __name__ == "__main__":
    print("=" * 60)
    print("IMF DataMapper API 테스트")
    print("=" * 60)

    # 1) GDP 성장률
    print("\n[1] 실질 GDP 성장률 (한·미·일, 2020~)")
    try:
        df = get_gdp_growth("KOR/USA/JPN", start_year=2020)
        if not df.empty:
            wide = df.pivot(index="year", columns="country", values="value")
            print(wide.to_string())
        else:
            print("  >> 데이터 없음")
    except Exception as e:
        print(f"  >> 오류: {e}")

    # 2) 인플레이션
    print("\n[2] CPI 인플레이션 (한·미·일, 2020~)")
    try:
        df = get_inflation("KOR/USA/JPN", start_year=2020)
        if not df.empty:
            wide = df.pivot(index="year", columns="country", values="value")
            print(wide.to_string())
        else:
            print("  >> 데이터 없음")
    except Exception as e:
        print(f"  >> 오류: {e}")

    # 3) 실업률
    print("\n[3] 실업률 (한·미·일, 2020~)")
    try:
        df = get_unemployment("KOR/USA/JPN", start_year=2020)
        if not df.empty:
            wide = df.pivot(index="year", columns="country", values="value")
            print(wide.to_string())
        else:
            print("  >> 데이터 없음")
    except Exception as e:
        print(f"  >> 오류: {e}")

    # 4) 정부부채
    print("\n[4] 정부 총부채/GDP (한·미·일, 2020~)")
    try:
        df = get_govt_debt("KOR/USA/JPN", start_year=2020)
        if not df.empty:
            wide = df.pivot(index="year", columns="country", values="value")
            print(wide.to_string())
        else:
            print("  >> 데이터 없음")
    except Exception as e:
        print(f"  >> 오류: {e}")

    print("\n" + "=" * 60)
    print("사용 예시:")
    print("  from imf_api import get_gdp_growth, get_inflation, get_unemployment")
    print('  df = get_gdp_growth("KOR/USA/JPN", start_year=2010)')
    print('  df = get_inflation("US/KR/JP")  # ISO 2자리도 가능')
    print('  df = get_country_snapshot("KOR", start_year=2020)')
    print('  df = get_group_data("NGDP_RPCH", "WEOWORLD")  # 세계 GDP 성장률')
    print("=" * 60)
