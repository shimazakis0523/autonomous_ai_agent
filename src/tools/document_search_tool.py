"""
内部ドキュメント検索ツール
"""
from typing import Dict, Any, List, ClassVar
import logging
from langchain.tools import BaseTool
from langchain.schema import HumanMessage
from pydantic import Field

from src.utils.document_retriever import DocumentRetriever

logger = logging.getLogger(__name__)

class DocumentSearchTool(BaseTool):
    """内部ドキュメント検索ツール"""
    
    name: ClassVar[str] = "document_search"
    description: ClassVar[str] = """
    内部ドキュメントから関連情報を検索します。
    入力は検索クエリ（文字列）です。
    出力は検索結果のリストで、各結果には以下の情報が含まれます：
    - content: ドキュメントの内容
    - source: ドキュメントのソースファイル
    - score: 類似度スコア（0-1）
    """
    
    retriever: DocumentRetriever = Field(
        description="ドキュメント検索エンジン",
        exclude=True  # シリアライズ時に除外
    )
    
    def __init__(self, retriever: DocumentRetriever):
        """
        初期化
        
        Args:
            retriever: ドキュメント検索エンジン
        """
        super().__init__(retriever=retriever)
    
    def _run(self, query: str) -> List[Dict[str, Any]]:
        """
        検索の実行
        
        Args:
            query: 検索クエリ
            
        Returns:
            検索結果のリスト
        """
        try:
            # 検索の実行
            logger.info(f"ドキュメント検索ツール呼び出し: query={query}")
            results = self.retriever.search(
                query=query,
                k=3,  # 上位3件を取得
                score_threshold=0.5  # 類似度50%以上に下げる
            )
            
            if not results:
                logger.info("検索結果が見つかりませんでした。")
                # 閾値を下げて再検索
                logger.info("閾値を下げて再検索を試みます...")
                results = self.retriever.search(
                    query=query,
                    k=3,
                    score_threshold=0.3  # さらに閾値を下げる
                )
                
                if not results:
                    logger.info("再検索でも結果が見つかりませんでした。")
                    return [{
                        "content": "関連する情報が見つかりませんでした。",
                        "source": "system",
                        "score": 0.0
                    }]
            
            # 検索結果の詳細なログ
            logger.info(f"検索結果数: {len(results)}")
            for i, result in enumerate(results, 1):
                logger.info(f"結果 {i}:")
                logger.info(f"  スコア: {result.get('score', 0.0)}")
                logger.info(f"  ソース: {result.get('source', 'unknown')}")
                logger.info(f"  内容: {result.get('content', '')[:200]}...")
            
            # RAGから情報がヒットした場合、その検索結果を必ずLLMに渡すためのプロンプトを追加
            if results:
                prompt = "以下の検索結果（RAG由来）を必ず参照して回答してください。\n\n"
                for i, result in enumerate(results, 1):
                    prompt += f"--- 検索結果 {i} ---\n"
                    prompt += f"スコア: {result.get('score', 0.0)}\n"
                    prompt += f"ソース: {result.get('source', 'unknown')}\n"
                    prompt += f"内容:\n{result.get('content', '')}\n\n"
                prompt += "---\n\n"
                # 各検索結果にプロンプトを追加
                for result in results:
                    result["prompt"] = prompt

            return results
            
        except Exception as e:
            logger.error(f"ドキュメント検索中にエラー: {str(e)}")
            logger.exception("スタックトレース:")
            return [{
                "content": f"検索中にエラーが発生しました: {str(e)}",
                "source": "system",
                "score": 0.0
            }]
    
    async def _arun(self, query: str) -> List[Dict[str, Any]]:
        """非同期実行（同期的な実装を使用）"""
        return self._run(query)
    
    def get_tool_info(self) -> Dict[str, Any]:
        """ツール情報の取得"""
        doc_info = self.retriever.get_document_info()
        return {
            "name": self.name,
            "description": self.description,
            "document_info": doc_info
        } 