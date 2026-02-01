# 유저 데이터 (`steam_users.jsonl`)

예시 구조: `{"steamid": "76561198000000000", "game_count": 55, "games": [ ... ]}`

| Field                | Type      | Description                         |
| :------------------- | :-------- | :---------------------------------- |
| **steamid**          | String    | 유저 고유 ID (64-bit Steam ID)      |
| **game_count**       | Int       | 보유 게임 총 개수 (필터링 적용 후)  |
| **games**            | List      | **보유 게임 리스트**                |
| └ `appid`            | Int/Str   | 게임 고유 ID                        |
| └ `name`             | String    | 게임 이름                           |
| └ `playtime_forever` | Int       | 누적 플레이 시간 (분 단위)          |
| └ `playtime_2weeks`  | Int       | 최근 2주 플레이 시간 (분 단위)      |
| └ `last_played`      | Timestamp | 마지막 플레이 일시 (Unix Timestamp) |

## 수집 기준
- **공개 프로필**: 게임 보유 목록이 공개된 유저만 수집합니다.
- **최소 플레이**: 유의미한 데이터 확보를 위해 플레이 시간이 너무 적은 게임은 제외될 수 있습니다. (기본값: 10분 이상)
