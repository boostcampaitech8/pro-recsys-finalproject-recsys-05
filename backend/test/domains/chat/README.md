# 챗 멀티턴 테스트

이 폴더는 멀티턴 챗 관련 테스트와 문서를 담고 있습니다.

## 테스트 목록
- `test_chat_multiturn_db.py`: DB 기반 멀티턴 히스토리 흐름 테스트
- `manual_clova_multiturn.py`: CLOVA 연동 수동 스모크 테스트 (pytest 자동 수집 제외)

## 실행 방법
레포 루트 기준:

```powershell
python -m pytest backend/test/domains/chat/test_chat_multiturn_db.py -s

CLOVA 수동 테스트(외부 API 호출이 필요할 때만):


$env:RUN_CLOVA_TEST=1
$env:PRINT_CLOVA=1
python -m pytest backend/test/domains/chat/manual_clova_multiturn.py -s


flowchart TD
  A[Client POST /chat/conversations/{id}/messages] --> B[send_message]
  B --> C[services.process_chat_turn]
  C --> D[DB: user 메시지 저장]
  C --> E[DB: 최근 메시지 조회 -> history 구성]
  C --> F[LLM 호출 -> 전체 응답 생성]
  C --> G[DB: assistant 메시지 저장]
  B --> H[JSON 응답 반환]


flowchart TD
  A2[Client POST /chat/conversations/{id}/messages/stream] --> B2[send_message_stream]
  B2 --> C2[services.process_chat_turn]
  C2 --> D2[DB: user 메시지 저장]
  C2 --> E2[DB: 최근 메시지 조회 -> history 구성]
  C2 --> F2[LLM 호출 -> 전체 응답 생성]
  C2 --> G2[DB: assistant 메시지 저장]
  B2 --> H2[fake_stream_chunks -> SSE]
  H2 --> I2[done 이벤트]

```