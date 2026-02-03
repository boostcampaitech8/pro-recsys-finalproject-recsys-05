import os

import pytest
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage


@pytest.mark.asyncio
async def test_clova_multiturn_smoke():
    """
    Integration smoke test for CLOVA API multi-turn behavior.
    Skips unless RUN_CLOVA_TEST=1 and CLOVA_API_KEY are set.
    """
    if os.getenv("RUN_CLOVA_TEST") != "1":
        pytest.skip("Set RUN_CLOVA_TEST=1 to enable CLOVA integration test.")

    api_key = os.getenv("CLOVA_API_KEY")
    if not api_key:
        pytest.skip("CLOVA_API_KEY not set.")

    base_url = os.getenv(
        "CLOVA_BASE_URL",
        "https://clovastudio.stream.ntruss.com/v1/openai/",
    )
    model = os.getenv("CLOVA_MODEL", "HCX-DASH-001")

    llm = ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=0.2,
        max_tokens=200,
    )

    show_payload = os.getenv("PRINT_CLOVA") == "1"

    user_turn_1 = "Recommend a simple breakfast."
    first = await llm.ainvoke([HumanMessage(content=user_turn_1)])
    assert first.content and first.content.strip()
    if show_payload:
        print(f"[CLOVA] turn1.user: {user_turn_1}")
        print(f"[CLOVA] turn1.assistant: {first.content}")

    user_turn_2 = "Suggest a drink that pairs well with that."
    second = await llm.ainvoke(
        [
            HumanMessage(content=user_turn_1),
            AIMessage(content=first.content),
            HumanMessage(content=user_turn_2),
        ]
    )
    assert second.content and second.content.strip()
    if show_payload:
        print(f"[CLOVA] turn2.user: {user_turn_2}")
        print(f"[CLOVA] turn2.assistant: {second.content}")
