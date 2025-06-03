"""
自律型AIエージェント - メインエージェント統合クラス
全フェーズを統合した自律実行システム
詳細なトレーシング機能付き
"""
import asyncio
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# 各フェーズのクラスをインポート
from .agent_state import AgentState, AgentPhase, create_initial_state
from ..processors.input_processor import InputProcessor
from ..processors.intent_analyzer import IntentAnalyzer
from ..processors.plan_generator import PlanGenerator
from ..external.mcp_manager import MCPManager
from ..processors.task_orchestrator import TaskOrchestrator
from ..processors.result_processor import ResultProcessor
from ..processors.response_generator import ResponseGenerator

# トレーシング機能をインポート
from ..utils.trace_logger import TraceLogger

# ドキュメント検索ツールをインポート
from src.tools.document_search_tool import DocumentSearchTool
from src.utils.document_retriever import DocumentRetriever

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# より詳細なログ設定
import traceback
import sys


class AutonomousAgent:
    """自律型AIエージェントメインクラス（トレーシング対応）"""
    
    def __init__(self, model_name: str = "o4-mini", enable_tracing: bool = True):
        """
        エージェントの初期化
        
        Args:
            model_name: 使用するLLMモデル名
            enable_tracing: トレーシング機能の有効化
        """
        # トレーシングの初期化
        self.trace_logger = TraceLogger() if enable_tracing else None
        
        if self.trace_logger:
            self.trace_logger.log_custom_event(
                "AGENT_INITIALIZATION", 
                f"エージェント初期化開始 - モデル: {model_name}",
                {"model_name": model_name, "tracing_enabled": enable_tracing}
            )
        
        # LLMの初期化
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=1,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        )
        
        # 各フェーズの処理クラス初期化（トレーシング対応）
        self.input_processor = InputProcessor(trace_logger=self.trace_logger)
        self.intent_analyzer = IntentAnalyzer(self.llm, trace_logger=self.trace_logger)
        self.plan_generator = PlanGenerator(self.llm, trace_logger=self.trace_logger)
        self.mcp_manager = MCPManager(trace_logger=self.trace_logger)
        self.task_orchestrator = TaskOrchestrator(self.mcp_manager, self.llm, trace_logger=self.trace_logger)
        self.result_processor = ResultProcessor(self.llm, trace_logger=self.trace_logger)
        self.response_generator = ResponseGenerator(self.llm, trace_logger=self.trace_logger)
        
        # ドキュメント検索エンジンの初期化
        self.document_retriever = DocumentRetriever()
        self.document_retriever.create_index()
        
        # ツールの追加
        self.tools = [
            DocumentSearchTool(self.document_retriever)
        ]
        
        # エージェント設定
        self.max_iterations = 20  # 増加
        self.session_timeout = 3600  # 1時間
        self.is_running = False
        
        if self.trace_logger:
            self.trace_logger.log_custom_event(
                "AGENT_INITIALIZATION", 
                "エージェント初期化完了",
                {
                    "model_name": model_name,
                    "max_iterations": self.max_iterations,
                    "session_timeout": self.session_timeout,
                    "processors_initialized": [
                        "InputProcessor", "IntentAnalyzer", "PlanGenerator",
                        "MCPManager", "TaskOrchestrator", "ResultProcessor", "ResponseGenerator"
                    ]
                }
            )
        
        logger.info(f"自律型AIエージェント初期化完了 (モデル: {model_name}, トレーシング: {enable_tracing})")
    
    async def run_session(self, session_id: Optional[str] = None) -> None:
        """
        対話セッションの実行
        
        Args:
            session_id: セッションID（指定しない場合は自動生成）
        """
        if self.is_running:
            logger.warning("既にセッションが実行中です")
            return
        
        self.is_running = True
        state = create_initial_state(session_id)
        
        if self.trace_logger:
            with self.trace_logger.trace_execution_step(
                "SESSION_START", 
                "INITIALIZATION", 
                {"session_id": state["session_metadata"]["session_id"]}
            ):
                # セッション開始ログ
                self.trace_logger.log_custom_event(
                    "SESSION_START",
                    f"自律型AIエージェントセッション開始",
                    {
                        "session_id": state["session_metadata"]["session_id"],
                        "start_time": datetime.now().isoformat(),
                        "initial_phase": state["current_phase"]
                    }
                )
        
        try:
            logger.info("🚀 自律型AIエージェントセッション開始")
            
            while self.is_running:
                try:
                    # メイン処理ループ
                    state = await self._execute_main_loop(state)
                    
                    # 完了チェック
                    if state["current_phase"] == AgentPhase.COMPLETED.value:
                        if self.trace_logger:
                            self.trace_logger.log_custom_event(
                                "SESSION_COMPLETED",
                                "セッション正常完了",
                                {"final_phase": state["current_phase"]}
                            )
                        logger.info("✅ セッション正常完了")
                        break
                    
                    # エラーハンドリング
                    if state["current_phase"] == AgentPhase.ERROR_HANDLING.value:
                        state = await self._handle_error(state)
                        if not self._should_continue_after_error(state):
                            break
                        # エラー処理後は入力処理に戻る
                        continue
                    
                    # 無限ループ防止
                    iteration_count = state["session_metadata"].get("iteration_count", 0)
                    if iteration_count >= self.max_iterations:
                        if self.trace_logger:
                            self.trace_logger.log_custom_event(
                                "SESSION_LIMIT_REACHED",
                                f"最大繰り返し回数に達しました",
                                {"iteration_count": iteration_count, "max_iterations": self.max_iterations}
                            )
                        logger.warning("最大繰り返し回数に達しました")
                        break
                    
                    # 新しい入力を待つかチェック
                    if self._should_wait_for_new_input(state):
                        if self.trace_logger:
                            self.trace_logger.log_custom_event(
                                "WAITING_FOR_INPUT",
                                "新しい入力を待機中",
                                {"current_phase": state["current_phase"]}
                            )
                        logger.info("🔄 新しい入力を待機中...")
                        continue
                    else:
                        logger.info(f"✅ 処理継続 - 現在フェーズ: {state['current_phase']}")
                        if state["current_phase"] == AgentPhase.COMPLETED.value:
                            logger.info("🎉 全処理が完了しました")
                        # 継続
                        
                except KeyboardInterrupt:
                    if self.trace_logger:
                        self.trace_logger.log_custom_event(
                            "SESSION_INTERRUPTED",
                            "ユーザーによる中断",
                            {"keyboard_interrupt": True}
                        )
                    logger.info("ユーザーによる中断")
                    break
                except Exception as e:
                    if self.trace_logger:
                        self.trace_logger.log_custom_event(
                            "SESSION_ERROR",
                            f"予期しないエラー: {str(e)}",
                            {"error_type": type(e).__name__, "error_message": str(e)}
                        )
                    logger.error(f"予期しないエラー: {str(e)}")
                    break
        
        finally:
            await self._cleanup_session(state)
            self.is_running = False
            
            # トレーシングサマリーの出力
            if self.trace_logger:
                self.trace_logger.print_final_summary()
                self.trace_logger.save_trace_data()
            
            logger.info("🏁 セッション終了")
    
    async def _execute_main_loop(self, state: AgentState) -> AgentState:
        """メイン処理ループの実行（トレーシング対応）"""
        phase = state["current_phase"]
        
        # 繰り返し回数の更新
        iteration_count = state["session_metadata"].get("iteration_count", 0) + 1
        state["session_metadata"]["iteration_count"] = iteration_count
        
        logger.info(f"🔄 フェーズ実行: {phase} (繰り返し: {iteration_count})")
        
        # フェーズ実行のトレーシング
        phase_input_data = {
            "current_phase": phase,
            "iteration_count": iteration_count,
            "session_id": state["session_metadata"]["session_id"],
            "previous_results": bool(state.get("execution_results"))
        }
        
        try:
            if self.trace_logger:
                with self.trace_logger.trace_execution_step(
                    f"PHASE_{phase.upper()}", 
                    phase, 
                    phase_input_data
                ):
                    state = await self._execute_phase(state, phase)
                    
                    # フェーズ完了後の出力データ記録
                    self.trace_logger.log_step_output({
                        "new_phase": state["current_phase"],
                        "has_results": bool(state.get("execution_results")),
                        "has_errors": bool(state.get("error_context"))
                    })
            else:
                state = await self._execute_phase(state, phase)
        
        except Exception as e:
            if self.trace_logger:
                self.trace_logger.log_custom_event(
                    "PHASE_ERROR",
                    f"フェーズ実行中にエラーが発生: {phase}",
                    {
                        "phase": phase,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "iteration_count": iteration_count
                    }
                )
            
            logger.error(f"フェーズ実行中にエラーが発生: {phase} - {str(e)}")
            import traceback
            logger.error(f"詳細なエラー情報: {traceback.format_exc()}")
            
            state["current_phase"] = AgentPhase.ERROR_HANDLING.value
            state["error_context"] = {
                "phase": phase,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        
        return state
    
    async def _execute_phase(self, state: AgentState, phase: str) -> AgentState:
        """個別フェーズの実行"""
        # フェーズ別処理の実行
        if phase == AgentPhase.INPUT_PROCESSING.value:
            state = await self.input_processor.process_input(state)
            
        elif phase == AgentPhase.INTENT_ANALYSIS.value:
            state = await self.intent_analyzer.analyze_intent(state)
            
        elif phase == AgentPhase.PLAN_GENERATION.value:
            state = await self.plan_generator.generate_plan(state)
            
        elif phase == AgentPhase.MCP_INITIALIZATION.value:
            state = await self.mcp_manager.initialize_connections(state)
            
        elif phase == AgentPhase.TASK_EXECUTION.value:
            state = await self.task_orchestrator.execute_tasks(state)
            
        elif phase == AgentPhase.RESULT_PROCESSING.value:
            state = await self.result_processor.process_results(state)
            
        elif phase == AgentPhase.RESPONSE_GENERATION.value:
            state = await self.response_generator.generate_response(state)
            
        else:
            logger.warning(f"未知のフェーズ: {phase}")
            state["current_phase"] = AgentPhase.ERROR_HANDLING.value
            state["error_context"] = {
                "phase": phase,
                "error": f"未知のフェーズが指定されました: {phase}"
            }
        
        return state
    
    async def _handle_error(self, state: AgentState) -> AgentState:
        """エラーハンドリング（トレーシング対応）"""
        error_context = state.get("error_context", {})
        error_phase = error_context.get("phase", "unknown")
        error_message = error_context.get("error", "不明なエラー")
        
        if self.trace_logger:
            with self.trace_logger.trace_execution_step(
                "ERROR_HANDLING", 
                "ERROR_RECOVERY", 
                error_context
            ):
                # エラー詳細をログ記録
                self.trace_logger.log_custom_event(
                    "ERROR_DETAILS",
                    f"エラー処理開始: {error_phase}",
                    {
                        "error_phase": error_phase,
                        "error_message": error_message,
                        "recoverable": self._is_recoverable_error(error_context)
                    }
                )
        
        logger.error(f"❌ エラー処理 ({error_phase}): {error_message}")
        
        # エラー応答の生成
        error_response = await self._generate_error_response(error_context, state)
        
        # ユーザーにエラーを通知
        print(f"\n❌ エラーが発生しました: {error_message}")
        print(f"🔧 対処方法: {error_response}")
        
        # 復旧可能かチェック
        if self._is_recoverable_error(error_context):
            if self.trace_logger:
                self.trace_logger.log_custom_event(
                    "ERROR_RECOVERY",
                    "復旧可能なエラー - 入力処理に戻ります",
                    {"recovery_action": "return_to_input_processing"}
                )
            logger.info("復旧可能なエラーです。入力処理に戻ります。")
            state["current_phase"] = AgentPhase.INPUT_PROCESSING.value
            state["error_context"] = None
        else:
            if self.trace_logger:
                self.trace_logger.log_custom_event(
                    "ERROR_FATAL",
                    "復旧不可能なエラー - セッション終了",
                    {"recovery_action": "terminate_session"}
                )
            logger.error("復旧不可能なエラーです。セッションを終了します。")
            self.is_running = False
        
        return state
    
    async def _generate_error_response(self, error_context: Dict[str, Any], 
                                     state: AgentState) -> str:
        """エラー応答の生成"""
        error_phase = error_context.get("phase", "unknown")
        error_message = error_context.get("error", "")
        
        error_solutions = {
            "input_processing": "入力を確認して再度お試しください。",
            "intent_analysis": "質問をより具体的にしてください。",
            "plan_generation": "要求をより簡単な内容に分割してみてください。",
            "mcp_initialization": "外部ツールに問題があります。基本機能で対応します。",
            "task_execution": "処理中にエラーが発生しました。別の方法を試してみます。",
            "result_processing": "結果処理でエラーが発生しました。部分的な結果をお示しします。",
            "response_generation": "応答生成でエラーが発生しました。簡潔な回答をお示しします。"
        }
        
        base_solution = error_solutions.get(error_phase, "お手数ですが、再度お試しください。")
        
        return f"{base_solution}\n詳細: {error_message}"
    
    def _is_recoverable_error(self, error_context: Dict[str, Any]) -> bool:
        """復旧可能なエラーかチェック"""
        error_phase = error_context.get("phase", "")
        error_message = error_context.get("error", "")
        
        # 復旧不可能なエラーパターン
        unrecoverable_patterns = [
            "APIキーが無効",
            "認証エラー",
            "権限がありません",
            "システム停止"
        ]
        
        for pattern in unrecoverable_patterns:
            if pattern in error_message:
                return False
        
        # 特定フェーズでの復旧不可能エラー
        if error_phase == "input_processing" and "中断" in error_message:
            return False
        
        return True
    
    def _should_continue_after_error(self, state: AgentState) -> bool:
        """エラー後に継続するかチェック"""
        error_count = state["session_metadata"].get("error_count", 0) + 1
        state["session_metadata"]["error_count"] = error_count
        
        max_errors = 3
        if error_count >= max_errors:
            logger.error(f"エラー回数が上限に達しました: {error_count}")
            return False
        
        return self.is_running
    
    def _should_wait_for_new_input(self, state: AgentState) -> bool:
        """新しい入力を待つかチェック"""
        current_phase = state["current_phase"]
        
        # 完了した場合のみ新しい入力を待つ
        if current_phase == AgentPhase.COMPLETED.value:
            state["current_phase"] = AgentPhase.INPUT_PROCESSING.value
            return True
        
        # エラーハンドリングフェーズの場合は継続しない
        if current_phase == AgentPhase.ERROR_HANDLING.value:
            return False
        
        # その他の場合は処理を継続
        return False
    
    async def _cleanup_session(self, state: AgentState) -> None:
        """セッションのクリーンアップ"""
        try:
            # MCP接続のクリーンアップ
            await self.mcp_manager.cleanup_connections()
            
            # セッション統計の出力
            self._print_session_summary(state)
            
        except Exception as e:
            logger.warning(f"クリーンアップ中にエラー: {str(e)}")
    
    def _print_session_summary(self, state: AgentState) -> None:
        """セッション要約の出力"""
        metadata = state["session_metadata"]
        
        print("\n" + "="*60)
        print("📊 セッション要約")
        print("="*60)
        print(f"セッションID: {metadata.get('session_id', 'N/A')}")
        print(f"開始時刻: {metadata.get('created_at', 'N/A')}")
        print(f"入力回数: {metadata.get('input_count', 0)}")
        print(f"繰り返し回数: {metadata.get('iteration_count', 0)}")
        print(f"エラー回数: {metadata.get('error_count', 0)}")
        print(f"最終フェーズ: {state.get('current_phase', 'N/A')}")
        
        # 実行計画の概要
        if state.get("execution_plan"):
            plan = state["execution_plan"]
            print(f"実行タスク数: {len(plan.subtasks)}")
            print(f"推定実行時間: {plan.estimated_duration}秒")
        
        print("="*60)
    
    def stop_session(self) -> None:
        """セッションの停止"""
        self.is_running = False
        logger.info("セッション停止要求を受信")


async def main():
    """メイン関数：デモ実行"""
    try:
        # APIキーの確認
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ エラー: OPENAI_API_KEYが設定されていません")
            print("💡 .envファイルでAPIキーを設定してください")
            return
        
        # エージェントの作成と実行
        agent = AutonomousAgent()
        await agent.run_session()
        
    except KeyboardInterrupt:
        print("\n👋 プログラムを終了します")
    except Exception as e:
        logger.error(f"プログラム実行エラー: {str(e)}")
        print(f"❌ 予期しないエラーが発生しました: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main()) 