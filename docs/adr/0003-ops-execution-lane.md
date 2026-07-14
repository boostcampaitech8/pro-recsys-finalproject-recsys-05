# ADR-0003 · 운영(ops) 티켓 실행 레인

- **상태**: Accepted (2026-07-08) · *참조 주석(T14, 2026-07-09): 본문의 `MAINTENANCE §0`·`seam(§2)`는 문서 재편 전 위치 — 현행 정본은 프로토콜=SPEC §4, seam 레지스트리=MAINTENANCE §1 (ADR-0006). 결정 내용은 불변.*
- **맥락**: ADR-0001 하네스는 실행을 "`scoped` → codex-rescue 위임 → diff 리뷰 → 커밋"으로 상정했다(코드 티켓 전제). T5(BentoML 3-stage 영구화) 마무리에서, 리포 코드 변경이 아니라 live 인프라 대상 작업(`ssh a1`로 서버 상태 실측·재배포 검증·prod curl)만 남은 부류가 드러났다. 이런 티켓은 ① codex-rescue가 리포 샌드박스 밖이라 위임 불가, ② 리뷰할 diff가 없음, ③ done 기준이 병합 PR이 아니라 "관측된 prod 동작"이다.

## 결정
1. **티켓 `kind` 2종** — `code`(리포 변경, codex 위임=기본) / `ops`(live 인프라·검증, 클로드 직접 실행). scoping 시 판정. 미표기 = `code`.
2. **ops 실행 레인** — 실행 주체는 **클로드 직접**(`ssh a1`·docker/compose·`gh`·`curl`·doppler). codex 위임 안 함.
   - **read-only 선(先)실측 → mutate**: mutate 전 상태 관측(git status·docker ps·아티팩트·health)이 code 레인의 diff 리뷰를 대신한다. 근거 없이 mutate 금지.
   - **실행 로그는 GitHub Issue에**: diff/커밋이 없으므로 명령 + 관측결과를 Issue에 남겨 감사추적을 확보.
   - **done 게이트 = 관측된 prod 동작** + seam 통합 게이트(예: T5 = `model_type: bentoml_3stage` + score>0, health 200).
3. **조사 게이트·seam guard는 공통** — ops도 `scoped` 전 mutate 금지, 걸린 seam(§2) guard 준수(예: S3 서버 dirty 정리).
4. **경계 규칙** — ops 작업 중 리포 코드 수정이 필요하면 `code` 서브티켓으로 분리해 code 레인으로.

## 결과
- 상세 프로토콜·티켓 스키마 반영 = `docs/MAINTENANCE.md` §0.
- 서버 접근은 `ssh a1`(테일넷 전용). 구체 접속정보(키·호스트)는 로컬 ssh config + 리포 밖 런북에만 두고 공개 리포엔 미기재.
- **트레이드오프**: 실행 주체가 티켓별로 갈리지만(codex vs 클로드), 인프라 액션에 억지로 codex를 끼우지 않아 감사추적(Issue 로그)이 실행 방식과 정합한다.
- ADR-0001을 대체하지 않고 **보완**한다(레인 추가).
