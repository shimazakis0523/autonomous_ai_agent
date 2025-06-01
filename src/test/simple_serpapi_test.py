"""
SerpAPIのシンプルなテスト
"""
import os
import logging
from dotenv import load_dotenv
from serpapi import GoogleSearch

logger = logging.getLogger(__name__)

def test_simple_serpapi():
    """SerpAPIのシンプルなテスト"""
    # 環境変数の読み込み
    load_dotenv()
    
    # APIキーの確認
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        logger.error("SERPAPI_API_KEYが設定されていません")
        return
    
    # 検索パラメータ
    params = {
        "engine": "google",
        "q": "最新のAI技術トレンド",
        "api_key": api_key,
        "num": 3,  # 結果数を制限
        "gl": "jp",  # 日本の検索結果
        "hl": "ja"   # 日本語の結果
    }
    
    try:
        # 検索の実行
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # 検索結果の処理
        if "organic_results" in results:
            logger.info("検索成功")
            logger.info(f"総結果数: {len(results['organic_results'])}件")
            
            # 検索結果の表示
            for i, result in enumerate(results["organic_results"], 1):
                logger.info(f"--- 結果 {i} ---")
                logger.info(f"タイトル: {result.get('title', 'N/A')}")
                logger.info(f"リンク: {result.get('link', 'N/A')}")
                logger.info(f"スニペット: {result.get('snippet', 'N/A')}")
                
                # リッチスニペット情報があれば表示
                if "rich_snippet" in result:
                    logger.info("リッチスニペット情報:")
                    for key, value in result["rich_snippet"].items():
                        logger.info(f"  {key}: {value}")
        else:
            logger.error("検索結果がありません")
            if "error" in results:
                logger.error(f"エラー: {results['error']}")
                
    except Exception as e:
        logger.error(f"検索中にエラー: {str(e)}")

if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # テスト実行
    test_simple_serpapi() 