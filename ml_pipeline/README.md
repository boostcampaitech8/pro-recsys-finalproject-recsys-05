# 📊 Advanced Data Collection Pipeline

이 디렉토리는 Steam 데이터 수집 및 ML 학습 엔진(`ml_pipeline`)입니다.
추천 시스템에 필요한 양질의 데이터(Top Games, Reviews, User Activities)를 안정적으로 수집하며, **Legacy 데이터 포맷과 완벽하게 호환**되어 기존 데이터셋과 함께 사용할 수 있습니다.

## 🏗️ 폴더 구조

- `pipeline_manager.py`: 전체 수집 프로세스(게임->리뷰->유저) 통합 관리자
- `collect_*.py`: 각 데이터 유형별 수집 모듈 (Games, Reviews, Users)
    - `collect_games.py`: 스마트 필터링(신작 보호) 및 정밀 파싱(Archive Logic) 적용
    - `collect_reviews.py`: 증분 수집(Incremental) 및 중복 방지
    - `collect_users.py`: 활동 유저(Active User) 기반 스노우볼링 수집
- `core/`: API 핸들러(Rate Limit) 및 데이터 저장소(DataManager, Cache)
- `prefect/`: Prefect 오케스트레이션 및 서브플로우
- `../data/`: **[Output]** 수집된 데이터(`.jsonl`) 및 로그(`logs/`) 저장소

## 🚀 주요 특징

1.  **Legacy 포맷 완벽 호환**: 출력되는 JSONL 파일의 키(Key) 이름과 데이터 구조가 기존 `archive` 코드와 100% 동일합니다. (전처리 코드 수정 불필요)
2.  **스마트 필터링 (Smart Filtering)**:
    -   기본적으로 리뷰 수 20개 미만인 게임은 제외하지만,
    -   **출시 14일 이내 신작(New Release)**은 리뷰가 적어도 수집하여 Cold Start 문제에 대응합니다.
3.  **증분 수집 (Incremental)**:
    -   리뷰 수집 시 스냅샷(덮어쓰기) 방식이 아닌, **개별 리뷰 단위(Recommendation ID) 저장** 방식을 사용합니다.
    -   이미 수집된 리뷰는 API 단계에서 필터링하거나 저장하지 않아 **중복 데이터가 발생하지 않습니다.**
4.  **증분 저장 (Delta Logging)**: 매 실행 시 `../data/logs/collection_delta_...jsonl` 파일을 생성하여 신규 수집된 데이터만 따로 확인할 수 있습니다.

## 🛠️ 실행 방법

이 폴더(`ml_pipeline`)가 아닌 **프로젝트 루트**에서 아래 명령어를 실행하는 것을 권장합니다.

```bash
# 파이프라인 직접 실행
python ml_pipeline/collectors/pipeline_manager.py
# Prefect Flow 실행
python -m ml_pipeline.prefect.flows
```
