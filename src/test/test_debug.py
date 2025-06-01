"""
デバッグ用テスト
"""
import os
import logging
from dotenv import load_dotenv

from src.utils.document_retriever import DocumentRetriever
from src.tools.document_search_tool import DocumentSearchTool
from src.external.web_search_tool import WebSearchTool

logger = logging.getLogger(__name__)

def test_debug():
    """デバッグ用テスト"""
    # 環境変数の読み込み
    load_dotenv()
    
    # 1. ドキュメント検索のテスト
    logger.info("=== ドキュメント検索のテスト ===")
    doc_dir = "internalDoc"
    persist_dir = "artifact/chroma_db"
    
    retriever = DocumentRetriever(
        doc_dir=doc_dir,
        persist_directory=persist_dir
    )
    retriever.create_index(force_recreate=False)
    
    search_tool = DocumentSearchTool(retriever=retriever)
    doc_results = search_tool._run("嶋崎の職歴")
    
    logger.info(f"ドキュメント検索結果: {len(doc_results)}件")
    for i, result in enumerate(doc_results, 1):
        logger.info(f"--- 結果 {i} ---")
        logger.info(f"スコア: {result['score']:.3f}")
        logger.info(f"ソース: {result['source']}")
        logger.info(f"内容: {result['content'][:200]}...")
    
    # 2. Web検索のテスト
    logger.info("\n=== Web検索のテスト ===")
    api_key = os.getenv("SERPAPI_API_KEY")
    if api_key:
        web_tool = WebSearchTool(api_key=api_key)
        web_results = web_tool._run("最新のAI技術トレンド")
        
        if web_results and web_results.get("status") == "success":
            logger.info(f"Web検索結果: {web_results.get('results_count', 0)}件")
            for i, result in enumerate(web_results.get("results", [])[:3], 1):
                logger.info(f"--- 結果 {i} ---")
                logger.info(f"タイトル: {result.get('title', 'N/A')}")
                logger.info(f"リンク: {result.get('link', 'N/A')}")
                logger.info(f"スニペット: {result.get('snippet', 'N/A')}")
        else:
            logger.error("Web検索失敗")
    else:
        logger.error("SERPAPI_API_KEYが設定されていません")

if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # テスト実行
    test_debug() 