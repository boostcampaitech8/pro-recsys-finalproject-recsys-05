# BentoML 실추천(3-Stage) 로컬 검증 런북

> 목표: **메인컴 로컬**에서 BentoML 3-Stage 추천이 임의 Steam 유저에 대해 실제 점수를 내는지 backend e2e로 검증.
> 범위: 로컬 검증만. **프로덕션(Oracle 12GB)은 EASE 폴백 그대로 두고 건드리지 않는다.**
> 작성: 2026-07-07 · 브랜치 `revive/reactivation`

> ✅ **검증 통과 (2026-07-07, 노트북 WSL 로컬 hands-on, RAM 7.7GB로 충분).**
> - 5-a bentoml `/recommend`: 실점수 반환 (예: item 334070 combined_score 0.779, `is_new_user:true`, ~1.05s).
> - 5-b backend e2e `/rec/recommend-from-steam` (공개계정 `76561197960265731`, 415게임): `model_type: bentoml_3stage`, score 전부 >0, DB 메타조인 정상, backend 로그 `✓ BentoML returned` (폴백 아님).

### 재현 시 실측 함정 (중요)
1. **GCS 부트스트랩 스킵 필수**: base compose bentoml은 `entrypoint`가 `bootstrap_data.py`로 GCS 다운로드를 시도 → `gcs_config.yaml` 없으면 부팅 실패. 아티팩트가 이미 로컬(bind-mount)이면 **`BENTOML_SKIP_GCS_BOOTSTRAP=true`** 를 bentoml 환경에 주입(예: untracked `docker-compose.bentoml-verify.yml`). 안 그러면 없는 `ease_candidates.json`(1.8GB)까지 받으려다 죽음.
2. **Docker Desktop cred 헬퍼 오류(WSL)**: `error getting credentials ... logon session does not exist` → 빌드/풀 전 `DOCKER_CONFIG=/tmp/dockercfg`(`{"auths":{}}`)로 익명 우회. 사용자 `~/.docker/config.json`은 건드리지 않음.
3. **테스트 appid는 학습셋(17,792개)에 있어야 함**: F2P 대작(570 Dota2, 730 CS)은 이 필터셋에 **없음** → EASE 후보 0 → "후보 생성 실패". token2id에 실재하는 appid(예: 50,130,2100,2600,2870)로 스모크. e2e는 학습셋과 겹치는 게임을 가진 공개 라이브러리 계정 필요.
4. **아티팩트 출처**: Gdrive 없이도 4개월 전 `pro-recsys-finalproject-recsys-05-bentoml` 이미지에서 `docker cp`로 전부 추출 가능. 큰 EASE(1.27GB backend-format)는 `backend/app/data/item_similarity.pkl`에 이미 있음.

---

## 0. 배경 — 왜 지금까지 실추천이 안 됐나 (근본 원인)

재활성화 내내 BentoML은 한 번도 안 돌았고(Phase 1·2에서 의도적 제외, Phase 3 prod compose엔 서비스 자체가 없음), 추천은 backend 로컬 EASE 폴백으로만 나왔다. 게다가 **켜도 안 되는 상태**였다:

- `model_loader.load_ease_model()`이 `saved_models/item_similarity.pkl`을 `pickle.load` 하는데, 이 파일은 **RecBole EASE 체크포인트(torch.save = ZIP, 매직바이트 `504b0304`)**라 `pickle.load`가 실패 → 조용히 `None` 반환.
- candidates JSON은 스킵되므로 모든 유저가 **신규-유저 경로** = `candidate_merger.generate_ease_candidates(ease_model=None, ...)` → 즉시 `[]` → `recommendation_service`가 `{"status":"error","error":"후보 생성 실패"}` 반환.
- backend는 이 status:error를 httpx 에러로 안 잡아서 EASE 폴백도 못 타고 400.

## 1. 적용된 수정 (이 브랜치에 커밋됨 — 메인컴은 `git pull`만)

1. **`ml_rec/scripts/stage4_serving/candidate_merger.py` · `generate_ease_candidates`**
   backend 서빙 dict(`{similarity_matrix, item_num, id2token, token2id}`)를 인식하는 분기 추가.
   backend `inference_service.recommend_for_new_user`와 동일한 **유사도 가중합**으로 신규-유저 EASE 후보를 실시간 생성. 레거시 dict-of-dicts 분기는 유지.
2. **`ml_rec/scripts/stage4_serving/model_loader.py` · `load_ease_model`**
   `item_similarity_backend_format.pkl`을 우선 로드. torch 체크포인트(ZIP) 감지 시 조용한 `None` 대신 **명확한 에러 로그**.

> candidates JSON 스킵은 그대로 둔다 — 신규-유저 경로는 precomputed 후보가 필요 없다(600MB 다운로드·RAM 절약).

## 2. 사전 준비 (메인컴)

```bash
cd <repo>                      # 메인컴의 pro-recsys-finalproject-recsys-05
git checkout revive/reactivation
git pull                        # 위 수정 반영
```

- DB는 Phase 1/2에서 이미 시드됨(`postgres_data` 볼륨, games 36k). 아니면 backend 최초 부팅이 다시 시드.
- Docker Desktop 기동 필요.

## 3. 아티팩트 배치 (Gdrive 백업 → `ml_rec/`)

G: (Google Drive Desktop) 또는 file-ID로 받아 아래 위치에 둔다. 합계 ~1.27GB(+5MB).

| 파일 | 놓을 위치 | Gdrive file-ID | 크기 |
|---|---|---|---|
| `dcn_v2_steam.pth` | `ml_rec/saved_models/` | `1xxrK-MQoauC9QkTXG7RanWGJ4G8Ov9_C` | 304KB |
| `xgb_final_scorer.pkl` | `ml_rec/saved_models/` | `1YnpbmpAQpd3yj6wJtcRRYasHiwmlpMD4` | 185KB |
| `item_similarity_backend_format.pkl` | `ml_rec/saved_models/` | `1SJQL2jrMfgEh2Z8zig_Qx1EsHyE5N03G` | 1.27GB |
| `lightgcn_embeddings.npz` | `ml_rec/candidates/` | `1K-9k17t0epHXCbMgQ1lhh9VZdusrqcxO` | 4.3MB |

- G: 경로(대략): 모델·임베딩은 `G:\내 드라이브\부스트캠프\backup\gcs_data-tailor-test\ml_rec\{models,candidates}\`, 변환본은 `...\backup\converted\item_similarity_backend_format.pkl`.
- `ml_rec/dataset/steam_optimal/steam_optimal.item`(popularity 메타)은 이미 있으면 그대로. 없어도 동작(popularity=0 기본).
- **주의**: `saved_models/item_similarity.pkl`(torch 체크포인트)이 남아 있어도 됨 — 로더가 `_backend_format.pkl`을 우선한다. 둘 다 없으면 EASE 신규-유저 후보 생성 불가.

배치 확인:
```bash
ls -lh ml_rec/saved_models/{dcn_v2_steam.pth,xgb_final_scorer.pkl,item_similarity_backend_format.pkl}
ls -lh ml_rec/candidates/lightgcn_embeddings.npz
# 매직바이트 확인 (backend dict = 8005, torch = 504b)
python -c "print(open('ml_rec/saved_models/item_similarity_backend_format.pkl','rb').read(2).hex())"  # -> 8005 기대
```

## 4. 빌드 & 기동

```bash
docker compose build bentoml                     # 메인컴 x86 네이티브
docker compose up -d db redis bentoml backend    # backend는 bentoml service_healthy 대기
docker compose logs -f bentoml                    # __init__에서 모델 로드 관찰
```

기대 로그(bentoml):
- `✓ EASE 모델 로드: item_similarity_backend_format.pkl`
- `✓ LightGCN 임베딩 로드`, `✓ DCN v2 모델 로드`, `✓ XGBoost 모델 로드`
- `✅ GameRecommendationService 초기화 완료!` → 헬스체크 통과 → backend 기동

## 5. 검증

### 5-a. BentoML 스모크 (직접 호출)
```bash
curl -s -X POST http://localhost:3000/recommend \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"smoke_test","user_games":[570,730,440,252490],"top_k":10}' | python -m json.tool
```
**합격 기준**: `"status":"success"`, `recommendations[]`에 `dcn_score`·`xgb_score`·`combined_score`가 **0이 아닌 실값**, `metadata.is_new_user: true`.
(570=Dota2, 730=CS2, 440=TF2, 252490=Rust — 학습셋 appid면 됨. 후보 0이면 다른 인기 appid로 교체)

### 5-b. Backend e2e (최종 합격 기준)
공개 게임 라이브러리를 가진 Steam64 ID로:
```bash
curl -s -X POST http://localhost:8000/recommend-from-steam \
  -H 'Content-Type: application/json' \
  -d '{"steamid":"<공개_STEAM64_ID>","top_k":10}' | python -m json.tool
```
**합격 기준**:
- `"model_type": "bentoml_3stage"` (← `ease_fallback`/`bentoml_3stage` 폴백표기 아님)
- `recommended_games[].score`가 **0이 아닌 실값**
- backend 로그에 `✓ BentoML returned N recommendations` (폴백 `Falling back to EASE...` 아님)

## 6. 트러블슈팅

| 증상 | 원인 | 조치 |
|---|---|---|
| bentoml 로그 `❌ EASE 모델이 torch 체크포인트(ZIP)` | `_backend_format.pkl` 미배치 | 3장 파일 배치 확인 |
| `/recommend` status:error "후보 생성 실패" | user_games가 전부 학습셋 밖 | 학습셋 appid(예: 570/730) 포함해 재시도 |
| backend가 `Falling back to EASE` | bentoml 미기동/헬스 실패 | `docker compose ps`·`logs bentoml` |
| `LightGCN 임베딩 로드 실패` | `lightgcn_embeddings.npz` 미배치 | candidates/ 확인 |
| combined_score는 나오는데 이름이 "Unknown Game" | DB games 미시드 | backend DB 시드 확인(별개 이슈, 추천 자체는 정상) |

## 7. 검증 후 (결과 회신)

- 5-a/5-b 응답(JSON 일부)과 bentoml 초기화 로그를 공유.
- 통과 시: 루트 `CLAUDE.md`의 "(선택) BentoML 경로 검증" 항목 갱신, 필요 시 이 수정을 dev/main으로 전파할지 결정(현재는 로컬 검증 범위).
