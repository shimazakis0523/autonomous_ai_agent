"""
自律型AIエージェント - コアレイヤ
エージェントの基本状態管理と中核システム
"""

from .agent_state import AgentState, AgentPhase, create_initial_state
from .autonomous_agent import AutonomousAgent

__all__ = [
    "AgentState",
    "AgentPhase", 
    "create_initial_state",
    "AutonomousAgent"
] 