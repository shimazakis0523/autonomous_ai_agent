"""
検索結果の表示テスト
"""
import os
import logging
from dotenv import load_dotenv

from src.utils.document_retriever import DocumentRetriever
from src.tools.document_search_tool import DocumentSearchTool
from src.external.web_search_tool import WebSearchTool

logger = logging.getLogger(__name__)

def show_search_results():
    """検索結果の表示テスト"""
    # 環境変数の読み込み
    load_dotenv()
    
    # 1. ドキュメント検索の結果表示
    logger.info("=== ドキュメント検索の結果 ===")
    doc_dir = "internalDoc"
    persist_dir = "artifact/chroma_db"
    
    retriever = DocumentRetriever(
        doc_dir=doc_dir,
        persist_directory=persist_dir
    )
    retriever.create_index(force_recreate=False)
    
    search_tool = DocumentSearchTool(retriever=retriever)
    
    # 複数のクエリで検索
    queries = [
        "嶋崎の職歴",
        "プロジェクト経験",
        "技術スタック"
    ]
    
    for query in queries:
        logger.info(f"\n検索クエリ: {query}")
        results = search_tool._run(query)
        
        if results:
            logger.info(f"検索結果: {len(results)}件")
            for i, result in enumerate(results, 1):
                logger.info(f"--- 結果 {i} ---")
                logger.info(f"スコア: {result['score']:.3f}")
                logger.info(f"ソース: {result['source']}")
                logger.info(f"内容: {result['content'][:200]}...")
        else:
            logger.info("検索結果が見つかりませんでした。")
    
    # 2. Web検索の結果表示
    logger.info("\n=== Web検索の結果 ===")
    api_key = os.getenv("SERPAPI_API_KEY")
    if api_key:
        web_tool = WebSearchTool(api_key=api_key)
        
        # 複数のクエリで検索
        web_queries = [
            "最新のAI技術トレンド",
            "LangChain 活用事例",
            "RAG システム 設計"
        ]
        
        for query in web_queries:
            logger.info(f"\n検索クエリ: {query}")
            results = web_tool._run(query)
            
            if results and results.get("status") == "success":
                logger.info(f"検索結果: {results.get('results_count', 0)}件")
                for i, result in enumerate(results.get("results", [])[:3], 1):
                    logger.info(f"--- 結果 {i} ---")
                    logger.info(f"タイトル: {result.get('title', 'N/A')}")
                    logger.info(f"リンク: {result.get('link', 'N/A')}")
                    logger.info(f"スニペット: {result.get('snippet', 'N/A')}")
                    logger.info(f"ソース: {result.get('source', 'N/A')}")
            else:
                logger.error("検索失敗")
                logger.error(f"エラー: {results.get('error', '不明なエラー')}")
    else:
        logger.error("SERPAPI_API_KEYが設定されていません")

if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # テスト実行
    show_search_results() 