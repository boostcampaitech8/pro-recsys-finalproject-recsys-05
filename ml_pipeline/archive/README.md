# Legacy Code Archive

이 폴더의 코드들은 **참고용(Reference) 구버전 코드**입니다.
현재 수집 파이프라인(`scheduler_aps.py`, `pipeline_manager.py`)에서 사용되지 않습니다.

## ⚠️ 주의 사항
- 이 파일들을 직접 실행하지 마세요.
- 로직 확인이나 과거 데이터 포맷 비교가 필요할 때만 참고하십시오.

## Mapping (Old -> New)
| Legacy File (Archive)    | New Active File (Root) | 비고                                             |
| :----------------------- | :--------------------- | :----------------------------------------------- |
| `game_info_crawing.py`   | `collect_games.py`     | 동일 로직 + Class 구조화 + 태그 수집 통합        |
| `review_crawing.py`      | `collect_reviews.py`   | 중복 제거 제거 (Append Only) + 기간 설정(Weekly) |
| `user_data_collector.py` | `collect_users.py`     | 구조 동일 + API Key 환경변수 처리                |
