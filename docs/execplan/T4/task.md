---
ticket: T4
issue: TBD
title: 루트 README 구조도 실제 트리로 갱신
base_sha: aad8ace
base_branch: dev
branch: feature/T4-readme-tree
steps:
  - step1.md
seam_guards: []
dont_touch:
  - backend/
  - frontend/
  - ml_rec/
  - .github/
---

루트 `README.md`의 "📂 프로젝트 구조" 섹션이 실제 디렉터리 트리와 불일치한다(버그 #5).
문서 전용 작업 — 코드/설정/배포에는 절대 손대지 않는다(문서만 수정).

권위 있는 실제 구조 기준:
- `ml_rec/scripts/{preprocessing, stage1_retrieval, stage2_ranking, stage3_scoring, stage4_serving}`
  (README의 `stage1_ease.py`·`stage2_dcn.py` 등 평면 나열은 구식)
- 컴포넌트 지도는 `docs/MAINTENANCE.md` §1 을 정본으로 참조.

이 task는 execute.py 파일럿(T13)의 최저위험 실증 대상이다.
