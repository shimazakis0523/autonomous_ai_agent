"""
ドキュメント検索エンジンのテスト
"""
import os
import logging
from pathlib import Path

from src.utils.document_retriever import DocumentRetriever

logger = logging.getLogger(__name__)

def test_document_retriever():
    """ドキュメント検索エンジンのテスト"""
    # テスト用の設定
    doc_dir = "internalDoc"
    persist_dir = "artifact/chroma_db"
    
    # 検索エンジンの初期化
    retriever = DocumentRetriever(
        doc_dir=doc_dir,
        persist_directory=persist_dir
    )
    
    # インデックスの作成
    retriever.create_index(force_recreate=False)
    
    # ドキュメント情報の取得
    doc_info = retriever.get_document_info()
    logger.info("=== ドキュメント情報 ===")
    logger.info(f"総ドキュメント数: {doc_info['total_documents']}")
    logger.info(f"総チャンク数: {doc_info['total_chunks']}")
    logger.info(f"最終更新日時: {doc_info['last_updated']}")
    
    # 検索テスト
    query = "嶋崎の職歴"
    logger.info(f"=== 検索クエリ: {query} ===")
    results = retriever.search(query, k=3, score_threshold=0.3)
    
    if results:
        logger.info(f"検索結果: {len(results)}件")
        for i, result in enumerate(results, 1):
            logger.info(f"--- 結果 {i} ---")
            logger.info(f"スコア: {result['score']:.3f}")
            logger.info(f"ソース: {result['source']}")
            logger.info("内容:")
            logger.info(result['content'])
    else:
        logger.info("検索結果が見つかりませんでした。")

if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # テスト実行
    test_document_retriever() 