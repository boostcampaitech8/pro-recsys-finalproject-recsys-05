# 배포 및 트러블슈팅 (GCP VM + OS Login)

이 문서는 현재 배포 흐름과 검증된 OS Login 설정 방법을 정리합니다.  
또한 새 인스턴스로 옮길 때 필요한 작업도 포함합니다.

## 현재 배포 흐름

- GitHub Actions가 이미지를 빌드해 Docker Hub에 푸시합니다.
- 배포 잡이 Tailscale로 VPN 접속합니다.
- `appleboy/scp-action`이 `deploy.sh`, `docker-compose.prod.yml`을 복사합니다.
- `appleboy/ssh-action`이 VM에서 `deploy.sh`를 실행합니다.

## OS Login 1회 설정

1) OS Login 활성화(프로젝트/인스턴스 메타데이터).

```bash
gcloud compute project-info add-metadata --metadata enable-oslogin=TRUE
gcloud compute instances add-metadata INSTANCE --zone ZONE \
  --metadata enable-oslogin=TRUE
```

2) CI용 키 생성(Windows 예시).

```powershell
mkdir $env:USERPROFILE\.ssh -Force
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\ci_deploy" -C "ci-deploy"
```

3) OS Login에 공개키 등록(Cloud Shell).

```bash
cat > /tmp/ci_deploy.pub <<'EOF'
ssh-ed25519 AAAA... ci-deploy
EOF
gcloud compute os-login ssh-keys add --key-file /tmp/ci_deploy.pub --ttl=0
gcloud compute os-login describe-profile --format="value(posixAccounts.username)"
```

위 출력의 `posixAccounts.username` 값이 SSH 접속 계정입니다.

## GitHub Secrets

- `SSH_HOST`: VM IP(또는 Tailscale IP)
- `SSH_USERNAME`: POSIX username (예: `gimbyeongju04_gmail_com`)
- `SSH_KEY`: `~/.ssh/ci_deploy`의 private key 전체(멀티라인 그대로)
- `TS_OAUTH_CLIENT_ID`, `TS_OAUTH_SECRET`: Tailscale
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: 서버의 `.env` 생성용

선택(권장):
- `fingerprint`: `appleboy/*` 액션의 host key fingerprint

## 수동 SSH 검증

```powershell
ssh -i "$env:USERPROFILE\.ssh\ci_deploy" -o IdentitiesOnly=yes \
  POSIX_USERNAME@VM_IP
```

## 새 인스턴스로 이전

1) 새 VM 생성 후 Docker/Docker Compose 설치
2) 새 인스턴스에 OS Login 활성화(또는 프로젝트 전체 활성화)
3) OS Login에 공개키 등록(동일 키 재사용 가능)
4) GitHub Secrets 갱신
   - `SSH_HOST`를 새 IP로 변경
   - `SSH_USERNAME`은 POSIX username 그대로 사용
5) GitHub Actions 배포 재실행

## 트러블슈팅 (5 Whys)

문제: CI 배포가 `ssh: handshake failed` 및 `no key found`로 실패.

1) 왜 실패했는가?  
   SSH 인증이 완료되지 않았다(공개키 방식 실패).
2) 왜 공개키 인증이 실패했는가?  
   러너가 유효한 private key 또는 올바른 사용자명을 제공하지 못했다.
3) 왜 키/사용자명이 맞지 않았는가?  
   OS Login 요구사항(POXIS username + private key)을 알지 못해
   이메일 계정/공개키를 사용했다.
4) 왜 OS Login 요구사항을 몰랐는가?  
   OS Login 활성화/키 등록 절차가 문서화되어 있지 않았다.
5) 왜 CI에서 늦게 드러났는가?  
   사전 검증(Secrets 유효성, 호스트 해석) 단계가 없었다.

개선:
- OS Login + POSIX username 기준으로 Secrets를 정합화.
- `SSH_KEY`는 private key 멀티라인 그대로 저장.
- `SSH_HOST`는 IP 사용(또는 MagicDNS/Tailscale DNS 구성).
- 배포 전 Secrets 길이/호스트 해석 체크 스텝 추가.
