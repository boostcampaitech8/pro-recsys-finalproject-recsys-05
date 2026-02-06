from typing import Dict
from app.domains.chat.tools.base import Tool

class ToolRegistry:
    """
    Central registry for all agent tools.
    Manages initialization and discovery of tools.
    """
    
    
    def __init__(self):
        # 이제 인스턴스 생성 시에는 아무것도 하지 않음 (Stateless Factory Pattern)
        pass
        
    def create_tools(self, db_session, embedding_model=None) -> Dict[str, Tool]:
        """
        Create and register tools with the provided dependencies (DB session, etc).
        This must be called per-request.
        """
        tools = {}
        
        # Import tools locally to avoid circular imports if any
        from app.domains.chat.tools.tool_search import (
            SearchByEmbeddingTool,
            SearchGamesByFilterTool,
            GameInfoTool,
            GameReviewsTool,
        )
        
        from app.domains.chat.tools.tool_recommand import (
            PersonalizedRecommendationTool,
        )
        
        # 1. RAG Search Tool (Requires Embeddings)
        if embedding_model:
            rag_tool = SearchByEmbeddingTool(db_session=db_session, embeddings_model=embedding_model)
            tools[rag_tool.name] = rag_tool
            
        # 2. Filter Search Tool
        filter_tool = SearchGamesByFilterTool(db_session=db_session)
        tools[filter_tool.name] = filter_tool
        
        # 3. Game Info Tool
        info_tool = GameInfoTool(db_session=db_session)
        tools[info_tool.name] = info_tool
        
        # 4. Review Tool
        review_tool = GameReviewsTool(db_session=db_session)
        tools[review_tool.name] = review_tool
        
        return tools