from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

# 의도(Intent) 정의: 라우터가 분류할 목적지
class UserIntent(str, Enum):
    RECOMMENDATION = "recommendation" # 추천 요청 ("할만한 게임 추천해줘")
    SEARCH = "search"                 # 단순 정보/검색 ("배그 가격 얼마야?")
    CHITCHAT = "chitchat"             # 일상 대화 ("안녕", "고마워")