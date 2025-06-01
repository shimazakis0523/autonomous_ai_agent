#!/usr/bin/env python3
"""
自律型AIエージェント - メインエントリーポイント
"""
import asyncio
import logging
import os
import sys
import signal
from datetime import datetime
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.autonomous_agent import AutonomousAgent
from src.utils.document_retriever import DocumentRetriever

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# グローバル変数
session_start_time = None
agent = None

def handle_exit(signum, frame):
    """シグナルハンドラ：エレガントな終了処理"""
    if agent and session_start_time:
        duration = datetime.now() - session_start_time
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        print("\n" + "="*60)
        print("📊 セッション統計")
        print(f"⏱️  実行時間: {hours:02d}:{minutes:02d}:{seconds:02d}")
        print(f"🔄 処理フェーズ: {agent.current_phase if agent else '不明'}")
        print("="*60)
        print("\n👋 プログラムを終了します")
        print("💡 またのご利用をお待ちしております")
        print("="*60)
    
    sys.exit(0)

async def main():
    """メイン関数：自律型AIエージェントの実行"""
    global session_start_time, agent
    
    try:
        # シグナルハンドラの設定
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)
        
        # APIキーの確認
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ エラー: OPENAI_API_KEYが設定されていません")
            print("💡 .envファイルでAPIキーを設定してください")
            return
        
        # APIキーの基本検証
        if not api_key.startswith('sk-'):
            print("⚠️  警告: APIキーの形式が正しくない可能性があります")
            print(f"🔍 APIキー（最初の10文字）: {api_key[:10]}...")
        else:
            print(f"✅ APIキー確認済み（最初の10文字）: {api_key[:10]}...")
        
        print("\n" + "="*60)
        print("🚀 自律型AIエージェントシステム起動中...")
        print("="*60)
        
        # セッション開始時間の記録
        session_start_time = datetime.now()
        
        # エージェントの作成と実行
        agent = AutonomousAgent()
        # テスト用に「嶋崎の職歴」検索を実行
        retriever = DocumentRetriever(doc_dir="internalDoc", persist_directory="artifact/chroma_db")
        retriever.create_index(force_recreate=False)
        doc_info = retriever.get_document_info()
        logger.info("=== ドキュメント情報 ===")
        logger.info(f"総ドキュメント数: {doc_info['total_documents']}")
        logger.info(f"総チャンク数: {doc_info['total_chunks']}")
        logger.info(f"最終更新日時: {doc_info['last_updated']}")
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
        # テスト用検索終了

        await agent.run_session()
        
    except KeyboardInterrupt:
        # シグナルハンドラが処理するため、ここには到達しない
        pass
    except Exception as e:
        logger.error(f"プログラム実行エラー: {str(e)}")
        import traceback
        logger.error(f"詳細エラー: {traceback.format_exc()}")
        print("\n" + "="*60)
        print("❌ 予期しないエラーが発生しました")
        print(f"🔍 エラー内容: {str(e)}")
        print("💡 詳細はログファイルを確認してください")
        print("="*60)
    finally:
        if session_start_time:
            duration = datetime.now() - session_start_time
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            logger.info(f"セッション終了 - 実行時間: {hours:02d}:{minutes:02d}:{seconds:02d}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # シグナルハンドラが処理するため、ここには到達しない
        pass 