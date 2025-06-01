"""
SerpAPI検索ツールのテスト
"""
import os
import logging
from dotenv import load_dotenv

from src.external.web_search_tool import WebSearchTool

logger = logging.getLogger(__name__)

def test_serpapi_search():
    """SerpAPI検索ツールのテスト"""
    # 環境変数の読み込み
    load_dotenv()
    
    # APIキーの確認
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        logger.error("SERPAPI_API_KEYが設定されていません")
        return
    
    # 検索ツールの初期化
    search_tool = WebSearchTool(api_key=api_key)
    
    # 検索テスト
    query = "最新のAI技術トレンド"
    logger.info(f"=== 検索クエリ: {query} ===")
    
    try:
        results = search_tool._run(query)
        
        if results and results.get("status") == "success":
            logger.info("検索成功")
            logger.info(f"総結果数: {results.get('results_count', 0)}件")
            
            # 検索結果の表示
            for i, result in enumerate(results.get("results", [])[:3], 1):
                logger.info(f"--- 結果 {i} ---")
                logger.info(f"タイトル: {result.get('title', 'N/A')}")
                logger.info(f"リンク: {result.get('link', 'N/A')}")
                logger.info(f"スニペット: {result.get('snippet', 'N/A')}")
                logger.info(f"ソース: {result.get('source', 'N/A')}")
        else:
            logger.error("検索失敗")
            logger.error(f"エラー: {results.get('error', '不明なエラー')}")
            
    except Exception as e:
        logger.error(f"検索中にエラー: {str(e)}")

if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # テスト実行
    test_serpapi_search() 