#!/usr/bin/env python3
"""
Steam Review Sentence Preprocessor
리뷰 JSONL을 문장 단위로 분할하고 품질 점수를 계산

입력 형식: 
{
  "appid": 730,
  "reviews": [
    {
      "id": "123",
      "language": "koreana",
      "text": "게임 정말 재미있어요...",
      "voted_up": true,
      "votes_up": 10,
      "weighted_vote_score": 0.85,
      "playtime": 1200,
      "date": 1234567890
    }
  ]
}

출력 형식:
{"appid": 730, "review_id": "123", "lang": "koreana", "sent": "게임 정말 재미있어요", "label": 1, "quality": 2.5, ...}

사용법:
python step1_review_to_sentences.py \
    --input /data/steam_reviews.jsonl \
    --output /data/steam_review_sents.jsonl \
    --allowed_langs koreana english \
    --min_sent_len 20 \
    --max_sent_len 200
"""

import argparse
import json
import re
import math
import sys
from pathlib import Path
from hashlib import sha1
from typing import Optional


# ==================== 정규표현식 패턴 ====================
LOW_INFO_RE = re.compile(
    r'^(ㅋ+|ㅎ+|ㅠ+|ㅜ+|ㅇ+|ㄷ+|굿+|갓겜+|노잼+|재밌+|별로+|추천+|비추+|good+|bad+|lol+|haha+|nice+|cool+)$',
    re.IGNORECASE
)
REPEAT_CHAR_RE = re.compile(r'(.)\1{3,}')
DEDUP_RE = re.compile(r'[\s\W_]+')


# ==================== 텍스트 정규화 ====================
def normalize_text(text: str) -> str:
    """텍스트 정규화: 공백, 반복 문자 처리"""
    if not text:
        return ""
    text = text.strip()
    text = REPEAT_CHAR_RE.sub(r'\1\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def content_ratio_ok(text: str, threshold: float = 0.35) -> bool:
    """의미 있는 문자 비율 체크"""
    if not text:
        return False
    total = len(text)
    meaningful = sum(ch.isalnum() or ('가' <= ch <= '힣') for ch in text)
    return (meaningful / total) >= threshold


def is_low_info_sentence(text: str) -> bool:
    """의미 없는 짧은 문장인지 체크"""
    cleaned = re.sub(r'\s+', '', text)
    return bool(LOW_INFO_RE.match(cleaned))


# ==================== 문장 분할 ====================
def split_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분할"""
    parts = re.split(r'[\n]+', text)
    sentences = []
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        chunks = re.split(r'(?<=[\.\!\?])\s+', part)
        for chunk in chunks:
            chunk = chunk.strip()
            if chunk:
                sentences.append(chunk)
    
    return sentences


# ==================== 품질 점수 계산 ====================
def playtime_factor(playtime_min: Optional[int]) -> float:
    """플레이 타임 기반 가중치"""
    if playtime_min is None:
        return 1.0
    if playtime_min < 30:
        return 0.6
    if playtime_min < 120:
        return 1.0
    return 1.3


def quality_score(votes_up: int, wvs: Optional[float], playtime_min: Optional[int]) -> float:
    """리뷰 품질 점수 계산"""
    votes_up = votes_up or 0
    wvs = wvs if (wvs is not None and wvs > 0) else 0.1
    return math.log1p(votes_up) * wvs * playtime_factor(playtime_min)


# ==================== 메인 처리 로직 ====================
class ReviewSentencePreprocessor:
    def __init__(self, 
                 allowed_langs: set[str],
                 min_review_len: int,
                 min_sent_len: int,
                 max_sent_len: int,
                 content_ratio: float):
        self.allowed_langs = allowed_langs
        self.min_review_len = min_review_len
        self.min_sent_len = min_sent_len
        self.max_sent_len = max_sent_len
        self.content_ratio = content_ratio
        self.seen_sent_hash = set()
        
        self.stats = {
            'total_game_lines': 0,
            'total_reviews': 0,
            'filtered_by_lang': 0,
            'filtered_by_length': 0,
            'total_sentences': 0,
            'filtered_low_info': 0,
            'filtered_content_ratio': 0,
            'filtered_duplicate': 0,
            'output_sentences': 0,
            'errors': 0
        }
    
    def process_review(self, review: dict, appid: int) -> list[dict]:
        """단일 리뷰 처리하여 문장 리스트 반환"""
        self.stats['total_reviews'] += 1
        
        # 언어 필터링
        lang = review.get("language")
        if lang not in self.allowed_langs:
            self.stats['filtered_by_lang'] += 1
            return []
        
        # 텍스트 정규화
        text = normalize_text(review.get("text", ""))
        if len(text) < self.min_review_len:
            self.stats['filtered_by_length'] += 1
            return []
        
        # 리뷰 메타데이터 추출
        review_id = str(review.get("id", ""))
        voted_up = bool(review.get("voted_up", False))
        label = 1 if voted_up else 0
        
        votes_up = int(review.get("votes_up") or 0)
        wvs_raw = review.get("weighted_vote_score")
        wvs = float(wvs_raw) if wvs_raw is not None else None
        playtime_raw = review.get("playtime")
        playtime_min = int(playtime_raw) if playtime_raw is not None else None
        date = review.get("date")
        
        # 품질 점수 계산
        q = quality_score(votes_up, wvs, playtime_min)
        
        # 문장 분리 및 필터링
        output_sentences = []
        for sent in split_sentences(text):
            self.stats['total_sentences'] += 1
            sent = normalize_text(sent)
            
            # 길이 체크
            if not (self.min_sent_len <= len(sent) <= self.max_sent_len):
                continue
            
            # 저품질 문장 체크
            if is_low_info_sentence(sent):
                self.stats['filtered_low_info'] += 1
                continue
            
            # 의미 있는 문자 비율 체크
            if not content_ratio_ok(sent, self.content_ratio):
                self.stats['filtered_content_ratio'] += 1
                continue
            
            # 중복 체크
            dedup_key = DEDUP_RE.sub('', sent.lower())
            h = sha1(dedup_key.encode("utf-8")).hexdigest()
            if h in self.seen_sent_hash:
                self.stats['filtered_duplicate'] += 1
                continue
            self.seen_sent_hash.add(h)
            
            # 출력 문장 생성
            output_sentences.append({
                "appid": appid,
                "review_id": review_id,
                "lang": lang,
                "sent": sent,
                "label": label,
                "quality": round(q, 4),
                "votes_up": votes_up,
                "wvs": wvs,
                "playtime_min": playtime_min,
                "date": date
            })
            self.stats['output_sentences'] += 1
        
        return output_sentences
    
    def process_file(self, input_path: Path, output_path: Path) -> None:
        """JSONL 파일 전체 처리"""
        print(f"📂 Input: {input_path}")
        print(f"📁 Output: {output_path}")
        print(f"⚙️  Config: langs={self.allowed_langs}, sent_len={self.min_sent_len}-{self.max_sent_len}")
        print("-" * 80)
        
        with input_path.open('r', encoding='utf-8') as fin, \
             output_path.open('w', encoding='utf-8') as fout:
            
            for line_num, line in enumerate(fin, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    obj = json.loads(line)
                    self.stats['total_game_lines'] += 1
                    
                    # appid 추출
                    appid = obj.get("appid")
                    if appid is None:
                        print(f"\n⚠️  [WARN] Line {line_num}: 'appid' 필드가 없습니다. 스킵합니다.", file=sys.stderr)
                        self.stats['errors'] += 1
                        continue
                    appid = int(appid)
                    
                    # reviews 추출
                    reviews = obj.get("reviews", [])
                    if not isinstance(reviews, list):
                        print(f"\n⚠️  [WARN] Line {line_num}: 'reviews' 필드가 리스트가 아닙니다. 스킵합니다.", file=sys.stderr)
                        self.stats['errors'] += 1
                        continue
                    
                    # 각 리뷰 처리
                    for review in reviews:
                        output_sentences = self.process_review(review, appid)
                        for sent_obj in output_sentences:
                            fout.write(json.dumps(sent_obj, ensure_ascii=False) + "\n")
                    
                    # 진행상황 출력 (1000줄마다)
                    if line_num % 1000 == 0:
                        print(f"📊 Processed {line_num:,} games | "
                              f"Output: {self.stats['output_sentences']:,} sentences", 
                              end='\r')
                
                except json.JSONDecodeError as e:
                    print(f"\n❌ [ERROR] Line {line_num}: JSON 파싱 실패 - {e}", file=sys.stderr)
                    self.stats['errors'] += 1
                    continue
                except Exception as e:
                    print(f"\n❌ [ERROR] Line {line_num}: {e}", file=sys.stderr)
                    self.stats['errors'] += 1
                    continue
        
        print()  # 줄바꿈
        self.print_stats()
    
    def print_stats(self) -> None:
        """처리 통계 출력"""
        print("\n" + "=" * 80)
        print("📊 Processing Statistics")
        print("=" * 80)
        print(f"Total game lines processed: {self.stats['total_game_lines']:,}")
        print(f"Total reviews processed: {self.stats['total_reviews']:,}")
        print(f"  - Filtered by language: {self.stats['filtered_by_lang']:,}")
        print(f"  - Filtered by review length: {self.stats['filtered_by_length']:,}")
        print(f"\nTotal sentences extracted: {self.stats['total_sentences']:,}")
        print(f"  - Filtered (low info): {self.stats['filtered_low_info']:,}")
        print(f"  - Filtered (content ratio): {self.stats['filtered_content_ratio']:,}")
        print(f"  - Filtered (duplicate): {self.stats['filtered_duplicate']:,}")
        print(f"\n✅ Output sentences: {self.stats['output_sentences']:,}")
        if self.stats['errors'] > 0:
            print(f"⚠️  Errors encountered: {self.stats['errors']:,}")
        print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Steam Review Sentence Preprocessor",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--input", type=Path, required=True, 
                        help="Input JSONL file (steam_reviews.jsonl)")
    parser.add_argument("--output", type=Path, required=True, 
                        help="Output JSONL file (steam_review_sents.jsonl)")
    parser.add_argument("--allowed_langs", nargs='+', default=["koreana", "english"],
                        help="Allowed languages (space-separated)")
    parser.add_argument("--min_review_len", type=int, default=30,
                        help="Minimum review length")
    parser.add_argument("--min_sent_len", type=int, default=20,
                        help="Minimum sentence length")
    parser.add_argument("--max_sent_len", type=int, default=200,
                        help="Maximum sentence length")
    parser.add_argument("--content_ratio", type=float, default=0.35,
                        help="Minimum ratio of meaningful characters")
    
    args = parser.parse_args()
    
    # 입력 파일 확인
    if not args.input.exists():
        print(f"❌ Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # 출력 디렉토리 생성
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    # 전처리기 생성 및 실행
    preprocessor = ReviewSentencePreprocessor(
        allowed_langs=set(args.allowed_langs),
        min_review_len=args.min_review_len,
        min_sent_len=args.min_sent_len,
        max_sent_len=args.max_sent_len,
        content_ratio=args.content_ratio
    )
    
    preprocessor.process_file(args.input, args.output)
    print(f"\n✅ Done! Output saved to: {args.output}")


if __name__ == "__main__":
    main()