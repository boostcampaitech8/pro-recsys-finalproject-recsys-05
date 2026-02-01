import json
import os
from pathlib import Path
from typing import Set, Dict, Any


class DataManager:
    """데이터 저장(JSONL), 체크포인트, 중복 방지를 관리하는 클래스"""

    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache = {}  # 성능 향상을 위한 메모리 캐시
        self.collected_ids = self._load_existing_ids()

    def _load_existing_ids(self) -> Set[str]:
        """기존 파일에서 이미 수집된 ID들을 로드하고 캐싱"""
        ids = set()
        if self.output_path.exists():
            with open(self.output_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if isinstance(data, dict) and data:
                            # Flat JSON 구조: appid가 필드로 존재
                            data_id = str(data.get("appid", ""))
                            if data_id:
                                ids.add(data_id)
                                # 최신 데이터로 캐시 갱신
                                self._cache[data_id] = data
                    except (json.JSONDecodeError, KeyError):
                        continue
        return ids

    def get_max_id(self) -> int:
        """수집된 ID 중 가장 큰 숫자(최신 AppID 등)를 반환"""
        numeric_ids = []
        for rid in self.collected_ids:
            try:
                numeric_ids.append(int(rid))
            except ValueError:
                continue
        return max(numeric_ids) if numeric_ids else 0

    def save_row(self, data_id: str, content: Dict[str, Any], timestamped: bool = True):
        """한 행의 데이터를 JSONL 파일에 즉시 저장 (CheckPointing)"""
        from datetime import datetime

        # Flat JSON 구조로 저장 (래퍼 제거)
        save_data = content.copy()  # 원본 변경 방지
        if timestamped:
            save_data["collected_at"] = datetime.now().isoformat()

        with open(self.output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(save_data, ensure_ascii=False) + "\n")

        self.collected_ids.add(str(data_id))
        self._cache[str(data_id)] = save_data

    def is_collected(self, data_id: str) -> bool:
        return str(data_id) in self.collected_ids

    def get_row(self, data_id: str) -> Dict[str, Any]:
        """특정 ID의 최신 데이터를 반환 (메모리 캐시 사용으로 성능 최적화)"""
        return self._cache.get(str(data_id))
