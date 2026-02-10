import os
import json
from datetime import datetime

class InteractionLogger:
    """
    Logging Layer: Saves detailed interaction data to JSONL files.
    """
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def _get_log_filepath(self):
        """Generate daily log filename."""
        today = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.log_dir, f"sim_log_{today}.jsonl")

    def log_interaction(self, query: str, context: list, prompt: str, response: str, model_info: str):
        """
        Append interaction details to the daily log file.
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "model_info": model_info,
            "query": query,
            "context_docs": [doc.page_content for doc in context] if context else [],
            "full_prompt": prompt,
            "response": response
        }
        
        filepath = self._get_log_filepath()
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"❌ Failed to write log: {e}")
