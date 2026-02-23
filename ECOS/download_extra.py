"""
ECOS 추가 데이터 다운로드 (채권, 신용, 증시, 유동성 등)
실행: python3 download_extra.py
"""

import os
import time
import pandas as pd
from ecos_api import search

SAVE_DIR = "/home/ubuntu/HDD1/ECOS/data"
os.makedirs(SAVE_DIR, exist_ok=True)

DOWNLOADS = [
    # ═══ 채권 ═══
    {
        "file": "bond_trade_monthly",
        "stat": "901Y015", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "채권종류별 거래 (국채/지방채/특수채/회사채, 월별)",
    },
    {
        "file": "bond_issue_balance",
        "stat": "282Y006", "cycle": "Q",
        "start": "2007Q1", "end": "2026Q4",
        "items": [],
        "desc": "채권발행-보유관계표 (잔액, 시가, 분기)",
    },

    # ═══ 예금은행 금리 (신규취급액 기준) ═══
    {
        "file": "bank_loan_rate_monthly",
        "stat": "121Y006", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "예금은행 대출금리 - 신규취급액 (월별)",
    },
    {
        "file": "bank_deposit_rate_monthly",
        "stat": "121Y002", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "예금은행 수신금리 - 신규취급액 (월별)",
    },
    {
        "file": "bank_loan_rate_balance",
        "stat": "121Y015", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "예금은행 대출금리 - 잔액 기준 (월별)",
    },
    {
        "file": "bank_deposit_rate_balance",
        "stat": "121Y013", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "예금은행 수신금리 - 잔액 기준 (월별)",
    },
    {
        "file": "nonbank_loan_rate_monthly",
        "stat": "121Y007", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "비은행금융기관 대출금리 - 신규취급액 (월별)",
    },

    # ═══ 대출/신용 ═══
    {
        "file": "bank_loan_balance_monthly",
        "stat": "104Y016", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "예금은행 대출금 (말잔, 월별)",
    },
    {
        "file": "household_credit_quarterly",
        "stat": "151Y001", "cycle": "Q",
        "start": "2007Q1", "end": "2026Q4",
        "items": [],
        "desc": "가계신용 - 업권별 (분기)",
    },
    {
        "file": "household_credit_use_quarterly",
        "stat": "151Y004", "cycle": "Q",
        "start": "2007Q1", "end": "2026Q4",
        "items": [],
        "desc": "가계신용 - 용도별 (분기)",
    },
    {
        "file": "loan_delinquency_monthly",
        "stat": "901Y054", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "은행대출금 연체율 (1일 이상, 월별)",
    },
    {
        "file": "industry_loan_quarterly",
        "stat": "131Y016", "cycle": "Q",
        "start": "2007Q1", "end": "2026Q4",
        "items": [],
        "desc": "산업별 대출금 - 예금취급기관 전산업 (분기)",
    },

    # ═══ 증시 ═══
    {
        "file": "stock_index_daily",
        "stat": "802Y001", "cycle": "D",
        "start": "20070101", "end": "20261231",
        "items": [],
        "desc": "주식거래/주가지수 (KOSPI/KOSDAQ/시총/외국인, 일별)",
    },
    {
        "file": "investor_trade_monthly",
        "stat": "901Y055", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "투자자별 주식거래 (기관/개인/외국인, 월별)",
    },
    {
        "file": "stock_margin_monthly",
        "stat": "901Y056", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "증시주변자금동향 (예탁금/신용융자/RP, 월별)",
    },
    {
        "file": "stock_futures_monthly",
        "stat": "901Y057", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "주가지수 선물거래 (월별)",
    },
    {
        "file": "stock_options_monthly",
        "stat": "901Y058", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "주가지수 옵션거래 (월별)",
    },

    # ═══ 유동성/통화 ═══
    {
        "file": "liquidity_L_monthly",
        "stat": "172Y002", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "L(광의유동성) 구성내역 (말잔, 원계열, 월별)",
    },
    {
        "file": "m2_detail_monthly",
        "stat": "161Y006", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "M2 전체 상품별 구성내역 (평잔, 원계열, 월별)",
    },

    # ═══ 수출입/경상수지 ═══
    {
        "file": "trade_summary_monthly",
        "stat": "901Y118", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "수출입 총괄 (월별)",
    },
    {
        "file": "trade_by_country_monthly",
        "stat": "901Y121", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "국가별 수출입 (월별)",
    },
    {
        "file": "current_account_sa_monthly",
        "stat": "301Y017", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "경상수지 계절조정 (월별)",
    },
    {
        "file": "terms_of_trade_monthly",
        "stat": "403Y005", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "교역조건지수 (월별)",
    },

    # ═══ 대외 포지션 ═══
    {
        "file": "iip_quarterly",
        "stat": "311Y001", "cycle": "Q",
        "start": "2007Q1", "end": "2026Q4",
        "items": [],
        "desc": "국제투자대조표 IIP (분기)",
    },
    {
        "file": "external_debt_quarterly",
        "stat": "311Y006", "cycle": "Q",
        "start": "2007Q1", "end": "2026Q4",
        "items": [],
        "desc": "외채 및 대외채권 (분기)",
    },

    # ═══ 해외 금융시장 ═══
    {
        "file": "global_stock_index_monthly",
        "stat": "902Y002", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "주요국 주가지수 (OECD, 월별)",
    },
    {
        "file": "global_interest_rate_monthly",
        "stat": "902Y023", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "주요국제금리 (OECD, 월별)",
    },
    {
        "file": "global_unemployment_monthly",
        "stat": "902Y021", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "주요국 실업률 (계절조정, OECD, 월별)",
    },
    {
        "file": "global_growth_quarterly",
        "stat": "902Y015", "cycle": "Q",
        "start": "2007Q1", "end": "2026Q4",
        "items": [],
        "desc": "주요국 경제성장률 (OECD, 분기)",
    },

    # ═══ 심리/기대 ═══
    {
        "file": "expected_inflation_monthly",
        "stat": "511Y003", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "기대인플레이션율 (월별)",
    },
    {
        "file": "consumer_survey_monthly",
        "stat": "511Y002", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "소비자동향조사 (CSI 전국, 월별)",
    },
    {
        "file": "bsi_monthly",
        "stat": "512Y013", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "기업경기조사 BSI 실적 (월별)",
    },

    # ═══ 기타 ═══
    {
        "file": "bill_dishonor_monthly",
        "stat": "801Y002", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "어음교환 및 부도 (월별)",
    },
    {
        "file": "credit_card_monthly",
        "stat": "601Y003", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "신용카드 이용실적 (월별)",
    },
    {
        "file": "savings_investment_quarterly",
        "stat": "200Y156", "cycle": "Q",
        "start": "2007Q1", "end": "2026Q4",
        "items": [],
        "desc": "총저축과 총투자 (원계열, 명목, 분기·연간)",
    },
    {
        "file": "industrial_production_monthly",
        "stat": "901Y033", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "전산업생산지수 (농림어업제외, 월별)",
    },
]


def download_one(d):
    """단일 통계 다운로드 → parquet 저장"""
    path = os.path.join(SAVE_DIR, f"{d['file']}.parquet")
    print(f"\n{'='*60}")
    print(f"[다운로드] {d['desc']}")
    print(f"  코드: {d['stat']} | 주기: {d['cycle']} | {d['start']}~{d['end']}")

    try:
        items = d.get("items", [])
        df = search(
            d["stat"], d["cycle"], d["start"], d["end"],
            items[0] if len(items) > 0 else "",
            items[1] if len(items) > 1 else "",
            items[2] if len(items) > 2 else "",
            items[3] if len(items) > 3 else "",
        )

        if df.empty:
            print(f"  >> 데이터 없음, 건너뜀")
            return None

        # 100,000건 한도 체크
        if len(df) == 100000:
            print(f"  >> 경고: 100,000건 한도 도달, 추가 다운로드 필요")

        df.to_parquet(path, index=False)
        print(f"  >> 저장: {path}")
        print(f"  >> {len(df):,}행 × {len(df.columns)}열")
        return path

    except Exception as e:
        print(f"  >> 오류: {e}")
        return None


def download_chunked_daily(file, stat, start_year, end_year, desc, items=None):
    """일별 데이터를 연도 단위로 분할 다운로드 (100k 한도 우회)"""
    path = os.path.join(SAVE_DIR, f"{file}.parquet")
    print(f"\n{'='*60}")
    print(f"[다운로드-분할] {desc}")
    print(f"  코드: {stat} | {start_year}~{end_year} (연도별)")

    all_dfs = []
    for year in range(start_year, end_year + 1):
        s = f"{year}0101"
        e = f"{year}1231"
        try:
            it = items or []
            df = search(stat, "D", s, e,
                        it[0] if len(it) > 0 else "",
                        it[1] if len(it) > 1 else "",
                        it[2] if len(it) > 2 else "",
                        it[3] if len(it) > 3 else "")
            if not df.empty:
                all_dfs.append(df)
                print(f"  {year}: {len(df):,}행", end="")
            else:
                print(f"  {year}: 0", end="")
        except Exception as ex:
            print(f"  {year}: 오류({ex})", end="")
        time.sleep(0.2)

    if not all_dfs:
        print(f"\n  >> 데이터 없음")
        return None

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=[c for c in ['ITEM_CODE1', 'TIME'] if c in combined.columns])
    combined = combined.sort_values('TIME').reset_index(drop=True)
    combined.to_parquet(path, index=False)
    print(f"\n  >> 저장: {path}")
    print(f"  >> 최종: {len(combined):,}행, {combined['TIME'].min()} ~ {combined['TIME'].max()}")
    return path


if __name__ == "__main__":
    print("=" * 60)
    print("ECOS 추가 데이터 다운로드 (채권/신용/증시/유동성)")
    print(f"저장 경로: {SAVE_DIR}")
    print(f"대상: {len(DOWNLOADS)}개 통계 + 일별 분할 다운로드")
    print("=" * 60)

    results = []

    # 일반 다운로드
    for i, d in enumerate(DOWNLOADS, 1):
        print(f"\n[{i}/{len(DOWNLOADS)}]", end="")
        path = download_one(d)
        results.append((d["file"], d["desc"], path))
        time.sleep(0.3)

    # 일별 데이터 분할 다운로드 (100k 한도 우회)
    print("\n\n>>> 일별 데이터 분할 다운로드 <<<")

    # stock_index_daily가 100k 넘으면 재다운로드
    stock_path = os.path.join(SAVE_DIR, "stock_index_daily.parquet")
    if os.path.exists(stock_path):
        df_check = pd.read_parquet(stock_path)
        if len(df_check) >= 100000:
            print("\n  stock_index_daily 100k 한도 도달 → 연도별 재다운로드")
            path = download_chunked_daily(
                "stock_index_daily", "802Y001", 2007, 2026,
                "주식거래/주가지수 일별 (분할)")
            # 결과 업데이트
            results = [(f, d, path if f == "stock_index_daily" else p) for f, d, p in results]

    # 결과 요약
    print("\n\n" + "=" * 60)
    print("다운로드 결과 요약")
    print("=" * 60)

    success = [(f, d, p) for f, d, p in results if p]
    failed = [(f, d, p) for f, d, p in results if not p]

    print(f"\n성공: {len(success)}/{len(results)}")
    for f, d, p in success:
        size = os.path.getsize(p)
        size_str = f"{size/1024:.0f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
        print(f"  {f:40s} {size_str:>8s}  {d}")

    if failed:
        print(f"\n실패/데이터없음: {len(failed)}")
        for f, d, _ in failed:
            print(f"  {f:40s}  {d}")

    total = sum(os.path.getsize(p) for _, _, p in success)
    print(f"\n이번 다운로드 용량: {total/1024/1024:.1f}MB")

    # 전체 파일 합산
    all_files = [os.path.join(SAVE_DIR, f) for f in os.listdir(SAVE_DIR) if f.endswith('.parquet')]
    grand_total = sum(os.path.getsize(f) for f in all_files)
    print(f"전체 data/ 용량: {grand_total/1024/1024:.1f}MB ({len(all_files)}개 파일)")
