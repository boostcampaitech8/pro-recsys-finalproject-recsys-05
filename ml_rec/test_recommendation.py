#!/usr/bin/env python3
"""
BentoML 추천 서비스 로컬 테스트
입력 데이터와 출력 결과를 명확하게 보여주는 테스트
"""

import json
import sys
from pathlib import Path

# 경로 설정
sys.path.insert(0, str(Path.cwd()))

from scripts.stage4_serving.recommendation_service import GameRecommendationService

def print_section(title):
    """섹션 제목 출력"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def main():
    print("\n🎮 BentoML 추천 서비스 로컬 테스트\n")
    
    # ==========================================
    # 1. 입력 데이터 정의
    # ==========================================
    print_section("1️⃣ 입력 데이터 (Input)")
    
    user_id = 'test_user_123'
    user_games = [35070, 203680, 1510]  # 사용자가 플레이한 게임
    top_k = 10
    
    print(f"\n📋 사용자 정보:")
    print(f"   • User ID: {user_id}")
    print(f"   • 플레이한 게임 ID: {user_games}")
    print(f"   • 요청 추천 개수: {top_k}개")
    
    # ==========================================
    # 2. 서비스 초기화 (모델 로드)
    # ==========================================
    print_section("2️⃣ 서비스 초기화 (모델 로드 중...)")
    
    try:
        service = GameRecommendationService()
        print("\n✅ 모든 모델 로드 완료!")
    except Exception as e:
        print(f"\n❌ 서비스 초기화 실패: {e}")
        sys.exit(1)
    
    # ==========================================
    # 3. 추천 요청
    # ==========================================
    print_section("3️⃣ 추천 요청 중...")
    
    try:
        result = service.recommend(
            user_id=user_id,
            user_games=user_games,
            top_k=top_k
        )
    except Exception as e:
        print(f"\n❌ 추천 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # ==========================================
    # 4. 출력 데이터 분석
    # ==========================================
    print_section("4️⃣ 추천 결과 (Output)")
    
    if result['status'] != 'success':
        print(f"\n❌ 상태: {result['status']}")
        print(f"❌ 에러: {result.get('error', 'Unknown error')}")
        return
    
    # 메타데이터
    metadata = result['metadata']
    print(f"\n📊 파이프라인 정보:")
    print(f"   • Stage 1 (Retrieval): {metadata['retrieval_candidates']} 후보 생성")
    print(f"   • Stage 2 (Ranking): {metadata['ranking_candidates']} 후보로 축소")
    print(f"   • Stage 3 (Scoring): {metadata['final_candidates']} 최종 추천 선택")
    print(f"   • 처리 시간: {metadata['processing_time_ms']}ms")
    print(f"   • 새 사용자: {metadata['is_new_user']}")
    
    # 추천 결과
    recommendations = result['recommendations']
    print(f"\n🎮 최종 추천 게임 ({len(recommendations)}개):")
    print()
    
    for rec in recommendations:
        print(f"   순위 #{rec['rank']}")
        print(f"   ├─ 게임 ID: {rec['game_id']}")
        print(f"   ├─ DCN 점수: {rec['dcn_score']:.4f}")
        print(f"   ├─ XGBoost 점수: {rec['xgb_score']:.4f}")
        print(f"   ├─ 최종 점수 (평균): {rec['combined_score']:.4f}")
        print(f"   └─ 추천 소스: {rec['source']}")
        print()
    
    # ==========================================
    # 5. 상세 분석
    # ==========================================
    print_section("5️⃣ 3-Stage 파이프라인 상세 분석")
    
    print(f"\n📍 Stage 1: Retrieval (후보 생성)")
    print(f"   입력: 사용자 게임 {user_games}")
    print(f"   처리:")
    print(f"   ├─ EASE 모델 기반 후보 생성 (또는 사전계산된 후보 로드)")
    print(f"   ├─ LightGCN 임베딩 기반 후보 생성 (또는 사전계산된 후보 로드)")
    print(f"   └─ 두 모델의 후보 병합 (역수 순위 가중치 사용)")
    print(f"   출력: {metadata['retrieval_candidates']} 개의 후보 (게임 ID)")
    
    print(f"\n📍 Stage 2: Ranking (후보 재순위화)")
    print(f"   입력: {metadata['retrieval_candidates']} 개의 후보")
    print(f"   처리:")
    print(f"   ├─ 각 후보별 66차원 피처 구성")
    print(f"   │  ├─ LightGCN 임베딩 (64-dim)")
    print(f"   │  ├─ EASE 점수 (1-dim)")
    print(f"   │  └─ LightGCN 점수 (1-dim)")
    print(f"   ├─ DCN v2 모델 (Deep+Cross Network)로 점수 계산")
    print(f"   └─ 상위 {metadata['ranking_candidates']} 개 선택")
    print(f"   출력: {metadata['ranking_candidates']} 개의 순위화된 후보 + DCN 점수")
    
    print(f"\n📍 Stage 3: Scoring (최종 점수화)")
    print(f"   입력: {metadata['ranking_candidates']} 개의 후보 + DCN 점수")
    print(f"   처리:")
    print(f"   ├─ 각 후보별 4차원 피처 구성")
    print(f"   │  ├─ DCN 점수 (1-dim)")
    print(f"   │  ├─ Discount Proxy (popularity 기반)")
    print(f"   │  ├─ Concurrent Proxy (동접자 수 추정)")
    print(f"   │  └─ Review Stability (출시 연도 기반)")
    print(f"   ├─ XGBoost 모델로 최종 점수 계산")
    print(f"   └─ 상위 {metadata['final_candidates']} 개 선택")
    print(f"   출력: {metadata['final_candidates']} 개의 최종 추천 게임")
    
    print_section("✅ 테스트 완료!")

if __name__ == '__main__':
    main()
