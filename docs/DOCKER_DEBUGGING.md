# 🐳 Docker 환경 파이썬 디버깅 가이드

이 문서는 로컬 VS Code 환경에서 **도커 컨테이너 내부에서 실행 중인 FastAPI 백엔드 코드**를 직접 디버깅하는 방법을 안내합니다.

## 1. 사전 준비 사항 (Prerequisites)

디버깅을 시작하기 전에 다음 도구들이 설치되어 있어야 합니다.

* **Docker & Docker Compose**
* **VS Code**
* **VS Code Extension:** [Python Debugger](https://marketplace.visualstudio.com/items?itemName=ms-python.debugpy) (Microsoft)

---

## 2. 개발용 컨테이너 실행

프로덕션 환경과 분리된 **개발 전용 Compose 파일**을 사용하여 컨테이너를 실행해야 합니다. 이 설정은 디버깅 포트(`5678`)를 개방하고 코드를 핫 리로딩(Hot-reloading) 합니다.

터미널에서 다음 명령어를 실행하세요:

```bash
# 개발용 컨테이너 빌드 및 실행
docker compose -f docker-compose.dev.yml up --build

# 로그 확인 (정상 실행 여부 체크)
docker compose -f docker-compose.dev.yml logs -f backend

```

> **참고:** 최초 실행 시 이미지를 빌드하느라 시간이 소요될 수 있습니다.

---

## 3. VS Code 설정 (`launch.json`)

VS Code의 디버거가 도커 컨테이너에 접속할 수 있도록 설정을 추가해야 합니다.
`.vscode/launch.json` 파일이 없다면 생성하고, 아래 내용을 붙여넣으세요.

**파일 경로:** `.vscode/launch.json`

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python Debugger: Current File",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal"
        },
        {
            "name": "Docker: Python Attach",
            "type": "debugpy",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "pathMappings": [
                {
                    // [중요] 내 컴퓨터(Host)의 소스 경로
                    "localRoot": "${workspaceFolder}/backend",
                    // [중요] 도커 컨테이너(Remote) 내부의 소스 경로
                    "remoteRoot": "/app/backend"
                }
            ],
            "justMyCode": true
        }
    ]
}

```

### 💡 설정 포인트

* **`port: 5678`**: `debugpy`가 도커 내부에서 대기 중인 포트입니다.
* **`pathMappings`**: 로컬의 `/backend` 폴더와 컨테이너의 `/app/backend`를 매핑하여, 브레이크 포인트가 정확한 위치에 찍히도록 합니다.

---

## 4. 디버깅 시작하기

1. **브레이크 포인트 설정:** 디버깅하고 싶은 파이썬 파일(`backend/app/...`)을 열고 줄 번호 왼쪽을 클릭하여 🔴 붉은 점(Breakpoint)을 찍습니다.
2. **디버거 실행:**
* VS Code 좌측 **'실행 및 디버그(Run and Debug)'** 탭으로 이동합니다 (`Ctrl + Shift + D`).
* 상단 드롭다운 메뉴에서 **`Docker: Python Attach`**를 선택합니다.
* 초록색 재생 버튼(▶)을 누르거나 `F5` 키를 입력합니다.


3. **API 요청:**
* 브라우저(`http://localhost:8000/...`)나 Swagger, Postman 등을 이용해 API를 호출합니다.


4. **디버깅:**
* 설정해둔 브레이크 포인트에서 코드 실행이 멈추면 변수 확인, 단계별 실행(Step Over/Into)을 수행합니다.



---

## 5. 디버깅 종료 및 컨테이너 관리

### 🔌 디버깅만 종료하기 (연결 해제)

* 디버그 툴바의 **'연결 끊기(Disconnect)'** 아이콘을 누르거나 `Shift + F5`를 입력합니다.
* **효과:** 컨테이너와 서버는 **계속 실행**됩니다. 언제든 다시 `F5`를 눌러 재연결할 수 있습니다.

### 🛑 컨테이너 완전히 끄기

* 개발을 마칠 때는 터미널에서 다음 명령어로 컨테이너를 종료합니다.

```bash
docker compose -f docker-compose.dev.yml down

```
