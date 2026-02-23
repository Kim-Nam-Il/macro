"""
전체 거시경제 데이터를 하나의 통합 테이블로 취합
소스별 스키마를 정규화 → 한국어 컬럼명 → parquet + csv 저장

실행: python3 consolidate.py
출력: data/macro_all.parquet, data/macro_all.csv
"""

import os
import pandas as pd
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# ══════════════════════════════════════════════════════════════
# 국가 코드 매핑
# ══════════════════════════════════════════════════════════════

COUNTRY_KR = {
    # ISO2
    "US": "미국", "KR": "한국", "JP": "일본", "DE": "독일", "GB": "영국",
    "FR": "프랑스", "CN": "중국", "IT": "이탈리아", "CA": "캐나다", "AU": "호주",
    "MX": "멕시코", "BR": "브라질", "IN": "인도", "ID": "인도네시아", "TR": "튀르키예",
    "RU": "러시아", "ZA": "남아프리카", "SA": "사우디아라비아",
    "AR": "아르헨티나", "NG": "나이지리아",
    # ISO3
    "USA": "미국", "KOR": "한국", "JPN": "일본", "DEU": "독일", "GBR": "영국",
    "FRA": "프랑스", "CHN": "중국", "ITA": "이탈리아", "CAN": "캐나다", "AUS": "호주",
    "MEX": "멕시코", "BRA": "브라질", "IND": "인도", "IDN": "인도네시아", "TUR": "튀르키예",
    "RUS": "러시아", "ZAF": "남아프리카", "SAU": "사우디아라비아",
    "ARG": "아르헨티나", "NGA": "나이지리아",
    # OECD 집계
    "OECD": "OECD", "G7": "G7", "EA20": "유로지역",
    # GEC(FIPS)
    "us": "미국", "ks": "한국", "ja": "일본", "gm": "독일", "uk": "영국",
    "fr": "프랑스", "ch": "중국", "it": "이탈리아", "ca": "캐나다", "as": "호주",
    "mx": "멕시코", "br": "브라질", "in": "인도", "id": "인도네시아", "tu": "튀르키예",
}

ISO3_TO_ISO2 = {
    "USA": "US", "KOR": "KR", "JPN": "JP", "DEU": "DE", "GBR": "GB",
    "FRA": "FR", "CHN": "CN", "ITA": "IT", "CAN": "CA", "AUS": "AU",
    "MEX": "MX", "BRA": "BR", "IND": "IN", "IDN": "ID", "TUR": "TR",
    "RUS": "RU", "ZAF": "ZA", "SAU": "SA", "ARG": "AR", "NGA": "NG",
}

GEC_TO_ISO2 = {
    "us": "US", "ks": "KR", "ja": "JP", "gm": "DE", "uk": "GB",
    "fr": "FR", "ch": "CN", "it": "IT", "ca": "CA", "as": "AU",
    "mx": "MX", "br": "BR", "in": "IN", "id": "ID", "tu": "TR",
}


def to_iso2(code: str) -> str:
    """국가코드를 ISO2로 통일"""
    if code in ISO3_TO_ISO2:
        return ISO3_TO_ISO2[code]
    if code in GEC_TO_ISO2:
        return GEC_TO_ISO2[code]
    if len(code) == 2:
        return code.upper()
    return code


def country_name(code: str) -> str:
    return COUNTRY_KR.get(code, code)


def load(name: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, f"{name}.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    return pd.DataFrame()


def make_row(소스, 국가코드, 기간, 지표명, 값, 단위, 주기):
    return {
        "소스": 소스,
        "국가코드": 국가코드,
        "국가명": country_name(국가코드),
        "기간": str(기간),
        "지표명": 지표명,
        "값": 값,
        "단위": 단위,
        "주기": 주기,
    }


# ══════════════════════════════════════════════════════════════
# FRED
# ══════════════════════════════════════════════════════════════

FRED_MAP = {
    "fred_gdp_real":             ("미국_실질GDP",              "십억달러(연율)", "분기"),
    "fred_gdp_growth":           ("미국_실질GDP성장률",        "%",             "분기"),
    "fred_cpi":                  ("미국_CPI",                  "지수",          "월별"),
    "fred_cpi_core":             ("미국_근원CPI",              "지수",          "월별"),
    "fred_pce":                  ("미국_PCE물가지수",          "지수",          "월별"),
    "fred_pce_core":             ("미국_근원PCE",              "지수",          "월별"),
    "fred_unemployment":         ("미국_실업률",               "%",             "월별"),
    "fred_payrolls":             ("미국_비농업고용",           "천명",          "월별"),
    "fred_participation":        ("미국_경제활동참가율",       "%",             "월별"),
    "fred_initial_claims":       ("미국_신규실업수당청구",     "건",            "주별"),
    "fred_fed_funds":            ("미국_연방기금금리",         "%",             "월별"),
    "fred_treasury_10y":         ("미국_10년국채수익률",       "%",             "월별"),
    "fred_treasury_2y":          ("미국_2년국채수익률",        "%",             "월별"),
    "fred_term_spread":          ("미국_장단기스프레드_10Y2Y", "%p",            "월별"),
    "fred_industrial_prod":      ("미국_산업생산지수",         "지수",          "월별"),
    "fred_retail_sales":         ("미국_소매판매",             "백만달러",      "월별"),
    "fred_consumer_sentiment":   ("미국_소비자심리지수",       "지수",          "월별"),
    "fred_m2":                   ("미국_M2통화량",             "십억달러",      "월별"),
}


def process_fred():
    rows = []
    for fname, (지표명, 단위, 주기) in FRED_MAP.items():
        df = load(fname)
        if df.empty:
            continue
        for _, r in df.iterrows():
            rows.append(make_row("FRED", "US", r["date"], 지표명, r["value"], 단위, 주기))
    return rows


# ══════════════════════════════════════════════════════════════
# OECD
# ══════════════════════════════════════════════════════════════

def process_oecd():
    rows = []

    # 1) 분기 GDP 성장률
    df = load("oecd_gdp_quarterly_growth")
    if not df.empty:
        for _, r in df.iterrows():
            trans = r.get("TRANSFORMATION", "")
            if trans == "GY":
                지표 = "GDP성장률_전년동기비"
            elif trans == "G1":
                지표 = "GDP성장률_전기비"
            else:
                지표 = f"GDP성장률_{trans}"
            rows.append(make_row("OECD", to_iso2(r["REF_AREA"]), r["TIME_PERIOD"],
                                 지표, r["OBS_VALUE"], "%", "분기"))

    # 2) 연간 GDP 성장률
    df = load("oecd_gdp_annual_growth")
    if not df.empty:
        for _, r in df.iterrows():
            rows.append(make_row("OECD", to_iso2(r["REF_AREA"]), r["TIME_PERIOD"],
                                 "GDP성장률_연간", r["OBS_VALUE"], "%", "연간"))

    # 3) GDP 수준
    df = load("oecd_gdp_level_usd")
    if not df.empty:
        for _, r in df.iterrows():
            rows.append(make_row("OECD", to_iso2(r["REF_AREA"]), r["TIME_PERIOD"],
                                 "GDP_PPP_연율", r["OBS_VALUE"], "USD_PPP", "분기"))

    # 4) CPI
    df = load("oecd_cpi")
    if not df.empty:
        for _, r in df.iterrows():
            trans = r.get("TRANSFORMATION", "")
            um = r.get("UNIT_MEASURE", "")
            if trans == "GY":
                지표 = "CPI_전년비"
                단위 = "%"
            elif trans == "G1":
                지표 = "CPI_전월비"
                단위 = "%"
            else:
                지표 = "CPI_지수"
                단위 = "지수"
            rows.append(make_row("OECD", to_iso2(r["REF_AREA"]), r["TIME_PERIOD"],
                                 지표, r["OBS_VALUE"], 단위, "월별"))

    # 5) 실업률
    df = load("oecd_unemployment")
    if not df.empty:
        for _, r in df.iterrows():
            rows.append(make_row("OECD", to_iso2(r["REF_AREA"]), r["TIME_PERIOD"],
                                 "실업률", r["OBS_VALUE"], "%", "월별"))

    # 6) 금리
    df = load("oecd_interest_rates")
    if not df.empty:
        measure_map = {"IR3TIB": "단기금리_3개월", "IRLT": "장기금리_국채", "IRSTCI": "정책금리"}
        for _, r in df.iterrows():
            m = r.get("MEASURE", "")
            지표 = measure_map.get(m, f"금리_{m}")
            rows.append(make_row("OECD", to_iso2(r["REF_AREA"]), r["TIME_PERIOD"],
                                 지표, r["OBS_VALUE"], "%", "월별"))

    # 7) CLI
    df = load("oecd_cli")
    if not df.empty:
        measure_map = {"LI": "경기선행지수", "BCICP": "경기종합지수", "LOLITOAA": "CLI_진폭조정"}
        for _, r in df.iterrows():
            m = r.get("MEASURE", "")
            adj = r.get("ADJUSTMENT", "")
            if m == "LI" and adj == "AA":
                지표 = "CLI_진폭조정"
            elif m == "LI":
                지표 = "경기선행지수"
            else:
                지표 = measure_map.get(m, f"CLI_{m}")
            rows.append(make_row("OECD", to_iso2(r["REF_AREA"]), r["TIME_PERIOD"],
                                 지표, r["OBS_VALUE"], "지수", "월별"))

    # 8) 산업생산
    df = load("oecd_industrial_production")
    if not df.empty:
        for _, r in df.iterrows():
            trans = r.get("TRANSFORMATION", "")
            if trans == "GY":
                지표 = "산업생산_전년비"
                단위 = "%"
            elif trans == "G1":
                지표 = "산업생산_전월비"
                단위 = "%"
            else:
                지표 = "산업생산_지수"
                단위 = "지수"
            rows.append(make_row("OECD", to_iso2(r["REF_AREA"]), r["TIME_PERIOD"],
                                 지표, r["OBS_VALUE"], 단위, "월별"))

    return rows


# ══════════════════════════════════════════════════════════════
# BIS
# ══════════════════════════════════════════════════════════════

def process_bis():
    rows = []

    # CPI
    df = load("bis_cpi_yoy")
    if not df.empty:
        for _, r in df.iterrows():
            rows.append(make_row("BIS", to_iso2(r["REF_AREA"]), r["TIME_PERIOD"],
                                 "CPI_전년비", r["OBS_VALUE"], "%", "월별"))

    df = load("bis_cpi_index")
    if not df.empty:
        for _, r in df.iterrows():
            rows.append(make_row("BIS", to_iso2(r["REF_AREA"]), r["TIME_PERIOD"],
                                 "CPI_지수", r["OBS_VALUE"], "2010=100", "월별"))

    # 정책금리
    df = load("bis_policy_rate")
    if not df.empty:
        for _, r in df.iterrows():
            rows.append(make_row("BIS", to_iso2(r["REF_AREA"]), r["TIME_PERIOD"],
                                 "정책금리", r["OBS_VALUE"], "%", "월별"))

    # 신용/GDP
    credit_map = {
        "bis_credit_private_gdp":   "민간신용_GDP비",
        "bis_credit_household_gdp": "가계신용_GDP비",
        "bis_credit_corporate_gdp": "기업신용_GDP비",
        "bis_credit_govt_gdp":      "정부신용_GDP비",
    }
    for fname, 지표 in credit_map.items():
        df = load(fname)
        if df.empty:
            continue
        for _, r in df.iterrows():
            rows.append(make_row("BIS", to_iso2(r["BORROWERS_CTY"]), r["TIME_PERIOD"],
                                 지표, r["OBS_VALUE"], "%", "분기"))

    # 신용/GDP 갭
    df = load("bis_credit_gap")
    if not df.empty:
        gap_type = {"A": "신용GDP비_추세", "B": "신용GDP비_실제", "C": "신용GDP_갭"}
        for _, r in df.iterrows():
            dtype = r.get("CG_DTYPE", "")
            지표 = gap_type.get(dtype, f"신용GDP갭_{dtype}")
            rows.append(make_row("BIS", to_iso2(r["BORROWERS_CTY"]), r["TIME_PERIOD"],
                                 지표, r["OBS_VALUE"], "%p" if dtype == "C" else "%", "분기"))

    # 부동산
    df = load("bis_property_prices")
    if not df.empty:
        for _, r in df.iterrows():
            vtype = r.get("VALUE", "")
            um = r.get("UNIT_MEASURE", "")
            if vtype == "R":
                prefix = "실질"
            else:
                prefix = "명목"
            if str(um) == "771":
                지표 = f"주택가격_{prefix}_전년비"
                단위 = "%"
            else:
                지표 = f"주택가격_{prefix}_지수"
                단위 = "2010=100"
            rows.append(make_row("BIS", to_iso2(r["REF_AREA"]), r["TIME_PERIOD"],
                                 지표, r["OBS_VALUE"], 단위, "분기"))

    # 실효환율
    df = load("bis_eer")
    if not df.empty:
        for _, r in df.iterrows():
            etype = r.get("EER_TYPE", "")
            if etype == "R":
                지표 = "실질실효환율"
            else:
                지표 = "명목실효환율"
            rows.append(make_row("BIS", to_iso2(r["REF_AREA"]), r["TIME_PERIOD"],
                                 지표, r["OBS_VALUE"], "지수", "월별"))

    # DSR
    df = load("bis_dsr")
    if not df.empty:
        borrower_map = {"P": "민간", "H": "가계", "N": "기업"}
        for _, r in df.iterrows():
            b = r.get("DSR_BORROWERS", "P")
            bname = borrower_map.get(b, b)
            지표 = f"원리금상환비율_{bname}"
            rows.append(make_row("BIS", to_iso2(r["BORROWERS_CTY"]), r["TIME_PERIOD"],
                                 지표, r["OBS_VALUE"], "%", "분기"))

    return rows


# ══════════════════════════════════════════════════════════════
# IMF
# ══════════════════════════════════════════════════════════════

IMF_MAP = {
    "NGDP_RPCH":   ("GDP성장률",          "%"),
    "NGDPD":       ("명목GDP",            "십억USD"),
    "NGDPDPC":     ("1인당GDP",           "USD"),
    "PPPGDP":      ("GDP_PPP",           "십억국제달러"),
    "PPPPC":       ("1인당GDP_PPP",      "국제달러"),
    "PCPIPCH":     ("CPI인플레이션",     "%"),
    "PCPIEPCH":    ("CPI인플레이션_기말", "%"),
    "LUR":         ("실업률",            "%"),
    "LP":          ("인구",              "백만명"),
    "GGXWDG_NGDP": ("정부부채_GDP비",    "%"),
    "GGXCNL_NGDP": ("재정수지_GDP비",    "%"),
    "BCA_NGDPD":   ("경상수지_GDP비",    "%"),
}


def process_imf():
    rows = []
    imf_files = [
        "imf_gdp_growth", "imf_gdp_nominal", "imf_gdp_per_capita",
        "imf_gdp_ppp", "imf_inflation", "imf_unemployment",
        "imf_population", "imf_govt_debt", "imf_fiscal_balance",
        "imf_current_account", "imf_gdp_per_capita_ppp", "imf_inflation_eop",
    ]
    for fname in imf_files:
        df = load(fname)
        if df.empty:
            continue
        for _, r in df.iterrows():
            ind = r["indicator"]
            지표, 단위 = IMF_MAP.get(ind, (ind, ""))
            rows.append(make_row("IMF", to_iso2(r["country"]), r["year"],
                                 지표, r["value"], 단위, "연간"))
    return rows


# ══════════════════════════════════════════════════════════════
# World Bank
# ══════════════════════════════════════════════════════════════

WB_MAP = {
    "NY.GDP.MKTP.KD.ZG":  ("GDP성장률",          "%"),
    "NY.GDP.MKTP.CD":     ("명목GDP",            "USD"),
    "NY.GDP.PCAP.CD":     ("1인당GDP",           "USD"),
    "NY.GDP.MKTP.PP.CD":  ("GDP_PPP",           "국제달러"),
    "FP.CPI.TOTL.ZG":     ("CPI인플레이션",     "%"),
    "SL.UEM.TOTL.ZS":     ("실업률",            "%"),
    "SP.POP.TOTL":         ("인구",              "명"),
    "NE.TRD.GNFS.ZS":     ("무역_GDP비",        "%"),
    "BX.KLT.DINV.CD.WD":  ("FDI순유입",         "USD"),
    "FM.LBL.BMNY.GD.ZS":  ("광의통화_GDP비",    "%"),
    "FS.AST.PRVT.GD.ZS":  ("민간신용_GDP비",    "%"),
}


def process_wb():
    rows = []
    wb_files = [
        "wb_gdp_growth", "wb_gdp_current_usd", "wb_gdp_per_capita",
        "wb_gdp_ppp", "wb_inflation", "wb_unemployment", "wb_population",
        "wb_trade_pct_gdp", "wb_fdi_net_inflows", "wb_broad_money_pct_gdp",
        "wb_domestic_credit_pct_gdp",
    ]
    for fname in wb_files:
        df = load(fname)
        if df.empty:
            continue
        for _, r in df.iterrows():
            ind = r["indicator_id"]
            지표, 단위 = WB_MAP.get(ind, (ind, ""))
            iso2 = r["country_id"]
            rows.append(make_row("WB", iso2, int(r["date"]) if pd.notna(r["date"]) else r["date"],
                                 지표, r["value"], 단위, "연간"))
    return rows


# ══════════════════════════════════════════════════════════════
# Factbook
# ══════════════════════════════════════════════════════════════

FB_FIELDS = {
    "gdp_ppp":                     ("GDP_PPP",              "USD"),
    "gdp_growth":                  ("GDP성장률",            "%"),
    "gdp_per_capita":              ("1인당GDP",             "USD"),
    "gdp_official":                ("명목GDP",              "USD"),
    "inflation":                   ("인플레이션",           "%"),
    "unemployment":                ("실업률",               "%"),
    "population":                  ("인구",                 "명"),
    "labor_force":                 ("노동력",               "명"),
    "public_debt_pct_gdp":         ("정부부채_GDP비",       "%"),
    "current_account":             ("경상수지",             "USD"),
    "exports":                     ("수출",                 "USD"),
    "imports":                     ("수입",                 "USD"),
    "fx_reserves":                 ("외환보유고",           "USD"),
    "industrial_production_growth":("산업생산성장률",       "%"),
    "gdp_share_agriculture":       ("농업비중",             "%"),
    "gdp_share_industry":          ("산업비중",             "%"),
    "gdp_share_services":          ("서비스비중",           "%"),
}


def process_factbook():
    rows = []
    df = load("factbook_economy_summary")
    if df.empty:
        return rows
    for _, r in df.iterrows():
        iso2 = r.get("iso2", "")
        if not iso2:
            iso2 = GEC_TO_ISO2.get(r.get("country", ""), r.get("country", ""))
        # 연도: 가능하면 gdp_growth_year 사용
        year = r.get("gdp_growth_year", "최신")
        for field, (지표, 단위) in FB_FIELDS.items():
            val = r.get(field)
            if pd.notna(val):
                rows.append(make_row("Factbook", iso2, year, 지표, val, 단위, "스냅샷"))
    return rows


# ══════════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════════

def main():
    print("데이터 통합 시작...")

    all_rows = []

    print("  FRED 처리 중...")
    all_rows.extend(process_fred())
    print(f"    → {len(all_rows):,}행")

    prev = len(all_rows)
    print("  OECD 처리 중...")
    all_rows.extend(process_oecd())
    print(f"    → +{len(all_rows)-prev:,}행")

    prev = len(all_rows)
    print("  BIS 처리 중...")
    all_rows.extend(process_bis())
    print(f"    → +{len(all_rows)-prev:,}행")

    prev = len(all_rows)
    print("  IMF 처리 중...")
    all_rows.extend(process_imf())
    print(f"    → +{len(all_rows)-prev:,}행")

    prev = len(all_rows)
    print("  World Bank 처리 중...")
    all_rows.extend(process_wb())
    print(f"    → +{len(all_rows)-prev:,}행")

    prev = len(all_rows)
    print("  Factbook 처리 중...")
    all_rows.extend(process_factbook())
    print(f"    → +{len(all_rows)-prev:,}행")

    print(f"\n총 {len(all_rows):,}행 통합")

    df = pd.DataFrame(all_rows)

    # 정렬
    df = df.sort_values(["소스", "국가코드", "지표명", "기간"]).reset_index(drop=True)

    # 저장
    pq_path = os.path.join(DATA_DIR, "macro_all.parquet")
    csv_path = os.path.join(DATA_DIR, "macro_all.csv")

    df.to_parquet(pq_path, index=False)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    print(f"\n저장 완료:")
    print(f"  {pq_path}  ({os.path.getsize(pq_path)/1024:.0f}KB)")
    print(f"  {csv_path}  ({os.path.getsize(csv_path)/1024:.0f}KB)")

    # 요약
    print(f"\n컬럼: {list(df.columns)}")
    print(f"\n소스별 행수:")
    print(df.groupby("소스").size().to_string())
    print(f"\n국가별 행수 (상위 10):")
    print(df.groupby("국가코드").size().sort_values(ascending=False).head(10).to_string())
    print(f"\n지표 종류: {df['지표명'].nunique()}개")
    print(f"  {sorted(df['지표명'].unique())}")


if __name__ == "__main__":
    main()
