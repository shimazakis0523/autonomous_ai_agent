"""
自律型AIエージェント - 応答生成エンジン
フェーズ7: ユーザー向け最終応答の生成
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


class ResponseGenerator:
    """応答生成エンジン"""
    
    def __init__(self, llm: ChatOpenAI, trace_logger=None):
        """
        応答生成エンジンの初期化
        
        Args:
            llm: 言語モデルインスタンス
            trace_logger: トレーシングロガー（オプション）
        """
        self.llm = llm
        self.trace_logger = trace_logger
        self.max_response_length = 2000
        self.min_response_length = 50
        
        # 応答スタイル設定
        self.response_styles = {
            "professional": {
                "tone": "丁寧で専門的",
                "format": "構造化された説明",
                "emoji_usage": "控えめ"
            },
            "friendly": {
                "tone": "親しみやすく分かりやすい",
                "format": "会話的な説明",
                "emoji_usage": "適度に使用"
            },
            "technical": {
                "tone": "技術的で詳細",
                "format": "コードや例を含む",
                "emoji_usage": "最小限"
            },
            "educational": {
                "tone": "教育的で段階的",
                "format": "ステップバイステップ",
                "emoji_usage": "理解を助ける程度"
            }
        }
        
        # 品質チェック項目
        self.quality_checks = [
            "completeness_check",    # 完全性
            "accuracy_check",        # 正確性
            "relevance_check",       # 関連性
            "clarity_check",         # 明確性
            "tone_consistency_check" # トーン一貫性
        ]
        
        if self.trace_logger:
            self.trace_logger.log_custom_event(
                "RESPONSE_GENERATOR_INIT",
                "ResponseGenerator初期化完了",
                {
                    "response_styles": list(self.response_styles.keys()),
                    "quality_checks": self.quality_checks,
                    "llm_model": getattr(llm, 'model_name', 'unknown')
                }
            )
        
    async def generate_response(self, state: AgentState) -> AgentState:
        """
        最終ユーザー応答の生成
        
        Args:
            state: 現在のエージェント状態
            
        Returns:
            最終応答を含む更新された状態
        """
        try:
            processed_result = state.get("processed_result", {})
            
            if not processed_result:
                logger.warning("処理済み結果がありません")
                return self._create_fallback_response(state)
            
            logger.info("最終応答を生成中...")
            
            # 1. 応答スタイルの決定
            response_style = self._determine_response_style(state)
            
            # 2. 主要応答の生成
            main_response = await self._generate_main_response(state, response_style)
            
            # 3. 補足情報の生成
            supplementary_info = self._generate_supplementary_info(state)
            
            # 4. 応答の最適化
            optimized_response = await self._optimize_response(main_response, state)
            
            # 5. 最終応答の構築
            final_response = self._build_final_response(
                optimized_response, supplementary_info, state
            )
            
            # 6. ユーザーへの出力
            self._display_response_to_user(final_response)
            
            logger.info("応答生成完了")
            
            # 状態の更新
            updated_state = state.copy()
            updated_state.update({
                "final_response": final_response,
                "current_phase": AgentPhase.COMPLETED.value,
                "messages": state["messages"] + [
                    AIMessage(content=final_response["main_content"])
                ]
            })
            
            return updated_state
            
        except Exception as e:
            logger.error(f"応答生成エラー: {str(e)}")
            return add_error_context(state, "response_generation", str(e))
    
    def _determine_response_style(self, state: AgentState) -> Dict[str, Any]:
        """応答スタイルの決定"""
        intent_analysis = state.get("intent_analysis", {})
        confidence_assessment = state.get("processed_result", {}).get("confidence_assessment", {})
        
        # 基本スタイル設定
        style = {
            "tone": "professional",  # professional, casual, technical
            "detail_level": "medium",  # brief, medium, detailed
            "format": "structured",  # narrative, structured, bullet_points
            "include_confidence": True,
            "include_next_steps": True
        }
        
        # 意図に基づくスタイル調整
        primary_intent = intent_analysis.get("primary_intent", "conversation")
        user_expertise = intent_analysis.get("user_expertise", "intermediate")
        
        if primary_intent == "code_generation":
            style["format"] = "code_focused"
            style["detail_level"] = "detailed"
            
        elif primary_intent == "conversation":
            style["tone"] = "casual"
            style["format"] = "narrative"
            
        elif primary_intent in ["data_analysis", "research_analysis"]:
            style["tone"] = "technical"
            style["detail_level"] = "detailed"
            style["format"] = "structured"
        
        # 専門レベルに基づく調整
        if user_expertise == "beginner":
            style["detail_level"] = "detailed"
            style["tone"] = "educational"
        elif user_expertise == "expert":
            style["detail_level"] = "brief"
            style["tone"] = "technical"
        
        # 信頼度に基づく調整
        confidence = confidence_assessment.get("overall_confidence", 0.5)
        if confidence < 0.5:
            style["include_confidence"] = True
            style["include_disclaimers"] = True
        
        return style
    
    async def _generate_main_response(self, state: AgentState, 
                                    response_style: Dict[str, Any]) -> str:
        """主要応答の生成"""
        user_input = state["user_input"]
        processed_result = state["processed_result"]
        intent_analysis = state.get("intent_analysis", {})
        
        # 統合された発見と洞察の抽出
        integrated_findings = processed_result.get("integrated_findings", {})
        insights = processed_result.get("insights_and_analysis", {})
        confidence_assessment = processed_result.get("confidence_assessment", {})
        
        # プロンプトの構築
        response_prompt = self._build_response_prompt(
            user_input, integrated_findings, insights, confidence_assessment, 
            intent_analysis, response_style
        )
        
        try:
            messages = [
                SystemMessage(content=self._get_system_prompt(response_style)),
                HumanMessage(content=response_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            main_response = response.content
            
            # 応答長の確認
            if len(main_response) < self.min_response_length:
                logger.warning("応答が短すぎます。詳細化を試行")
                main_response = await self._expand_response(main_response, state)
            elif len(main_response) > self.max_response_length:
                logger.warning("応答が長すぎます。要約を試行")
                main_response = await self._summarize_response(main_response, state)
            
            return main_response
            
        except Exception as e:
            logger.warning(f"主要応答生成に失敗: {str(e)}")
            return self._create_basic_response(integrated_findings, user_input)
    
    def _build_response_prompt(self, user_input: str, integrated_findings: Dict[str, Any],
                             insights: Dict[str, Any], confidence_assessment: Dict[str, Any],
                             intent_analysis: Dict[str, Any], response_style: Dict[str, Any]) -> str:
        """応答生成プロンプトの構築"""
        
        main_findings = integrated_findings.get("main_findings", [])
        key_insights = insights.get("key_insights", [])
        confidence = confidence_assessment.get("overall_confidence", 0.5)
        reliability_level = confidence_assessment.get("reliability_level", "中信頼度")
        
        prompt = f"""
ユーザーの質問に対して、以下の分析結果に基づいて包括的で有用な回答を生成してください：

**ユーザーの質問:**
{user_input}

**主要な発見:**
{chr(10).join(f"• {finding}" for finding in main_findings)}

**重要な洞察:**
{chr(10).join(f"• {insight}" for insight in key_insights)}

**信頼度情報:**
- 全体信頼度: {confidence:.1%}
- 信頼性レベル: {reliability_level}

**応答スタイル指示:**
- トーン: {response_style.get('tone', 'professional')}
- 詳細レベル: {response_style.get('detail_level', 'medium')}
- フォーマット: {response_style.get('format', 'structured')}

**応答要件:**
1. ユーザーの質問に直接答える
2. 主要な発見を分かりやすく説明する
3. 実用的な洞察や推奨事項を提供する
4. 必要に応じて制限事項や注意点を明記する
5. 自然で読みやすい文章にする

専門的で正確、かつユーザーにとって価値のある回答を提供してください。
        """
        
        return prompt.strip()
    
    def _get_system_prompt(self, response_style: Dict[str, Any]) -> str:
        """システムプロンプトの取得"""
        base_prompt = "あなたは高度なAIアシスタントです。"
        
        tone = response_style.get("tone", "professional")
        if tone == "technical":
            base_prompt += "技術的に正確で詳細な情報を提供し、専門用語を適切に使用してください。"
        elif tone == "casual":
            base_prompt += "親しみやすく、分かりやすい言葉で説明してください。"
        elif tone == "educational":
            base_prompt += "教育的で段階的な説明を心がけ、初心者にも理解しやすくしてください。"
        else:
            base_prompt += "専門的で信頼性が高く、明確で簡潔な回答を提供してください。"
        
        base_prompt += "ユーザーの真のニーズを理解し、実行可能で価値のある情報を提供することを最優先にしてください。"
        
        return base_prompt
    
    async def _optimize_response(self, main_response: str, state: AgentState) -> str:
        """応答の最適化"""
        # 基本的な最適化ルール
        
        # 1. 冗長性の除去
        optimized = self._remove_redundancy(main_response)
        
        # 2. 構造の改善
        optimized = self._improve_structure(optimized)
        
        # 3. 読みやすさの向上
        optimized = self._improve_readability(optimized)
        
        return optimized
    
    def _generate_supplementary_info(self, state: AgentState) -> Dict[str, Any]:
        """補足情報の生成"""
        processed_result = state.get("processed_result", {})
        confidence_assessment = processed_result.get("confidence_assessment", {})
        execution_summary = state.get("task_results", {}).get("execution_summary", {})
        
        supplementary = {}
        
        # 信頼度情報
        if confidence_assessment:
            confidence = confidence_assessment.get("overall_confidence", 0)
            reliability = confidence_assessment.get("reliability_level", "不明")
            supplementary["confidence_info"] = {
                "level": f"{confidence:.1%}",
                "reliability": reliability,
                "recommendation": confidence_assessment.get("recommendation", "")
            }
        
        # 実行統計
        if execution_summary:
            supplementary["execution_stats"] = {
                "total_tasks": execution_summary.get("total_tasks", 0),
                "success_rate": f"{execution_summary.get('success_rate', 0):.1%}",
                "execution_time": f"{execution_summary.get('execution_time', 0):.1f}秒"
            }
        
        # 次のステップの提案
        intent_analysis = state.get("intent_analysis", {})
        if intent_analysis.get("complexity") in ["high", "critical"]:
            supplementary["next_steps"] = [
                "結果の詳細確認",
                "追加の分析検討",
                "専門家への相談"
            ]
        else:
            supplementary["next_steps"] = [
                "追加質問があれば遠慮なくどうぞ",
                "他の関連トピックについても質問可能"
            ]
        
        return supplementary
    
    def _build_final_response(self, main_response: str, supplementary_info: Dict[str, Any],
                            state: AgentState) -> Dict[str, Any]:
        """最終応答の構築"""
        confidence_info = supplementary_info.get("confidence_info", {})
        
        return {
            "main_content": main_response,
            "confidence_level": confidence_info.get("level", "不明"),
            "reliability": confidence_info.get("reliability", "不明"),
            "execution_stats": supplementary_info.get("execution_stats", {}),
            "next_steps": supplementary_info.get("next_steps", []),
            "generated_at": datetime.now().isoformat(),
            "response_type": "comprehensive_analysis",
            "metadata": {
                "user_input": state["user_input"],
                "session_id": state["session_metadata"]["session_id"],
                "processing_time": self._calculate_total_processing_time(state)
            }
        }
    
    def _display_response_to_user(self, final_response: Dict[str, Any]) -> None:
        """ユーザーへの応答表示"""
        print("\n" + "="*80)
        print("🤖 自律型AIエージェント - 回答")
        print("="*80)
        
        # メイン応答
        print(final_response["main_content"])
        
        # 信頼度情報
        if final_response.get("confidence_level"):
            print(f"\n📊 信頼度: {final_response['confidence_level']} ({final_response.get('reliability', 'N/A')})")
        
        # 実行統計
        exec_stats = final_response.get("execution_stats", {})
        if exec_stats:
            print(f"\n⚡ 実行統計:")
            print(f"   • 処理タスク数: {exec_stats.get('total_tasks', 'N/A')}")
            print(f"   • 成功率: {exec_stats.get('success_rate', 'N/A')}")
            print(f"   • 実行時間: {exec_stats.get('execution_time', 'N/A')}")
        
        # 次のステップ
        next_steps = final_response.get("next_steps", [])
        if next_steps:
            print(f"\n💡 次のステップ:")
            for step in next_steps:
                print(f"   • {step}")
        
        print("\n" + "="*80)
    
    def _remove_redundancy(self, text: str) -> str:
        """冗長性の除去"""
        # 同じ文の繰り返しを除去（簡単な実装）
        sentences = text.split('。')
        unique_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and sentence not in unique_sentences:
                unique_sentences.append(sentence)
        
        return '。'.join(unique_sentences)
    
    def _improve_structure(self, text: str) -> str:
        """構造の改善"""
        # 段落の整理（簡単な実装）
        lines = text.split('\n')
        improved_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                improved_lines.append(line)
        
        return '\n\n'.join(improved_lines)
    
    def _improve_readability(self, text: str) -> str:
        """読みやすさの向上"""
        # 基本的な読みやすさの改善
        improved = text.replace('。\n', '。\n\n')  # 段落間の間隔
        improved = improved.replace('：', ':\n')  # リスト形式の改善
        
        return improved
    
    async def _expand_response(self, short_response: str, state: AgentState) -> str:
        """短い応答の詳細化"""
        expand_prompt = f"""
以下の回答をより詳細で有用なものに拡張してください：

{short_response}

ユーザーの元の質問: {state['user_input']}

詳細な説明、具体例、実用的なアドバイスを追加して、{self.min_response_length}文字以上の包括的な回答にしてください。
        """
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="簡潔な回答を詳細で有用な回答に拡張してください。"),
                HumanMessage(content=expand_prompt)
            ])
            return response.content
        except Exception:
            return short_response  # 拡張に失敗した場合は元の応答を返す
    
    async def _summarize_response(self, long_response: str, state: AgentState) -> str:
        """長い応答の要約"""
        summarize_prompt = f"""
以下の回答を{self.max_response_length}文字以内で要約してください。重要な情報は保持し、簡潔で分かりやすくしてください：

{long_response}
        """
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="長い回答を簡潔で分かりやすく要約してください。"),
                HumanMessage(content=summarize_prompt)
            ])
            return response.content
        except Exception:
            # 要約に失敗した場合は先頭から切り取り
            return long_response[:self.max_response_length] + "..."
    
    def _create_basic_response(self, integrated_findings: Dict[str, Any], user_input: str) -> str:
        """基本的な応答の作成"""
        main_findings = integrated_findings.get("main_findings", [])
        summary = integrated_findings.get("summary", "")
        
        if main_findings:
            response = f"ご質問「{user_input}」について、以下の結果をお伝えします：\n\n"
            for i, finding in enumerate(main_findings[:3], 1):
                response += f"{i}. {finding}\n"
            
            if summary:
                response += f"\n{summary}"
            
            return response
        else:
            return f"ご質問「{user_input}」について処理を行いましたが、明確な結果が得られませんでした。より具体的な質問をしていただけると、より良い回答を提供できます。"
    
    def _create_fallback_response(self, state: AgentState) -> AgentState:
        """フォールバック応答の作成"""
        user_input = state["user_input"]
        
        fallback_response = {
            "main_content": f"ご質問「{user_input}」について処理を試みましたが、十分な結果を得ることができませんでした。申し訳ございません。より具体的な質問や、別の方法でのアプローチをお試しください。",
            "confidence_level": "低",
            "reliability": "要注意",
            "generated_at": datetime.now().isoformat(),
            "response_type": "fallback"
        }
        
        self._display_response_to_user(fallback_response)
        
        updated_state = state.copy()
        updated_state.update({
            "final_response": fallback_response,
            "current_phase": AgentPhase.COMPLETED.value
        })
        
        return updated_state
    
    def _calculate_total_processing_time(self, state: AgentState) -> float:
        """総処理時間の計算"""
        session_start = state["session_metadata"].get("created_at")
        if session_start:
            start_time = datetime.fromisoformat(session_start)
            current_time = datetime.now()
            total_time = (current_time - start_time).total_seconds()
            return total_time
        return 0.0 