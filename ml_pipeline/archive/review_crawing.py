import requests
import json
import time
import os
import re

# ==========================================
# ⚙️ 설정 (Quotas)
# ==========================================
# INPUT_ID_FILE = "target_games_part1.json"
# OUTPUT_FILE = "steam_reviews.jsonl"

INPUT_ID_FILE = "target_games_all.json"
OUTPUT_FILE = "steam_reviews.jsonl"


TARGET_RECENT = 75  # 한국어 최근 (트렌드)
TARGET_ALL_TIME = 75  # 한국어 역대 (공략/심층)
TOTAL_LIMIT = 200  # 게임당 최대 수집 리뷰 수
BATCH_SIZE = 10
DELAY_SECONDS = 1.5


# ==========================================
# 🛠️ 기능 1: 정확한 수치 통계 수집 (New!)
# ==========================================
def fetch_stats_only(app_id):
    """
    리뷰 텍스트 수집과는 별개로, '정확한 긍정/부정 수치'만 API로 빠르게 가져옵니다.
    """
    base_url = f"https://store.steampowered.com/appreviews/{app_id}"
    stats = {
        "total_positive": 0,
        "total_negative": 0,
        "total_count": 0,
        "review_score_desc": "",
        "recent_positive": 0,
        "recent_negative": 0,
        "recent_count": 0,
        "recent_score_desc": "",
    }

    try:
        # 1. 전체 기간 (All time)
        p_all = {
            "json": 1,
            "language": "all",
            "purchase_type": "all",
            "num_per_page": 0,
        }
        res = requests.get(base_url, params=p_all, timeout=5)
        if res.status_code == 200:
            summary = res.json().get("query_summary", {})
            stats["total_positive"] = summary.get("total_positive", 0)
            stats["total_negative"] = summary.get("total_negative", 0)
            stats["total_count"] = summary.get("total_reviews", 0)
            stats["review_score_desc"] = summary.get("review_score_desc", "N/A")

        # 2. 최근 30일 (Recent)
        time.sleep(0.2)
        p_recent = {
            "json": 1,
            "language": "all",
            "purchase_type": "all",
            "num_per_page": 0,
            "day_range": "30",
        }
        res_recent = requests.get(base_url, params=p_recent, timeout=5)
        if res_recent.status_code == 200:
            summary = res_recent.json().get("query_summary", {})
            stats["recent_positive"] = summary.get("total_positive", 0)
            stats["recent_negative"] = summary.get("total_negative", 0)
            stats["recent_count"] = summary.get("total_reviews", 0)
            stats["recent_score_desc"] = summary.get("review_score_desc", "N/A")

    except Exception as e:
        print(f"⚠️ 통계 수집 중 에러: {e}")

    return stats


# ==========================================
# 🛠️ 기능 2: 정교한 리뷰 텍스트 수집 (Balanced Logic)
# ==========================================
def clean_review_text(text):
    if not text:
        return ""
    # 과도한 도배(장식선)만 축소
    text = re.sub(r"([─━│║═░▒▓█=_\-\.]){10,}", r"\1\1\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:2000]  # 2000자 제한


def parse_review(r):
    return {
        "id": r.get("recommendationid"),
        "language": r.get("language"),
        "text": clean_review_text(r.get("review", "")),
        "voted_up": r.get("voted_up"),
        "votes_up": r.get("votes_up"),
        "weighted_vote_score": float(r.get("weighted_vote_score", 0)),
        "playtime": r.get("author", {}).get("playtime_forever", 0),
        "date": r.get("timestamp_created"),
    }


def fetch_reviews_balanced(app_id):
    base_url = f"https://store.steampowered.com/appreviews/{app_id}"
    collected = {}

    # 기본 파라미터: '유용한 순(filter=all)'으로 가져옵니다.
    params = {"json": 1, "filter": "all", "review_type": "all", "purchase_type": "all"}

    # 1. [한국어] 최근 (트렌드 파악)
    try:
        p = {
            **params,
            "language": "koreana",
            "day_range": "365",
            "num_per_page": TARGET_RECENT,
        }
        res = requests.get(base_url, params=p, timeout=10)
        if res.status_code == 200:
            for r in res.json().get("reviews", []):
                collected[r["recommendationid"]] = parse_review(r)

        # 2. [한국어] 역대 (심층 분석, 최근 것과 중복 방지)
        time.sleep(0.5)
        p = {
            **params,
            "language": "koreana",
            "day_range": "36500",
            "num_per_page": TARGET_ALL_TIME,
        }
        res = requests.get(base_url, params=p, timeout=10)
        if res.status_code == 200:
            for r in res.json().get("reviews", []):
                if r["recommendationid"] not in collected:
                    collected[r["recommendationid"]] = parse_review(r)
    except:
        pass

    # 3. [영어] 한국어 부족 시 보충
    if len(collected) < 50:
        try:
            time.sleep(0.5)
            p = {
                **params,
                "language": "english",
                "day_range": "36500",
                "num_per_page": 50 - len(collected),
            }
            res = requests.get(base_url, params=p, timeout=10)
            if res.status_code == 200:
                for r in res.json().get("reviews", []):
                    if r["recommendationid"] not in collected:
                        collected[r["recommendationid"]] = parse_review(r)
        except:
            pass

    # 4. [글로벌] 영어도 부족하면 아무 언어나 가져옴
    if len(collected) < 30:
        try:
            needed = 50 - len(collected)
            time.sleep(0.5)
            p = {
                **params,
                "language": "all",
                "day_range": "36500",
                "num_per_page": needed,
            }
            res = requests.get(base_url, params=p, timeout=10)
            if res.status_code == 200:
                for r in res.json().get("reviews", []):
                    if r["recommendationid"] not in collected:
                        collected[r["recommendationid"]] = parse_review(r)
        except:
            pass

    # 가중치 점수(유용함) 순으로 정렬 후 반환
    final = list(collected.values())
    final.sort(key=lambda x: x["weighted_vote_score"], reverse=True)
    return final[:TOTAL_LIMIT]


# ==========================================
# 🚀 메인 실행부
# ==========================================
# [메인 실행부 수정]
def main():
    print("🚀 스팀 리뷰 수집기 시작")

    # 1. 기존에 어디까지 했는지 확인 (JSONL은 줄 수만 세면 됨)
    collected_ids = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    # 저장된 데이터의 key(게임ID)를 가져옴
                    game_id = list(data.keys())[0]
                    collected_ids.add(str(game_id))
                except:
                    pass
        print(f"📂 기존 데이터 {len(collected_ids)}개 로드 완료. 이어서 진행합니다.")

    # 2. 수집 루프
    # 1. 파일 로드 (game_info_crawing.py와 동일 로직 적용)
    target_ids = []
    if os.path.exists(INPUT_ID_FILE):
        with open(INPUT_ID_FILE, "r", encoding="utf-8") as f:
            target_ids = json.load(f)
        print(f"📂 타겟 파일 로드: {len(target_ids)}개")
    else:
        print(f"❌ '{INPUT_ID_FILE}' 파일이 없습니다.")
        return

    for app_id in target_ids:
        str_id = str(app_id)
        if str_id in collected_ids:
            continue  # 이미 있으면 패스

        print(f"⚖️ {app_id} 처리 중...", end=" ")

        # 데이터 수집 (함수는 그대로 사용)
        stats = fetch_stats_only(app_id)
        reviews = fetch_reviews_balanced(app_id)

        # 저장할 데이터 구조
        row_data = {str_id: {"stats": stats, "reviews": reviews}}

        # 바로바로 이어쓰기 (Append)
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(row_data, ensure_ascii=False) + "\n")

        print(f"✅ 저장 완료 ({len(reviews)}개)")
        time.sleep(DELAY_SECONDS)


if __name__ == "__main__":
    main()
