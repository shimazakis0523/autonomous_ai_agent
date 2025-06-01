"""
自律型AIエージェント - 実行計画生成エンジン
フェーズ3: タスク分解と実行戦略の策定
トレーシング機能付き
"""
import json
import logging
import uuid
import re
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from ..core.agent_state import (
    AgentState, AgentPhase, MCPTool, SubTask, ExecutionPlan, 
    TaskStatus, TaskPriority, add_error_context
)

logger = logging.getLogger(__name__)


class PlanGenerator:
    """実行計画生成エンジン（トレーシング対応）"""
    
    def __init__(self, llm: ChatOpenAI, trace_logger=None):
        """
        初期化
        
        Args:
            llm: ChatOpenAI インスタンス
            trace_logger: トレーシングロガー（オプション）
        """
        self.llm = llm
        self.trace_logger = trace_logger
        self.available_tools = self._load_available_tools()
        self.max_subtasks = 20
        self.max_parallel_tasks = 5
        self.max_planning_time = 300  # 5分
        
        # 優先度のマッピング
        self.priority_mapping = {
            1: TaskPriority.LOW,
            2: TaskPriority.MEDIUM,
            3: TaskPriority.HIGH,
            4: TaskPriority.CRITICAL
        }
        
        if self.trace_logger:
            self.trace_logger.log_custom_event(
                "PLAN_GENERATOR_INIT",
                "PlanGenerator初期化完了",
                {
                    "max_subtasks": self.max_subtasks,
                    "max_parallel_tasks": self.max_parallel_tasks,
                    "max_planning_time": self.max_planning_time,
                    "available_tools": list(self.available_tools.keys()),
                    "llm_model": getattr(llm, 'model_name', 'unknown')
                }
            )
    
    async def generate_plan(self, state: AgentState) -> AgentState:
        """
        詳細実行計画の生成
        
        Args:
            state: 現在のエージェント状態
            
        Returns:
            実行計画を含む更新された状態
        """
        try:
            intent_analysis = state["intent_analysis"]
            user_input = state["user_input"]
            
            logger.info("実行計画の生成を開始...")
            
            # 基本計画の生成
            base_plan = await self._generate_base_plan(user_input, intent_analysis)
            
            # 計画の最適化
            optimized_plan = await self._optimize_plan(base_plan, intent_analysis)
            
            # ExecutionPlan オブジェクトの作成
            execution_plan = self._create_execution_plan(optimized_plan)
            
            # 計画の妥当性検証
            self._validate_execution_plan(execution_plan)
            
            # リソース要件の計算
            resource_requirements = self._calculate_resource_requirements(execution_plan)
            execution_plan.resource_requirements = resource_requirements
            
            logger.info(f"実行計画生成完了: {len(execution_plan.subtasks)}個のサブタスク")
            
            # 状態の更新
            updated_state = state.copy()
            updated_state.update({
                "execution_plan": execution_plan,
                "current_phase": AgentPhase.MCP_INITIALIZATION.value,
                "messages": state["messages"] + [
                    AIMessage(content=f"実行計画を立案しました。{len(execution_plan.subtasks)}個のサブタスクに分解し、"
                                    f"推定実行時間は{execution_plan.estimated_duration}秒です。")
                ]
            })
            
            return updated_state
            
        except Exception as e:
            logger.error(f"計画生成エラー: {str(e)}")
            return add_error_context(state, "plan_generation", str(e))
    
    def _extract_json_from_response(self, content: str) -> Optional[Dict[str, Any]]:
        """LLMの応答からJSONを抽出"""
        # JSONブロックの抽出を試みる
        json_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        matches = re.findall(json_pattern, content)
        
        if matches:
            for json_str in matches:
                try:
                    return json.loads(json_str.strip())
                except json.JSONDecodeError:
                    continue
        
        # JSONブロックがない場合、全体をJSONとして解析を試みる
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            return None
    
    async def _generate_base_plan(self, user_input: str, intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """基本計画の生成"""
        planning_prompt = f"""
        以下のユーザー要求に対する詳細な実行計画を作成してください：

        **ユーザー入力:** {user_input}
        
        **意図分析:**
        {json.dumps(intent_analysis, ensure_ascii=False, indent=2)}
        
        **重要:**
        - 個人情報は必ずinternalDoc/personal_info.txtから取得してください
        - 外部検索は使用せず、ローカルファイルの内容のみを使用してください
        
        **利用可能ツール:**
        {json.dumps({name: tool.description for name, tool in self.available_tools.items()}, 
                   ensure_ascii=False, indent=2)}

        **優先度の定義:**
        - 1: LOW (低優先度)
        - 2: MEDIUM (中優先度)
        - 3: HIGH (高優先度)
        - 4: CRITICAL (最重要)

        以下の形式でJSONを返してください：
        {{
            "task_id": "unique_task_id",
            "overview": "計画の概要説明",
            "subtasks": [
                {{
                    "id": "subtask_1",
                    "description": "personal_info.txtから個人情報を読み取る",
                    "tool_name": "file_operations",
                    "parameters": {{
                        "operation": "read",
                        "path": "internalDoc/personal_info.txt"
                    }},
                    "dependencies": [],
                    "priority": 3,
                    "estimated_duration": 5
                }},
                {{
                    "id": "subtask_2",
                    "description": "読み取った情報から職歴情報を抽出",
                    "tool_name": "text_processing",
                    "parameters": {{
                        "operation": "extract",
                        "text": "{{subtask_1.result}}",
                        "target_section": "職歴"
                    }},
                    "dependencies": ["subtask_1"],
                    "priority": 3,
                    "estimated_duration": 10
                }},
                {{
                    "id": "subtask_3",
                    "description": "抽出した職歴情報を整形して回答を生成",
                    "tool_name": "text_processing",
                    "parameters": {{
                        "operation": "format",
                        "text": "{{subtask_2.result}}",
                        "format_type": "career_history"
                    }},
                    "dependencies": ["subtask_2"],
                    "priority": 2,
                    "estimated_duration": 15
                }}
            ],
            "execution_order": ["subtask_1", "subtask_2", "subtask_3"],
            "parallel_groups": [],
            "estimated_duration": 30,
            "success_criteria": [
                "personal_info.txtから正しく情報を読み取れる",
                "職歴情報が適切に抽出できる",
                "整形された回答が生成できる"
            ],
            "risk_factors": [
                "ファイルが存在しない",
                "ファイルの内容が不正",
                "必要な情報が見つからない"
            ],
            "contingency_plans": [
                "ファイルが見つからない場合はエラーメッセージを表示",
                "情報が見つからない場合はその旨を報告"
            ]
        }}
        """
        
        messages = [
            SystemMessage(content="あなたは実行計画の専門家です。ローカルファイルから情報を取得し、効率的で安全な実行計画を立案してください。必ず有効なJSONを返してください。"),
            HumanMessage(content=planning_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        plan_data = self._extract_json_from_response(response.content)
        
        if plan_data is None:
            logger.warning("JSON解析エラー、フォールバック計画を使用")
            return self._create_fallback_plan(user_input, intent_analysis)
        
        return plan_data
    
    async def _optimize_plan(self, base_plan: Dict[str, Any], intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """計画の最適化"""
        optimization_prompt = f"""
        以下の実行計画を最適化してください：

        **基本計画:**
        {json.dumps(base_plan, ensure_ascii=False, indent=2)}
        
        **最適化観点:**
        1. 実行効率の向上（並列化、冗長な処理の削除）
        2. リスクの軽減（失敗しやすいタスクの対策強化）
        3. リソース使用量の最適化
        4. ユーザー体験の向上（進捗の可視化、中間結果の提示）

        最適化された計画を以下の形式でJSONブロックとして返してください：
        ```json
        {{
            "task_id": "optimized_{base_plan['task_id']}",
            "overview": "最適化された計画の概要",
            "subtasks": [
                {{
                    "id": "subtask_1",
                    "description": "具体的な処理内容",
                    "tool_name": "使用するツール名",
                    "parameters": {{}},
                    "dependencies": [],
                    "priority": 2,
                    "estimated_duration": 30
                }}
            ],
            "execution_order": ["subtask_1"],
            "parallel_groups": [],
            "estimated_duration": 120,
            "optimization_notes": ["最適化のポイント1", "最適化のポイント2"]
        }}
        ```

        必ず有効なJSONブロックを返してください。
        """
        
        messages = [
            SystemMessage(content="あなたは計画最適化の専門家です。効率的で安全な実行計画を立案してください。必ず有効なJSONブロックを返してください。"),
            HumanMessage(content=optimization_prompt)
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            optimized_plan = self._extract_json_from_response(response.content)
            
            if optimized_plan is None:
                logger.warning("最適化結果のJSON解析に失敗、基本計画を使用")
                return base_plan
            
            # 最適化の検証
            if self._is_valid_optimization(base_plan, optimized_plan):
                logger.info("計画の最適化が成功しました")
                return optimized_plan
            else:
                logger.warning("最適化結果が不適切なため、基本計画を使用")
                return base_plan
                
        except Exception as e:
            logger.warning(f"計画最適化エラー、基本計画を使用: {str(e)}")
            return base_plan
    
    def _create_execution_plan(self, plan_data: Dict[str, Any]) -> ExecutionPlan:
        """プラン辞書からExecutionPlanオブジェクト作成"""
        subtasks = []
        
        for st_data in plan_data["subtasks"]:
            # タスクIDの生成（指定されていない場合）
            task_id = st_data.get("id", f"task_{str(uuid.uuid4())[:8]}")
            
            # 優先度の変換（安全な方法）
            priority_value = st_data.get("priority", 2)
            try:
                if isinstance(priority_value, int) and 1 <= priority_value <= 4:
                    priority = self.priority_mapping[priority_value]
                else:
                    priority = TaskPriority.MEDIUM
            except (KeyError, TypeError):
                priority = TaskPriority.MEDIUM
                logger.warning(f"無効な優先度値: {priority_value}、デフォルト値(MEDIUM)を使用")
            
            subtask = SubTask(
                id=task_id,
                description=st_data["description"],
                tool_name=st_data.get("tool_name"),
                parameters=st_data.get("parameters", {}),
                dependencies=st_data.get("dependencies", []),
                priority=priority
            )
            
            # 追加メタデータの設定
            subtask.result = None
            subtask.error = None
            subtasks.append(subtask)
        
        # タスクIDの生成
        task_id = plan_data.get("task_id", f"plan_{str(uuid.uuid4())[:8]}")
        
        return ExecutionPlan(
            task_id=task_id,
            subtasks=subtasks,
            execution_order=plan_data.get("execution_order", [st.id for st in subtasks]),
            parallel_groups=plan_data.get("parallel_groups", []),
            estimated_duration=plan_data.get("estimated_duration", 60),
            resource_requirements=plan_data.get("resource_requirements", {})
        )
    
    def _validate_execution_plan(self, plan: ExecutionPlan) -> None:
        """実行計画の妥当性検証"""
        # サブタスク数の制限チェック
        if len(plan.subtasks) > self.max_subtasks:
            raise ValueError(f"サブタスク数が制限を超えています: {len(plan.subtasks)} > {self.max_subtasks}")
        
        # 依存関係の循環参照チェック
        for subtask in plan.subtasks:
            if self._has_circular_dependency(subtask, plan.subtasks):
                raise ValueError(f"循環依存が検出されました: {subtask.id}")
        
        # 実行順序の整合性チェック
        subtask_ids = {st.id for st in plan.subtasks}
        for order_id in plan.execution_order:
            if order_id not in subtask_ids:
                raise ValueError(f"存在しないサブタスクID: {order_id}")
        
        # 並列グループの検証
        for group in plan.parallel_groups:
            if len(group) > self.max_parallel_tasks:
                raise ValueError(f"並列タスク数が制限を超えています: {len(group)} > {self.max_parallel_tasks}")
            
            for task_id in group:
                if task_id not in subtask_ids:
                    raise ValueError(f"並列グループに存在しないタスクID: {task_id}")
        
        # ツール名の検証
        for subtask in plan.subtasks:
            if subtask.tool_name and subtask.tool_name not in self.available_tools:
                logger.warning(f"未知のツール名: {subtask.tool_name}")
    
    def _has_circular_dependency(self, subtask: SubTask, all_subtasks: List[SubTask]) -> bool:
        """循環依存の検出"""
        def dfs(current_id: str, visited: set, path: set) -> bool:
            if current_id in path:
                return True  # 循環検出
            if current_id in visited:
                return False
            
            visited.add(current_id)
            path.add(current_id)
            
            current_task = next((st for st in all_subtasks if st.id == current_id), None)
            if current_task:
                for dep_id in current_task.dependencies:
                    if dfs(dep_id, visited, path):
                        return True
            
            path.remove(current_id)
            return False
        
        return dfs(subtask.id, set(), set())
    
    def _calculate_resource_requirements(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """リソース要件の計算"""
        total_duration = plan.estimated_duration
        tool_count = len(set(st.tool_name for st in plan.subtasks if st.tool_name))
        parallel_tasks = len(plan.parallel_groups)
        
        # リソース要件の推定
        cpu_requirement = "low"
        memory_requirement = "low"
        network_requirement = "low"
        
        if total_duration > 300 or tool_count > 3:
            cpu_requirement = "medium"
        if total_duration > 600 or tool_count > 5:
            cpu_requirement = "high"
        
        if parallel_tasks > 2 or len(plan.subtasks) > 10:
            memory_requirement = "medium"
        if parallel_tasks > 4 or len(plan.subtasks) > 15:
            memory_requirement = "high"
        
        # ネットワーク要件（ツールの種類に基づく）
        network_tools = ["web_search", "data_analysis", "file_operations"]
        if any(st.tool_name in network_tools for st in plan.subtasks if st.tool_name):
            network_requirement = "medium"
        
        return {
            "cpu": cpu_requirement,
            "memory": memory_requirement,
            "network": network_requirement,
            "estimated_peak_memory": f"{len(plan.subtasks) * 10}MB",
            "estimated_storage": f"{max(100, total_duration)}MB",
            "concurrent_connections": min(parallel_tasks, 5)
        }
    
    def _is_valid_optimization(self, base_plan: Dict[str, Any], optimized_plan: Dict[str, Any]) -> bool:
        """最適化結果の妥当性チェック"""
        try:
            # 基本的な構造チェック
            required_keys = ["task_id", "subtasks", "execution_order"]
            for key in required_keys:
                if key not in optimized_plan:
                    logger.warning(f"最適化結果に必須キーがありません: {key}")
                    return False
            
            # サブタスク数の比較（大幅な増加は無効）
            base_count = len(base_plan.get("subtasks", []))
            opt_count = len(optimized_plan.get("subtasks", []))
            
            if opt_count > base_count * 1.5:  # 50%以上の増加は無効
                logger.warning(f"サブタスク数が過剰に増加: {base_count} -> {opt_count}")
                return False
            
            # サブタスクの必須フィールドチェック
            for subtask in optimized_plan["subtasks"]:
                required_subtask_keys = ["id", "description", "priority"]
                for key in required_subtask_keys:
                    if key not in subtask:
                        logger.warning(f"サブタスクに必須キーがありません: {key}")
                        return False
                
                # 優先度の値チェック
                if not isinstance(subtask["priority"], int) or not 1 <= subtask["priority"] <= 4:
                    logger.warning(f"無効な優先度値: {subtask['priority']}")
                    return False
            
            # 実行順序の整合性チェック
            subtask_ids = {st["id"] for st in optimized_plan["subtasks"]}
            for order_id in optimized_plan["execution_order"]:
                if order_id not in subtask_ids:
                    logger.warning(f"実行順序に存在しないタスクID: {order_id}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"最適化検証エラー: {str(e)}")
            return False
    
    def _create_fallback_plan(self, user_input: str, intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """フォールバック計画の生成"""
        task_id = f"fallback_{str(uuid.uuid4())[:8]}"
        
        return {
            "task_id": task_id,
            "overview": "基本的な応答計画",
            "subtasks": [
                {
                    "id": f"{task_id}_main",
                    "description": f"ユーザーの質問「{user_input}」に対して直接回答する",
                    "tool_name": None,
                    "parameters": {},
                    "dependencies": [],
                    "priority": 2,
                    "estimated_duration": 30,
                    "success_criteria": "適切な回答が生成される",
                    "fallback_strategy": "簡潔な回答に変更"
                }
            ],
            "execution_order": [f"{task_id}_main"],
            "parallel_groups": [],
            "estimated_duration": 30,
            "success_criteria": ["ユーザーの質問に回答できる"],
            "risk_factors": ["複雑な要求の場合、回答が不十分になる可能性"],
            "contingency_plans": ["追加質問での詳細化"]
        }
    
    def _load_available_tools(self) -> Dict[str, MCPTool]:
        """利用可能ツールの定義読み込み"""
        return {
            "file_operations": MCPTool(
                name="file_operations",
                server_path="./mcp-servers/file-operations",
                description="ファイル読み書き、検索、管理操作",
                parameters={"base_path": "./workspace"}
            ),
            "web_search": MCPTool(
                name="web_search",
                server_path="./mcp-servers/web-search",
                description="インターネット検索とウェブスクレイピング",
                parameters={"max_results": 10}
            ),
            "code_execution": MCPTool(
                name="code_execution",
                server_path="./mcp-servers/code-executor",
                description="Python/Node.jsコード実行と結果取得",
                parameters={"timeout": 60}
            ),
            "data_analysis": MCPTool(
                name="data_analysis",
                server_path="./mcp-servers/data-analyzer",
                description="データ分析、統計処理、可視化",
                parameters={"output_format": "json"}
            ),
            "text_processing": MCPTool(
                name="text_processing",
                server_path="./mcp-servers/text-processor",
                description="テキスト処理、要約、翻訳",
                parameters={"max_length": 10000}
            )
        } 