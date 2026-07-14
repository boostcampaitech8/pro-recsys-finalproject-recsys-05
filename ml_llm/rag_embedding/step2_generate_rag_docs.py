#!/usr/bin/env python3
"""
Steam Game RAG Document Generator
게임 정보와 리뷰 문장을 결합하여 RAG용 문서를 생성

입력 1: steam_review_sents.jsonl (Step 1 출력)
입력 2: games_info.jsonl (게임 메타데이터)

출력: rag_documents.jsonl (3가지 문서 타입)
1. game_card: 게임 기본 정보
2. pros_summary: 긍정 리뷰 요약
3. cons_summary: 부정 리뷰 요약

사용법:
python step2_generate_rag_docs.py \
    --sents /data/steam_review_sents.jsonl \
    --info /data/games_info.jsonl \
    --output /data/rag_documents.jsonl \
    --top_pos 80 \
    --top_neg 40 \
    --bullets 8
"""

import argparse
import json
import re
import sys
from pathlib import Path
from collections import defaultdict
from typing import Any, Optional
import heapq


# ==================== 정규표현식 ====================
BBCODE_RE = re.compile(
    r"\[/?(b|i|u|url|quote|code|list|\*|img|h1|h2|h3|spoiler|table|tr|td|th|hr|br)(=[^\]]+)?\]",
    re.IGNORECASE
)
WS_RE = re.compile(r"\s+")
DEDUP_RE = re.compile(r"[\s\W_]+")


# ==================== 소프트웨어 태그 필터 ====================
NON_GAME_TAGS = {
    "360 Video",
    "Animation & Modeling",
    "Audio Production",
    "Benchmark",
    "Coding",
    "Design & Illustration",
    "Documentary",
    "Education",
    "Electronic Music",
    "Experience",
    "Feature Film",
    "Hardware",
    "Instrumental Music",
    "Movie",
    "Music",
    "Photo Editing",
    "Programming",
    "Rock Music",
    "Short",
    "Software",
    "Software Training",
    "Soundtrack",
    "Tutorial",
    "Typing",
    "Utilities",
    "Video Production",
    "Web Publishing"
}


def is_non_game(tags_en: list) -> bool:
    """소프트웨어/비게임 태그가 있는지 확인"""
    if not tags_en:
        return False
    return any(tag in NON_GAME_TAGS for tag in tags_en)


# ==================== 유틸리티 함수 ====================
def clean_sent(text: str) -> str:
    """BBCode 제거 및 공백 정리"""
    if not text:
        return ""
    text = BBCODE_RE.sub("", text)
    text = WS_RE.sub(" ", text).strip()
    return text


def safe_list(x: Any) -> list:
    """None-safe 리스트 변환"""
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def join_nonempty(items: list, sep: str = ", ") -> str:
    """빈 값 제외하고 조인"""
    items = [str(x).strip() for x in items if x is not None and str(x).strip()]
    return sep.join(items)


def summarize_platforms(platforms: Optional[dict]) -> list[str]:
    """플랫폼 정보 요약"""
    if not isinstance(platforms, dict):
        return []
    out = []
    for key in ["windows", "mac", "linux"]:
        if platforms.get(key) is True:
            out.append(key)
    return out


def price_str(is_free: bool, price_int: Optional[int], currency: str = "KRW") -> str:
    """가격 문자열 생성"""
    if is_free:
        return "무료"
    if price_int in (None, -1):
        return "가격 정보 없음"
    if price_int == -2:
        return "가격 조회 오류"
    if price_int == 0:
        return "무료"
    try:
        return f"{int(price_int):,} {currency}"
    except Exception:
        return f"{price_int} {currency}"


# ==================== Heap 유틸리티 ====================
def push_topk(heap: list, item: tuple, k: int) -> None:
    """Min-heap을 사용하여 상위 k개 유지"""
    if len(heap) < k:
        heapq.heappush(heap, item)
    else:
        if item[0] > heap[0][0]:
            heapq.heapreplace(heap, item)


def heap_to_sorted_list(heap: list) -> list:
    """Heap을 점수 내림차순 리스트로 변환"""
    return sorted(heap, key=lambda x: x[0], reverse=True)


# ==================== RAG 문서 생성기 ====================
class RAGDocumentGenerator:
    def __init__(self, top_pos: int, top_neg: int, bullets: int):
        self.top_pos = top_pos
        self.top_neg = top_neg
        self.bullets = bullets
        
        self.stats = {
            'games_info_loaded': 0,
            'games_info_missing_appid': 0,
            'filtered_non_game': 0,
            'sentences_processed': 0,
            'unique_appids': 0,
            'game_cards_created': 0,
            'pros_summaries_created': 0,
            'cons_summaries_created': 0,
            'total_docs_created': 0,
            'skipped_missing_info': 0
        }
    
    def load_games_info(self, info_path: Path) -> dict[int, dict]:
        """게임 정보 JSONL 로드 (소프트웨어 필터링)"""
        print(f"📂 Loading games info: {info_path}")
        info_by_appid = {}
        
        with info_path.open('r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    appid = obj.get("appid", obj.get("steam_appid", None))
                    if appid is None:
                        self.stats['games_info_missing_appid'] += 1
                        continue
                    appid = int(appid)
                    
                    # 소프트웨어 태그 필터링
                    tags_en = safe_list(obj.get("tags_en"))
                    if is_non_game(tags_en):
                        self.stats['filtered_non_game'] += 1
                        continue
                    
                    info_by_appid[appid] = obj
                    self.stats['games_info_loaded'] += 1
                except Exception as e:
                    print(f"⚠️  [WARN] Error at line {line_num}: {e}", file=sys.stderr)
                    continue
        
        print(f"✅ Loaded {self.stats['games_info_loaded']:,} game info records")
        print(f"   Filtered {self.stats['filtered_non_game']:,} non-game software")
        return info_by_appid
    
    def load_and_aggregate_sentences(self, sents_path: Path) -> tuple[dict, dict]:
        """문장 JSONL 로드 및 appid별로 상위 문장 집계"""
        print(f"📂 Loading sentences: {sents_path}")
        
        pos_heaps = defaultdict(list)
        neg_heaps = defaultdict(list)
        seen_hash = defaultdict(set)
        counter = 0  # tie-breaking용 카운터
        
        with sents_path.open('r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                
                try:
                    r = json.loads(line)
                    appid = int(r["appid"])
                    sent = clean_sent(r.get("sent", ""))
                    
                    if not sent:
                        continue
                    
                    # appid별 중복 제거
                    key = DEDUP_RE.sub("", sent.lower())
                    if key and key in seen_hash[appid]:
                        continue
                    if key:
                        seen_hash[appid].add(key)
                    
                    label = int(r.get("label", 0))
                    q = float(r.get("quality", 0.0))
                    
                    payload = {
                        "review_id": str(r.get("review_id", "")),
                        "sent": sent,
                        "quality": q,
                        "votes_up": int(r.get("votes_up", 0)),
                        "wvs": float(r.get("wvs", 0.0)),
                        "playtime_min": int(r.get("playtime_min", 0)),
                        "date": int(r.get("date", 0)),
                    }
                    
                    counter += 1
                    # (quality, counter, payload) 튜플로 저장 - counter로 tie-breaking
                    item = (q, counter, payload)
                    if label == 1:
                        push_topk(pos_heaps[appid], item, self.top_pos)
                    else:
                        push_topk(neg_heaps[appid], item, self.top_neg)
                    
                    self.stats['sentences_processed'] += 1
                    
                    # 진행상황 출력
                    if line_num % 10000 == 0:
                        print(f"📊 Processed {line_num:,} sentences", end='\r')
                
                except Exception as e:
                    if line_num % 10000 == 0:  # 너무 많은 에러 출력 방지
                        print(f"\n⚠️  [WARN] Error at line {line_num}: {e}", file=sys.stderr)
                    continue
        
        print()  # 줄바꿈
        self.stats['unique_appids'] = len(set(list(pos_heaps.keys()) + list(neg_heaps.keys())))
        print(f"✅ Processed {self.stats['sentences_processed']:,} sentences")
        print(f"✅ Found {self.stats['unique_appids']:,} unique appids")
        
        return pos_heaps, neg_heaps
    
    def create_game_card(self, appid: int, info: dict) -> dict:
        """게임 카드 문서 생성"""
        name = info.get("name") or info.get("name_en") or f"appid:{appid}"
        name_en = info.get("name_en") or ""
        gtype = info.get("type") or "game"
        is_kr = bool(info.get("is_available_in_kr", True))
        is_free = bool(info.get("is_free", False))
        price_int = info.get("price_int", None)
        currency = info.get("price_currency", "KRW")
        
        platforms = summarize_platforms(info.get("platforms"))
        is_ko_sub = bool(info.get("is_korean_supported", False))
        is_ko_dub = bool(info.get("is_korean_dubbed", False))
        
        short_kr = info.get("short_description_kr") or ""
        short_en = info.get("short_description_en") or ""
        
        genres_kr = safe_list(info.get("genres_kr"))
        genres_en = safe_list(info.get("genres_en"))
        cats_kr = safe_list(info.get("categories_kr"))
        cats_en = safe_list(info.get("categories_en"))
        tags_en = safe_list(info.get("tags_en"))
        
        developers = safe_list(info.get("developers"))
        publishers = safe_list(info.get("publishers"))
        
        release_date = info.get("release_date") or ""
        age_rating = info.get("age_rating", 0)
        metacritic = info.get("metacritic", 0)
        rec_total = info.get("recommendations_total", 0)
        
        # 텍스트 구성
        card_lines = []
        card_lines.append(f"게임: {name}" + (f" ({name_en})" if name_en else ""))
        card_lines.append(f"타입: {gtype} | 한국 스토어: {'가능' if is_kr else '불가'}")
        card_lines.append(f"가격: {price_str(is_free, price_int, currency)}")
        if platforms:
            card_lines.append(f"플랫폼: {', '.join(platforms)}")
        card_lines.append(f"한국어: 자막 {'O' if is_ko_sub else 'X'} / 더빙 {'O' if is_ko_dub else 'X'}")
        if release_date:
            card_lines.append(f"출시일: {release_date} | 연령등급: {age_rating}")
        if developers:
            card_lines.append(f"개발사: {join_nonempty(developers)}")
        if publishers:
            card_lines.append(f"배급사: {join_nonempty(publishers)}")
        if genres_kr or genres_en:
            card_lines.append(f"장르: {join_nonempty(genres_kr) or join_nonempty(genres_en)}")
        if cats_kr or cats_en:
            card_lines.append(f"플레이 유형: {join_nonempty(cats_kr) or join_nonempty(cats_en)}")
        if tags_en:
            card_lines.append(f"태그(Top): {', '.join(tags_en[:10])}")
        if metacritic:
            card_lines.append(f"Metacritic: {metacritic}")
        if rec_total:
            card_lines.append(f"Steam 추천 수: {rec_total}")
        if short_kr:
            card_lines.append(f"설명: {short_kr}")
        elif short_en:
            card_lines.append(f"설명(EN): {short_en}")
        
        return {
            "doc_id": f"{appid}::game_card::v1",
            "appid": appid,
            "lang": "ko",
            "doc_type": "game_card",
            "text": "\n".join(card_lines),
            "meta": {
                "name": name,
                "name_en": name_en,
                "type": gtype,
                "is_available_in_kr": is_kr,
                "is_free": is_free,
                "price_int": price_int,
                "price_currency": currency,
                "platforms": info.get("platforms"),
                "is_korean_supported": is_ko_sub,
                "is_korean_dubbed": is_ko_dub,
                "genres_en": genres_en,
                "categories_en": cats_en,
                "tags_en": tags_en,
                "release_date": release_date,
                "age_rating": age_rating,
                "metacritic": metacritic,
                "recommendations_total": rec_total,
                "header_image": info.get("header_image"),
            }
        }
    
    def create_summary(self, appid: int, doc_type: str, items: list, label_name: str) -> Optional[dict]:
        """리뷰 요약 문서 생성"""
        if not items:
            return None
        
        bullets = items[:self.bullets]
        text_lines = [f"{label_name}에서 자주 언급되는 핵심 포인트(근거 문장):"]
        for b in bullets:
            text_lines.append(f"- {b['sent']}")
        
        meta = {
            "evidence_count": len(bullets),
            "quality_avg": round(sum(x["quality"] for x in bullets) / len(bullets), 4),
        }
        
        return {
            "doc_id": f"{appid}::{doc_type}::v1",
            "appid": appid,
            "lang": "ko",
            "doc_type": doc_type,
            "text": "\n".join(text_lines),
            "meta": meta,
            "evidence": bullets
        }
    
    def generate_documents(self, 
                          info_by_appid: dict,
                          pos_heaps: dict,
                          neg_heaps: dict,
                          output_path: Path) -> None:
        """RAG 문서 생성 및 저장"""
        print(f"\n📝 Generating RAG documents...")
        print(f"📁 Output: {output_path}")
        print("-" * 80)
        
        all_appids = sorted(set(list(pos_heaps.keys()) + list(neg_heaps.keys())))
        
        with output_path.open('w', encoding='utf-8') as fout:
            for idx, appid in enumerate(all_appids, 1):
                info = info_by_appid.get(appid)
                
                if info is None:
                    self.stats['skipped_missing_info'] += 1
                    continue
                
                # 1. Game Card 생성
                game_card = self.create_game_card(appid, info)
                fout.write(json.dumps(game_card, ensure_ascii=False) + "\n")
                self.stats['game_cards_created'] += 1
                self.stats['total_docs_created'] += 1
                
                # 2. Pros Summary 생성 (튜플 언패킹 수정: _, _, p)
                pos_items = [p for _, _, p in heap_to_sorted_list(pos_heaps.get(appid, []))]
                if pos_items:
                    pros = self.create_summary(appid, "pros_summary", pos_items, "장점(긍정 리뷰)")
                    if pros:
                        fout.write(json.dumps(pros, ensure_ascii=False) + "\n")
                        self.stats['pros_summaries_created'] += 1
                        self.stats['total_docs_created'] += 1
                
                # 3. Cons Summary 생성 (튜플 언패킹 수정: _, _, p)
                neg_items = [p for _, _, p in heap_to_sorted_list(neg_heaps.get(appid, []))]
                if neg_items:
                    cons = self.create_summary(appid, "cons_summary", neg_items, "단점/주의(부정 리뷰)")
                    if cons:
                        fout.write(json.dumps(cons, ensure_ascii=False) + "\n")
                        self.stats['cons_summaries_created'] += 1
                        self.stats['total_docs_created'] += 1
                
                # 진행상황 출력
                if idx % 100 == 0:
                    print(f"📊 Processed {idx:,}/{len(all_appids):,} games | "
                          f"Docs: {self.stats['total_docs_created']:,}", end='\r')
        
        print()  # 줄바꿈
        self.print_stats()
    
    def print_stats(self) -> None:
        """처리 통계 출력"""
        print("\n" + "=" * 80)
        print("📊 RAG Document Generation Statistics")
        print("=" * 80)
        print(f"Games info loaded: {self.stats['games_info_loaded']:,}")
        print(f"  - Missing appid: {self.stats['games_info_missing_appid']:,}")
        print(f"  - Filtered (non-game software): {self.stats['filtered_non_game']:,}")
        print(f"\nSentences processed: {self.stats['sentences_processed']:,}")
        print(f"Unique appids: {self.stats['unique_appids']:,}")
        print(f"Skipped (missing info): {self.stats['skipped_missing_info']:,}")
        print(f"\nDocuments created:")
        print(f"  - Game cards: {self.stats['game_cards_created']:,}")
        print(f"  - Pros summaries: {self.stats['pros_summaries_created']:,}")
        print(f"  - Cons summaries: {self.stats['cons_summaries_created']:,}")
        print(f"\n✅ Total documents: {self.stats['total_docs_created']:,}")
        print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Steam Game RAG Document Generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--sents", type=Path, required=True,
                        help="Input sentences JSONL file (from Step 1)")
    parser.add_argument("--info", type=Path, required=True,
                        help="Input games info JSONL file")
    parser.add_argument("--output", type=Path, required=True,
                        help="Output RAG documents JSONL file")
    parser.add_argument("--top_pos", type=int, default=80,
                        help="Top K positive sentences per game")
    parser.add_argument("--top_neg", type=int, default=40,
                        help="Top K negative sentences per game")
    parser.add_argument("--bullets", type=int, default=8,
                        help="Number of bullet points in summaries")
    
    args = parser.parse_args()
    
    # 입력 파일 확인
    if not args.sents.exists():
        print(f"❌ Error: Sentences file not found: {args.sents}", file=sys.stderr)
        sys.exit(1)
    
    if not args.info.exists():
        print(f"❌ Error: Games info file not found: {args.info}", file=sys.stderr)
        sys.exit(1)
    
    # 출력 디렉토리 생성
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    # RAG 문서 생성기 생성 및 실행
    generator = RAGDocumentGenerator(
        top_pos=args.top_pos,
        top_neg=args.top_neg,
        bullets=args.bullets
    )
    
    # 1. 게임 정보 로드
    info_by_appid = generator.load_games_info(args.info)
    
    # 2. 문장 로드 및 집계
    pos_heaps, neg_heaps = generator.load_and_aggregate_sentences(args.sents)
    
    # 3. RAG 문서 생성
    generator.generate_documents(info_by_appid, pos_heaps, neg_heaps, args.output)
    
    print(f"\n✅ Done! RAG documents saved to: {args.output}")


if __name__ == "__main__":
    main()