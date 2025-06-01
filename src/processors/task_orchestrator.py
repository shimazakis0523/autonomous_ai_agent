"""
自律型AIエージェント - タスクオーケストレーション・実行
フェーズ5: 複雑なタスクの並列・順次実行制御
トレーシング機能付き
"""
import asyncio
import logging
from typing import Dict, List, Any, Set, TYPE_CHECKING, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage

from ..core.agent_state import AgentState, AgentPhase, TaskStatus, add_error_context
from ..external.mcp_manager import MCPManager

if TYPE_CHECKING:
    from ..external.mcp_manager import MCPManager

logger = logging.getLogger(__name__)


class TaskOrchestrator:
    """タスク実行オーケストレーター（トレーシング対応）"""
    
    def __init__(self, mcp_manager: MCPManager, llm: ChatOpenAI, trace_logger=None):
        """
        タスクオーケストレーターの初期化
        
        Args:
            mcp_manager: MCP管理インスタンス
            llm: 言語モデルインスタンス
            trace_logger: トレーシングロガー（オプション）
        """
        self.mcp_manager = mcp_manager
        self.llm = llm
        self.trace_logger = trace_logger
        self.max_parallel_tasks = 5
        self.task_timeout = 120  # 2分
        self.executor = ThreadPoolExecutor(max_workers=self.max_parallel_tasks)
        self.max_retries = 3
        
        # 実行統計
        self.execution_stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'retried_tasks': 0,
            'avg_execution_time': 0,
            'total_execution_time': 0
        }
        
        if self.trace_logger:
            self.trace_logger.log_custom_event(
                "TASK_ORCHESTRATOR_INIT",
                "TaskOrchestrator初期化完了",
                {
                    "max_workers": 5,
                    "max_retries": self.max_retries,
                    "task_timeout": self.task_timeout,
                    "parallel_limit": self.max_parallel_tasks,
                    "llm_model": getattr(llm, 'model_name', 'unknown')
                }
            )
        
    async def execute_tasks(self, state: AgentState) -> AgentState:
        """
        実行計画に基づくタスクの実行
        
        Args:
            state: 現在のエージェント状態
            
        Returns:
            タスク実行結果を含む更新された状態
        """
        try:
            execution_plan = state["execution_plan"]
            if not execution_plan:
                logger.warning("実行計画が見つかりません")
                return self._update_to_result_processing(state, {"error": "実行計画なし"})
            
            logger.info(f"タスク実行開始: {len(execution_plan.subtasks)}個のサブタスク")
            
            # 実行結果の初期化
            task_results = {}
            completed_tasks: Set[str] = set()
            failed_tasks: Set[str] = set()
            
            # タスク実行の進捗追跡
            progress_tracker = {
                "total_tasks": len(execution_plan.subtasks),
                "completed": 0,
                "failed": 0,
                "in_progress": 0
            }
            
            # 実行ループ
            while len(completed_tasks) + len(failed_tasks) < len(execution_plan.subtasks):
                # 実行可能なタスクの特定
                ready_tasks = execution_plan.get_ready_tasks(completed_tasks)
                
                if not ready_tasks:
                    logger.warning("実行可能なタスクが見つかりません。依存関係を確認してください。")
                    break
                
                # 並列実行グループの取得
                parallel_groups = self._get_parallel_execution_groups(
                    ready_tasks, execution_plan.parallel_groups
                )
                
                # 並列実行
                for group in parallel_groups:
                    if len(group) == 1:
                        # 単一タスクの実行
                        task_id = group[0]
                        result = await self._execute_single_task(
                            task_id, execution_plan, state, progress_tracker
                        )
                        task_results[task_id] = result
                        
                        if result.get("status") == "success":
                            completed_tasks.add(task_id)
                        else:
                            failed_tasks.add(task_id)
                    else:
                        # 並列タスクの実行
                        parallel_results = await self._execute_parallel_tasks(
                            group, execution_plan, state, progress_tracker
                        )
                        
                        for task_id, result in parallel_results.items():
                            task_results[task_id] = result
                            if result.get("status") == "success":
                                completed_tasks.add(task_id)
                            else:
                                failed_tasks.add(task_id)
                
                # 進捗状況の更新
                progress_tracker["completed"] = len(completed_tasks)
                progress_tracker["failed"] = len(failed_tasks)
                progress_tracker["in_progress"] = 0
                
                self._print_progress(progress_tracker)
                
                # 失敗タスクが多すぎる場合は中断
                if len(failed_tasks) > len(execution_plan.subtasks) * 0.5:
                    logger.error("失敗タスクが50%を超えました。実行を中断します。")
                    break
            
            # 実行結果の最終処理
            final_results = self._process_final_results(
                task_results, execution_plan, completed_tasks, failed_tasks
            )
            
            logger.info(f"タスク実行完了: 成功{len(completed_tasks)}, 失敗{len(failed_tasks)}")
            
            return self._update_to_result_processing(state, final_results)
            
        except Exception as e:
            logger.error(f"タスクオーケストレーションエラー: {str(e)}")
            return add_error_context(state, "task_execution", str(e))
    
    async def _execute_single_task(self, task_id: str, execution_plan, 
                                 state: AgentState, progress_tracker: Dict) -> Dict[str, Any]:
        """単一タスクの実行"""
        subtask = execution_plan.get_subtask_by_id(task_id)
        if not subtask:
            return {"status": "error", "error": f"タスクが見つかりません: {task_id}"}
        
        try:
            logger.info(f"🔄 タスク実行: {task_id} - {subtask.description[:50]}...")
            progress_tracker["in_progress"] += 1
            
            # タスクステータス更新
            subtask.status = TaskStatus.EXECUTING
            
            start_time = datetime.now()
            
            if subtask.tool_name:
                # 外部ツールを使用するタスク
                result = await asyncio.wait_for(
                    self.mcp_manager.execute_tool(subtask.tool_name, subtask.parameters),
                    timeout=self.task_timeout
                )
            else:
                # LLMによる直接処理
                result = await self._execute_llm_task(subtask, state)
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # 成功結果の処理
            subtask.status = TaskStatus.COMPLETED
            subtask.result = result
            subtask.completed_at = end_time.isoformat()
            
            progress_tracker["in_progress"] -= 1
            
            logger.info(f"✅ タスク完了: {task_id} ({execution_time:.2f}秒)")
            
            return {
                "status": "success",
                "task_id": task_id,
                "result": result,
                "execution_time": execution_time,
                "completed_at": end_time.isoformat()
            }
            
        except asyncio.TimeoutError:
            error_msg = f"タスクタイムアウト: {task_id}"
            logger.error(error_msg)
            subtask.status = TaskStatus.FAILED
            subtask.error = error_msg
            progress_tracker["in_progress"] -= 1
            
            return {"status": "error", "task_id": task_id, "error": error_msg}
            
        except Exception as e:
            error_msg = f"タスク実行エラー ({task_id}): {str(e)}"
            logger.error(error_msg)
            subtask.status = TaskStatus.FAILED
            subtask.error = str(e)
            progress_tracker["in_progress"] -= 1
            
            return {"status": "error", "task_id": task_id, "error": str(e)}
    
    async def _execute_parallel_tasks(self, task_group: List[str], execution_plan,
                                    state: AgentState, progress_tracker: Dict) -> Dict[str, Any]:
        """並列タスクの実行"""
        logger.info(f"⚡ 並列実行開始: {len(task_group)}個のタスク")
        
        # 並列実行タスクの作成
        tasks = []
        for task_id in task_group:
            task = asyncio.create_task(
                self._execute_single_task(task_id, execution_plan, state, progress_tracker),
                name=f"task_{task_id}"
            )
            tasks.append(task)
        
        # 並列実行の待機
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果の処理
        parallel_results = {}
        for i, (task_id, result) in enumerate(zip(task_group, results)):
            if isinstance(result, Exception):
                logger.error(f"並列タスクエラー ({task_id}): {str(result)}")
                parallel_results[task_id] = {
                    "status": "error",
                    "task_id": task_id,
                    "error": str(result)
                }
            else:
                parallel_results[task_id] = result
        
        successful_count = sum(1 for r in parallel_results.values() if r.get("status") == "success")
        logger.info(f"⚡ 並列実行完了: {successful_count}/{len(task_group)}個成功")
        
        return parallel_results
    
    async def _execute_llm_task(self, subtask, state: AgentState) -> Dict[str, Any]:
        """LLMによるタスク実行"""
        user_input = state["user_input"]
        context = self._build_task_context(subtask, state)
        
        task_prompt = f"""
        以下のタスクを実行してください：

        **タスク内容:** {subtask.description}
        
        **ユーザーの元の要求:** {user_input}
        
        **実行文脈:**
        {context}
        
        **パラメータ:**
        {subtask.parameters}

        タスクを実行し、結果を以下の形式で返してください：
        - 実行した内容の詳細
        - 得られた結果や知見
        - 次のタスクへの引き継ぎ情報（あれば）
        
        明確で有用な回答を提供してください。
        """
        
        response = await self.llm.ainvoke([
            {"role": "system", "content": "あなたは高性能なタスク実行AIです。与えられたタスクを確実に実行し、有用な結果を提供してください。"},
            {"role": "user", "content": task_prompt}
        ])
        
        return {
            "type": "llm_execution",
            "response": response.content,
            "task_description": subtask.description,
            "parameters": subtask.parameters
        }
    
    def _get_parallel_execution_groups(self, ready_tasks: List[str], 
                                     parallel_groups: List[List[str]]) -> List[List[str]]:
        """並列実行グループの取得"""
        execution_groups = []
        remaining_tasks = set(ready_tasks)
        
        # 定義済み並列グループの処理
        for group in parallel_groups:
            available_in_group = [t for t in group if t in remaining_tasks]
            if available_in_group:
                # 並列実行数の制限
                if len(available_in_group) > self.max_parallel_tasks:
                    # グループを分割
                    for i in range(0, len(available_in_group), self.max_parallel_tasks):
                        sub_group = available_in_group[i:i + self.max_parallel_tasks]
                        execution_groups.append(sub_group)
                        remaining_tasks -= set(sub_group)
                else:
                    execution_groups.append(available_in_group)
                    remaining_tasks -= set(available_in_group)
        
        # 残りのタスクを個別実行として追加
        for task in remaining_tasks:
            execution_groups.append([task])
        
        return execution_groups
    
    def _build_task_context(self, subtask, state: AgentState) -> str:
        """タスク実行のための文脈構築"""
        context_parts = []
        
        # 意図分析の情報
        if state.get("intent_analysis"):
            intent = state["intent_analysis"]
            context_parts.append(f"ユーザー意図: {intent.get('primary_intent', 'N/A')}")
            context_parts.append(f"複雑度: {intent.get('complexity', 'N/A')}")
        
        # 依存タスクの結果
        if subtask.dependencies:
            context_parts.append("依存タスクの結果:")
            for dep_id in subtask.dependencies:
                if dep_id in state.get("task_results", {}):
                    result = state["task_results"][dep_id]
                    context_parts.append(f"  {dep_id}: {str(result)[:100]}...")
        
        # 利用可能ツール情報
        available_tools = self.mcp_manager.get_available_tools()
        context_parts.append(f"利用可能ツール: {', '.join(available_tools)}")
        
        return "\n".join(context_parts)
    
    def _process_final_results(self, task_results: Dict[str, Any], execution_plan,
                             completed_tasks: Set[str], failed_tasks: Set[str]) -> Dict[str, Any]:
        """最終結果の処理"""
        
        # 成功率の計算
        total_tasks = len(execution_plan.subtasks)
        success_rate = len(completed_tasks) / total_tasks if total_tasks > 0 else 0
        
        # 重要な結果の抽出
        key_results = []
        for task_id in completed_tasks:
            result = task_results.get(task_id, {})
            if result.get("status") == "success":
                key_results.append({
                    "task_id": task_id,
                    "description": execution_plan.get_subtask_by_id(task_id).description,
                    "result": result.get("result"),
                    "execution_time": result.get("execution_time", 0)
                })
        
        # 失敗分析
        failure_analysis = []
        for task_id in failed_tasks:
            result = task_results.get(task_id, {})
            failure_analysis.append({
                "task_id": task_id,
                "description": execution_plan.get_subtask_by_id(task_id).description,
                "error": result.get("error", "不明なエラー")
            })
        
        return {
            "execution_summary": {
                "total_tasks": total_tasks,
                "completed_tasks": len(completed_tasks),
                "failed_tasks": len(failed_tasks),
                "success_rate": success_rate,
                "execution_time": sum(
                    r.get("execution_time", 0) for r in task_results.values()
                    if isinstance(r, dict)
                )
            },
            "key_results": key_results,
            "failure_analysis": failure_analysis,
            "raw_results": task_results,
            "completed_task_ids": list(completed_tasks),
            "failed_task_ids": list(failed_tasks)
        }
    
    def _print_progress(self, progress_tracker: Dict) -> None:
        """進捗状況の表示"""
        total = progress_tracker["total_tasks"]
        completed = progress_tracker["completed"]
        failed = progress_tracker["failed"]
        in_progress = progress_tracker["in_progress"]
        
        progress_percentage = ((completed + failed) / total) * 100 if total > 0 else 0
        
        print(f"📊 実行進捗: {progress_percentage:.1f}% "
              f"(完了: {completed}, 失敗: {failed}, 実行中: {in_progress})")
    
    def _update_to_result_processing(self, state: AgentState, 
                                   results: Dict[str, Any]) -> AgentState:
        """結果処理フェーズへの状態更新"""
        updated_state = state.copy()
        updated_state.update({
            "task_results": results,
            "current_phase": AgentPhase.RESULT_PROCESSING.value,
            "messages": state["messages"] + [
                AIMessage(content=f"タスク実行が完了しました。結果を処理しています...")
            ]
        })
        return updated_state 