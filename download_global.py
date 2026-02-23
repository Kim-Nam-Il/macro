"""
글로벌 거시경제 데이터 통합 다운로드 (FRED + OECD + BIS + IMF + WorldBank + Factbook)
성장·물가·고용·금리·신용·부동산 → parquet/csv 저장

실행: python3 download_global.py              # 전체 (parquet만)
      python3 download_global.py --csv        # 전체 (parquet + csv)
      python3 download_global.py --csv imf wb # 선택적 + csv
"""

import os
import sys
import time
import pandas as pd

# ── 설정 ──────────────────────────────────────────────────────────
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(SAVE_DIR, exist_ok=True)

# CSV 동시 저장 플래그 (--csv)
SAVE_CSV = "--csv" in sys.argv

# FRED API 키 (없으면 FRED 건너뜀)
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

# 대상 국가
OECD_COUNTRIES = "KOR+USA+JPN+DEU+GBR+FRA+CHN+CAN+AUS+ITA"
BIS_COUNTRIES = "KR+US+JP+DE+GB+FR+CN+CA+AU+IT"
IMF_COUNTRIES = "USA/KOR/JPN/DEU/GBR/FRA/CHN/ITA/CAN/AUS/MEX/BRA/IND/IDN/TUR"
WB_COUNTRIES = "US;KR;JP;DE;GB;FR;CN;IT;CA;AU;MX;BR;IN;ID;TR"

# 기간
START_YEAR = "2007"
START_YEAR_INT = 2007
START_MONTH = "2007-01"
START_QUARTER = "2007-Q1"


# ── 다운로드 작업 정의 ────────────────────────────────────────────

def _downloads_fred():
    """FRED 다운로드 목록"""
    if not FRED_API_KEY:
        print("[FRED] API 키 없음 → 건너뜀")
        print("  설정: export FRED_API_KEY=your_key")
        return []

    from fred_api import get_series, get_multi_series, set_api_key
    set_api_key(FRED_API_KEY)

    return [
        # ── 성장 ──
        {
            "file": "fred_gdp_real",
            "desc": "[FRED] 미국 실질 GDP (분기, 연율)",
            "func": lambda: get_series("GDPC1", f"{START_YEAR}-01-01"),
        },
        {
            "file": "fred_gdp_growth",
            "desc": "[FRED] 미국 실질 GDP 성장률 (분기, 연율 %)",
            "func": lambda: get_series("A191RL1Q225SBEA", f"{START_YEAR}-01-01"),
        },

        # ── 물가 ──
        {
            "file": "fred_cpi",
            "desc": "[FRED] 미국 CPI 전체 (월별, 계절조정)",
            "func": lambda: get_series("CPIAUCSL", f"{START_YEAR}-01-01"),
        },
        {
            "file": "fred_cpi_core",
            "desc": "[FRED] 미국 Core CPI (식품·에너지 제외)",
            "func": lambda: get_series("CPILFESL", f"{START_YEAR}-01-01"),
        },
        {
            "file": "fred_pce",
            "desc": "[FRED] 미국 PCE 물가지수 (월별)",
            "func": lambda: get_series("PCEPI", f"{START_YEAR}-01-01"),
        },
        {
            "file": "fred_pce_core",
            "desc": "[FRED] 미국 Core PCE (월별)",
            "func": lambda: get_series("PCEPILFE", f"{START_YEAR}-01-01"),
        },

        # ── 고용 ──
        {
            "file": "fred_unemployment",
            "desc": "[FRED] 미국 실업률 (월별, %)",
            "func": lambda: get_series("UNRATE", f"{START_YEAR}-01-01"),
        },
        {
            "file": "fred_payrolls",
            "desc": "[FRED] 미국 비농업 고용자 수 (월별, 천명)",
            "func": lambda: get_series("PAYEMS", f"{START_YEAR}-01-01"),
        },
        {
            "file": "fred_participation",
            "desc": "[FRED] 미국 경제활동참가율 (월별, %)",
            "func": lambda: get_series("CIVPART", f"{START_YEAR}-01-01"),
        },
        {
            "file": "fred_initial_claims",
            "desc": "[FRED] 미국 신규 실업수당 청구 (주별)",
            "func": lambda: get_series("ICSA", f"{START_YEAR}-01-01"),
        },

        # ── 금리 ──
        {
            "file": "fred_fed_funds",
            "desc": "[FRED] 연방기금금리 (월별)",
            "func": lambda: get_series("FEDFUNDS", f"{START_YEAR}-01-01"),
        },
        {
            "file": "fred_treasury_10y",
            "desc": "[FRED] 10년물 국채수익률 (월별)",
            "func": lambda: get_series("DGS10", f"{START_YEAR}-01-01", frequency="m"),
        },
        {
            "file": "fred_treasury_2y",
            "desc": "[FRED] 2년물 국채수익률 (월별)",
            "func": lambda: get_series("DGS2", f"{START_YEAR}-01-01", frequency="m"),
        },
        {
            "file": "fred_term_spread",
            "desc": "[FRED] 장단기 스프레드 10Y-2Y (월별)",
            "func": lambda: get_series("T10Y2Y", f"{START_YEAR}-01-01", frequency="m"),
        },

        # ── 기타 ──
        {
            "file": "fred_industrial_prod",
            "desc": "[FRED] 미국 산업생산지수 (월별)",
            "func": lambda: get_series("INDPRO", f"{START_YEAR}-01-01"),
        },
        {
            "file": "fred_retail_sales",
            "desc": "[FRED] 미국 소매판매 (월별)",
            "func": lambda: get_series("RSXFS", f"{START_YEAR}-01-01"),
        },
        {
            "file": "fred_consumer_sentiment",
            "desc": "[FRED] 미시건 소비자심리지수 (월별)",
            "func": lambda: get_series("UMCSENT", f"{START_YEAR}-01-01"),
        },
        {
            "file": "fred_m2",
            "desc": "[FRED] M2 통화량 (월별)",
            "func": lambda: get_series("M2SL", f"{START_YEAR}-01-01"),
        },
    ]


def _downloads_oecd():
    """OECD 다운로드 목록"""
    from oecd_api import (get_gdp_quarterly, get_gdp_annual, get_gdp_level,
                          get_cpi, get_unemployment, get_interest_rates,
                          get_cli, get_industrial_production)

    return [
        # ── 성장 ──
        {
            "file": "oecd_gdp_quarterly_growth",
            "desc": "[OECD] 분기 실질 GDP 성장률 (주요국)",
            "func": lambda: get_gdp_quarterly(OECD_COUNTRIES, START_QUARTER),
        },
        {
            "file": "oecd_gdp_annual_growth",
            "desc": "[OECD] 연간 GDP 성장률 (주요국)",
            "func": lambda: get_gdp_annual(OECD_COUNTRIES, START_YEAR),
        },
        {
            "file": "oecd_gdp_level_usd",
            "desc": "[OECD] 분기 GDP 수준 (USD, 주요국)",
            "func": lambda: get_gdp_level(OECD_COUNTRIES, START_QUARTER),
        },

        # ── 물가 ──
        {
            "file": "oecd_cpi",
            "desc": "[OECD] CPI (전년비 + 지수, 주요국)",
            "func": lambda: get_cpi(OECD_COUNTRIES, START_MONTH),
        },

        # ── 고용 ──
        {
            "file": "oecd_unemployment",
            "desc": "[OECD] 조화실업률 (주요국, 월별)",
            "func": lambda: get_unemployment(OECD_COUNTRIES, START_MONTH),
        },

        # ── 금리 ──
        {
            "file": "oecd_interest_rates",
            "desc": "[OECD] 단기/장기 금리 (주요국, 월별)",
            "func": lambda: get_interest_rates(OECD_COUNTRIES, START_MONTH),
        },

        # ── 경기선행지수 ──
        {
            "file": "oecd_cli",
            "desc": "[OECD] 경기선행지수 (주요국, 월별)",
            "func": lambda: get_cli(OECD_COUNTRIES, START_MONTH),
        },

        # ── 산업생산 ──
        {
            "file": "oecd_industrial_production",
            "desc": "[OECD] 산업생산지수 (주요국, 월별)",
            "func": lambda: get_industrial_production(OECD_COUNTRIES, START_MONTH),
        },
    ]


def _downloads_bis():
    """BIS 다운로드 목록"""
    from bis_api import (get_cpi_yoy, get_cpi_index, get_policy_rate,
                         get_credit_to_gdp, get_total_credit,
                         get_credit_gap, get_property_prices,
                         get_effective_exchange_rate, get_debt_service_ratio)

    return [
        # ── 물가 ──
        {
            "file": "bis_cpi_yoy",
            "desc": "[BIS] CPI 전년비 (%, 주요국, 월별)",
            "func": lambda: get_cpi_yoy(BIS_COUNTRIES, START_MONTH),
        },
        {
            "file": "bis_cpi_index",
            "desc": "[BIS] CPI 지수 (2010=100, 주요국, 월별)",
            "func": lambda: get_cpi_index(BIS_COUNTRIES, START_MONTH),
        },

        # ── 정책금리 ──
        {
            "file": "bis_policy_rate",
            "desc": "[BIS] 중앙은행 정책금리 (주요국, 월별)",
            "func": lambda: get_policy_rate(BIS_COUNTRIES, START_MONTH),
        },

        # ── 신용 ──
        {
            "file": "bis_credit_private_gdp",
            "desc": "[BIS] 민간 신용/GDP (%, 주요국, 분기)",
            "func": lambda: get_credit_to_gdp(BIS_COUNTRIES, START_QUARTER),
        },
        {
            "file": "bis_credit_household_gdp",
            "desc": "[BIS] 가계 신용/GDP (%, 주요국, 분기)",
            "func": lambda: get_credit_to_gdp(BIS_COUNTRIES, START_QUARTER, borrower="H"),
        },
        {
            "file": "bis_credit_corporate_gdp",
            "desc": "[BIS] 기업 신용/GDP (%, 주요국, 분기)",
            "func": lambda: get_credit_to_gdp(BIS_COUNTRIES, START_QUARTER, borrower="N"),
        },
        {
            "file": "bis_credit_govt_gdp",
            "desc": "[BIS] 정부 신용/GDP (%, 주요국, 분기)",
            "func": lambda: get_credit_to_gdp(BIS_COUNTRIES, START_QUARTER, borrower="G"),
        },

        # ── 신용/GDP 갭 ──
        {
            "file": "bis_credit_gap",
            "desc": "[BIS] 신용/GDP 갭 (주요국, 분기)",
            "func": lambda: get_credit_gap(BIS_COUNTRIES, START_QUARTER),
        },

        # ── 부동산 ──
        {
            "file": "bis_property_prices",
            "desc": "[BIS] 주택가격지수 (명목+실질, 주요국, 분기)",
            "func": lambda: get_property_prices(BIS_COUNTRIES, START_QUARTER),
        },

        # ── 실효환율 ──
        {
            "file": "bis_eer",
            "desc": "[BIS] 실효환율 (명목+실질, 주요국, 월별)",
            "func": lambda: get_effective_exchange_rate(BIS_COUNTRIES, START_MONTH),
        },

        # ── DSR ──
        {
            "file": "bis_dsr",
            "desc": "[BIS] 원리금상환비율 (주요국, 분기)",
            "func": lambda: get_debt_service_ratio(BIS_COUNTRIES, START_QUARTER),
        },
    ]


def _downloads_imf():
    """IMF 다운로드 목록"""
    from imf_api import (get_gdp_growth, get_gdp_nominal, get_gdp_per_capita,
                         get_gdp_ppp, get_inflation, get_unemployment,
                         get_population, get_govt_debt, get_fiscal_balance,
                         get_current_account, get_indicator)

    return [
        # ── 성장 ──
        {
            "file": "imf_gdp_growth",
            "desc": "[IMF] 실질 GDP 성장률 (%, 연간)",
            "func": lambda: get_gdp_growth(IMF_COUNTRIES, START_YEAR_INT),
        },
        {
            "file": "imf_gdp_nominal",
            "desc": "[IMF] 명목 GDP (십억 USD, 연간)",
            "func": lambda: get_gdp_nominal(IMF_COUNTRIES, START_YEAR_INT),
        },
        {
            "file": "imf_gdp_per_capita",
            "desc": "[IMF] 1인당 GDP (USD, 연간)",
            "func": lambda: get_gdp_per_capita(IMF_COUNTRIES, START_YEAR_INT),
        },
        {
            "file": "imf_gdp_ppp",
            "desc": "[IMF] GDP PPP (십억 국제달러, 연간)",
            "func": lambda: get_gdp_ppp(IMF_COUNTRIES, START_YEAR_INT),
        },

        # ── 물가 ──
        {
            "file": "imf_inflation",
            "desc": "[IMF] CPI 인플레이션 (%, 연간)",
            "func": lambda: get_inflation(IMF_COUNTRIES, START_YEAR_INT),
        },

        # ── 고용 ──
        {
            "file": "imf_unemployment",
            "desc": "[IMF] 실업률 (%, 연간)",
            "func": lambda: get_unemployment(IMF_COUNTRIES, START_YEAR_INT),
        },
        {
            "file": "imf_population",
            "desc": "[IMF] 인구 (백만명, 연간)",
            "func": lambda: get_population(IMF_COUNTRIES, START_YEAR_INT),
        },

        # ── 재정 ──
        {
            "file": "imf_govt_debt",
            "desc": "[IMF] 정부 총부채/GDP (%, 연간)",
            "func": lambda: get_govt_debt(IMF_COUNTRIES, START_YEAR_INT),
        },
        {
            "file": "imf_fiscal_balance",
            "desc": "[IMF] 재정수지/GDP (%, 연간)",
            "func": lambda: get_fiscal_balance(IMF_COUNTRIES, START_YEAR_INT),
        },

        # ── 대외 ──
        {
            "file": "imf_current_account",
            "desc": "[IMF] 경상수지/GDP (%, 연간)",
            "func": lambda: get_current_account(IMF_COUNTRIES, START_YEAR_INT),
        },
        {
            "file": "imf_gdp_per_capita_ppp",
            "desc": "[IMF] 1인당 GDP PPP (국제달러, 연간)",
            "func": lambda: get_indicator("PPPPC", IMF_COUNTRIES, START_YEAR_INT),
        },
        {
            "file": "imf_inflation_eop",
            "desc": "[IMF] CPI 인플레이션 기말 (%, 연간)",
            "func": lambda: get_indicator("PCPIEPCH", IMF_COUNTRIES, START_YEAR_INT),
        },
    ]


def _downloads_worldbank():
    """World Bank 다운로드 목록"""
    from worldbank_api import (get_gdp_growth, get_inflation, get_unemployment,
                               get_population, get_indicator)

    return [
        # ── 성장 ──
        {
            "file": "wb_gdp_growth",
            "desc": "[WB] GDP 성장률 (%, 연간)",
            "func": lambda: get_gdp_growth(WB_COUNTRIES, START_YEAR_INT),
        },
        {
            "file": "wb_gdp_current_usd",
            "desc": "[WB] 명목 GDP (current USD, 연간)",
            "func": lambda: get_indicator("NY.GDP.MKTP.CD", WB_COUNTRIES, START_YEAR_INT),
        },
        {
            "file": "wb_gdp_per_capita",
            "desc": "[WB] 1인당 GDP (current USD, 연간)",
            "func": lambda: get_indicator("NY.GDP.PCAP.CD", WB_COUNTRIES, START_YEAR_INT),
        },
        {
            "file": "wb_gdp_ppp",
            "desc": "[WB] GDP PPP (current intl$, 연간)",
            "func": lambda: get_indicator("NY.GDP.MKTP.PP.CD", WB_COUNTRIES, START_YEAR_INT),
        },

        # ── 물가 ──
        {
            "file": "wb_inflation",
            "desc": "[WB] CPI 인플레이션 (%, 연간)",
            "func": lambda: get_inflation(WB_COUNTRIES, START_YEAR_INT),
        },

        # ── 고용 ──
        {
            "file": "wb_unemployment",
            "desc": "[WB] 실업률 (ILO 추정, %, 연간)",
            "func": lambda: get_unemployment(WB_COUNTRIES, START_YEAR_INT),
        },
        {
            "file": "wb_population",
            "desc": "[WB] 인구 (연간)",
            "func": lambda: get_population(WB_COUNTRIES, START_YEAR_INT),
        },

        # ── 무역 ──
        {
            "file": "wb_trade_pct_gdp",
            "desc": "[WB] 무역/GDP (%, 연간)",
            "func": lambda: get_indicator("NE.TRD.GNFS.ZS", WB_COUNTRIES, START_YEAR_INT),
        },
        {
            "file": "wb_fdi_net_inflows",
            "desc": "[WB] FDI 순유입 (current USD, 연간)",
            "func": lambda: get_indicator("BX.KLT.DINV.CD.WD", WB_COUNTRIES, START_YEAR_INT),
        },

        # ── 금융 ──
        {
            "file": "wb_broad_money_pct_gdp",
            "desc": "[WB] 광의통화/GDP (%, 연간)",
            "func": lambda: get_indicator("FM.LBL.BMNY.GD.ZS", WB_COUNTRIES, START_YEAR_INT),
        },
        {
            "file": "wb_domestic_credit_pct_gdp",
            "desc": "[WB] 민간 국내신용/GDP (%, 연간)",
            "func": lambda: get_indicator("FS.AST.PRVT.GD.ZS", WB_COUNTRIES, START_YEAR_INT),
        },
    ]


def _downloads_factbook():
    """CIA Factbook 다운로드 목록"""
    from factbook_api import get_multi_country_summary

    # 주요 15개국 GEC 코드
    fb_countries = ["us", "ks", "ja", "gm", "uk", "fr", "ch", "it",
                    "ca", "as", "mx", "br", "in", "id", "tu"]

    return [
        {
            "file": "factbook_economy_summary",
            "desc": "[Factbook] 주요국 경제 요약 (최신 스냅샷)",
            "func": lambda: get_multi_country_summary(fb_countries),
        },
    ]


# ── 실행 ──────────────────────────────────────────────────────────

def download_one(d: dict, delay: float = 0.3) -> str | None:
    """단일 항목 다운로드 → parquet (+ csv) 저장"""
    path = os.path.join(SAVE_DIR, f"{d['file']}.parquet")
    print(f"\n  [{d['desc']}]")

    try:
        df = d["func"]()

        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            print(f"    >> 데이터 없음, 건너뜀")
            return None

        df.to_parquet(path, index=False)
        print(f"    >> 저장: {path}")

        if SAVE_CSV:
            csv_path = os.path.join(SAVE_DIR, f"{d['file']}.csv")
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"    >> CSV:  {csv_path}")

        print(f"    >> {len(df):,}행 × {len(df.columns)}열")
        time.sleep(delay)
        return path

    except Exception as e:
        print(f"    >> 오류: {e}")
        return None


def download_source(source_name: str, downloads: list, delay: float = 0.3):
    """특정 소스의 전체 항목 다운로드"""
    print(f"\n{'='*60}")
    print(f"  {source_name} ({len(downloads)}개 항목)")
    print(f"{'='*60}")

    results = []
    for i, d in enumerate(downloads, 1):
        print(f"\n  [{i}/{len(downloads)}]", end="")
        path = download_one(d, delay)
        results.append((d["file"], d["desc"], path))

    return results


def main():
    fmt = "parquet + csv" if SAVE_CSV else "parquet"
    print("=" * 60)
    print("글로벌 거시경제 데이터 통합 다운로드")
    print(f"저장 경로: {SAVE_DIR}")
    print(f"저장 형식: {fmt}")
    print("=" * 60)

    all_results = []

    # 소스별 선택 실행 (--csv 등 플래그 제외)
    ALL_SOURCES = ["fred", "oecd", "bis", "imf", "wb", "factbook"]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sources = args if args else ALL_SOURCES

    for src in sources:
        src = src.lower()
        if src == "fred":
            downloads = _downloads_fred()
            if downloads:
                results = download_source("FRED", downloads, delay=0.3)
                all_results.extend(results)
        elif src == "oecd":
            downloads = _downloads_oecd()
            results = download_source("OECD", downloads, delay=1.0)
            all_results.extend(results)
        elif src == "bis":
            downloads = _downloads_bis()
            results = download_source("BIS", downloads, delay=0.5)
            all_results.extend(results)
        elif src == "imf":
            downloads = _downloads_imf()
            results = download_source("IMF", downloads, delay=0.5)
            all_results.extend(results)
        elif src in ("wb", "worldbank"):
            downloads = _downloads_worldbank()
            results = download_source("World Bank", downloads, delay=0.3)
            all_results.extend(results)
        elif src == "factbook":
            downloads = _downloads_factbook()
            results = download_source("CIA Factbook", downloads, delay=0.5)
            all_results.extend(results)
        else:
            print(f"\n[!] 알 수 없는 소스: {src} ({'/'.join(ALL_SOURCES)} 중 선택)")

    # ── 결과 요약 ──
    if not all_results:
        print("\n다운로드할 항목이 없습니다.")
        return

    print(f"\n\n{'='*60}")
    print("다운로드 결과 요약")
    print(f"{'='*60}")

    success = [(f, d, p) for f, d, p in all_results if p]
    failed = [(f, d, p) for f, d, p in all_results if not p]

    print(f"\n성공: {len(success)}/{len(all_results)}")
    for f, d, p in success:
        size = os.path.getsize(p)
        size_str = f"{size/1024:.0f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
        print(f"  {f:35s} {size_str:>8s}  {d}")

    if failed:
        print(f"\n실패: {len(failed)}")
        for f, d, _ in failed:
            print(f"  {f:35s}  {d}")

    total = sum(os.path.getsize(p) for _, _, p in success)
    print(f"\n총 용량 (parquet): {total/1024/1024:.1f}MB")

    if SAVE_CSV:
        csv_total = 0
        for f, _, p in success:
            csv_p = p.replace(".parquet", ".csv")
            if os.path.exists(csv_p):
                csv_total += os.path.getsize(csv_p)
        print(f"총 용량 (csv):     {csv_total/1024/1024:.1f}MB")


if __name__ == "__main__":
    main()
