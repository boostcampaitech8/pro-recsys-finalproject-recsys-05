# GCP 서버 SSH 접속 가이드

VS Code Remote - SSH 확장을 사용하여 GCP 인스턴스에 안전하게 접속하는 방법입니다.

## 1. SSH 키 생성 (Windows PowerShell)

이미 키가 있다면 건너뛰어도 됩니다.

```powershell
ssh-keygen -t rsa -f "C:\Users\rlaqu\.ssh\gcp_key" -C "gimbyeongju04_gmail_com"
```
- 엔터를 계속 눌러 기본값으로 생성합니다.

## 2. GCP에 공개키 등록

1. **공개키 내용 복사**:
   ```powershell
   Get-Content C:\Users\rlaqu\.ssh\gcp_key.pub
   ```
   > **주의**: 출력된 내용을 `ssh-rsa`부터 끝까지 **한 줄로 공백 없이** 복사해야 합니다.

2. **GCP 콘솔 등록**:
   - [GCP Compute Engine 메타데이터](https://console.cloud.google.com/compute/metadata?tab=ssh-keys) 페이지로 이동
   - **수정** -> **항목 추가**
   - 복사한 키 붙여넣기 (사용자 이름이 `gimbyeongju04_gmail_com`으로 뜨는지 확인)
   - **저장**

   > **안 되면 수동 등록**:
   > 1. GCP 콘솔에서 [SSH] 버튼 눌러 웹 터미널 접속
   > 2. `nano ~/.ssh/authorized_keys` 입력
   > 3. 복사한 키 붙여넣기 -> `Ctrl+O`(저장) -> `Enter` -> `Ctrl+X`(종료)

## 3. VS Code 설정 (`config` 파일)

`c:\Users\rlaqu\.ssh\config` 파일을 열고 아래 내용을 추가합니다.
(Tailscale을 사용하므로 HostName에는 Tailscale 도메인이나 IP를 넣습니다.)

```ssh
Host gcp-server
    HostName <Tailscale_IP_또는_도메인>
    User gimbyeongju04_gmail_com
    IdentityFile C:\Users\rlaqu\.ssh\gcp_key
```

## 4. 접속 방법

1. VS Code 좌측 하단 초록색 아이콘 (`><`) 클릭
2. **Connect to Host...** 선택
3. **gcp-server** 선택
4. 최초 접속 시 에러(`Host key verification failed`)가 나면, 터미널에서 `ssh gcp-server` 입력 후 `yes`를 타이핑하여 승인해줍니다.
