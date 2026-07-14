---
title: README 프로젝트 구조 섹션을 실제 트리로 교체
verify: skip
---

루트 `README.md`의 "## 📂 프로젝트 구조" 코드블록을 실제 디렉터리 구조로 갱신한다.

수행:
1. 실제 트리를 근거로 확인한다:
   - `ml_rec/scripts/` 하위는 `preprocessing/`, `stage1_retrieval/`, `stage2_ranking/`,
     `stage3_scoring/`, `stage4_serving/` 디렉터리 구조다(README의 `stage1_ease.py` 등
     단일 파일 평면 나열은 틀림).
   - 루트에 `scripts/`, `docs/`(adr·execplan·MAINTENANCE 등)가 있다.
2. README의 구조도 코드블록만 실제와 맞게 고친다. 각 항목의 한 줄 설명은 유지·정리한다.
3. 트리에 없는 항목(구식 경로)은 제거하고, 실제 존재하나 누락된 상위 디렉터리는 보강한다.

경계:
- `README.md` 하나만 수정한다. 다른 파일은 건드리지 않는다.
- 구조도 섹션 외의 README 내용(배지·설명·설치법 등)은 변경하지 않는다.

수용 기준: 구조도가 실제 `ml_rec/scripts/` 스테이지 디렉터리 구조를 반영하고,
존재하지 않는 경로가 남아있지 않다.
