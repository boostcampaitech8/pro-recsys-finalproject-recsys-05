import requests
import time
import json
import random
import os
from collections import deque

# ==========================================
# [⚙️ 설정: API 및 파일 경로]
# ==========================================
STEAM_API_KEY = "YOUR_API_KEY_HERE"  # ⚠️ 발급받은 Steam Web API Key를 입력하세요.

# 입력 파일: 장르별 시드 게임 목록
SEED_FILE = "seed_games.json"

# 출력 파일: 수집된 유저 데이터 저장 경로
OUTPUT_FILE = "collected_user_data.jsonl"

# 중복 방지: 이미 수집된 파일 목록 (재실행 시 중복 수집 방지)
EXISTING_FILES = [
    "collected_user_data.jsonl",  # 현재 수집 중인 파일도 포함
    # "part1_data.jsonl",        # 분산 수집 시 다른 머신의 결과 파일 추가 가능
]

# ==========================================
# [⚙️ 설정: 수집 옵션]
# ==========================================
# 목표 수집 유저 수
TARGET_USER_COUNT = 40000

# 장르당 초기 시드(Seed) 유저 추출 수
SEEDS_PER_GENRE = 150

# 유효 데이터 필터링 기준 (분 단위)
# 누적 플레이 10분 이상 OR 최근 2주 플레이 기록 존재 시 수집
MIN_PLAYTIME_MINUTES = 10


# ==========================================
# [함수 정의]
# ==========================================
def load_seed_games(filepath):
    """JSON 파일에서 시드 게임 ID 목록을 로드합니다."""
    if not os.path.exists(filepath):
        print(f"❌ 오류: '{filepath}' 파일을 찾을 수 없습니다.")
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_existing_ids(file_list):
    """
    기존 수집 파일들을 스캔하여 이미 수집된 Steam ID 목록을 반환합니다.
    (중복 수집 및 API 낭비 방지)
    """
    existing_ids = set()
    print("📂 기존 데이터 로드 중 (중복 방지)...")

    for filepath in file_list:
        if not os.path.exists(filepath):
            continue

        count = 0
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if "steamid" in data:
                            existing_ids.add(data["steamid"])
                            count += 1
                    except:
                        continue
        except Exception as e:
            print(f"   ⚠️ 파일 읽기 오류 ({filepath}): {e}")

        print(f"   -> '{filepath}': {count}명 로드 완료")

    print(f"🛡️ 총 {len(existing_ids)}명의 유저를 수집 대상에서 제외합니다.\n")
    return existing_ids


def safe_request(url, params, retries=3):
    """API 요청 실패 시 재시도 및 Rate Limit(429) 처리"""
    for i in range(retries):
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                time.sleep(10)  # Rate Limit 발생 시 대기
            elif response.status_code == 403:
                return None  # 비공개 프로필
        except Exception:
            time.sleep(1)
        time.sleep(1.0)  # 기본 딜레이
    return None


def get_seed_users_from_review(game_id, limit=50):
    """특정 게임의 최근 리뷰 작성자들을 시드 유저로 추출합니다."""
    url = f"https://store.steampowered.com/appreviews/{game_id}?json=1"
    params = {"filter": "recent", "num_per_page": 100, "purchase_type": "steam"}
    data = safe_request(url, params)

    users = set()
    if data and "reviews" in data:
        for review in data["reviews"]:
            users.add(review["author"]["steamid"])
            if len(users) >= limit:
                break
    return list(users)


def get_user_data(steam_id):
    """
    유저의 보유 게임 목록을 조회하고 필터링합니다.
    - 국가 코드 조회 API는 속도 최적화를 위해 제거되었습니다.
    """
    url_games = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
    params_games = {
        "key": STEAM_API_KEY,
        "steamid": steam_id,
        "format": "json",
        "include_appinfo": 1,
        "include_played_free_games": 1,
    }
    data_games = safe_request(url_games, params_games)

    if (
        not data_games
        or "response" not in data_games
        or "games" not in data_games["response"]
    ):
        return None  # 비공개 계정 또는 게임 없음

    games = data_games["response"]["games"]

    # 게임이 너무 적은 계정(깡통 계정) 제외
    if len(games) < 3:
        return None

    clean_games = []

    # 게임별 유효성 검사
    for g in games:
        pt_forever = g.get("playtime_forever", 0)
        pt_2weeks = g.get("playtime_2weeks", 0)

        # [필터 조건] 누적 10분 이상 OR 최근 2주 플레이 기록 존재
        if pt_forever >= MIN_PLAYTIME_MINUTES or pt_2weeks > 0:
            clean_games.append(
                {
                    "appid": g["appid"],
                    "name": g.get("name", "Unknown"),
                    "playtime_forever": pt_forever,
                    "playtime_2weeks": pt_2weeks,
                    "last_played": g.get("rtime_last_played", 0),
                }
            )

    # 유효한 게임이 하나라도 있는 경우만 저장
    if len(clean_games) > 0:
        return {
            "steamid": steam_id,
            "game_count": len(clean_games),
            "games": clean_games,
        }
    return None


def get_friends(steam_id):
    """유저의 친구 목록을 조회합니다 (스노우볼링 용도)"""
    url = "http://api.steampowered.com/ISteamUser/GetFriendList/v0001/"
    data = safe_request(
        url, {"key": STEAM_API_KEY, "steamid": steam_id, "relationship": "friend"}
    )
    if data and "friendslist" in data:
        return [f["steamid"] for f in data["friendslist"]["friends"]]
    return []


# ==========================================
# [Main: 실행 로직]
# ==========================================
def main():
    if "YOUR_API_KEY" in STEAM_API_KEY:
        print("❌ [설정 오류] 코드 상단의 'STEAM_API_KEY'에 본인의 키를 입력해주세요.")
        return

    # 1. 시드 게임 파일 로드
    seed_games = load_seed_games(SEED_FILE)
    if not seed_games:
        return

    print(f"🌱 로드된 장르 그룹: {list(seed_games.keys())}")

    # 2. 중복 방지: 기존 데이터 로드
    visited = load_existing_ids(EXISTING_FILES)

    # 3. 초기 시드(Seed) 유저 수집
    print("🔍 초기 시드 유저 추출 중...")
    initial_seeds = set()

    for genre, game_ids in seed_games.items():
        # 장르 내 게임 수에 맞춰 할당량 분배
        limit_per_game = max(10, SEEDS_PER_GENRE // len(game_ids))
        for gid in game_ids:
            users = get_seed_users_from_review(gid, limit=limit_per_game)
            for u in users:
                if u not in visited:  # 중복 제외
                    initial_seeds.add(u)

    print(f"\n🚀 시드 유저 {len(initial_seeds)}명 확보 -> 수집 시작")

    # 4. 큐(Queue) 생성 및 셔플
    queue = deque(list(initial_seeds))
    random.shuffle(queue)
    visited.update(initial_seeds)

    collected_count = 0

    # 파일 생성 (없으면 생성)
    if not os.path.exists(OUTPUT_FILE):
        open(OUTPUT_FILE, "w").close()

    # 5. 메인 루프 (BFS 탐색)
    while queue:
        if collected_count >= TARGET_USER_COUNT:
            print("\n🎉 목표 수집량을 달성했습니다!")
            break

        curr_id = queue.popleft()

        # 유저 데이터 수집
        user_data = get_user_data(curr_id)

        if user_data:
            # 파일에 이어쓰기 (JSONL 형식)
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(user_data, ensure_ascii=False) + "\n")

            collected_count += 1
            if collected_count % 50 == 0:
                print(
                    f"[{collected_count}/{TARGET_USER_COUNT}] 데이터 수집 중... (남은 대기열: {len(queue)})"
                )

        # 친구 목록을 큐에 추가 (스노우볼링)
        # 메모리 관리를 위해 대기열 20,000명 제한
        if len(queue) < 20000:
            friends = get_friends(curr_id)
            for f_id in friends:
                if f_id not in visited:
                    visited.add(f_id)
                    queue.append(f_id)

    print(f"\n✅ 수집 완료. 결과 파일: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
