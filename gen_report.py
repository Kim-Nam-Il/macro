"""
macro_all 전체 데이터를 PDF 리포트로 생성
- Executive Summary: 글로벌 스냅샷 + 핵심지표 + 시계열 차트 8종
- 요약 통계 + 전체 데이터 (소스·국가·지표별 정리)
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager as fm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSET_DIR = os.path.join(BASE_DIR, "report_assets")
OUT_TEX = os.path.join(BASE_DIR, "macro_all_report.tex")

# ── matplotlib 한글 설정 ──
_KR_FONT_PATH = None
# 직접 알려진 경로 시도
_KNOWN_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]
for p in _KNOWN_PATHS:
    if os.path.exists(p):
        _KR_FONT_PATH = p
        break

if _KR_FONT_PATH:
    fm.fontManager.addfont(_KR_FONT_PATH)
    _font_prop = fm.FontProperties(fname=_KR_FONT_PATH)
    _font_name = _font_prop.get_name()
    plt.rcParams["font.family"] = _font_name
    plt.rcParams["font.sans-serif"] = [_font_name]
else:
    plt.rcParams["font.family"] = "sans-serif"

plt.rcParams["axes.unicode_minus"] = False

# ── 차트 스타일 상수 ──
CHART_DPI = 220
CHART_COLORS = ["#0055AA", "#E03030", "#30A030", "#FF8C00", "#8B008B", "#00BFBF",
                "#808080", "#CC6699"]
COUNTRY_NAMES = {
    "US": "미국", "KR": "한국", "JP": "일본", "DE": "독일", "GB": "영국",
    "FR": "프랑스", "CN": "중국", "AU": "호주", "CA": "캐나다", "IT": "이탈리아",
    "IN": "인도", "BR": "브라질",
}


# ══════════════════════════════════════════════════════════
# 유틸
# ══════════════════════════════════════════════════════════

def esc(s):
    """LaTeX 특수문자 이스케이프"""
    if pd.isna(s):
        return ""
    s = str(s)
    s = s.replace("\\", "\\textbackslash{}")
    s = s.replace("&", "\\&")
    s = s.replace("%", "\\%")
    s = s.replace("$", "\\$")
    s = s.replace("#", "\\#")
    s = s.replace("_", "\\_")
    s = s.replace("{", "\\{")
    s = s.replace("}", "\\}")
    s = s.replace("~", "\\textasciitilde{}")
    s = s.replace("^", "\\textasciicircum{}")
    return s


def fmt_val(v):
    """값 포맷팅"""
    if pd.isna(v):
        return "-"
    if abs(v) >= 1e12:
        return f"{v/1e12:,.2f}T"
    if abs(v) >= 1e9:
        return f"{v/1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"{v/1e6:,.2f}M"
    if abs(v) >= 100:
        return f"{v:,.1f}"
    if abs(v) >= 1:
        return f"{v:,.2f}"
    if v == 0:
        return "0"
    return f"{v:,.4f}"


def fmt_period(s):
    """기간 문자열 정리 (datetime 잔재 제거)"""
    s = str(s)
    if " 00:00:00" in s:
        s = s.replace(" 00:00:00", "")
    return s


def _parse_period(s):
    """기간 문자열 → datetime (차트용)"""
    import re
    s = fmt_period(s)
    # 분기 형식: 2007-Q1 → 2007-01, 2007-Q2 → 2007-04, etc.
    qm = re.match(r"^(\d{4})-Q([1-4])$", s)
    if qm:
        yr, q = int(qm.group(1)), int(qm.group(2))
        month = (q - 1) * 3 + 1
        return pd.Timestamp(yr, month, 1)
    for fmt in ["%Y-%m-%d", "%Y-%m", "%Y"]:
        try:
            return pd.Timestamp(datetime.strptime(s, fmt))
        except ValueError:
            continue
    return pd.NaT


def _get_ts(df, src, indicator, country):
    """소스·지표·국가로 시계열 추출 → (날짜 Series, 값 Series)"""
    sub = df[(df["소스"] == src) & (df["지표명"] == indicator) & (df["국가코드"] == country)].copy()
    if sub.empty:
        return pd.Series(dtype="datetime64[ns]"), pd.Series(dtype="float64")
    sub["_dt"] = sub["기간"].apply(_parse_period)
    sub = sub.dropna(subset=["_dt", "값"]).sort_values("_dt")
    return sub["_dt"].reset_index(drop=True), sub["값"].astype(float).reset_index(drop=True)


def _get_latest(df, src, indicator, country):
    """최신값 + 기간 반환"""
    sub = df[(df["소스"] == src) & (df["지표명"] == indicator) & (df["국가코드"] == country)].copy()
    if sub.empty:
        return np.nan, ""
    sub["_dt"] = sub["기간"].apply(_parse_period)
    sub = sub.dropna(subset=["_dt", "값"]).sort_values("_dt")
    if sub.empty:
        return np.nan, ""
    row = sub.iloc[-1]
    return float(row["값"]), fmt_period(row["기간"])


def _get_latest_n(df, src, indicator, country, n=2):
    """최근 n개 값 반환 (최신→과거 순)"""
    sub = df[(df["소스"] == src) & (df["지표명"] == indicator) & (df["국가코드"] == country)].copy()
    if sub.empty:
        return []
    sub["_dt"] = sub["기간"].apply(_parse_period)
    sub = sub.dropna(subset=["_dt", "값"]).sort_values("_dt")
    return [(float(r["값"]), fmt_period(r["기간"])) for _, r in sub.tail(n).iloc[::-1].iterrows()]


# ══════════════════════════════════════════════════════════
# 차트 생성 함수들
# ══════════════════════════════════════════════════════════

def _make_line_chart(series_list, title, ylabel, out_path, figsize=(11, 4.5),
                     start_year=None, hline=None, fill_between=False):
    """범용 라인 차트
    series_list: [(dates, values, label), ...]
    """
    fig, ax = plt.subplots(figsize=figsize, dpi=CHART_DPI)
    for i, (dates, vals, label) in enumerate(series_list):
        if len(dates) == 0:
            continue
        color = CHART_COLORS[i % len(CHART_COLORS)]
        if fill_between and i == 0:
            ax.fill_between(dates, vals, 0, alpha=0.3, color=color)
            ax.plot(dates, vals, color=color, linewidth=1.2, label=label)
        else:
            ax.plot(dates, vals, color=color, linewidth=1.3, label=label)
    if hline is not None:
        ax.axhline(hline, color="gray", linewidth=0.7, linestyle="--", alpha=0.6)
    if start_year:
        ax.set_xlim(left=pd.Timestamp(f"{start_year}-01-01"))
    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.set_ylabel(ylabel, fontsize=10)
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(fontsize=8, ncol=min(len(handles), 6), loc="upper left",
                  framealpha=0.8)
    ax.grid(True, alpha=0.3, linewidth=0.5)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    fig.tight_layout()
    fig.savefig(out_path, dpi=CHART_DPI, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"  차트 저장: {out_path}")


def generate_charts(df):
    """8개 차트 PNG 생성"""
    os.makedirs(ASSET_DIR, exist_ok=True)

    # ── 1. 주요국 GDP 성장률 (IMF) ──
    countries = ["US", "KR", "JP", "DE", "CN", "GB"]
    series = []
    for c in countries:
        dt, val = _get_ts(df, "IMF", "GDP성장률", c)
        if len(dt) > 0:
            # IMF는 연도이므로 2025년까지만 (미래 전망 제외)
            mask = dt <= pd.Timestamp("2025-12-31")
            series.append((dt[mask], val[mask], f"{COUNTRY_NAMES.get(c, c)} ({c})"))
    _make_line_chart(series, "주요국 GDP 성장률 (%YoY)", "%",
                     os.path.join(ASSET_DIR, "chart_gdp_growth.png"), hline=0)

    # ── 2. 주요국 인플레이션 (BIS CPI_전년비) ──
    series = []
    for c in countries:
        dt, val = _get_ts(df, "BIS", "CPI_전년비", c)
        if len(dt) > 0:
            series.append((dt, val, f"{COUNTRY_NAMES.get(c, c)} ({c})"))
    _make_line_chart(series, "주요국 CPI 인플레이션 (%YoY)", "%",
                     os.path.join(ASSET_DIR, "chart_cpi_inflation.png"), hline=2)

    # ── 3. 주요 중앙은행 정책금리 (BIS + OECD fallback) ──
    rate_countries = ["US", "KR", "JP", "GB", "AU", "CN"]
    series = []
    for c in rate_countries:
        dt, val = _get_ts(df, "BIS", "정책금리", c)
        if len(dt) == 0:
            dt, val = _get_ts(df, "OECD", "정책금리", c)
        if len(dt) > 0:
            series.append((dt, val, f"{COUNTRY_NAMES.get(c, c)} ({c})"))
    _make_line_chart(series, "주요 중앙은행 정책금리 (%)", "%",
                     os.path.join(ASSET_DIR, "chart_policy_rates.png"), hline=0)

    # ── 4. 미국 매크로 종합 (FRED + BIS) ──
    us_indicators = [
        ("FRED", "미국_실업률", "US", "실업률"),
        ("FRED", "미국_연방기금금리", "US", "Fed Funds"),
        ("FRED", "미국_10년국채수익률", "US", "10Y"),
        ("BIS", "CPI_전년비", "US", "CPI (YoY)"),
    ]
    series = []
    for src, ind, c, label in us_indicators:
        dt, val = _get_ts(df, src, ind, c)
        if len(dt) > 0:
            series.append((dt, val, label))
    _make_line_chart(series, "미국 매크로 종합", "%",
                     os.path.join(ASSET_DIR, "chart_us_macro.png"))

    # ── 5. 미국 장단기 금리차 (FRED) ──
    dt, val = _get_ts(df, "FRED", "미국_장단기스프레드_10Y2Y", "US")
    if len(dt) > 0:
        _make_line_chart(
            [(dt, val, "10Y-2Y Spread")],
            "미국 장단기 금리차 (10Y-2Y)", "%p",
            os.path.join(ASSET_DIR, "chart_us_term_spread.png"),
            hline=0, fill_between=True)

    # ── 6. 주요국 주택가격 (BIS 실질주택가격지수) ──
    house_countries = ["US", "KR", "JP", "DE", "GB", "AU"]
    series = []
    for c in house_countries:
        dt, val = _get_ts(df, "BIS", "주택가격_실질_지수", c)
        if len(dt) > 0:
            series.append((dt, val, f"{COUNTRY_NAMES.get(c, c)} ({c})"))
    _make_line_chart(series, "주요국 실질주택가격지수 (2010=100)", "Index",
                     os.path.join(ASSET_DIR, "chart_housing_prices.png"))

    # ── 7. 주요국 민간신용/GDP (BIS) ──
    credit_countries = ["US", "KR", "JP", "DE", "CN", "GB"]
    series = []
    for c in credit_countries:
        dt, val = _get_ts(df, "BIS", "민간신용_GDP비", c)
        if len(dt) > 0:
            series.append((dt, val, f"{COUNTRY_NAMES.get(c, c)} ({c})"))
    _make_line_chart(series, "주요국 민간부문 신용/GDP 비율", "% of GDP",
                     os.path.join(ASSET_DIR, "chart_credit_gdp.png"))

    # ── 8. 한국 매크로 종합 (BIS+OECD) ──
    kr_indicators = [
        ("BIS", "정책금리", "KR", "정책금리"),
        ("BIS", "CPI_전년비", "KR", "CPI (YoY)"),
        ("OECD", "실업률", "KR", "실업률"),
    ]
    series = []
    for src, ind, c, label in kr_indicators:
        dt, val = _get_ts(df, src, ind, c)
        if len(dt) > 0:
            series.append((dt, val, label))
    _make_line_chart(series, "한국 매크로 종합", "%",
                     os.path.join(ASSET_DIR, "chart_kr_macro.png"))

    print(f"차트 {8}개 생성 완료 → {ASSET_DIR}")


# ══════════════════════════════════════════════════════════
# Executive Summary LaTeX 생성
# ══════════════════════════════════════════════════════════

def _build_snapshot_table(df, w):
    """글로벌 매크로 스냅샷 테이블"""
    w(r"\subsection{글로벌 매크로 스냅샷}")
    w(r"{\small")
    w(r"\begin{tabular}{l " + " ".join(["R{2.6cm}"] * 6) + "}")
    w(r"\toprule")
    w(r"\rowcolor{hdrBg}"
      r"\textcolor{hdrFg}{\textbf{국가}} & "
      r"\textcolor{hdrFg}{\textbf{GDP성장률}} & "
      r"\textcolor{hdrFg}{\textbf{CPI (YoY)}} & "
      r"\textcolor{hdrFg}{\textbf{정책금리}} & "
      r"\textcolor{hdrFg}{\textbf{실업률}} & "
      r"\textcolor{hdrFg}{\textbf{정부부채/GDP}} & "
      r"\textcolor{hdrFg}{\textbf{경상수지/GDP}} \\")
    w(r"\midrule")

    snap_countries = ["US", "KR", "JP", "DE", "GB", "FR", "CN", "AU", "CA", "IT"]
    indicator_defs = [
        ("IMF", "GDP성장률"),
        ("BIS", "CPI_전년비"),
        ("BIS", "정책금리"),
        ("IMF", "실업률"),
        ("IMF", "정부부채_GDP비"),
        ("IMF", "경상수지_GDP비"),
    ]

    for i, c in enumerate(snap_countries):
        cname = COUNTRY_NAMES.get(c, c)
        cells = [f"\\textbf{{{esc(cname)}}} ({esc(c)})"]
        for src, ind in indicator_defs:
            val, period = _get_latest(df, src, ind, c)
            if pd.isna(val):
                # fallback: OECD for policy rate
                if ind == "정책금리":
                    val, period = _get_latest(df, "OECD", "정책금리", c)
            if pd.isna(val):
                cells.append("-")
            else:
                # 기간에서 연도만 혹은 연-월 표시
                p_short = period[:7] if len(period) >= 7 else period
                cells.append(f"{val:.1f} \\scriptsize{{({esc(p_short)})}}")
        row = " & ".join(cells) + r" \\"
        if i % 2 == 1:
            w(r"\rowcolor{rowB}" + row)
        else:
            w(row)

    w(r"\bottomrule")
    w(r"\end{tabular}")
    w(r"}")
    w(r"\vspace{1em}")
    w("")


def _build_us_box(df, w):
    """미국 핵심 지표 최신값"""
    w(r"\subsection{미국 핵심 지표}")
    w(r"{\small")
    w(r"\begin{tabular}{l R{2cm} R{2.5cm} l R{2cm} R{2.5cm}}")
    w(r"\toprule")
    w(r"\rowcolor{hdrBg}"
      r"\textcolor{hdrFg}{\textbf{지표}} & "
      r"\textcolor{hdrFg}{\textbf{최신값}} & "
      r"\textcolor{hdrFg}{\textbf{기간}} & "
      r"\textcolor{hdrFg}{\textbf{지표}} & "
      r"\textcolor{hdrFg}{\textbf{최신값}} & "
      r"\textcolor{hdrFg}{\textbf{기간}} \\")
    w(r"\midrule")

    us_items = [
        ("FRED", "미국_연방기금금리", "US", "Fed Funds Rate"),
        ("FRED", "미국_10년국채수익률", "US", "10Y Treasury"),
        ("FRED", "미국_2년국채수익률", "US", "2Y Treasury"),
        ("FRED", "미국_장단기스프레드_10Y2Y", "US", "Term Spread"),
        ("BIS", "CPI_전년비", "US", "CPI (YoY)"),
        ("FRED", "미국_실업률", "US", "실업률"),
        ("IMF", "GDP성장률", "US", "GDP 성장률"),
        ("IMF", "정부부채_GDP비", "US", "정부부채/GDP"),
    ]

    # 2열 배치
    for ri in range(0, len(us_items), 2):
        cells = []
        for ci in range(2):
            idx = ri + ci
            if idx < len(us_items):
                src, ind, c, label = us_items[idx]
                recent = _get_latest_n(df, src, ind, c, 2)
                if recent:
                    val, period = recent[0]
                    p_short = period[:10]
                    arrow = ""
                    if len(recent) > 1:
                        prev_val = recent[1][0]
                        diff = val - prev_val
                        if diff > 0.005:
                            arrow = r" {\color{red}$\uparrow$}"
                        elif diff < -0.005:
                            arrow = r" {\color{blue}$\downarrow$}"
                        else:
                            arrow = r" $\rightarrow$"
                    cells.append(f"{esc(label)} & {val:.2f}{arrow} & {esc(p_short)}")
                else:
                    cells.append(f"{esc(label)} & - & -")
            else:
                cells.append("& &")
        row = " & ".join(cells) + r" \\"
        if (ri // 2) % 2 == 1:
            w(r"\rowcolor{rowB}" + row)
        else:
            w(row)

    w(r"\bottomrule")
    w(r"\end{tabular}")
    w(r"}")
    w(r"\vspace{1em}")
    w("")


def _build_kr_box(df, w):
    """한국 핵심 지표 최신값"""
    w(r"\subsection{한국 핵심 지표}")
    w(r"{\small")
    w(r"\begin{tabular}{l R{2cm} R{2.5cm} l R{2cm} R{2.5cm}}")
    w(r"\toprule")
    w(r"\rowcolor{hdrBg}"
      r"\textcolor{hdrFg}{\textbf{지표}} & "
      r"\textcolor{hdrFg}{\textbf{최신값}} & "
      r"\textcolor{hdrFg}{\textbf{기간}} & "
      r"\textcolor{hdrFg}{\textbf{지표}} & "
      r"\textcolor{hdrFg}{\textbf{최신값}} & "
      r"\textcolor{hdrFg}{\textbf{기간}} \\")
    w(r"\midrule")

    kr_items = [
        ("BIS", "정책금리", "KR", "정책금리"),
        ("BIS", "CPI_전년비", "KR", "CPI (YoY)"),
        ("OECD", "실업률", "KR", "실업률"),
        ("IMF", "GDP성장률", "KR", "GDP 성장률"),
        ("BIS", "주택가격_실질_지수", "KR", "실질주택가격지수"),
        ("BIS", "민간신용_GDP비", "KR", "민간신용/GDP"),
    ]

    for ri in range(0, len(kr_items), 2):
        cells = []
        for ci in range(2):
            idx = ri + ci
            if idx < len(kr_items):
                src, ind, c, label = kr_items[idx]
                recent = _get_latest_n(df, src, ind, c, 2)
                if recent:
                    val, period = recent[0]
                    p_short = period[:10]
                    arrow = ""
                    if len(recent) > 1:
                        prev_val = recent[1][0]
                        diff = val - prev_val
                        if diff > 0.005:
                            arrow = r" {\color{red}$\uparrow$}"
                        elif diff < -0.005:
                            arrow = r" {\color{blue}$\downarrow$}"
                        else:
                            arrow = r" $\rightarrow$"
                    cells.append(f"{esc(label)} & {val:.2f}{arrow} & {esc(p_short)}")
                else:
                    cells.append(f"{esc(label)} & - & -")
            else:
                cells.append("& &")
        row = " & ".join(cells) + r" \\"
        if (ri // 2) % 2 == 1:
            w(r"\rowcolor{rowB}" + row)
        else:
            w(row)

    w(r"\bottomrule")
    w(r"\end{tabular}")
    w(r"}")
    w(r"\vspace{1em}")
    w("")


def _build_charts_section(w):
    """차트 8개 삽입 (2개씩 4페이지)"""
    chart_files = [
        ("chart_gdp_growth.png", "주요국 GDP 성장률"),
        ("chart_cpi_inflation.png", "주요국 CPI 인플레이션"),
        ("chart_policy_rates.png", "주요 중앙은행 정책금리"),
        ("chart_us_macro.png", "미국 매크로 종합"),
        ("chart_us_term_spread.png", "미국 장단기 금리차"),
        ("chart_housing_prices.png", "주요국 실질주택가격"),
        ("chart_credit_gdp.png", "주요국 민간신용/GDP"),
        ("chart_kr_macro.png", "한국 매크로 종합"),
    ]
    w(r"\subsection{주요 시계열 차트}")
    w("")

    for i, (fname, caption) in enumerate(chart_files):
        fpath = os.path.join(ASSET_DIR, fname)
        if not os.path.exists(fpath):
            continue
        # LaTeX에서 경로의 _를 처리하기 위해 상대 경로 사용
        rel = f"report_assets/{fname}"
        w(r"\noindent")
        w(r"\begin{center}")
        w(r"\includegraphics[width=\linewidth]{%s}" % rel)
        w(r"\end{center}")
        w(r"\vspace{0.3em}")
        # 2개마다 페이지 넘김
        if i % 2 == 1 and i < len(chart_files) - 1:
            w(r"\newpage")
        w("")

    w(r"\newpage")
    w("")


# ══════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════

def main():
    df = pd.read_parquet(os.path.join(DATA_DIR, "macro_all.parquet"))
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── 차트 생성 ──
    print("차트 생성 중...")
    generate_charts(df)

    lines = []
    w = lines.append

    # ══════════════════════════════════════════════════════════
    # 프리앰블
    # ══════════════════════════════════════════════════════════
    w(r"""\documentclass[9pt,a4paper,landscape]{article}
\usepackage{kotex}
\usepackage{fontspec}
\usepackage[left=1.5cm,right=1.5cm,top=1.8cm,bottom=1.5cm]{geometry}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{setspace}
\usepackage{pdflscape}
\usepackage{colortbl}
\usepackage{graphicx}
\usepackage{multicol}

\singlespacing

\definecolor{accent}{RGB}{0,85,140}
\definecolor{hdrBg}{RGB}{0,85,140}
\definecolor{hdrFg}{RGB}{255,255,255}
\definecolor{rowA}{RGB}{255,255,255}
\definecolor{rowB}{RGB}{245,248,252}
\definecolor{secBg}{RGB}{220,235,250}

\hypersetup{colorlinks=true,linkcolor=accent,urlcolor=accent}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\textcolor{gray}{글로벌 거시경제 통합 데이터 리포트}}
\fancyhead[C]{\small\textcolor{gray}{macro\_all (%s)}}
\fancyhead[R]{\small\textcolor{gray}{\thepage}}
\renewcommand{\headrulewidth}{0.4pt}

\titleformat{\section}{\Large\bfseries\color{accent}}{\thesection}{1em}{}
\titleformat{\subsection}{\large\bfseries\color{accent}}{\thesubsection}{1em}{}
\titleformat{\subsubsection}{\normalsize\bfseries\color{accent!70!black}}{\thesubsubsection}{1em}{}

\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}p{#1}}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\setlength{\tabcolsep}{3pt}

\begin{document}
""" % esc(now))

    # ══════════════════════════════════════════════════════════
    # 표지
    # ══════════════════════════════════════════════════════════
    w(r"""
\begin{titlepage}
\centering
\vspace*{5cm}
{\Huge\bfseries\color{accent} 글로벌 거시경제 통합 데이터\par}
\vspace{0.8cm}
{\Huge\bfseries\color{accent} 전체 리포트\par}
\vspace{2cm}
{\Large FRED $\cdot$ OECD $\cdot$ BIS $\cdot$ IMF $\cdot$ World Bank $\cdot$ CIA Factbook\par}
\vspace{2cm}
{\large 김남일\par}
{\normalsize DS증권 퀀트\par}
\vspace{0.3cm}
{\large NAMIL KIM\par}
{\normalsize DS Investment \& Securities\par}
\vspace{2cm}
{\large 생성: %s\par}
\vspace{0.5cm}
{\normalsize 총 %s행 $\times$ %d열\par}
\vfill
\end{titlepage}
\tableofcontents
\newpage
""" % (esc(now), f"{len(df):,}", len(df.columns)))

    # ══════════════════════════════════════════════════════════
    # Executive Summary
    # ══════════════════════════════════════════════════════════
    w(r"\section{Executive Summary}")
    w("")

    # 2a. 글로벌 스냅샷
    _build_snapshot_table(df, w)

    w(r"\newpage")

    # 2b. 미국 핵심 지표
    _build_us_box(df, w)

    # 2c. 한국 핵심 지표
    _build_kr_box(df, w)

    w(r"\newpage")

    # 2d. 차트 삽입
    _build_charts_section(w)

    # ══════════════════════════════════════════════════════════
    # 1. 데이터셋 개요
    # ══════════════════════════════════════════════════════════
    w(r"\section{데이터셋 개요}")
    w(r"\begin{itemize}")
    w(r"\item 총 행 수: \textbf{%s}" % f"{len(df):,}")
    w(r"\item 컬럼: 소스, 국가코드, 국가명, 기간, 지표명, 값, 단위, 주기")
    fsize = os.path.getsize(os.path.join(DATA_DIR, "macro_all.csv"))
    w(r"\item CSV 파일 크기: \textbf{%.1f MB}" % (fsize / 1024 / 1024))
    w(r"\item 소스 수: \textbf{%d}" % df["소스"].nunique())
    w(r"\item 국가 수: \textbf{%d}" % df["국가코드"].nunique())
    w(r"\item 지표 수: \textbf{%d}" % df["지표명"].nunique())
    w(r"\item 결측값: \textbf{%d}행 (값 컬럼, %.2f\%%)" % (
        df["값"].isna().sum(), df["값"].isna().mean() * 100))
    w(r"\end{itemize}")
    w("")

    # ── 소스별 요약 테이블 ──
    w(r"\subsection{소스별 요약}")
    w(r"\begin{tabular}{l r r r l l}")
    w(r"\toprule")
    w(r"\rowcolor{hdrBg}\textcolor{hdrFg}{\textbf{소스}} & "
      r"\textcolor{hdrFg}{\textbf{행수}} & "
      r"\textcolor{hdrFg}{\textbf{국가}} & "
      r"\textcolor{hdrFg}{\textbf{지표}} & "
      r"\textcolor{hdrFg}{\textbf{시작}} & "
      r"\textcolor{hdrFg}{\textbf{종료}} \\")
    w(r"\midrule")
    for src in ["FRED", "OECD", "BIS", "IMF", "WB", "Factbook"]:
        sub = df[df["소스"] == src]
        if sub.empty:
            continue
        periods = sub["기간"].apply(fmt_period)
        w(r"%s & %s & %d & %d & %s & %s \\" % (
            esc(src), f"{len(sub):,}", sub["국가코드"].nunique(),
            sub["지표명"].nunique(),
            esc(str(periods.min())), esc(str(periods.max()))))
    w(r"\bottomrule")
    w(r"\end{tabular}")
    w(r"\vspace{1em}")
    w("")

    # ── 주기별 분포 ──
    w(r"\subsection{주기별 분포}")
    w(r"\begin{tabular}{l r r}")
    w(r"\toprule")
    w(r"\rowcolor{hdrBg}\textcolor{hdrFg}{\textbf{주기}} & "
      r"\textcolor{hdrFg}{\textbf{행수}} & "
      r"\textcolor{hdrFg}{\textbf{비중(\%)}} \\")
    w(r"\midrule")
    freq = df["주기"].value_counts()
    for k, v in freq.items():
        w(r"%s & %s & %.1f \\" % (esc(k), f"{v:,}", v / len(df) * 100))
    w(r"\bottomrule")
    w(r"\end{tabular}")
    w(r"\vspace{1em}")
    w("")

    # ── 국가별 행수 ──
    w(r"\subsection{국가별 행수}")
    w(r"\begin{tabular}{l l r r}")
    w(r"\toprule")
    w(r"\rowcolor{hdrBg}\textcolor{hdrFg}{\textbf{코드}} & "
      r"\textcolor{hdrFg}{\textbf{국가명}} & "
      r"\textcolor{hdrFg}{\textbf{행수}} & "
      r"\textcolor{hdrFg}{\textbf{비중(\%)}} \\")
    w(r"\midrule")
    country_counts = df.groupby(["국가코드", "국가명"]).size().reset_index(name="cnt")
    country_counts = country_counts.sort_values("cnt", ascending=False)
    for _, cr in country_counts.iterrows():
        w(r"%s & %s & %s & %.1f \\" % (
            esc(cr["국가코드"]), esc(cr["국가명"]),
            f"{cr['cnt']:,}", cr["cnt"] / len(df) * 100))
    w(r"\bottomrule")
    w(r"\end{tabular}")
    w(r"\newpage")
    w("")

    # ══════════════════════════════════════════════════════════
    # 2. 전체 데이터 (소스별 → 국가별 → 지표별)
    # ══════════════════════════════════════════════════════════
    w(r"\section{전체 데이터}")
    w("")

    source_order = ["FRED", "OECD", "BIS", "IMF", "WB", "Factbook"]

    for src in source_order:
        src_df = df[df["소스"] == src].copy()
        if src_df.empty:
            continue

        w(r"\subsection{%s (%s행)}" % (esc(src), f"{len(src_df):,}"))
        w("")

        countries = sorted(src_df["국가코드"].unique())

        for country in countries:
            c_df = src_df[src_df["국가코드"] == country].copy()
            cname = c_df["국가명"].iloc[0]

            w(r"\subsubsection{%s (%s) --- %s행}" % (
                esc(cname), esc(country), f"{len(c_df):,}"))
            w("")

            indicators = sorted(c_df["지표명"].unique())

            for ind in indicators:
                i_df = c_df[c_df["지표명"] == ind].copy()
                i_df = i_df.sort_values("기간")

                unit = i_df["단위"].iloc[0] if not i_df["단위"].isna().all() else ""
                cycle = i_df["주기"].iloc[0] if not i_df["주기"].isna().all() else ""

                # 지표 헤더
                w(r"\noindent\colorbox{secBg}{\parbox{\dimexpr\linewidth-2\fboxsep}{"
                  r"\small\textbf{%s} \hfill 단위: %s \quad 주기: %s \quad %s행}}"
                  % (esc(ind), esc(unit), esc(cycle), f"{len(i_df):,}"))
                w(r"\vspace{2pt}")
                w("")

                # 많은 행: longtable 사용
                # 한 행에 기간+값을 여러 컬럼으로 배치 (compact)
                vals = list(zip(
                    i_df["기간"].apply(fmt_period),
                    i_df["값"].apply(fmt_val)
                ))
                n = len(vals)

                # 컬럼 수 결정: 데이터 양에 따라 (최대 5)
                if n <= 12:
                    ncols = min(n, 4)
                elif n <= 40:
                    ncols = 4
                else:
                    ncols = 5

                # 테이블 생성 (고정폭 컬럼)
                col_spec = " ".join(["L{2cm} R{1.6cm}"] * ncols)
                w(r"{\footnotesize")
                w(r"\begin{longtable}{@{}%s@{}}" % col_spec)
                w(r"\toprule")
                hdr = " & ".join([r"\textbf{기간} & \textbf{값}"] * ncols)
                w(hdr + r" \\")
                w(r"\midrule")
                w(r"\endhead")

                # 행 채우기
                row_count = (n + ncols - 1) // ncols
                for ri in range(row_count):
                    cells = []
                    for ci in range(ncols):
                        idx = ri + ci * row_count
                        if idx < n:
                            period, val = vals[idx]
                            cells.append(f"{esc(period)} & {esc(val)}")
                        else:
                            cells.append("&")
                    # 줄무늬
                    if ri % 2 == 1:
                        w(r"\rowcolor{rowB}" + " & ".join(cells) + r" \\")
                    else:
                        w(" & ".join(cells) + r" \\")

                w(r"\bottomrule")
                w(r"\end{longtable}")
                w(r"}")  # close \footnotesize
                w(r"\vspace{4pt}")
                w("")

        w(r"\newpage")
        w("")

    # ══════════════════════════════════════════════════════════
    w(r"\end{document}")

    # 파일 저장
    with open(OUT_TEX, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"TeX 생성 완료: {OUT_TEX}")
    print(f"총 {len(lines):,}줄")


if __name__ == "__main__":
    main()
