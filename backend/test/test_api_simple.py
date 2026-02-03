"""
간단한 API 테스트 - 실제 서비스 동작 확인

실제 실행 중인 서버에 HTTP 요청을 보내서 테스트합니다.
"""

import httpx
import asyncio
import json
import time


async def test_chat_api():
    """
    가장 간단한 테스트: /chat/single_chat API 호출

    실행 방법:
        cd backend
        python test/test_api_simple.py
    """

    BASE_URL = "http://localhost:8000"

    # 테스트 1: 기본 질문 (Steam API + BentoML 미사용)
    print("\n" + "="*60)
    print("테스트 1: 기본 게임 검색 (RAG)")
    print("="*60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/chat/single_chat",
            headers={"id": "test_user_001"},
            json={"text": "액션 게임 추천해줘"}
        )

        print(f"\n📊 상태 코드: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 응답 받음")
            print(f"\n💬 챗봇 답변:")
            print(f"   {data['text'][:200]}...")

            # DEBUG 정보 확인
            if "debug" in data:
                debug = data["debug"]
                print(f"\n⏱️  성능 메트릭:")
                print(f"   - 전체: {debug['metrics']['total_ms']:.0f}ms")
                print(f"   - 임베딩: {debug['metrics']['embedding_time_ms']:.0f}ms")
                print(f"   - 검색: {debug['metrics']['retrieval_time_ms']:.0f}ms")
                print(f"   - LLM: {debug['metrics']['llm_api_time_ms']:.0f}ms")

                print(f"\n🎮 검색된 게임:")
                for doc in debug['retrieved_docs'][:3]:
                    print(f"   - {doc['name']} (유사도: {doc['similarity']:.3f})")
        else:
            print(f"❌ 에러: {response.text}")


    # 테스트 2: 개인화 추천 (Steam API + BentoML 사용)
    print("\n" + "="*60)
    print("테스트 2: 개인화 추천 (Steam API + BentoML)")
    print("="*60)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Steam ID를 포함한 질문
        response = await client.post(
            f"{BASE_URL}/chat/single_chat",
            headers={"id": "test_user_002"},
            json={
                "text": "내 Steam ID는 76561198012345678이고, 나한테 맞는 게임 추천해줘"
            }
        )

        print(f"\n📊 상태 코드: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 응답 받음")
            print(f"\n💬 챗봇 답변:")
            print(f"   {data['text'][:300]}...")

            # DEBUG 정보 확인
            if "debug" in data:
                debug = data["debug"]
                print(f"\n⏱️  성능 메트릭:")
                print(f"   - 전체: {debug['metrics']['total_ms']:.0f}ms")
                print(f"   - 임베딩: {debug['metrics']['embedding_time_ms']:.0f}ms")
                print(f"   - 검색: {debug['metrics']['retrieval_time_ms']:.0f}ms")
                print(f"   - LLM: {debug['metrics']['llm_api_time_ms']:.0f}ms")

                print(f"\n🎮 검색된 게임:")
                for doc in debug['retrieved_docs'][:3]:
                    print(f"   - {doc['name']} (유사도: {doc['similarity']:.3f})")
        else:
            print(f"❌ 에러: {response.text}")


    # 테스트 3: 캐시 성능 비교
    print("\n" + "="*60)
    print("테스트 3: 캐시 성능 비교 (같은 쿼리 2번)")
    print("="*60)

    async with httpx.AsyncClient(timeout=60.0) as client:
        query = "액션 RPG 추천해줘"

        # 첫 번째 호출 (캐시 없음)
        print(f"\n🔍 첫 번째 호출 (캐시 없음)...")
        start = time.time()
        response1 = await client.post(
            f"{BASE_URL}/chat/single_chat",
            headers={"id": "test_user_003"},
            json={"text": query}
        )
        first_duration = time.time() - start

        if response1.status_code == 200:
            data1 = response1.json()
            if "debug" in data1:
                first_total = data1['debug']['metrics']['total_ms']
                print(f"   ⏱️  {first_duration*1000:.0f}ms (기록: {first_total:.0f}ms)")
            print(f"   ✅ 완료")

        # 두 번째 호출 (캐시 히트)
        print(f"\n🔍 두 번째 호출 (캐시 히트)...")
        start = time.time()
        response2 = await client.post(
            f"{BASE_URL}/chat/single_chat",
            headers={"id": "test_user_003"},
            json={"text": query}
        )
        second_duration = time.time() - start

        if response2.status_code == 200:
            data2 = response2.json()
            if "debug" in data2:
                second_total = data2['debug']['metrics']['total_ms']
                print(f"   ⏱️  {second_duration*1000:.0f}ms (기록: {second_total:.0f}ms)")
            print(f"   ✅ 완료")

            # 성능 비교
            if first_duration > 0:
                improvement = first_duration / second_duration
                print(f"\n📈 성능 개선: {improvement:.1f}배 빠름")


    # 테스트 4: 에러 처리
    print("\n" + "="*60)
    print("테스트 4: 에러 처리 (존재하지 않는 Steam ID)")
    print("="*60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/chat/single_chat",
            headers={"id": "test_user_004"},
            json={
                "text": "내 Steam ID는 999999999999999999이고, 나한테 맞는 게임 추천해줘"
            }
        )

        print(f"\n📊 상태 코드: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 응답 받음 (에러 처리됨)")
            print(f"\n💬 챗봇 답변:")
            print(f"   {data['text'][:200]}...")
        else:
            print(f"❌ 에러: {response.text}")


    print("\n" + "="*60)
    print("🎉 모든 테스트 완료!")
    print("="*60)


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║          GameTools 간단 API 테스트                         ║
║                                                            ║
║  실행 전 확인:                                             ║
║  1. docker-compose up -d  (모든 서비스 실행)               ║
║  2. http://localhost:8000/docs (Swagger 접속 확인)        ║
║════════════════════════════════════════════════════════════╝
    """)

    asyncio.run(test_chat_api())
