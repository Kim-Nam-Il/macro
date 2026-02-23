"""
한국은행 ECOS Open API 데이터 다운로드 모듈
https://ecos.bok.or.kr/api/
"""

import requests
import pandas as pd
import json
import time

API_KEY = "QEJYMXQ0WLAQYDKZC54Y"
BASE_URL = "https://ecos.bok.or.kr/api"


def _request(service, params="", lang="kr", start=1, end=100000):
    """ECOS API 기본 요청 함수"""
    url = f"{BASE_URL}/{service}/{API_KEY}/json/{lang}/{start}/{end}/{params}"
    resp = requests.get(url, timeout=30)
    data = resp.json()

    # 에러 체크
    if "RESULT" in data:
        code = data["RESULT"]["CODE"]
        msg = data["RESULT"]["MESSAGE"]
        if code.startswith("ERROR"):
            raise Exception(f"[{code}] {msg}")
        if code == "INFO-200":
            print(f"  >> 데이터 없음: {msg}")
            return []

    # 서비스 이름에 해당하는 키에서 row 추출
    for key in data:
        if key != "RESULT" and "row" in data[key]:
            return data[key]["row"]

    return []


def get_stat_table_list(stat_code=""):
    """
    서비스 통계 목록 조회

    Parameters:
        stat_code: 통계표코드 (빈 문자열이면 전체 목록)

    Returns:
        DataFrame with columns: P_STAT_CODE, STAT_CODE, STAT_NAME, CYCLE, SRCH_YN, ORG_NAME
    """
    rows = _request("StatisticTableList", stat_code)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def get_stat_item_list(stat_code):
    """
    통계 세부항목 목록 조회

    Parameters:
        stat_code: 통계표코드 (예: "901Y009")

    Returns:
        DataFrame with item codes and names
    """
    rows = _request("StatisticItemList", stat_code)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def search(stat_code, cycle, start_date, end_date,
           item_code1="", item_code2="", item_code3="", item_code4=""):
    """
    통계 데이터 조회 (StatisticSearch)

    Parameters:
        stat_code:  통계표코드 (예: "901Y009")
        cycle:      주기 (A:연, S:반년, Q:분기, M:월, SM:반월, D:일)
        start_date: 검색시작일자 (예: "2020", "202301", "20230101")
        end_date:   검색종료일자
        item_code1~4: 통계항목코드 (선택)

    Returns:
        DataFrame with time series data
    """
    params = f"{stat_code}/{cycle}/{start_date}/{end_date}"
    for code in [item_code1, item_code2, item_code3, item_code4]:
        params += f"/{code}"

    rows = _request("StatisticSearch", params)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def get_key_stat_list():
    """100대 통계지표 조회"""
    rows = _request("KeyStatisticList")
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def search_stat_word(word):
    """통계용어사전 검색"""
    rows = _request("StatisticWord", word)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def find_tables(keyword):
    """
    통계표 이름으로 검색 (키워드 포함 필터링)

    Parameters:
        keyword: 검색할 키워드 (예: "금리", "환율", "GDP", "물가")

    Returns:
        검색 가능한 통계표 목록 DataFrame
    """
    df = get_stat_table_list()
    if df.empty:
        return df
    mask = df["STAT_NAME"].str.contains(keyword, na=False) & (df["SRCH_YN"] == "Y")
    result = df[mask][["STAT_CODE", "STAT_NAME", "CYCLE", "ORG_NAME"]].reset_index(drop=True)
    return result


# ── 주요 통계코드 사전 ──────────────────────────────────────────
STAT_CODES = {
    # 통화/금융
    "본원통화(평잔,계절조정)": ("102Y004", "M"),
    "본원통화(말잔,원계열)":   ("102Y001", "M"),
    "M1(평잔,계절조정)":      ("161Y001", "M"),
    "M2(평잔,계절조정)":      ("101Y004", "M"),

    # 금리
    "한국은행 기준금리":      ("722Y001", "MM"),
    "시장금리(일별)":         ("817Y002", "D"),
    "예금은행 금리":          ("121Y002", "M"),

    # 환율
    "주요국 환율(일별)":      ("731Y003", "D"),
    "원/달러 환율(월별)":     ("731Y004", "M"),

    # 물가
    "소비자물가지수":         ("901Y009", "A"),
    "소비자물가지수(월)":     ("901Y009", "M"),
    "생산자물가지수":         ("404Y014", "M"),

    # 국민소득/GDP
    "GDP(명목,연간)":         ("200Y113", "A"),
    "GDP(명목,분기)":         ("200Y107", "Q"),
    "GDP(실질,분기)":         ("200Y108", "Q"),
    "GDP(원계열,명목)":       ("200Y109", "Q"),
    "GDP(원계열,실질)":       ("200Y110", "Q"),

    # 국제수지
    "국제수지":               ("301Y013", "M"),

    # 경기/고용
    "경제심리지수":           ("513Y001", "M"),
    "고용동향":               ("901Y056", "M"),

    # 부동산
    "주택매매가격지수":       ("901Y062", "M"),
    "전세가격지수":           ("901Y063", "M"),
}


if __name__ == "__main__":
    print("=" * 60)
    print("한국은행 ECOS API 테스트")
    print("=" * 60)

    # 1) 소비자물가지수 (연간, 총지수만)
    print("\n[1] 소비자물가지수 (연간, 2020~2024)")
    df = search("901Y009", "A", "2020", "2024", "0")
    if not df.empty:
        print(df[["ITEM_NAME1", "TIME", "DATA_VALUE", "UNIT_NAME"]].to_string(index=False))

    # 2) GDP 실질 (연간)
    print("\n[2] GDP 실질성장률 (연간, 2020~2024)")
    df = search("200Y003", "A", "2020", "2024")
    if not df.empty:
        subset = df[df["ITEM_NAME1"].str.contains("국내총생산", na=False)].head(5)
        if not subset.empty:
            print(subset[["ITEM_NAME1", "TIME", "DATA_VALUE", "UNIT_NAME"]].to_string(index=False))
        else:
            print(df[["ITEM_NAME1", "TIME", "DATA_VALUE"]].head(10).to_string(index=False))

    # 3) 통계표 키워드 검색 예시
    print("\n[3] '금리' 관련 통계표 검색")
    df = find_tables("금리")
    if not df.empty:
        print(df.head(10).to_string(index=False))

    print("\n" + "=" * 60)
    print("사용 예시:")
    print("  from ecos_api import search, find_tables, STAT_CODES")
    print('  df = search("901Y009", "M", "202301", "202412", "0")')
    print('  df = find_tables("환율")')
    print("=" * 60)
