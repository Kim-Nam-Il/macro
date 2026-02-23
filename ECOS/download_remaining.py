"""
ECOS 미다운로드 통계 중 실용적인 것들 일괄 다운로드
"""

import os
import time
import pandas as pd
from ecos_api import search

SAVE_DIR = "/home/ubuntu/HDD1/ECOS/data"
os.makedirs(SAVE_DIR, exist_ok=True)

DOWNLOADS = [
    # ═══ 채권시장 / 자금순환 ═══
    ("bond_market_monthly",       "901Y120", "M",  "200701", "202612", [], "채권시장별 거래 (월별)"),
    ("govt_bond_monthly",         "191Y001", "M",  "200701", "202612", [], "주요 국공채 발행액/잔액 (월별)"),
    ("bond_issue_nominal",        "282Y001", "Q",  "2007Q1", "2026Q4", [], "채권 발행잔액(명목, 분기)"),
    ("bond_issue_market",         "282Y002", "Q",  "2007Q1", "2026Q4", [], "채권 발행잔액(시가, 분기)"),
    ("bond_net_issue",            "282Y003", "Q",  "2007Q1", "2026Q4", [], "채권 순발행액(시가, 분기)"),
    ("bond_holding",              "282Y004", "Q",  "2007Q1", "2026Q4", [], "채권 보유잔액(시가, 분기)"),
    ("bond_net_acquisition",      "282Y005", "Q",  "2007Q1", "2026Q4", [], "채권 순취득액(시가, 분기)"),
    ("flow_of_funds_key",         "283Y001", "Q",  "2007Q1", "2026Q4", [], "자금순환 주요지표 (분기)"),
    ("flow_of_funds_transaction", "281Y001", "Q",  "2007Q1", "2026Q4", [], "자금순환 금융거래표 (분기)"),
    ("flow_of_funds_balance",     "281Y002", "Q",  "2007Q1", "2026Q4", [], "자금순환 금융자산부채잔액표 (분기)"),

    # ═══ 금융기관 / 통화 상세 ═══
    ("bok_balance_monthly",       "103Y002", "M",  "200701", "202612", [], "한국은행 주요계정 (말잔, 월별)"),
    ("currency_issue_monthly",    "871Y001", "M",  "200701", "202612", [], "화폐발행잔액 (월별)"),
    ("reserve_req_monthly",       "814Y001", "M",  "200701", "202612", [], "예금은행 지급준비액 (월별)"),
    ("bok_won_loan_monthly",      "641Y001", "M",  "200701", "202612", [], "한국은행 원화대출금 (월별)"),
    ("household_loan_monthly",    "151Y002", "M",  "200701", "202612", [], "예금취급기관 가계대출 업권별 (월별)"),
    ("household_loan_use_monthly","151Y005", "M",  "200701", "202612", [], "예금취급기관 가계대출 용도별 (월별)"),
    ("nonbank_deposit_rate",      "121Y004", "M",  "200701", "202612", [], "비은행금융기관 수신금리 (월별)"),
    ("bank_fixed_var_rate",       "121Y010", "M",  "200701", "202612", [], "예금은행 고정/변동금리대출 비중 - 신규 (월별)"),
    ("bank_fixed_var_balance",    "121Y011", "M",  "200701", "202612", [], "예금은행 고정/변동금리대출 비중 - 잔액 (월별)"),
    ("delinquency_1m_monthly",    "901Y124", "M",  "200701", "202612", [], "은행대출금 연체율 1개월 이상 (월별)"),
    ("insurance_monthly",         "901Y059", "M",  "200701", "202612", [], "보험계약실적 (월별)"),

    # ═══ 재정 ═══
    ("fiscal_balance_monthly",    "901Y013", "M",  "200701", "202612", [], "통합재정수지 (월별)"),
    ("tax_revenue_annual",        "901Y081", "A",  "2007",   "2026",   [], "조세징수액 (연간)"),

    # ═══ 주식시장 상세 ═══
    ("stock_market_monthly",      "901Y014", "M",  "200701", "202612", [], "주식시장 월별 (상장/거래/시총)"),

    # ═══ GDP 상세 ═══
    ("gdp_activity_nominal_q",    "200Y103", "Q",  "2007Q1", "2026Q4", [], "경제활동별 GDP·GNI (계절조정, 명목, 분기)"),
    ("gdp_activity_real_q",       "200Y104", "Q",  "2007Q1", "2026Q4", [], "경제활동별 GDP·GNI (계절조정, 실질, 분기)"),
    ("gdp_activity_raw_q",        "200Y106", "Q",  "2007Q1", "2026Q4", [], "경제활동별 GDP·GNI (원계열, 실질, 분기·연간)"),
    ("gdp_deflator_q",            "200Y111", "Q",  "2007Q1", "2026Q4", [], "경제활동별 GDP 디플레이터 (분기·연간)"),
    ("gdp_expenditure_deflator",  "200Y112", "Q",  "2007Q1", "2026Q4", [], "지출 GDP 디플레이터 (분기·연간)"),
    ("consumption_purpose_q",     "200Y140", "Q",  "2007Q1", "2026Q4", [], "가계 목적별 최종소비지출 (계절조정, 명목, 분기)"),
    ("national_income_annual",    "200Y116", "A",  "2007",   "2026",   [], "국민소득과 부문별 국민처분가능소득 (연간)"),
    ("savings_invest_sa_q",       "200Y155", "Q",  "2007Q1", "2026Q4", [], "총저축과 총투자 (계절조정, 명목, 분기)"),

    # ═══ 물가 상세 ═══
    ("cpi_special_monthly",       "901Y010", "M",  "200701", "202612", [], "소비자물가지수 특수분류 (월별)"),
    ("export_price_monthly",      "402Y014", "M",  "200701", "202612", [], "수출물가지수 기본분류 (월별)"),
    ("import_price_monthly",      "401Y015", "M",  "200701", "202612", [], "수입물가지수 기본분류 (월별)"),
    ("import_price_use_monthly",  "401Y018", "M",  "200701", "202612", [], "수입물가지수 용도별 (월별)"),
    ("apt_price_monthly",         "901Y089", "M",  "200701", "202612", [], "아파트 매매 실거래가격지수 (월별)"),
    ("land_price_monthly",        "901Y064", "M",  "200701", "202612", [], "지역별 지가변동률 (월별)"),
    ("house_price_type_monthly",  "901Y113", "M",  "200701", "202612", [], "유형별 주택매매가격지수 (2025기준, 월별)"),
    ("house_rent_type_monthly",   "901Y114", "M",  "200701", "202612", [], "유형별 주택전세가격지수 (2025기준, 월별)"),
    ("office_rent_quarterly",     "901Y096", "Q",  "2007Q1", "2026Q4", [], "상권별 오피스임대가격지수 (분기)"),

    # ═══ 무역 상세 ═══
    ("trade_continent_monthly",   "901Y119", "M",  "200701", "202612", [], "대륙별 수출입 (월별)"),
    ("trade_type_monthly",        "901Y092", "M",  "200701", "202612", [], "성질별 수출입 (월별)"),
    ("export_value_index",        "403Y001", "M",  "200701", "202612", [], "수출금액지수 (월별)"),
    ("export_volume_index",       "403Y002", "M",  "200701", "202612", [], "수출물량지수 (월별)"),
    ("import_value_index",        "403Y003", "M",  "200701", "202612", [], "수입금액지수 (월별)"),
    ("import_volume_index",       "403Y004", "M",  "200701", "202612", [], "수입물량지수 (월별)"),
    ("fdi_outward_monthly",       "901Y060", "M",  "200701", "202612", [], "해외직접투자 (월별)"),
    ("fdi_inward_quarterly",      "901Y061", "Q",  "2007Q1", "2026Q4", [], "외국인직접투자 (분기)"),
    ("bop_service_monthly",       "301Y014", "M",  "200701", "202612", [], "서비스무역 세분류 (월별)"),
    ("current_account_region",    "301Y015", "A",  "2007",   "2026",   [], "지역별 경상수지 (연간)"),

    # ═══ 대외 포지션 상세 ═══
    ("external_debt_detail",      "311Y004", "Q",  "2007Q1", "2026Q4", [], "대외채무 상세 (분기)"),
    ("external_claim_detail",     "311Y005", "Q",  "2007Q1", "2026Q4", [], "대외채권 상세 (분기)"),
    ("iip_regional_annual",       "311Y002", "A",  "2007",   "2026",   [], "지역별 국제투자대조표 (연간)"),
    ("iip_currency_annual",       "311Y003", "A",  "2007",   "2026",   [], "통화별 국제투자대조표 (연간)"),

    # ═══ 산업/실물경제 ═══
    ("capex_index_monthly",       "901Y066", "M",  "200701", "202612", [], "설비투자지수 (월별)"),
    ("industry_prod_monthly",     "901Y032", "M",  "200701", "202612", [], "산업별 생산/출하/재고 지수 (월별)"),
    ("mfg_capacity_monthly",      "901Y035", "M",  "200701", "202612", [], "제조업 생산능력/가동률 지수 (월별)"),
    ("mfg_inventory_monthly",     "901Y026", "M",  "200701", "202612", [], "제조업 재고율 (월별)"),
    ("construction_monthly",      "901Y020", "M",  "200701", "202612", [], "국내건설수주액 (월별)"),
    ("unsold_housing_monthly",    "901Y074", "M",  "200701", "202612", [], "미분양주택현황 (월별)"),
    ("housing_permit_monthly",    "901Y105", "M",  "200701", "202612", [], "주택건설인허가실적 (월별)"),
    ("service_prod_monthly",      "901Y038", "M",  "200701", "202612", [], "산업별 서비스업생산지수 (월별)"),
    ("retail_sales_monthly",      "901Y098", "M",  "200701", "202612", [], "소매업태별 판매액지수 (월별)"),
    ("electricity_monthly",       "901Y019", "M",  "200701", "202612", [], "부문별 전력사용량 (월별)"),
    ("energy_supply_monthly",     "901Y072", "M",  "200701", "202612", [], "일차에너지 공급 (월별)"),
    ("machine_order_monthly",     "901Y018", "M",  "200701", "202612", [], "기계수주액 (월별)"),
    ("auto_reg_monthly",          "901Y099", "M",  "200701", "202612", [], "자동차등록대수 (월별)"),

    # ═══ 고용/임금 ═══
    ("wage_monthly",              "901Y052", "M",  "200701", "202612", [], "산업/규모별 임금 및 근로시간 (월별)"),
    ("employment_insurance",      "901Y083", "M",  "200701", "202612", [], "고용보험 가입자수 (월별)"),
    ("unemployment_benefit",      "901Y084", "M",  "200701", "202612", [], "실업급여수급실적 (월별)"),
    ("labor_productivity_q",      "901Y107", "Q",  "2007Q1", "2026Q4", [], "노동생산성지수 (분기)"),
    ("unit_labor_cost_q",         "901Y088", "Q",  "2007Q1", "2026Q4", [], "단위노동비용지수 (분기)"),

    # ═══ 심리/서베이 상세 ═══
    ("bsi_forecast_monthly",      "512Y014", "M",  "200701", "202612", [], "기업경기조사 BSI 전망 (월별)"),
    ("bsi_weighted_monthly",      "512Y015", "M",  "200701", "202612", [], "기업경기조사 BSI 매출액가중 실적 (월별)"),
    ("loan_attitude_quarterly",   "514Y001", "Q",  "2007Q1", "2026Q4", [], "대출행태서베이 - 대출태도 (분기)"),
    ("loan_risk_quarterly",       "514Y002", "Q",  "2007Q1", "2026Q4", [], "대출행태서베이 - 신용위험 (분기)"),
    ("loan_demand_quarterly",     "514Y003", "Q",  "2007Q1", "2026Q4", [], "대출행태서베이 - 대출수요 (분기)"),

    # ═══ 가계/소득분배 ═══
    ("household_asset_region",    "903Y201", "A",  "2007",   "2026",   [], "시도별 가계 자산/부채/소득 (연간)"),
    ("income_distribution",       "901Y112", "A",  "2007",   "2026",   [], "소득분배지표 (연간)"),
    ("household_income_q",        "901Y117", "Q",  "2007Q1", "2026Q4", [], "가구당 월평균 가계수지 (분기)"),

    # ═══ 기업경영분석 핵심 ═══
    ("corp_growth_annual",        "501Y005", "A",  "2007",   "2026",   [], "기업경영 성장성 지표 (연간)"),
    ("corp_profit_annual",        "501Y006", "A",  "2007",   "2026",   [], "기업경영 손익 지표 (연간)"),
    ("corp_asset_annual",         "501Y007", "A",  "2007",   "2026",   [], "기업경영 자산/자본 지표 (연간)"),
    ("corp_bs_annual",            "501Y001", "A",  "2007",   "2026",   [], "기업 재무상태표 (연간)"),
    ("corp_is_annual",            "501Y002", "A",  "2007",   "2026",   [], "기업 손익계산서 (연간)"),
    ("corp_growth_q",             "502Y001", "Q",  "2007Q1", "2026Q4", [], "기업경영 성장성 분기"),
    ("corp_profit_q",             "502Y002", "Q",  "2007Q1", "2026Q4", [], "기업경영 손익 분기"),

    # ═══ 해외 비교 추가 ═══
    ("global_m0_monthly",         "902Y004", "M",  "200701", "202612", [], "주요국 본원통화 (IMF, 월별)"),
    ("global_m2_monthly",         "902Y005", "M",  "200701", "202612", [], "주요국 광의통화 (IMF, 월별)"),
    ("global_ppi_monthly",        "902Y007", "M",  "200701", "202612", [], "주요국 생산자물가지수 (IMF, 월별)"),
    ("global_export_monthly",     "902Y012", "M",  "200701", "202612", [], "주요국 수출 통관기준 (IMF, 월별)"),
    ("global_import_monthly",     "902Y013", "M",  "200701", "202612", [], "주요국 수입 통관기준 (IMF, 월별)"),
    ("global_fx_reserve_monthly", "902Y014", "M",  "200701", "202612", [], "주요국 외환보유액 (IMF, 월별)"),
    ("global_indprod_monthly",    "902Y020", "M",  "200701", "202612", [], "주요국 산업생산지수 계절조정 (OECD, 월별)"),
    ("global_current_acct_q",     "902Y009", "Q",  "2007Q1", "2026Q4", [], "주요국 경상수지 (IMF, 분기)"),

    # ═══ 북한 ═══
    ("nk_gdp_annual",             "251Y001", "A",  "2007",   "2026",   [], "북한 경제활동별 GDP (연간)"),
    ("nk_sk_ratio_annual",        "251Y002", "A",  "2007",   "2026",   [], "남북한 경제 배율 (연간)"),
]


def download_one(file, stat, cycle, start, end, items, desc):
    path = os.path.join(SAVE_DIR, f"{file}.parquet")
    if os.path.exists(path):
        return path  # skip existing

    try:
        df = search(stat, cycle, start, end,
                     items[0] if len(items) > 0 else "",
                     items[1] if len(items) > 1 else "",
                     items[2] if len(items) > 2 else "",
                     items[3] if len(items) > 3 else "")
        if df.empty:
            return None
        df.to_parquet(path, index=False)
        size = os.path.getsize(path)
        size_str = f"{size/1024:.0f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
        print(f"  {file:40s} {len(df):>8,}행  {size_str:>8s}  {desc}")
        return path
    except Exception as e:
        print(f"  {file:40s} 오류: {e}")
        return None


if __name__ == "__main__":
    print("=" * 80)
    print(f"ECOS 추가 다운로드: {len(DOWNLOADS)}개")
    print("=" * 80)

    success, failed = 0, 0
    for i, (file, stat, cycle, start, end, items, desc) in enumerate(DOWNLOADS, 1):
        path = download_one(file, stat, cycle, start, end, items, desc)
        if path:
            success += 1
        else:
            failed += 1
            print(f"  {file:40s} [데이터없음] {desc}")
        if i % 10 == 0:
            time.sleep(0.5)
        else:
            time.sleep(0.2)

    print(f"\n성공: {success}, 실패/없음: {failed}")
    all_files = [f for f in os.listdir(SAVE_DIR) if f.endswith('.parquet')]
    total = sum(os.path.getsize(os.path.join(SAVE_DIR, f)) for f in all_files)
    print(f"전체: {len(all_files)}개 파일, {total/1024/1024:.1f}MB")
