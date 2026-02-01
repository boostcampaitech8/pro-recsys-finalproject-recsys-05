import requests
import json
import time
import os
from bs4 import BeautifulSoup

# ==========================================
# ⚙️ 설정 (Configuration)
# ==========================================
# !!!!!!!!!!!!!!!!!! PART를 수정할 것 !!!!!!!!!!!!!!!!!!
# PART = 1
# INPUT_ID_FILE = f"target_games_part{PART}_info.json"
# OUTPUT_FILE = f"steam_games_info_part{PART}.jsonl"
INPUT_ID_FILE = f"target_games_all.json"
OUTPUT_FILE = f"steam_games_info_raw.jsonl"

DELAY_SECONDS = 2.2  # 안정적인 API 호출을 위해 안전하게 대기

# ==========================================
# 🧹 파싱 헬퍼 함수
# ==========================================


def clean_html(html_text):
    """HTML 태그 제거"""
    if not html_text or isinstance(html_text, list):
        return "정보 없음"
    return BeautifulSoup(html_text, "html.parser").get_text(separator=" ").strip()


def parse_languages(html_text):
    """자막/음성(더빙) 지원 여부 정밀 분석"""
    if not html_text:
        return {"interface": [], "audio": []}

    clean_text = html_text.replace("languages with full audio support", "")
    interface_list = []
    audio_list = []

    raw_langs = clean_text.split(",")
    for raw in raw_langs:
        if not raw.strip():
            continue
        is_audio = "*" in raw
        lang_name = (
            BeautifulSoup(raw, "html.parser").get_text().replace("*", "").strip()
        )

        if lang_name:
            interface_list.append(lang_name)
            if is_audio:
                audio_list.append(lang_name)

    return {"interface": interface_list, "audio": audio_list}


# ==========================================
# 📡 네트워크 요청 함수들
# ==========================================


def fetch_steam_tags_en(appid):
    """[크롤링] 영어 태그 수집 (임베딩용)"""
    url = f"https://store.steampowered.com/app/{appid}/?l=english&cc=us"
    cookies = {
        "birthtime": "946684801",
        "lastagecheckage": "1-0-2000",
        "wants_mature_content": "1",
        "Steam_Language": "english",
    }
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        response = requests.get(url, headers=headers, cookies=cookies, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            tags = [t.get_text(strip=True) for t in soup.select("a.app_tag")]
            return tags[:20]
    except:
        pass
    return []


def fetch_app_details(appid, lang="koreana"):
    """
    [강력 버전] 한국 실패 시 즉시 미국(US) 우회 시도
    """
    url = "https://store.steampowered.com/api/appdetails"
    str_id = str(appid)
    # 1라운드: 한국 (KR) 시도
    try:
        # print(f"  -> 🇰🇷 KR 시도...", end=" ") # 디버깅용
        res = requests.get(
            url, params={"appids": appid, "l": lang, "cc": "kr"}, timeout=5
        )

        if res.status_code == 429:
            print("\n🚨 [IP WARNING] 429 차단됨. 60초 휴식.")
            time.sleep(60)
            return fetch_app_details(appid, lang)  # 재귀 호출

        data = res.json()
        if data and str_id in data and data[str_id]["success"] is True:
            # print("성공!")
            result = data[str_id]["data"]
            result["_region_source"] = "KR"
            return result

    except Exception as e:
        print(f"(KR 에러: {e})", end=" ")

    # 2라운드: 미국 (US) 시도 - 한국 실패 시 무조건 실행
    try:
        # print(f"🇺🇸 US 우회 시도...", end=" ") # 디버깅용
        res = requests.get(
            url, params={"appids": appid, "l": lang, "cc": "us"}, timeout=5
        )

        data = res.json()
        if data and str_id in data and data[str_id]["success"] is True:
            # print("우회 성공!")
            result = data[str_id]["data"]
            result["_region_source"] = "US"  # 미국 데이터임을 표시
            return result

    except Exception as e:
        pass

    # 3. 둘 다 실패
    return None


# ==========================================
# 🧠 데이터 조립 (Main Logic)
# ==========================================


def process_game(appid):
    # 1. 한국어 데이터 수집 (UI용)
    kr_data = fetch_app_details(appid, "koreana")
    if not kr_data:
        return None

    # 2. 영어 데이터 수집 (AI 임베딩용)
    time.sleep(0.5)
    en_data = fetch_app_details(appid, "english")
    if not en_data:
        return None

    # 3. 추가 정보 수집 (태그)
    tags_en = fetch_steam_tags_en(appid)

    # --- 데이터 가공 ---
    # 언어 분석
    langs = parse_languages(en_data.get("supported_languages", ""))
    is_kr_interface = "Korean" in langs["interface"]
    is_kr_audio = "Korean" in langs["audio"]

    # 가격 정보 (-1 : 정보없음, -2: 에러)
    price_int = -1
    price_currency = "KRW"

    if kr_data.get("is_free"):
        price_int = 0
    else:
        price_data = kr_data.get("price_overview")
        if price_data:
            raw_price = price_data.get("initial")

            # 값이 없거나(None) 비정상이면 -2(에러)로 강제 설정
            if raw_price is None:
                raw_price = -2

            if price_data.get("currency") == "KRW" and raw_price >= 0:
                price_int = int(raw_price / 100)
            else:
                price_int = raw_price

            price_currency = price_data.get("currency", "KRW")

    def get_req_text(data, key, subkey):
        req = data.get(key, {})
        # Steam API 버그: 비어있으면 {}가 아니라 []로 옴 -> 딕셔너리 아니면 무시
        if isinstance(req, list):
            return "정보 없음"
        return clean_html(req.get(subkey))

    specs = {
        "pc_min": get_req_text(en_data, "pc_requirements", "minimum"),
        "pc_rec": get_req_text(en_data, "pc_requirements", "recommended"),
        "mac_min": get_req_text(en_data, "mac_requirements", "minimum"),
        "mac_rec": get_req_text(en_data, "mac_requirements", "recommended"),
        "linux_min": get_req_text(en_data, "linux_requirements", "minimum"),
        "linux_rec": get_req_text(en_data, "linux_requirements", "recommended"),
    }

    # 미디어 URL 추출
    screenshots_thumb = [s["path_thumbnail"] for s in kr_data.get("screenshots", [])][
        :10
    ]
    screenshots_full = [s["path_full"] for s in kr_data.get("screenshots", [])][:10]

    # --- 영상 로직 (480p, Max, HLS 모두 수집) ---
    movies_data = []

    for m in en_data.get("movies", []):
        movie_entry = {
            "id": m.get("id"),
            "name": m.get("name"),
            "thumbnail": m.get("thumbnail", ""),
            "mp4": {},  # 여기에 480, max를 담음
            "webm": {},
            "hls": "",
        }

        # 1. MP4 수집 (일반적인 경우)
        if "mp4" in m:
            movie_entry["mp4"] = {
                "480": m["mp4"].get("480", ""),  # 저화질 (리스트용)
                "max": m["mp4"].get("max", ""),  # 고화질 (상세용)
            }

        # 2. WebM 수집 (보조용)
        if "webm" in m:
            movie_entry["webm"] = {
                "480": m["webm"].get("480", ""),
                "max": m["webm"].get("max", ""),
            }

        # 3. HLS 수집 (스트리밍 전용, 또는 최신 고화질 트레일러)
        # 보통 hls_h264 키가 있으면 그걸 씁니다.
        if "hls_h264" in m:
            movie_entry["hls"] = m["hls_h264"]

        # [유효성 검사]
        # mp4, webm, hls 중 하나라도 재생 가능한 링크가 있어야 저장
        has_video = (
            movie_entry["mp4"].get("max")
            or movie_entry["webm"].get("max")
            or movie_entry["hls"]
        )

        if has_video:
            movies_data.append(movie_entry)

    # 최종 딕셔너리
    return {
        # --- 식별자 ---
        "name": kr_data.get("name"),
        "type": kr_data.get("type"),
        # 한국 스토어에서 가져왔는지 여부
        "is_available_in_kr": (kr_data.get("_region_source") == "KR"),
        # --- 기본 스펙 ---
        "is_free": kr_data.get("is_free"),
        "price_int": price_int,
        "price_currency": price_currency,
        "release_date": en_data.get("release_date", {}).get("date", "Unknown"),
        "age_rating": kr_data.get("required_age", 0),
        "dlc_count": len(kr_data.get("dlc", [])),
        # --- 언어/플랫폼 정보 ---
        "supported_languages": langs["interface"],
        "audio_languages": langs["audio"],
        "is_korean_supported": is_kr_interface,
        "is_korean_dubbed": is_kr_audio,
        "platforms": en_data.get("platforms", {}),  # win, mac, linux (bool)
        "specs": specs,  # 상세 요구사항 텍스트
        # --- UI 표시용 텍스트 (KR) ---
        "short_description_kr": kr_data.get("short_description", ""),
        "genres_kr": [g["description"] for g in kr_data.get("genres", [])],
        "categories_kr": [c["description"] for c in kr_data.get("categories", [])],
        "developers": en_data.get("developers", []),
        "publishers": en_data.get("publishers", []),
        # --- AI 임베딩용 텍스트 (EN) ---
        "name_en": en_data.get("name") if en_data else kr_data.get("name"),
        "short_description_en": en_data.get("short_description", "") if en_data else "",
        "genres_en": (
            [g["description"] for g in en_data.get("genres", [])] if en_data else []
        ),
        "categories_en": [c["description"] for c in en_data.get("categories", [])],
        "tags_en": tags_en,  # (크롤링된 영어 태그),
        # --- 통계 (단순 제공값만) ---
        "metacritic": kr_data.get("metacritic", {}).get("score", 0),
        "recommendations_total": kr_data.get("recommendations", {}).get("total", 0),
        # --- 미디어 에셋 (URL) ---
        "header_image": kr_data.get("header_image"),
        "screenshots_thumbnail": screenshots_thumb,
        "screenshots_full": screenshots_full,
        "movies": movies_data,
    }


# ==========================================
# 🚀 메인 실행부
# ==========================================
def main():
    print("🚀 Ultimate Steam Info Crawler (JSONL Ver.)")

    # 1. 대상 로드
    target_ids = []
    if os.path.exists(INPUT_ID_FILE):
        with open(INPUT_ID_FILE, "r", encoding="utf-8") as f:
            target_ids = json.load(f)
        print(f"📂 타겟 파일 로드: {len(target_ids)}개")
    else:
        print("❌ 타겟 파일이 없습니다.")
        return

    # 2. 기존 데이터 확인 (JSONL 라인 스캔)
    collected_ids = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    # { "appid": {...} } 형태라고 가정하고 키를 추출
                    key = list(data.keys())[0]
                    collected_ids.add(str(key))
                except:
                    pass
    print(f"📂 기존 데이터 {len(collected_ids)}개 로드 완료. 이어서 진행합니다.")

    # 3. 수집 루프
    count = 0
    for appid in target_ids:
        str_id = str(appid)
        if str_id in collected_ids:
            continue

        print(f"[{count+1}] 🔍 {appid} 수집 중...", end=" ")

        try:
            game_data = process_game(appid)
            if game_data:
                # ✅ [핵심] JSONL 저장 (한 줄씩 Append)
                row_data = {str_id: game_data}

                with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(row_data, ensure_ascii=False) + "\n")

                print(f"✅ {game_data['name']} (Tags: {len(game_data['tags_en'])})")
            else:
                print("🚫 패스 (게임 아님)")
        except Exception as e:
            print(f"❌ 에러: {e}")

        count += 1
        if count % 50 == 0:
            print("☕ 50개 수집 완료. 10초간 API 쿨다운...")
            time.sleep(10)
        time.sleep(DELAY_SECONDS)

    print("✨ 모든 수집 완료!")


if __name__ == "__main__":
    main()
