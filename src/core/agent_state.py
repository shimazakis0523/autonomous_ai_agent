"""
自律型AIエージェント - データ構造・ステート定義
1クラス1ファイル設計
"""
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class TaskStatus(Enum):
    """タスク実行状態"""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """タスク優先度"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class MCPTool:
    """MCP外部ツール定義"""
    name: str
    server_path: str
    description: str
    parameters: Dict[str, Any]
    timeout: int = 30
    retry_count: int = 3


@dataclass
class SubTask:
    """サブタスク定義"""
    id: str
    description: str
    tool_name: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


@dataclass
class ExecutionPlan:
    """実行計画"""
    task_id: str
    subtasks: List[SubTask]
    execution_order: List[str]
    parallel_groups: List[List[str]]
    estimated_duration: int
    resource_requirements: Dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def get_subtask_by_id(self, task_id: str) -> Optional[SubTask]:
        """IDでサブタスクを取得"""
        return next((st for st in self.subtasks if st.id == task_id), None)
    
    def get_ready_tasks(self, completed_ids: set) -> List[str]:
        """実行可能なタスクIDリストを取得"""
        ready = []
        for subtask in self.subtasks:
            if (subtask.id not in completed_ids and 
                subtask.status == TaskStatus.PENDING and
                all(dep in completed_ids for dep in subtask.dependencies)):
                ready.append(subtask.id)
        return ready


class AgentState(TypedDict):
    """エージェント状態管理"""
    # メッセージ履歴
    messages: Annotated[List[BaseMessage], add_messages]
    
    # ユーザー入力
    user_input: str
    
    # 意図分析結果
    intent_analysis: Dict[str, Any]
    
    # 実行計画
    execution_plan: Optional[ExecutionPlan]
    
    # タスク実行結果
    task_results: Dict[str, Any]
    
    # 処理済み結果
    processed_result: Dict[str, Any]
    
    # 最終応答
    final_response: Dict[str, Any]
    
    # 現在のフェーズ
    current_phase: str
    
    # エラー情報
    error_context: Optional[Dict[str, Any]]
    
    # セッションメタデータ
    session_metadata: Dict[str, Any]
    
    # MCP接続情報
    mcp_connections: Dict[str, Any]


class AgentPhase(Enum):
    """エージェント処理フェーズ"""
    INPUT_PROCESSING = "input_processing"
    INTENT_ANALYSIS = "intent_analysis"
    PLAN_GENERATION = "plan_generation"
    MCP_INITIALIZATION = "mcp_initialization"
    TASK_EXECUTION = "task_execution"
    RESULT_PROCESSING = "result_processing"
    RESPONSE_GENERATION = "response_generation"
    COMPLETED = "completed"
    ERROR_HANDLING = "error_handling"


def create_initial_state(session_id: str = None) -> AgentState:
    """初期状態の作成"""
    if session_id is None:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return {
        "messages": [],
        "user_input": "",
        "intent_analysis": {},
        "execution_plan": None,
        "task_results": {},
        "processed_result": {},
        "final_response": {},
        "current_phase": AgentPhase.INPUT_PROCESSING.value,
        "error_context": None,
        "session_metadata": {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "input_count": 0,
            "last_input_time": None
        },
        "mcp_connections": {}
    }


def update_state_phase(state: AgentState, new_phase: AgentPhase) -> AgentState:
    """状態のフェーズ更新"""
    updated_state = state.copy()
    updated_state["current_phase"] = new_phase.value
    return updated_state


def add_error_context(state: AgentState, phase: str, error: str) -> AgentState:
    """エラー情報の追加"""
    updated_state = state.copy()
    updated_state["error_context"] = {
        "phase": phase,
        "error": error,
        "timestamp": datetime.now().isoformat()
    }
    updated_state["current_phase"] = AgentPhase.ERROR_HANDLING.value
    return updated_state 