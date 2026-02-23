"""
OECD SDMX REST API 모듈
https://sdmx.oecd.org/public/rest/

OECD 회원국 거시경제 패널: GDP, CPI, 실업률, 고용, 금리, 선행지수 등
인증 불필요 (무료 공개)

차원 구조:
  - QNA (GDP 성장률): FREQ.ADJUSTMENT.REF_AREA.SECTOR.COUNTERPART_SECTOR.TRANSACTION.
                       INSTR_ASSET.ACTIVITY.EXPENDITURE.UNIT_MEASURE.PRICE_BASE.
                       TRANSFORMATION.TABLE_IDENTIFIER  (13개)
  - KEI (CPI·실업률 등): REF_AREA.FREQ.MEASURE.UNIT_MEASURE.ACTIVITY.ADJUSTMENT.TRANSFORMATION  (7개)
  - CLI (선행지수):       REF_AREA.FREQ.MEASURE.UNIT_MEASURE.ADJUSTMENT  (5개)
"""

import requests
import pandas as pd
import io
import time

BASE_URL = "https://sdmx.oecd.org/public/rest"

# ── 주요 국가 코드 (ISO 3자리) ─────────────────────────────────────
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
    "OECD": "OECD 전체",
    "G7": "G7",
    "EA20": "유로지역(20)",
}

# ISO 2→3 매핑 (BIS와 호환용)
ISO2_TO_ISO3 = {
    "KR": "KOR", "US": "USA", "JP": "JPN", "DE": "DEU",
    "GB": "GBR", "FR": "FRA", "CN": "CHN", "IT": "ITA",
    "CA": "CAN", "AU": "AUS", "MX": "MEX", "BR": "BRA",
    "IN": "IND", "ID": "IDN", "TR": "TUR",
}


def _fetch_csv(url: str, params: dict = None, max_retries: int = 3) -> pd.DataFrame:
    """SDMX CSV 응답을 DataFrame으로 변환 (429 자동 재시도)"""
    headers = {"Accept": "application/vnd.sdmx.data+csv;version=2.0.0"}

    for attempt in range(max_retries):
        resp = requests.get(url, params=params, headers=headers, timeout=60)

        if resp.status_code == 429:
            wait = 10 * (attempt + 1)
            print(f"  [OECD] Rate limit, {wait}초 대기 후 재시도 ({attempt+1}/{max_retries})")
            time.sleep(wait)
            continue

        if resp.status_code == 404 and "NoRecordsFound" in resp.text:
            return pd.DataFrame()

        resp.raise_for_status()

        text = resp.text.strip()
        if not text:
            return pd.DataFrame()

        df = pd.read_csv(io.StringIO(text))
        if "OBS_VALUE" in df.columns:
            df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
        return df

    resp.raise_for_status()
    return pd.DataFrame()


def _build_url(agency: str, dataflow_id: str, version: str,
               key: str = "") -> str:
    """SDMX 데이터 URL 생성 (v1 스타일 - startPeriod 지원)"""
    url = f"{BASE_URL}/data/{agency},{dataflow_id},{version}"
    if key:
        url += f"/{key}"
    return url


def get_data(agency: str, dataflow_id: str, version: str,
             key: str = "", start_period: str = None,
             end_period: str = None) -> pd.DataFrame:
    """
    OECD SDMX 데이터 조회 (범용)

    Parameters:
        agency:       기관 코드 (예: "OECD.SDD.NAD")
        dataflow_id:  데이터플로우 ID (예: "DSD_NAMAIN1@DF_QNA")
        version:      버전 (예: "1.1")
        key:          차원 필터 (점으로 구분, 빈값=와일드카드)
        start_period: 시작기간 (예: "2020-Q1", "2020-01")
        end_period:   종료기간

    Returns:
        DataFrame (CSV 파싱 결과)
    """
    url = _build_url(agency, dataflow_id, version, key)
    params = {"detail": "dataonly"}
    if start_period:
        params["startPeriod"] = start_period
    if end_period:
        params["endPeriod"] = end_period

    return _fetch_csv(url, params)


# ── 편의 함수: GDP 성장률 ─────────────────────────────────────────
# QNA 13차원: FREQ.ADJUSTMENT.REF_AREA.SECTOR.COUNTERPART_SECTOR.
#             TRANSACTION.INSTR_ASSET.ACTIVITY.EXPENDITURE.
#             UNIT_MEASURE.PRICE_BASE.TRANSFORMATION.TABLE_IDENTIFIER

def get_gdp_quarterly(countries: str = "KOR+USA+JPN+DEU+GBR+FRA",
                      start: str = "2007-Q1", end: str = None,
                      transform: str = "GY") -> pd.DataFrame:
    """
    분기 실질 GDP 성장률 (지출 접근)

    Parameters:
        countries:  국가 코드 (+로 연결, ISO 3자리)
        start:      시작분기 (YYYY-QN)
        transform:  GY=전년동기비, G1=전기비, GCM=전기비 연율

    Returns:
        DataFrame [..., REF_AREA, TRANSACTION, TRANSFORMATION, TIME_PERIOD, OBS_VALUE, ...]
    """
    # FREQ=Q, ADJUSTMENT=Y(계절조정), SECTOR=S1, COUNTERPART_SECTOR=S1,
    # TRANSACTION=B1GQ(GDP), INSTR_ASSET=_Z, ACTIVITY=_Z, EXPENDITURE=_Z,
    # UNIT_MEASURE=PC, PRICE_BASE=L, TABLE_IDENTIFIER=T0102
    key = f"Q.Y.{countries}.S1.S1.B1GQ._Z._Z._Z.PC.L.{transform}.T0102"
    return get_data(
        "OECD.SDD.NAD", "DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD", "1.1",
        key, start, end
    )


def get_gdp_annual(countries: str = "KOR+USA+JPN+DEU+GBR+FRA",
                   start: str = "2007", end: str = None) -> pd.DataFrame:
    """
    연간 GDP 성장률 (지출 접근)
    Annual dataflow는 12차원 (ADJUSTMENT 없음), TRANSFORMATION=G1
    """
    key = f"A.{countries}.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102"
    return get_data(
        "OECD.SDD.NAD", "DSD_NAMAIN10@DF_TABLE1_EXPENDITURE_GROWTH", "2.0",
        key, start, end
    )


def get_gdp_level(countries: str = "KOR+USA+JPN+DEU+GBR+FRA",
                  start: str = "2007-Q1", end: str = None) -> pd.DataFrame:
    """
    분기 GDP 수준 (USD PPP, 계절조정, 연율화)
    UNIT_MEASURE=USD_PPP, PRICE_BASE=V(volume), TRANSFORMATION=LA(level annualized)
    """
    key = f"Q.Y.{countries}.S1.S1.B1GQ._Z._Z._Z.USD_PPP.V.LA.T0102"
    return get_data(
        "OECD.SDD.NAD", "DSD_NAMAIN1@DF_QNA_EXPENDITURE_USD", "1.1",
        key, start, end
    )


# ── 편의 함수: 물가 (CPI) ─────────────────────────────────────────
# KEI 7차원: REF_AREA.FREQ.MEASURE.UNIT_MEASURE.ACTIVITY.ADJUSTMENT.TRANSFORMATION

def get_cpi(countries: str = "KOR+USA+JPN+DEU+GBR+FRA",
            start: str = "2007-01", end: str = None) -> pd.DataFrame:
    """
    소비자물가지수 (Key Economic Indicators)
    전년동월비(GY) + 전월비(G1) + 지수(_Z) 모두 포함

    Returns:
        DataFrame [REF_AREA, FREQ, MEASURE, UNIT_MEASURE, TRANSFORMATION,
                   TIME_PERIOD, OBS_VALUE, ...]
    """
    # MEASURE=CP(CPI), 나머지 와일드카드
    key = f"{countries}.M.CP...."
    return get_data(
        "OECD.SDD.STES", "DSD_KEI@DF_KEI", "4.0",
        key, start, end
    )


def get_cpi_yoy(countries: str = "KOR+USA+JPN+DEU+GBR+FRA",
                start: str = "2007-01", end: str = None) -> pd.DataFrame:
    """CPI 전년동월비 (%) 전용"""
    key = f"{countries}.M.CP.GR..Y.GY"
    return get_data(
        "OECD.SDD.STES", "DSD_KEI@DF_KEI", "4.0",
        key, start, end
    )


# ── 편의 함수: 고용/실업 ──────────────────────────────────────────

def get_unemployment(countries: str = "KOR+USA+JPN+DEU+GBR+FRA",
                     start: str = "2007-01", end: str = None) -> pd.DataFrame:
    """
    실업률 (Unemployment Rate, 월별)

    Returns:
        DataFrame [REF_AREA, ..., TIME_PERIOD, OBS_VALUE]
    """
    # MEASURE=UNEMP, UNIT_MEASURE=PT_LF(노동력 대비 %)
    key = f"{countries}.M.UNEMP...."
    return get_data(
        "OECD.SDD.STES", "DSD_KEI@DF_KEI", "4.0",
        key, start, end
    )


def get_employment(countries: str = "KOR+USA+JPN+DEU+GBR+FRA",
                   start: str = "2007-01", end: str = None) -> pd.DataFrame:
    """
    고용 (Employment, 월별)
    """
    key = f"{countries}.M.EMP...."
    return get_data(
        "OECD.SDD.STES", "DSD_KEI@DF_KEI", "4.0",
        key, start, end
    )


# ── 편의 함수: 금리 ───────────────────────────────────────────────

def get_interest_rates(countries: str = "KOR+USA+JPN+DEU+GBR+FRA",
                       start: str = "2007-01", end: str = None) -> pd.DataFrame:
    """
    단기(IR3TIB)/장기(IRLT) 금리 + 단기정책금리(IRSTCI)

    MEASURE:
        IR3TIB = 3개월 인터뱅크 금리
        IRLT   = 장기 국채수익률
        IRSTCI = 단기정책금리
    """
    key = f"{countries}.M.IR3TIB+IRLT+IRSTCI...."
    return get_data(
        "OECD.SDD.STES", "DSD_KEI@DF_KEI", "4.0",
        key, start, end
    )


# ── 편의 함수: 경기선행지수 (CLI) ──────────────────────────────────
# CLI 9차원: REF_AREA.FREQ.MEASURE.UNIT_MEASURE.ACTIVITY.ADJUSTMENT.TRANSFORMATION.TIME_HORIZ.METHODOLOGY

def get_cli(countries: str = "KOR+USA+JPN+DEU+GBR+FRA",
            start: str = "2007-01", end: str = None) -> pd.DataFrame:
    """
    경기선행지수 (Composite Leading Indicators)
    9차원: REF_AREA.FREQ.MEASURE.UNIT_MEASURE.ACTIVITY.ADJUSTMENT.TRANSFORMATION.TIME_HORIZ.METHODOLOGY
    """
    key = f"{countries}.M......_Z.H"
    return get_data(
        "OECD.SDD.STES", "DSD_STES@DF_CLI", "4.1",
        key, start, end
    )


# ── 편의 함수: 산업생산 ───────────────────────────────────────────

def get_industrial_production(countries: str = "KOR+USA+JPN+DEU+GBR+FRA",
                              start: str = "2007-01",
                              end: str = None) -> pd.DataFrame:
    """
    산업생산지수 (KEI)
    """
    key = f"{countries}.M.PRVM...."
    return get_data(
        "OECD.SDD.STES", "DSD_KEI@DF_KEI", "4.0",
        key, start, end
    )


# ── 편의 함수: 소매판매 ───────────────────────────────────────────

def get_retail_sales(countries: str = "KOR+USA+JPN+DEU+GBR+FRA",
                     start: str = "2007-01", end: str = None) -> pd.DataFrame:
    """
    소매판매 (KEI)
    """
    key = f"{countries}.M.RS...."
    return get_data(
        "OECD.SDD.STES", "DSD_KEI@DF_KEI", "4.0",
        key, start, end
    )


# ── 편의 함수: 수출입 ─────────────────────────────────────────────

def get_trade(countries: str = "KOR+USA+JPN+DEU+GBR+FRA",
              start: str = "2007-01", end: str = None) -> pd.DataFrame:
    """
    수출(EX)/수입(IM)
    """
    key = f"{countries}.M.EX+IM...."
    return get_data(
        "OECD.SDD.STES", "DSD_KEI@DF_KEI", "4.0",
        key, start, end
    )


# ── 데이터플로우 목록 사전 ─────────────────────────────────────────

DATAFLOWS = {
    # GDP / 국민계정
    "GDP_quarterly":           ("OECD.SDD.NAD", "DSD_NAMAIN1@DF_QNA", "1.1"),
    "GDP_quarterly_growth":    ("OECD.SDD.NAD", "DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD", "1.1"),
    "GDP_quarterly_usd":       ("OECD.SDD.NAD", "DSD_NAMAIN1@DF_QNA_EXPENDITURE_USD", "1.1"),
    "GDP_annual":              ("OECD.SDD.NAD", "DSD_NAMAIN10@DF_TABLE1", "2.0"),
    "GDP_annual_growth":       ("OECD.SDD.NAD", "DSD_NAMAIN10@DF_TABLE1_EXPENDITURE_GROWTH", "2.0"),

    # 경기 단기지표 (KEI)
    "KEI":                     ("OECD.SDD.STES", "DSD_KEI@DF_KEI", "4.0"),
    "CLI":                     ("OECD.SDD.STES", "DSD_STES@DF_CLI", "4.1"),
    "BTS":                     ("OECD.SDD.STES", "DSD_STES@DF_BTS", "4.0"),
    "consumer_survey":         ("OECD.SDD.STES", "DSD_STES@DF_CS", "4.0"),
    "financial_market":        ("OECD.SDD.STES", "DSD_STES@DF_FINMARK", "4.0"),
    "monetary_aggregates":     ("OECD.SDD.STES", "DSD_STES@DF_MONAGG", "4.0"),

    # 고용
    "employment":              ("OECD.SDD.TPS", "DSD_ALFS@DF_ALFS_EMP", "4.0"),
    "labor_force_summary":     ("OECD.SDD.TPS", "DSD_ALFS@DF_SUMTAB", "4.0"),
}

# ── KEI MEASURE 코드 사전 ─────────────────────────────────────────
KEI_MEASURES = {
    "CP":      "소비자물가지수 (CPI)",
    "UNEMP":   "실업률",
    "EMP":     "고용",
    "PRVM":    "산업생산 (제조업)",
    "RS":      "소매판매",
    "EX":      "수출",
    "IM":      "수입",
    "IR3TIB":  "3개월 인터뱅크 금리",
    "IRLT":    "장기 국채수익률",
    "IRSTCI":  "단기 정책금리",
    "SHARE":   "주가지수",
    "BCICP":   "경기선행지수 (종합)",
    "CCICP":   "소비자신뢰지수",
    "CC":      "소비자신뢰지수 (원본)",
    "LI":      "경기선행지수",
    "MABM":    "통화량 (M1)",
    "MANM":    "통화량 (M3)",
    "TOCAPA":  "설비가동률",
    "TOVM":    "제조업 수주",
}


def list_dataflows(keyword: str = None) -> pd.DataFrame:
    """사용 가능한 데이터플로우 검색"""
    rows = []
    for name, (agency, df_id, ver) in DATAFLOWS.items():
        rows.append({"name": name, "agency": agency, "dataflow_id": df_id, "version": ver})
    df = pd.DataFrame(rows)
    if keyword:
        mask = df["name"].str.contains(keyword, case=False, na=False)
        return df[mask].reset_index(drop=True)
    return df


if __name__ == "__main__":
    print("=" * 60)
    print("OECD SDMX API 테스트")
    print("=" * 60)

    # 1) 분기 GDP 성장률
    print("\n[1] 분기 실질 GDP 성장률 (한·미·일, 2024~)")
    try:
        df = get_gdp_quarterly("KOR+USA+JPN", start="2024-Q1")
        if not df.empty:
            cols = [c for c in ["REF_AREA", "TRANSFORMATION", "TIME_PERIOD", "OBS_VALUE"]
                    if c in df.columns]
            print(df[cols].to_string(index=False))
        else:
            print("  >> 데이터 없음")
    except Exception as e:
        print(f"  >> 오류: {e}")

    # 2) CPI
    print("\n[2] CPI (한·미·일, 2024~)")
    try:
        df = get_cpi("KOR+USA+JPN", start="2024-01")
        if not df.empty:
            cols = [c for c in ["REF_AREA", "UNIT_MEASURE", "TRANSFORMATION",
                                "TIME_PERIOD", "OBS_VALUE"]
                    if c in df.columns]
            print(df[cols].head(20).to_string(index=False))
        else:
            print("  >> 데이터 없음")
    except Exception as e:
        print(f"  >> 오류: {e}")

    # 3) 실업률
    print("\n[3] 실업률 (한·미·일, 2024~)")
    try:
        df = get_unemployment("KOR+USA+JPN", start="2024-01")
        if not df.empty:
            cols = [c for c in ["REF_AREA", "TIME_PERIOD", "OBS_VALUE"] if c in df.columns]
            print(df[cols].head(20).to_string(index=False))
        else:
            print("  >> 데이터 없음")
    except Exception as e:
        print(f"  >> 오류: {e}")

    # 4) 금리
    print("\n[4] 금리 (한·미·일, 2024~)")
    try:
        df = get_interest_rates("KOR+USA+JPN", start="2024-01")
        if not df.empty:
            cols = [c for c in ["REF_AREA", "MEASURE", "TIME_PERIOD", "OBS_VALUE"]
                    if c in df.columns]
            print(df[cols].head(20).to_string(index=False))
        else:
            print("  >> 데이터 없음")
    except Exception as e:
        print(f"  >> 오류: {e}")

    print("\n" + "=" * 60)
    print("사용 예시:")
    print("  from oecd_api import get_gdp_quarterly, get_cpi, get_unemployment")
    print('  df = get_gdp_quarterly("KOR+USA+JPN+DEU", "2020-Q1")')
    print('  df = get_cpi("KOR+USA", "2020-01")')
    print('  df = get_unemployment("KOR+USA", "2020-01")')
    print("=" * 60)
