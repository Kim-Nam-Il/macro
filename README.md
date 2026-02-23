# Macro Data Pipeline

글로벌 거시경제 지표를 여러 공개 API에서 수집하고, 하나의 통합 테이블로 정리하는 프로젝트입니다.

- 소스: `FRED`, `OECD`, `BIS`, `IMF`, `World Bank`, `CIA Factbook`
- 출력: `parquet`(기본), 필요 시 `csv` 동시 저장
- 통합 결과: `data/macro_all.parquet`, `data/macro_all.csv`

## 주요 스크립트

- `download_global.py`
  - 글로벌 데이터 일괄 다운로드
  - 예: 성장, 물가, 고용, 금리, 신용, 부동산
- `consolidate.py`
  - 소스별 파일을 공통 스키마로 정규화해 단일 테이블 생성
- `*_api.py`
  - 각 데이터 소스별 API 래퍼 모듈

## 디렉터리 구조

```text
macro/
├─ download_global.py
├─ consolidate.py
├─ fred_api.py
├─ oecd_api.py
├─ bis_api.py
├─ imf_api.py
├─ worldbank_api.py
├─ factbook_api.py
├─ ecos_api.py
├─ data/                  # 글로벌 데이터 결과 파일
└─ ECOS/                  # 한국은행 ECOS 전용 수집 스크립트/데이터
```

## 요구사항

- Python 3.10+
- 권장 패키지:
  - `pandas`
  - `requests`
  - `pyarrow` (parquet 저장/읽기용)
  - `numpy`

설치 예시:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pandas requests pyarrow numpy
```

## FRED API 키 설정

`FRED`는 API 키가 필요합니다. 키가 없으면 `download_global.py` 실행 시 FRED 항목은 자동으로 건너뜁니다.

1) 환경변수 방식(권장)

```bash
export FRED_API_KEY="YOUR_KEY"
```

2) 로컬 파일 방식

```bash
echo "YOUR_KEY" > fred_api_key.txt
```

`fred_api_key.txt`는 `.gitignore`에 포함되어 있습니다.

## 빠른 시작

전체 다운로드(parquet만):

```bash
python3 download_global.py
```

전체 다운로드(parquet + csv):

```bash
python3 download_global.py --csv
```

선택 소스만 다운로드:

```bash
python3 download_global.py --csv imf wb
python3 download_global.py oecd bis
```

통합 테이블 생성:

```bash
python3 consolidate.py
```

## 통합 결과 스키마

`consolidate.py` 결과(`data/macro_all.*`)의 기본 컬럼:

- `소스`
- `국가코드`
- `국가명`
- `기간`
- `지표명`
- `값`
- `단위`
- `주기`

## ECOS(한국은행) 관련

루트의 `ecos_api.py`와 `ECOS/` 폴더 스크립트로 한국은행 ECOS 데이터를 별도로 수집할 수 있습니다.

- `ECOS/download_major.py`
- `ECOS/download_extra.py`
- `ECOS/download_remaining.py`

주의:

- 일부 ECOS 스크립트는 저장 경로가 절대경로(`/home/ubuntu/HDD1/ECOS/data`)로 고정되어 있습니다.
- 현재 작업 경로(`macro/ECOS/data`)에 저장하려면 스크립트의 `SAVE_DIR`를 맞게 수정하세요.

## 데이터 소스

- FRED: <https://fred.stlouisfed.org/docs/api/fred/>
- OECD SDMX: <https://sdmx.oecd.org/public/rest/>
- BIS SDMX: <https://stats.bis.org/api-doc/v2/>
- IMF DataMapper: <https://www.imf.org/external/datamapper/api/v1/>
- World Bank Open Data: <https://api.worldbank.org/v2/>
- CIA Factbook JSON: <https://github.com/factbook/factbook.json>
