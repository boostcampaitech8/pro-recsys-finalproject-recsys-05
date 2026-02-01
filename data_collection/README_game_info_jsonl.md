# 게임 상세 정보 (`steam_games_info.jsonl`)

게임의 메타데이터, 가격, 스펙, 미디어 정보를 담고 있습니다.

### 🆔 기본 정보 & 식별
| Field                | Type   | Description                                  |
| :------------------- | :----- | :------------------------------------------- |
| `name`               | String | 게임 제목 (한국어 우선, 없으면 영어)         |
| `name_en`            | String | 영어 제목 (검색 및 매칭용)                   |
| `type`               | String | 컨텐츠 타입 (game, dlc, demo 등)             |
| `is_available_in_kr` | Bool   | 한국 스토어 접속 가능 여부 (True/False)      |
| `release_date`       | String | 출시일                                       |
| `age_rating`         | Int    | 연령 등급 (0이면 전체 이용가 또는 정보 없음) |
| `developers`         | List   | 개발사 목록                                  |
| `publishers`         | List   | 배급사 목록                                  |
| `dlc_count`          | Int    | 출시된 DLC 개수                              |

### 💰 가격 & 언어 & 플랫폼
| Field                 | Type   | Description                                        |
| :-------------------- | :----- | :------------------------------------------------- |
| `is_free`             | Bool   | 무료 게임 여부                                     |
| `price_int`           | Int    | 가격 (단위: KRW). **0:무료, -1:정보없음, -2:에러** |
| `price_currency`      | String | 통화 단위 (보통 "KRW")                             |
| `platforms`           | Object | 지원 플랫폼 `{windows: T/F, mac: T/F, linux: T/F}` |
| `supported_languages` | List   | 자막(인터페이스) 지원 언어 목록                    |
| `audio_languages`     | List   | 음성(더빙) 지원 언어 목록                          |
| `is_korean_supported` | Bool   | 한국어 자막 지원 여부                              |
| `is_korean_dubbed`    | Bool   | 한국어 더빙 지원 여부                              |

### 📝 설명 & 분류 (AI 임베딩용)
| Field                  | Type   | Description                                  |
| :--------------------- | :----- | :------------------------------------------- |
| `short_description_kr` | String | 짧은 설명 (한국어) - UI 표시용               |
| `short_description_en` | String | 짧은 설명 (영어) - AI 분석/검색용            |
| `genres_kr`            | List   | 장르 (한국어)                                |
| `genres_en`            | List   | 장르 (영어)                                  |
| `categories_kr`        | List   | 카테고리 (싱글플레이, 멀티플레이 등)         |
| `categories_en`        | List   | 카테고리 (영어)                              |
| `tags_en`              | List   | **스팀 유저 태그 (Top 20)** - 중요 분석 지표 |

### 📊 외부 평가 지표
| Field                   | Type | Description                        |
| :---------------------- | :--- | :--------------------------------- |
| `metacritic`            | Int  | 메타크리틱 점수 (없으면 0)         |
| `recommendations_total` | Int  | 스팀 전체 추천 수 (리뷰 수보다 큼) |

### 🖥 시스템 요구사항 (`specs`)
HTML 태그가 제거된 순수 텍스트입니다.
| Field         | Type   | Description          |
| :------------ | :----- | :------------------- |
| `specs`       | Object | **시스템 요구사항**  |
| └ `pc_min`    | String | Windows 최소 사양    |
| └ `pc_rec`    | String | Windows 권장 사양    |
| └ `mac_...`   | String | Mac 최소/권장 사양   |
| └ `linux_...` | String | Linux 최소/권장 사양 |

### 🎬 미디어 (`movies`, `screenshots`)
| Field                   | Type   | Description                           |
| :---------------------- | :----- | :------------------------------------ |
| `header_image`          | String | 대표 이미지 URL                       |
| `screenshots_thumbnail` | List   | 스크린샷 썸네일 URL (최대 10개)       |
| `screenshots_full`      | List   | 스크린샷 원본 URL (최대 10개)         |
| **movies**              | List   | **트레일러 영상 리스트**              |
| └ `id`                  | Int    | 영상 고유 ID                          |
| └ `name`                | String | 영상 제목 (예: "Launch Trailer")      |
| └ `thumbnail`           | String | 영상 미리보기 이미지 URL              |
| └ `mp4`                 | Object | `480`(저화질), `max`(고화질) URL 포함 |
| └ `webm`                | Object | `480`, `max` URL (웹 최적화 포맷)     |
| └ `hls`                 | String | 스트리밍용 m3u8 URL                   |