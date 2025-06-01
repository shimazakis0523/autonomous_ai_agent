"""
トレース機能付きエージェントのデモ
"""
import os
import logging
import asyncio
from dotenv import load_dotenv

from src.core.autonomous_agent import AutonomousAgent
from src.utils.trace_logger import TraceLogger

logger = logging.getLogger(__name__)

async def run_traced_agent_demo():
    """トレース機能付きエージェントのデモ実行"""
    # 環境変数の読み込み
    load_dotenv()
    
    # APIキーの確認
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEYが設定されていません")
        return
    
    # トレースロガーの初期化
    trace_logger = TraceLogger(
        log_dir="logs",
        project_name="autonomous_agent_demo",
        run_name="traced_demo"
    )
    
    try:
        # エージェントの初期化
        agent = AutonomousAgent(trace_logger=trace_logger)
        
        # デモ用の質問
        questions = [
            "嶋崎の職歴を教えてください",
            "最新のAI技術トレンドについて教えてください",
            "RAGシステムの設計ポイントを教えてください"
        ]
        
        for question in questions:
            logger.info(f"\n=== 質問: {question} ===")
            
            # エージェントの実行
            response = await agent.run_session(question)
            
            # 結果の表示
            logger.info("=== 回答 ===")
            logger.info(response)
            
            # トレース情報の表示
            logger.info("\n=== トレース情報 ===")
            trace_info = trace_logger.get_trace_info()
            logger.info(f"実行時間: {trace_info['execution_time']:.2f}秒")
            logger.info(f"処理フェーズ数: {trace_info['phase_count']}")
            logger.info(f"LLM呼び出し回数: {trace_info['llm_calls']}")
            logger.info(f"ツール使用回数: {trace_info['tool_uses']}")
            
            # 次の質問の前に少し待機
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"デモ実行中にエラー: {str(e)}")
    finally:
        # トレースロガーの終了処理
        trace_logger.close()

if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # デモ実行
    asyncio.run(run_traced_agent_demo()) 