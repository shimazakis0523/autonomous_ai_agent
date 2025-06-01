"""
自律型AIエージェント - 意図分析エンジン
フェーズ2: ユーザー意図の理解と分類
トレーシング機能付き
"""
import json
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from ..core.agent_state import AgentState, AgentPhase, add_error_context

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """意図理解・分析エンジン（トレーシング対応）"""
    
    def __init__(self, llm: ChatOpenAI, trace_logger=None):
        """
        初期化
        
        Args:
            llm: ChatOpenAI インスタンス
            trace_logger: トレーシングロガー（オプション）
        """
        self.llm = llm
        self.trace_logger = trace_logger
        self.intent_categories = [
            "information_request",    # 情報要求
            "task_execution",        # タスク実行
            "file_operation",        # ファイル操作
            "web_search",           # ウェブ検索
            "calculation",          # 計算処理
            "code_generation",      # コード生成
            "data_analysis",        # データ分析
            "creative_writing",     # 創作
            "conversation",         # 会話
            "system_operation",     # システム操作
            "research_analysis",    # 調査・分析
            "problem_solving"       # 問題解決
        ]
        
        self.complexity_levels = ["low", "medium", "high", "critical"]
        self.expertise_levels = ["beginner", "intermediate", "expert"]
        
        if self.trace_logger:
            self.trace_logger.log_custom_event(
                "INTENT_ANALYZER_INIT",
                "IntentAnalyzer初期化完了",
                {
                    "intent_categories_count": len(self.intent_categories),
                    "complexity_levels": self.complexity_levels,
                    "expertise_levels": self.expertise_levels,
                    "llm_model": getattr(llm, 'model_name', 'unknown')
                }
            )
    
    async def analyze_intent(self, state: AgentState) -> AgentState:
        """
        ユーザー意図の詳細分析
        
        Args:
            state: 現在のエージェント状態
            
        Returns:
            意図分析結果を含む更新された状態
        """
        try:
            user_input = state["user_input"]
            context = self._get_conversation_context(state)
            
            logger.info("意図分析を開始...")
            logger.debug(f"分析対象入力: {user_input}")
            
            # 意図分析の実行
            intent_analysis = await self._perform_intent_analysis(user_input, context)
            logger.debug(f"LLM分析結果: {intent_analysis}")
            
            # 分析結果の検証と補強
            validated_analysis = self._validate_and_enhance_analysis(intent_analysis)
            logger.debug(f"検証済み分析: {validated_analysis}")
            
            # エンティティ抽出
            entities = await self._extract_entities(user_input, validated_analysis)
            validated_analysis["entities"] = entities
            logger.debug(f"抽出されたエンティティ: {entities}")
            
            # リスク評価
            risk_assessment = await self._assess_risks(user_input, validated_analysis)
            validated_analysis["risk_assessment"] = risk_assessment
            logger.debug(f"リスク評価: {risk_assessment}")
            
            logger.info(f"意図分析完了: {validated_analysis['primary_intent']} "
                       f"(信頼度: {validated_analysis['confidence']:.2f})")
            
            # 状態の更新
            updated_state = state.copy()
            updated_state.update({
                "intent_analysis": validated_analysis,
                "current_phase": AgentPhase.PLAN_GENERATION.value,
                "messages": state["messages"] + [
                    AIMessage(content=f"意図を理解しました: {validated_analysis['primary_intent']} "
                                    f"({validated_analysis['complexity']}レベル)")
                ]
            })
            
            return updated_state
            
        except Exception as e:
            logger.error(f"意図分析エラー: {str(e)}")
            import traceback
            logger.error(f"意図分析の詳細エラー: {traceback.format_exc()}")
            return add_error_context(state, "intent_analysis", str(e))
    
    async def _perform_intent_analysis(self, user_input: str, context: str) -> Dict[str, Any]:
        """LLMによる意図分析の実行"""
        try:
            logger.debug("LLM API呼び出しを開始...")
            
            analysis_prompt = f"""
            ユーザーの入力を詳細に分析し、以下の形式で正確なJSONを返してください：

            {{
                "primary_intent": "主要な意図カテゴリ",
                "confidence": 0.95,
                "secondary_intents": ["副次的な意図1", "副次的な意図2"],
                "complexity": "low|medium|high|critical",
                "requires_external_tools": true,
                "estimated_steps": 3,
                "user_expertise": "beginner|intermediate|expert",
                "urgency": "low|medium|high",
                "scope": "personal|business|academic|technical",
                "output_format_preference": "text|structured|visual|code"
            }}

            **対話文脈:**
            {context}

            **ユーザー入力:**
            {user_input}

            **利用可能な意図カテゴリ:**
            {', '.join(self.intent_categories)}

            **分析観点:**
            1. 明示的な要求内容の特定
            2. 暗黙的なニーズの推測
            3. 実行に必要なリソースの評価
            4. ユーザーの専門レベルの推定
            5. 緊急度と重要度の評価

            必ず有効なJSONのみを返してください。
            """
            
            messages = [
                SystemMessage(content="あなたは高度な意図分析AI専門家です。ユーザーの真のニーズを正確に理解し、実行可能な分析を提供してください。"),
                HumanMessage(content=analysis_prompt)
            ]
            
            logger.debug(f"LLMに送信するメッセージ数: {len(messages)}")
            
            response = await self.llm.ainvoke(messages)
            logger.debug(f"LLM応答受信: {response.content[:200]}...")
            
            try:
                intent_analysis = json.loads(response.content)
                logger.debug("JSON解析成功")
                return intent_analysis
            except json.JSONDecodeError as e:
                logger.warning(f"JSON解析エラー、再試行します: {str(e)}")
                logger.warning(f"元の応答: {response.content}")
                
                # JSONブロックを抽出して再試行
                content = response.content
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    if end > start:
                        json_content = content[start:end].strip()
                        try:
                            intent_analysis = json.loads(json_content)
                            logger.info("JSONブロック抽出で解析成功")
                            return intent_analysis
                        except json.JSONDecodeError:
                            pass
                
                # フォールバック: 基本的な分析を提供
                return self._create_fallback_analysis(user_input)
                
        except Exception as e:
            logger.error(f"LLM呼び出しエラー: {str(e)}")
            import traceback
            logger.error(f"LLM呼び出しの詳細エラー: {traceback.format_exc()}")
            
            # フォールバック分析を返す
            return self._create_fallback_analysis(user_input)
    
    def _get_conversation_context(self, state: AgentState) -> str:
        """会話履歴から文脈を抽出"""
        messages = state["messages"][-5:]  # 直近5メッセージ
        context = ""
        
        for msg in messages:
            if isinstance(msg, HumanMessage):
                context += f"ユーザー: {msg.content[:100]}...\n"
            elif isinstance(msg, AIMessage):
                context += f"AI: {msg.content[:100]}...\n"
        
        if not context:
            context = "初回の対話です。"
        
        return context
    
    def _validate_and_enhance_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """意図分析結果の検証と補強"""
        # 必須フィールドの確認
        required_fields = [
            "primary_intent", "confidence", "complexity", 
            "requires_external_tools", "estimated_steps"
        ]
        
        for field in required_fields:
            if field not in analysis:
                logger.warning(f"必須フィールドが不足: {field}")
                analysis[field] = self._get_default_value(field)
        
        # 値の範囲チェック
        if analysis["confidence"] < 0.0 or analysis["confidence"] > 1.0:
            analysis["confidence"] = max(0.0, min(1.0, analysis["confidence"]))
        
        if analysis["confidence"] < 0.3:
            logger.warning("信頼度が低いため、基本的な分析にフォールバック")
            analysis = self._create_fallback_analysis("")
        
        # カテゴリの検証
        if analysis["primary_intent"] not in self.intent_categories:
            logger.warning(f"不明な意図カテゴリ: {analysis['primary_intent']}")
            analysis["primary_intent"] = "conversation"
        
        # 複雑度の検証
        if analysis["complexity"] not in self.complexity_levels:
            analysis["complexity"] = "medium"
        
        # タイムスタンプの追加
        analysis["analyzed_at"] = datetime.now().isoformat()
        
        return analysis
    
    async def _extract_entities(self, user_input: str, intent_analysis: Dict[str, Any]) -> Dict[str, List[str]]:
        """エンティティの抽出"""
        entity_prompt = f"""
        以下のユーザー入力から重要なエンティティを抽出してください：

        ユーザー入力: {user_input}
        意図: {intent_analysis['primary_intent']}

        以下の形式でJSONを返してください：
        {{
            "targets": ["操作対象1", "操作対象2"],
            "actions": ["実行アクション1", "実行アクション2"],
            "constraints": ["制約条件1", "制約条件2"],
            "parameters": ["パラメータ1", "パラメータ2"],
            "locations": ["場所1", "場所2"],
            "timeframes": ["時間枠1", "時間枠2"]
        }}
        """
        
        try:
            messages = [
                SystemMessage(content="あなたはエンティティ抽出の専門家です。"),
                HumanMessage(content=entity_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            entities = json.loads(response.content)
            
            return entities
            
        except Exception as e:
            logger.warning(f"エンティティ抽出エラー: {str(e)}")
            return {
                "targets": [],
                "actions": [],
                "constraints": [],
                "parameters": [],
                "locations": [],
                "timeframes": []
            }
    
    async def _assess_risks(self, user_input: str, intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """リスク評価の実行"""
        risk_factors = []
        risk_level = "low"
        
        # 基本的なリスク評価ロジック
        high_risk_keywords = [
            "削除", "フォーマット", "reset", "destroy", "remove", 
            "システム", "管理者", "root", "sudo"
        ]
        
        medium_risk_keywords = [
            "変更", "編集", "update", "modify", "install", "download"
        ]
        
        for keyword in high_risk_keywords:
            if keyword in user_input.lower():
                risk_factors.append(f"高リスクキーワード検出: {keyword}")
                risk_level = "high"
        
        for keyword in medium_risk_keywords:
            if keyword in user_input.lower():
                risk_factors.append(f"中リスクキーワード検出: {keyword}")
                if risk_level == "low":
                    risk_level = "medium"
        
        # 複雑度に基づくリスク評価
        if intent_analysis["complexity"] == "critical":
            risk_factors.append("複雑度が極めて高い")
            risk_level = "high"
        elif intent_analysis["complexity"] == "high":
            risk_factors.append("複雑度が高い")
            if risk_level == "low":
                risk_level = "medium"
        
        return {
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "mitigation_required": risk_level in ["medium", "high"],
            "approval_required": risk_level == "high"
        }
    
    def _create_fallback_analysis(self, user_input: str) -> Dict[str, Any]:
        """フォールバック用の基本分析"""
        return {
            "primary_intent": "conversation",
            "confidence": 0.5,
            "secondary_intents": [],
            "complexity": "medium",
            "requires_external_tools": False,
            "estimated_steps": 1,
            "user_expertise": "intermediate",
            "urgency": "low",
            "scope": "personal",
            "output_format_preference": "text",
            "fallback_analysis": True,
            "analyzed_at": datetime.now().isoformat()
        }
    
    def _get_default_value(self, field: str) -> Any:
        """フィールドのデフォルト値を取得"""
        defaults = {
            "primary_intent": "conversation",
            "confidence": 0.5,
            "complexity": "medium",
            "requires_external_tools": False,
            "estimated_steps": 1,
            "user_expertise": "intermediate",
            "urgency": "low",
            "scope": "personal",
            "output_format_preference": "text"
        }
        return defaults.get(field, None) 