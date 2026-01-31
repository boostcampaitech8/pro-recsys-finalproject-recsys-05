# TailorPlay - Steam 게임 추천 챗봇

개인화된 Steam 게임 추천을 제공하는 대화형 웹 애플리케이션입니다. 사용자의 Steam 계정 정보를 기반으로 맞춤형 게임을 추천하고, 추가 검색을 통해 더 많은 게임을 탐색할 수 있습니다.

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [주요 기능](#주요-기능)
3. [기술 스택](#기술-스택)
4. [설치 및 실행](#설치-및-실행)
5. [사용 방법](#사용-방법)
6. [프로젝트 구조](#프로젝트-구조)
7. [개발 가이드](#개발-가이드)
8. [배포](#배포)

---

## 프로젝트 개요

TailorPlay는 Naver Boostcamp 최종 프로젝트의 프론트엔드 부분입니다. 사용자가 자신의 Steam ID를 입력하면, 머신러닝 기반의 추천 알고리즘을 통해 개인화된 게임 추천을 받을 수 있습니다.

### 주요 특징

- **개인화 추천**: Steam 플레이 이력을 분석하여 맞춤형 게임 추천
- **다양한 UI 스타일**: 기존 텍스트 기반과 개선된 카드 기반 두 가지 스타일 제공
- **실시간 검색**: 추가 검색을 통해 원하는 게임 탐색
- **반응형 디자인**: 모바일 친화적 레이아웃

---

## 주요 기능

### 1. Steam ID 기반 추천
- Steam ID 입력을 통한 사용자 식별
- 사용자의 게임 플레이 기록 분석
- 선호도 기반 게임 자동 분류

### 2. 두 가지 추천 스타일
- **기존 스타일 (텍스트 기반)**
  - 간결한 텍스트 포맷
  - 빠른 정보 확인

- **개선 스타일 (카드 기반)**
  - 이모지를 포함한 시각적 카드
  - 게임 설명과 아이콘 표시
  - 호버 효과를 통한 인터랙션

### 3. 실시간 검색
- 하단에 고정된 검색 입력창
- 추천 게임 외 다른 게임 검색 가능
- 스크롤 중에도 항상 접근 가능

---

## 기술 스택

### Frontend
- **React 18+**: UI 라이브러리
- **TypeScript**: 타입 안정성
- **Tailwind CSS**: 스타일링
- **Vite**: 빌드 도구 (권장)

### 기타
- **Node.js**: 런타임 환경
- **npm/yarn**: 패키지 관리

---

## 설치 및 실행

### 사전 요구사항
- Node.js 16.0.0 이상
- npm 8.0.0 이상 또는 yarn 3.0.0 이상

### 설치 방법

```bash
# configs/frontend/.env ?? (???)
# (???: configs/frontend/.env.example)
VITE_API_URL=http://localhost:8000
```

### 스타일링 (Tailwind CSS)

이 프로젝트는 Tailwind CSS를 사용합니다. 주요 색상:
- 배경: `bg-slate-950`, `bg-[#212529]`, `bg-[#2D3338]`
- 텍스트: `text-white`, `text-slate-300`, `text-slate-400`
- 액센트: `text-blue-400`, `bg-blue-900`

### 상태 관리

현재는 React의 `useState` Hook을 사용합니다:

```typescript
const [style, setStyle] = useState<boolean>(true); // true: 기존 스타일, false: 개선 스타일
```

### 레이아웃 구조

```
MainPage
├── Header 섹션 (상단)
│   ├── 로고
│   ├── 인사말
│   └── 게임 샘플
├── Content 섹션 (중단, flex-1)
│   ├── 스타일 토글 버튼
│   └── 추천 뷰 (OldRecommendationView | NewRecommendationView)
└── Search 섹션 (하단, fixed)
    ├── 검색 입력
    └── 제출 버튼
```

### 추가 개발 시 주의사항

1. **반응형 디자인**: `max-w-360` 클래스로 최대 너비 제한
2. **Fixed 요소**: 하단 검색 창은 `pb-28`로 여백 확보 필요
3. **색상 일관성**: 기존 색상 팔레트 유지 권장
4. **Tailwind 클래스**: 인라인 스타일 대신 Tailwind 유틸리티 클래스 사용

---

## API 연동

### Steam API 통합 (예정)

현재 목업 데이터로 구현되어 있으며, 백엔드 API 연동 시:

```typescript
// 예상 API 엔드포인트
GET /api/recommendations/:steamId
GET /api/search?query=:gameTitle
```

### 데이터 포맷

**추천 게임 응답:**
```json
{
  "recommendations": [
    {
      "num": 1,
      "title": "게임 제목",
      "desc": "게임 설명",
      "icon": "🎮"
    }
  ],
  "userStyles": ["스토리 중심", "싱글 플레이"]
}
```

---

## 배포

### 빌드 방법

```bash
npm run build
```

생성되는 파일: `dist/` 디렉토리

### 배포 환경

- **Vercel**: `vercel deploy`
- **GitHub Pages**: GitHub Actions 연동
- **Docker**: Dockerfile 작성 후 컨테이너화

### 환경 변수 설정

배포 플랫폼에서 다음 변수 설정:
- `VITE_API_URL`: 백엔드 API 서버 URL