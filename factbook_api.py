"""
CIA World Factbook 데이터 모듈
https://github.com/factbook/factbook.json

261개 국가·지역 프로필: GDP, 인플레이션, 실업률, 인구, 무역, 재정 등
인증 불필요 (Public Domain, 매주 목요일 자동 업데이트)

주의: GEC(FIPS) 코드 사용 — ISO 코드와 다름 (예: 한국=KS, 독일=GM, 영국=UK)
"""

import requests
import pandas as pd
import re
import json

BASE_URL = "https://raw.githubusercontent.com/factbook/factbook.json/master"

# ── GEC(FIPS) → ISO 매핑 + 지역 폴더 ──────────────────────────────
COUNTRY_MAP = {
    # (GEC코드, 지역폴더, ISO2, 국가명)
    "us": ("north-america",              "US", "미국"),
    "ks": ("east-n-southeast-asia",      "KR", "한국"),
    "ja": ("east-n-southeast-asia",      "JP", "일본"),
    "gm": ("europe",                     "DE", "독일"),
    "uk": ("europe",                     "GB", "영국"),
    "fr": ("europe",                     "FR", "프랑스"),
    "ch": ("east-n-southeast-asia",      "CN", "중국"),
    "it": ("europe",                     "IT", "이탈리아"),
    "ca": ("north-america",              "CA", "캐나다"),
    "as": ("australia-oceania",          "AU", "호주"),
    "mx": ("north-america",              "MX", "멕시코"),
    "br": ("south-america",              "BR", "브라질"),
    "in": ("south-asia",                 "IN", "인도"),
    "id": ("east-n-southeast-asia",      "ID", "인도네시아"),
    "tu": ("middle-east",                "TR", "튀르키예"),
    "rs": ("central-asia",               "RU", "러시아"),
    "za": ("africa",                     "ZA", "남아프리카"),
    "sa": ("middle-east",                "SA", "사우디아라비아"),
    "ar": ("south-america",              "AR", "아르헨티나"),
    "ni": ("africa",                     "NG", "나이지리아"),
    "sn": ("europe",                     "ES", "스페인"),
    "nl": ("europe",                     "NL", "네덜란드"),
    "sz": ("europe",                     "CH", "스위스"),
    "sw": ("europe",                     "SE", "스웨덴"),
    "no": ("europe",                     "NO", "노르웨이"),
    "pl": ("europe",                     "PL", "폴란드"),
    "th": ("east-n-southeast-asia",      "TH", "태국"),
    "vm": ("east-n-southeast-asia",      "VN", "베트남"),
    "rp": ("east-n-southeast-asia",      "PH", "필리핀"),
    "my": ("east-n-southeast-asia",      "MY", "말레이시아"),
    "sn": ("europe",                     "ES", "스페인"),
    "tw": ("east-n-southeast-asia",      "TW", "대만"),
    "hk": ("east-n-southeast-asia",      "HK", "홍콩"),
    "xx": ("world",                      "WD", "세계"),
}

# ISO → GEC 역매핑
ISO_TO_GEC = {info[1]: gec for gec, info in COUNTRY_MAP.items()}


def _parse_number(text: str) -> float | None:
    """
    Factbook 텍스트에서 숫자 추출

    예시:
        "$25.676 trillion (2024 est.)" → 25676000000000
        "2.8% (2024 est.)"            → 2.8
        "338,016,259 (2025 est.)"     → 338016259
        "52.3% of GDP (2023 est.)"    → 52.3
    """
    if not text:
        return None

    # 퍼센트 패턴
    pct = re.search(r"([-\d,.]+)%", text)
    if pct:
        return float(pct.group(1).replace(",", ""))

    # 달러/통화 패턴 (trillion/billion/million)
    money = re.search(r"\$?([-\d,.]+)\s*(trillion|billion|million)", text, re.IGNORECASE)
    if money:
        val = float(money.group(1).replace(",", ""))
        unit = money.group(2).lower()
        multipliers = {"trillion": 1e12, "billion": 1e9, "million": 1e6}
        return val * multipliers.get(unit, 1)

    # 일반 숫자 (쉼표 포함)
    num = re.search(r"([-\d,]+(?:\.\d+)?)", text)
    if num:
        try:
            return float(num.group(1).replace(",", ""))
        except ValueError:
            return None

    return None


def _parse_year(key: str) -> int | None:
    """키 이름에서 연도 추출: 'Real GDP growth rate 2024' → 2024"""
    m = re.search(r"(\d{4})", key)
    return int(m.group(1)) if m else None


def _extract_time_series(section: dict) -> list[dict]:
    """
    시계열 필드에서 (year, text, value) 리스트 추출

    {"Field 2024": {"text": "..."}, "Field 2023": {"text": "..."}, "note": "..."}
    → [{"year": 2024, "text": "...", "value": ...}, ...]
    """
    results = []
    for key, val in section.items():
        if key == "note" or not isinstance(val, dict):
            continue
        year = _parse_year(key)
        text = val.get("text", "")
        value = _parse_number(text)
        results.append({"year": year, "text": text, "value": value})
    return sorted(results, key=lambda x: x.get("year") or 0, reverse=True)


def _get_latest(section: dict) -> dict | None:
    """시계열 필드에서 최신 값만 추출"""
    series = _extract_time_series(section)
    return series[0] if series else None


# ── 국가 데이터 로드 ──────────────────────────────────────────────

def get_country_raw(gec_code: str) -> dict:
    """
    국가 전체 JSON 데이터 로드 (raw)

    Parameters:
        gec_code: GEC/FIPS 코드 (소문자, 예: "us", "ks", "ja")
                  또는 ISO 2자리 코드 (자동 변환, 예: "US", "KR", "JP")

    Returns:
        전체 JSON dict
    """
    # ISO → GEC 자동 변환
    code = gec_code.lower()
    if code.upper() in ISO_TO_GEC:
        code = ISO_TO_GEC[code.upper()]

    if code not in COUNTRY_MAP:
        raise ValueError(f"알 수 없는 국가 코드: {gec_code}. "
                         f"사용 가능: {list(COUNTRY_MAP.keys())}")

    region = COUNTRY_MAP[code][0]
    url = f"{BASE_URL}/{region}/{code}.json"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_economy(gec_code: str) -> dict:
    """국가 경제 섹션 전체"""
    data = get_country_raw(gec_code)
    return data.get("Economy", {})


def get_economy_summary(gec_code: str) -> dict:
    """
    국가 주요 경제 지표 요약

    Returns:
        dict {
            "country": str,
            "gdp_ppp": float,          # 실질 GDP PPP (USD)
            "gdp_growth": float,       # GDP 성장률 (%)
            "gdp_per_capita": float,   # 1인당 GDP (USD)
            "gdp_official": float,     # GDP 명목 (USD)
            "inflation": float,        # 인플레이션 (%)
            "unemployment": float,     # 실업률 (%)
            "population": float,       # 인구
            "labor_force": float,      # 노동력
            "public_debt_pct_gdp": float,  # 정부부채/GDP (%)
            "budget_revenue": float,   # 정부수입 (USD)
            "budget_expenditure": float,   # 정부지출 (USD)
            "current_account": float,  # 경상수지 (USD)
            "exports": float,          # 수출 (USD)
            "imports": float,          # 수입 (USD)
            "industrial_production_growth": float,  # 산업생산 성장률 (%)
            ...
        }
    """
    data = get_country_raw(gec_code)
    econ = data.get("Economy", {})
    people = data.get("People and Society", {})

    result = {"country": gec_code}

    # GDP
    gdp_ppp = econ.get("Real GDP (purchasing power parity)", {})
    latest = _get_latest(gdp_ppp)
    if latest:
        result["gdp_ppp"] = latest["value"]
        result["gdp_ppp_year"] = latest["year"]

    gdp_growth = econ.get("Real GDP growth rate", {})
    latest = _get_latest(gdp_growth)
    if latest:
        result["gdp_growth"] = latest["value"]
        result["gdp_growth_year"] = latest["year"]

    gdp_pc = econ.get("Real GDP per capita", {})
    latest = _get_latest(gdp_pc)
    if latest:
        result["gdp_per_capita"] = latest["value"]

    gdp_off = econ.get("GDP (official exchange rate)", {})
    if "text" in gdp_off:
        result["gdp_official"] = _parse_number(gdp_off["text"])

    # 물가
    inflation = econ.get("Inflation rate (consumer prices)", {})
    latest = _get_latest(inflation)
    if latest:
        result["inflation"] = latest["value"]
        result["inflation_year"] = latest["year"]

    # 고용
    unemp = econ.get("Unemployment rate", {})
    latest = _get_latest(unemp)
    if latest:
        result["unemployment"] = latest["value"]
        result["unemployment_year"] = latest["year"]

    labor = econ.get("Labor force", {})
    if "text" in labor:
        result["labor_force"] = _parse_number(labor["text"])

    # 인구
    pop = people.get("Population", {})
    total = pop.get("total", {})
    if "text" in total:
        result["population"] = _parse_number(total["text"])

    # 재정
    public_debt = econ.get("Public debt", {})
    latest = _get_latest(public_debt)
    if latest:
        result["public_debt_pct_gdp"] = latest["value"]

    budget = econ.get("Budget", {})
    rev = budget.get("revenues", {})
    if "text" in rev:
        result["budget_revenue"] = _parse_number(rev["text"])
    exp = budget.get("expenditures", {})
    if "text" in exp:
        result["budget_expenditure"] = _parse_number(exp["text"])

    # 국제수지
    ca = econ.get("Current account balance", {})
    latest = _get_latest(ca)
    if latest:
        result["current_account"] = latest["value"]

    exports = econ.get("Exports", {})
    latest = _get_latest(exports)
    if latest:
        result["exports"] = latest["value"]

    imports = econ.get("Imports", {})
    latest = _get_latest(imports)
    if latest:
        result["imports"] = latest["value"]

    # 산업생산
    ip = econ.get("Industrial production growth rate", {})
    if "text" in ip:
        result["industrial_production_growth"] = _parse_number(ip["text"])

    # GDP 구성
    comp = econ.get("GDP - composition, by sector of origin", {})
    for sector in ["agriculture", "industry", "services"]:
        s = comp.get(sector, {})
        if "text" in s:
            result[f"gdp_share_{sector}"] = _parse_number(s["text"])

    # 외환보유고
    reserves = econ.get("Reserves of foreign exchange and gold", {})
    latest = _get_latest(reserves)
    if latest:
        result["fx_reserves"] = latest["value"]

    return result


def get_multi_country_summary(gec_codes: list = None) -> pd.DataFrame:
    """
    여러 국가 경제 요약을 DataFrame으로

    Parameters:
        gec_codes: GEC 또는 ISO 코드 리스트 (None이면 주요 20개국)

    Returns:
        DataFrame (각 행이 국가, 열이 지표)
    """
    if gec_codes is None:
        gec_codes = ["us", "ks", "ja", "gm", "uk", "fr", "ch", "it",
                     "ca", "as", "mx", "br", "in", "id", "tu"]

    rows = []
    for code in gec_codes:
        try:
            summary = get_economy_summary(code)
            # 국가명 추가
            c = code.lower()
            if c.upper() in ISO_TO_GEC:
                c = ISO_TO_GEC[c.upper()]
            if c in COUNTRY_MAP:
                summary["iso2"] = COUNTRY_MAP[c][1]
                summary["country_name"] = COUNTRY_MAP[c][2]
            rows.append(summary)
        except Exception as e:
            print(f"  [{code}] 오류: {e}")

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def get_gdp_growth_series(gec_code: str) -> pd.DataFrame:
    """국가 GDP 성장률 시계열 (보통 최근 3년)"""
    econ = get_economy(gec_code)
    series = _extract_time_series(econ.get("Real GDP growth rate", {}))
    if not series:
        return pd.DataFrame()
    return pd.DataFrame(series)[["year", "value"]].rename(
        columns={"value": "gdp_growth"})


def get_inflation_series(gec_code: str) -> pd.DataFrame:
    """국가 인플레이션 시계열 (보통 최근 3년)"""
    econ = get_economy(gec_code)
    series = _extract_time_series(econ.get("Inflation rate (consumer prices)", {}))
    if not series:
        return pd.DataFrame()
    return pd.DataFrame(series)[["year", "value"]].rename(
        columns={"value": "inflation"})


def get_unemployment_series(gec_code: str) -> pd.DataFrame:
    """국가 실업률 시계열 (보통 최근 3년)"""
    econ = get_economy(gec_code)
    series = _extract_time_series(econ.get("Unemployment rate", {}))
    if not series:
        return pd.DataFrame()
    return pd.DataFrame(series)[["year", "value"]].rename(
        columns={"value": "unemployment"})


if __name__ == "__main__":
    print("=" * 60)
    print("CIA World Factbook 테스트")
    print("=" * 60)

    # 1) 미국 경제 요약
    print("\n[1] 미국 경제 요약")
    s = get_economy_summary("us")
    for k, v in s.items():
        if isinstance(v, float) and v > 1e9:
            print(f"  {k:35s}: ${v/1e12:.2f}T")
        elif isinstance(v, float):
            print(f"  {k:35s}: {v:,.2f}")
        else:
            print(f"  {k:35s}: {v}")

    # 2) 한국 경제 요약
    print("\n[2] 한국 경제 요약 (ISO 코드 'KR' 사용)")
    s = get_economy_summary("KR")
    for k, v in s.items():
        if isinstance(v, float) and v > 1e9:
            print(f"  {k:35s}: ${v/1e12:.2f}T")
        elif isinstance(v, float):
            print(f"  {k:35s}: {v:,.2f}")
        else:
            print(f"  {k:35s}: {v}")

    # 3) 주요국 비교 테이블
    print("\n[3] 주요 5개국 비교")
    df = get_multi_country_summary(["us", "ks", "ja", "gm", "ch"])
    if not df.empty:
        cols = ["country_name", "gdp_growth", "inflation", "unemployment",
                "public_debt_pct_gdp"]
        cols = [c for c in cols if c in df.columns]
        print(df[cols].to_string(index=False))

    print("\n" + "=" * 60)
    print("사용 예시:")
    print("  from factbook_api import get_economy_summary, get_multi_country_summary")
    print('  s = get_economy_summary("KR")  # ISO 코드 사용 가능')
    print('  df = get_multi_country_summary(["us","ks","ja","gm","ch"])')
    print('  df = get_multi_country_summary()  # 주요 15개국')
    print("=" * 60)
