# 리뷰 데이터 (`steam_reviews.jsonl`)

예시 구조: `{"appid": "1091500", "stats": {.....}, "reviews": {......}}`


| Field                   | Type      | Description                                       |
| :---------------------- | :-------- | :------------------------------------------------ |
| **stats**               | Object    | **정량적 통계 데이터**                            |
| └ `total_positive`      | Int       | 역대 긍정 리뷰 개수                               |
| └ `total_negative`      | Int       | 역대 부정 리뷰 개수                               |
| └ `total_count`         | Int       | 역대 리뷰 총 개수 (`total_reviews` 매핑)          |
| └ `review_score_desc`   | String    | 종합 평가 등급 (예: "Overwhelmingly Positive")    |
| └ `recent_positive`     | Int       | 최근 30일 긍정 개수                               |
| └ `recent_negative`     | Int       | 최근 30일 부정 개수                               |
| └ `recent_count`        | Int       | 최근 30일 리뷰 총 개수                            |
| └ `recent_score_desc`   | String    | 최근 평가 등급                                    |
| **reviews**             | List      | **개별 리뷰 리스트**                              |
| └ `id`                  | String    | 리뷰 고유 ID (`recommendationid`)                 |
| └ `language`            | String    | 리뷰 작성 언어 (koreana, english 등)              |
| └ `text`                | String    | 리뷰 본문 (전처리됨: 도배 문자 제거, 2000자 제한) |
| └ `voted_up`            | Bool      | 따봉 여부 (True: 추천, False: 비추천)             |
| └ `votes_up`            | Int       | 이 리뷰가 받은 추천 수 (따봉 개수)                |
| └ `weighted_vote_score` | Float     | 유용함 점수 (0~1 사이, 높을수록 상단 노출)        |
| └ `playtime`            | Int       | 리뷰 작성 시점의 플레이 시간 (분 단위)            |
| └ `date`                | Timestamp | 작성 일시                                         |