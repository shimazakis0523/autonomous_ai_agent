"""
自律型AIエージェント - ユーザー入力処理
フェーズ1: 入力受付・前処理・検証
トレーシング機能付き
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain_core.messages import HumanMessage

from ..core.agent_state import AgentState, AgentPhase, add_error_context

logger = logging.getLogger(__name__)


class InputProcessor:
    """ユーザー入力処理クラス（トレーシング対応）"""
    
    def __init__(self, trace_logger=None):
        """
        初期化
        
        Args:
            trace_logger: トレーシングロガー（オプション）
        """
        self.trace_logger = trace_logger
        self.input_history: List[Dict[str, Any]] = []
        self.context_window = 10
        self.max_input_length = 5000
        self.min_input_length = 1
        
        if self.trace_logger:
            self.trace_logger.log_custom_event(
                "INPUT_PROCESSOR_INIT",
                "InputProcessor初期化完了",
                {
                    "context_window": self.context_window,
                    "max_input_length": self.max_input_length,
                    "min_input_length": self.min_input_length
                }
            )
    
    async def process_input(self, state: AgentState) -> AgentState:
        """
        ユーザー入力受付と前処理
        
        Args:
            state: 現在のエージェント状態
            
        Returns:
            更新されたエージェント状態
        """
        if self.trace_logger:
            with self.trace_logger.trace_execution_step(
                "INPUT_PROCESSING", 
                "INPUT_PROCESSING", 
                {"session_id": state["session_metadata"]["session_id"]}
            ):
                return await self._process_input_with_tracing(state)
        else:
            return await self._process_input_basic(state)
    
    async def _process_input_with_tracing(self, state: AgentState) -> AgentState:
        """トレーシング付きの入力処理"""
        try:
            # ユーザー入力の受信
            self.trace_logger.log_custom_event(
                "INPUT_RECEIVE_START",
                "ユーザー入力の受信開始",
                {}
            )
            
            user_input = self._receive_user_input()
            
            self.trace_logger.log_custom_event(
                "INPUT_RECEIVED",
                f"ユーザー入力受信完了",
                {
                    "input_length": len(user_input),
                    "input_preview": user_input[:50] + "..." if len(user_input) > 50 else user_input
                }
            )
            
            # 入力検証
            self._validate_input(user_input)
            self.trace_logger.log_custom_event(
                "INPUT_VALIDATED",
                "入力検証完了",
                {"is_valid": True}
            )
            
            # 入力の前処理
            processed_input = self._preprocess_input(user_input)
            
            # 履歴への追加
            self._add_to_history(processed_input, state)
            
            # メッセージ履歴に追加
            user_message = HumanMessage(content=processed_input)
            
            # セッションメタデータの更新
            updated_metadata = self._update_session_metadata(state["session_metadata"])
            
            logger.info(f"ユーザー入力処理完了: {processed_input[:50]}...")
            
            # 状態の更新
            updated_state = state.copy()
            updated_state.update({
                "user_input": processed_input,
                "messages": state["messages"] + [user_message],
                "current_phase": AgentPhase.INTENT_ANALYSIS.value,
                "session_metadata": updated_metadata
            })
            
            # トレーシングに出力データを記録
            self.trace_logger.log_step_output({
                "processed_input_length": len(processed_input),
                "next_phase": AgentPhase.INTENT_ANALYSIS.value,
                "message_count": len(updated_state["messages"])
            })
            
            return updated_state
            
        except Exception as e:
            self.trace_logger.log_custom_event(
                "INPUT_ERROR",
                f"入力処理エラー: {str(e)}",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            logger.error(f"入力処理エラー: {str(e)}")
            return add_error_context(state, "input_processing", str(e))
    
    async def _process_input_basic(self, state: AgentState) -> AgentState:
        """基本的な入力処理（トレーシングなし）"""
        try:
            # ユーザー入力の受信
            user_input = self._receive_user_input()
            
            # 入力検証
            self._validate_input(user_input)
            
            # 入力の前処理
            processed_input = self._preprocess_input(user_input)
            
            # 履歴への追加
            self._add_to_history(processed_input, state)
            
            # メッセージ履歴に追加
            user_message = HumanMessage(content=processed_input)
            
            # セッションメタデータの更新
            updated_metadata = self._update_session_metadata(state["session_metadata"])
            
            logger.info(f"ユーザー入力処理完了: {processed_input[:50]}...")
            
            # 状態の更新
            updated_state = state.copy()
            updated_state.update({
                "user_input": processed_input,
                "messages": state["messages"] + [user_message],
                "current_phase": AgentPhase.INTENT_ANALYSIS.value,
                "session_metadata": updated_metadata
            })
            
            return updated_state
            
        except Exception as e:
            logger.error(f"入力処理エラー: {str(e)}")
            return add_error_context(state, "input_processing", str(e))
    
    def _receive_user_input(self) -> str:
        """標準入力からユーザー入力を受信"""
        print("\n🤖 自律型AIエージェントです。何をお手伝いしましょうか？")
        print("📝 詳細な指示や質問を自然な日本語でどうぞ")
        print("-" * 60)
        
        try:
            user_input = input("👤 あなた: ").strip()
            return user_input
        except (KeyboardInterrupt, EOFError):
            raise ValueError("入力が中断されました")
    
    def _validate_input(self, user_input: str) -> None:
        """入力検証"""
        if not user_input:
            raise ValueError("空の入力は受け付けられません")
        
        if len(user_input) < self.min_input_length:
            raise ValueError(f"入力が短すぎます（最小{self.min_input_length}文字）")
        
        if len(user_input) > self.max_input_length:
            raise ValueError(f"入力が長すぎます（最大{self.max_input_length}文字）")
        
        # 危険なコマンドのチェック
        dangerous_patterns = [
            "rm -rf", "del /", "format c:", "__import__", "exec(", "eval("
        ]
        
        for pattern in dangerous_patterns:
            if pattern in user_input.lower():
                raise ValueError(f"危険なコマンドが含まれています: {pattern}")
    
    def _preprocess_input(self, user_input: str) -> str:
        """入力の前処理"""
        # 前後の空白を除去
        processed = user_input.strip()
        
        # 連続する空白を単一空白に変換
        processed = " ".join(processed.split())
        
        # 絵文字や特殊文字の正規化（必要に応じて）
        # processed = unicodedata.normalize('NFKC', processed)
        
        return processed
    
    def _add_to_history(self, user_input: str, state: AgentState) -> None:
        """入力履歴に追加"""
        history_entry = {
            "input": user_input,
            "timestamp": datetime.now().isoformat(),
            "session_id": state["session_metadata"]["session_id"],
            "input_length": len(user_input)
        }
        
        self.input_history.append(history_entry)
        
        # 履歴サイズの制限
        if len(self.input_history) > self.context_window * 2:
            self.input_history = self.input_history[-self.context_window:]
    
    def _update_session_metadata(self, current_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """セッションメタデータの更新"""
        updated_metadata = current_metadata.copy()
        updated_metadata.update({
            "last_input_time": datetime.now().isoformat(),
            "input_count": current_metadata.get("input_count", 0) + 1
        })
        return updated_metadata
    
    def get_context_summary(self) -> str:
        """過去の入力履歴から文脈要約を生成"""
        if len(self.input_history) <= 1:
            return "初回の対話です。"
        
        recent_inputs = self.input_history[-self.context_window:]
        context = "最近の対話履歴:\n"
        
        for i, entry in enumerate(recent_inputs[-3:], 1):
            timestamp = entry["timestamp"][:16]  # YYYY-MM-DDTHH:MM まで
            context += f"{i}. [{timestamp}] {entry['input']}\n"
        
        return context
    
    def get_input_statistics(self) -> Dict[str, Any]:
        """入力統計情報の取得"""
        if not self.input_history:
            return {"total_inputs": 0}
        
        total_inputs = len(self.input_history)
        total_characters = sum(entry["input_length"] for entry in self.input_history)
        avg_length = total_characters / total_inputs if total_inputs > 0 else 0
        
        recent_activity = [
            entry for entry in self.input_history
            if (datetime.now() - datetime.fromisoformat(entry["timestamp"])).seconds < 3600
        ]
        
        return {
            "total_inputs": total_inputs,
            "total_characters": total_characters,
            "average_length": avg_length,
            "recent_activity_count": len(recent_activity),
            "longest_input": max(entry["input_length"] for entry in self.input_history),
            "shortest_input": min(entry["input_length"] for entry in self.input_history)
        }
    
    def clear_history(self) -> None:
        """履歴のクリア"""
        self.input_history.clear()
        logger.info("入力履歴をクリアしました") 