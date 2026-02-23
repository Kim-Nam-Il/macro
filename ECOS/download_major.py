"""
ECOS 주요 경제 데이터 일괄 다운로드 → parquet 저장
실행: python3 download_major.py
"""

import os
import time
import pandas as pd
from ecos_api import search, _request

SAVE_DIR = "/home/ubuntu/HDD1/ECOS/data"
os.makedirs(SAVE_DIR, exist_ok=True)

# ── 다운로드 대상 정의 ─────────────────────────────────────────
# (파일명, 통계코드, 주기, 시작일, 종료일, item_code1, ..., 설명)
DOWNLOADS = [
    # ── 금리 ──
    {
        "file": "base_rate_monthly",
        "stat": "722Y001", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": ["0101000"],
        "desc": "한국은행 기준금리 (월별)",
    },
    {
        "file": "market_rate_daily",
        "stat": "817Y002", "cycle": "D",
        "start": "20070101", "end": "20261231",
        "items": [],
        "desc": "시장금리 일별 (콜금리, 국고채, 회사채, CD 등)",
    },
    {
        "file": "market_rate_monthly",
        "stat": "721Y001", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "시장금리 월별",
    },

    # ── 환율 ──
    {
        "file": "fx_krw_daily",
        "stat": "731Y003", "cycle": "D",
        "start": "20070101", "end": "20261231",
        "items": [],
        "desc": "원/달러, 원/위안, 원/엔 환율 (일별)",
    },
    {
        "file": "fx_major_monthly",
        "stat": "731Y004", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "주요국 통화 대원화 환율 (월별)",
    },

    # ── 물가 ──
    {
        "file": "cpi_monthly",
        "stat": "901Y009", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": ["0"],
        "desc": "소비자물가지수 총지수 (월별)",
    },
    {
        "file": "ppi_monthly",
        "stat": "404Y014", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": ["*AA"],
        "desc": "생산자물가지수 총지수 (월별)",
    },

    # ── GDP / 국민계정 ──
    {
        "file": "gdp_nominal_annual",
        "stat": "200Y113", "cycle": "A",
        "start": "2007", "end": "2026",
        "items": [],
        "desc": "GDP 명목 (연간)",
    },
    {
        "file": "gdp_nominal_quarterly",
        "stat": "200Y107", "cycle": "Q",
        "start": "2007Q1", "end": "2026Q4",
        "items": [],
        "desc": "GDP 명목 (분기, 계절조정)",
    },
    {
        "file": "gdp_real_quarterly",
        "stat": "200Y108", "cycle": "Q",
        "start": "2007Q1", "end": "2026Q4",
        "items": [],
        "desc": "GDP 실질 (분기, 계절조정)",
    },
    {
        "file": "gdp_key_annual",
        "stat": "200Y101", "cycle": "A",
        "start": "2007", "end": "2026",
        "items": [],
        "desc": "국민계정 주요지표 (연간)",
    },
    {
        "file": "gdp_key_quarterly",
        "stat": "200Y102", "cycle": "Q",
        "start": "2007Q1", "end": "2026Q4",
        "items": [],
        "desc": "국민계정 주요지표 (분기)",
    },

    # ── 통화 ──
    {
        "file": "m2_monthly",
        "stat": "161Y006", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": ["BBHA00"],
        "desc": "M2 통화량 (평잔, 원계열, 월별)",
    },

    # ── 국제수지 ──
    {
        "file": "bop_monthly",
        "stat": "301Y013", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "국제수지 (월별)",
    },

    # ── 외환보유액 ──
    {
        "file": "fx_reserves_monthly",
        "stat": "732Y001", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": ["99"],
        "desc": "외환보유액 합계 (월별)",
    },

    # ── 심리/경기 지수 ──
    {
        "file": "esi_monthly",
        "stat": "513Y001", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "경제심리지수 (월별)",
    },
    {
        "file": "cli_monthly",
        "stat": "901Y067", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "경기종합지수 (선행/동행/후행, 월별)",
    },

    # ── 고용 ──
    {
        "file": "labor_monthly",
        "stat": "901Y027", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "경제활동인구 (월별)",
    },

    # ── 부동산 ──
    {
        "file": "house_price_monthly",
        "stat": "901Y062", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "주택매매가격지수 (월별)",
    },
    {
        "file": "house_rent_monthly",
        "stat": "901Y063", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "주택전세가격지수 (월별)",
    },

    # ── 해외 비교 ──
    {
        "file": "global_policy_rate",
        "stat": "902Y006", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "주요국 중앙은행 정책금리 (BIS, 월별)",
    },
    {
        "file": "global_cpi",
        "stat": "902Y008", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "주요국 소비자물가지수 (IMF, 월별)",
    },
    {
        "file": "global_gdp_annual",
        "stat": "902Y016", "cycle": "A",
        "start": "2007", "end": "2026",
        "items": [],
        "desc": "주요국 GDP (OECD, 연간)",
    },
    {
        "file": "global_gdp_per_capita",
        "stat": "902Y018", "cycle": "A",
        "start": "2007", "end": "2026",
        "items": [],
        "desc": "주요국 1인당 GDP (OECD, 연간)",
    },
    {
        "file": "commodity_price_monthly",
        "stat": "902Y003", "cycle": "M",
        "start": "200701", "end": "202612",
        "items": [],
        "desc": "국제상품가격 (월별)",
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

        df.to_parquet(path, index=False)
        print(f"  >> 저장 완료: {path}")
        print(f"  >> {len(df):,}행 × {len(df.columns)}열")
        return path

    except Exception as e:
        print(f"  >> 오류: {e}")
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("ECOS 주요 경제 데이터 일괄 다운로드")
    print(f"저장 경로: {SAVE_DIR}")
    print(f"대상: {len(DOWNLOADS)}개 통계")
    print("=" * 60)

    results = []
    for i, d in enumerate(DOWNLOADS, 1):
        print(f"\n[{i}/{len(DOWNLOADS)}]", end="")
        path = download_one(d)
        results.append((d["file"], d["desc"], path))
        time.sleep(0.3)  # API 부하 방지

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
        print(f"  {f:30s} {size_str:>8s}  {d}")

    if failed:
        print(f"\n실패: {len(failed)}")
        for f, d, _ in failed:
            print(f"  {f:30s}  {d}")

    # 전체 크기
    total = sum(os.path.getsize(p) for _, _, p in success)
    print(f"\n총 용량: {total/1024/1024:.1f}MB")
