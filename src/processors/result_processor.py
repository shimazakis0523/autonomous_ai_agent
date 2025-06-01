"""
自律型AIエージェント - 結果処理エンジン
フェーズ6: タスク実行結果の統合・分析・品質評価
トレーシング機能付き
"""
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from statistics import mean, stdev
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from ..core.agent_state import AgentState, AgentPhase, add_error_context

logger = logging.getLogger(__name__)


class ResultProcessor:
    """結果処理・統合エンジン（トレーシング対応）"""
    
    def __init__(self, llm: ChatOpenAI, trace_logger=None):
        """
        初期化
        
        Args:
            llm: ChatOpenAI インスタンス
            trace_logger: トレーシングロガー（オプション）
        """
        self.llm = llm
        self.trace_logger = trace_logger
        self.max_result_length = 10000
        self.confidence_threshold = 0.7
        
        # 品質評価基準
        self.quality_criteria = {
            "completeness": {"min_score": 0.7, "weight": 0.3},
            "accuracy": {"min_score": 0.8, "weight": 0.3},
            "relevance": {"min_score": 0.75, "weight": 0.25},
            "clarity": {"min_score": 0.7, "weight": 0.15}
        }
        
        if self.trace_logger:
            self.trace_logger.log_custom_event(
                "RESULT_PROCESSOR_INIT",
                "ResultProcessor初期化完了",
                {
                    "quality_criteria": self.quality_criteria,
                    "max_result_length": self.max_result_length,
                    "confidence_threshold": self.confidence_threshold,
                    "llm_model": getattr(llm, 'model_name', 'unknown')
                }
            )
        
    async def process_results(self, state: AgentState) -> AgentState:
        """
        タスク実行結果の処理と推論
        
        Args:
            state: 現在のエージェント状態
            
        Returns:
            処理済み結果を含む更新された状態
        """
        try:
            task_results = state.get("task_results", {})
            
            if not task_results:
                logger.warning("処理する結果がありません")
                return self._create_empty_result(state)
            
            logger.info("結果処理・推論を開始...")
            
            # 1. 結果の検証と品質評価
            validation_result = await self._validate_results(task_results, state)
            
            # 2. 結果の統合と構造化
            integrated_result = await self._integrate_results(task_results, validation_result, state)
            
            # 3. 推論と洞察の生成
            insights = await self._generate_insights(integrated_result, state)
            
            # 4. 信頼度評価
            confidence_assessment = await self._assess_confidence(
                integrated_result, insights, validation_result
            )
            
            # 5. 最終結果の構築
            processed_result = self._build_final_result(
                integrated_result, insights, confidence_assessment, validation_result
            )
            
            logger.info(f"結果処理完了 (信頼度: {confidence_assessment['overall_confidence']:.2f})")
            
            # 状態の更新
            updated_state = state.copy()
            updated_state.update({
                "processed_result": processed_result,
                "current_phase": AgentPhase.RESPONSE_GENERATION.value,
                "messages": state["messages"] + [
                    AIMessage(content="結果の処理と分析が完了しました。最終回答を生成しています...")
                ]
            })
            
            return updated_state
            
        except Exception as e:
            logger.error(f"結果処理エラー: {str(e)}")
            return add_error_context(state, "result_processing", str(e))
    
    async def _validate_results(self, task_results: Dict[str, Any], 
                              state: AgentState) -> Dict[str, Any]:
        """結果の検証と品質評価"""
        logger.info("結果の検証を実行中...")
        
        execution_summary = task_results.get("execution_summary", {})
        key_results = task_results.get("key_results", [])
        failure_analysis = task_results.get("failure_analysis", [])
        
        # 基本統計の分析
        total_tasks = execution_summary.get("total_tasks", 0)
        completed_tasks = execution_summary.get("completed_tasks", 0)
        success_rate = execution_summary.get("success_rate", 0)
        
        # 品質スコアの計算
        quality_metrics = {
            "completion_rate": success_rate,
            "result_comprehensiveness": self._assess_comprehensiveness(key_results),
            "result_consistency": await self._assess_consistency(key_results, state),
            "error_severity": self._assess_error_severity(failure_analysis)
        }
        
        # 総合品質スコア
        overall_quality = (
            quality_metrics["completion_rate"] * 0.3 +
            quality_metrics["result_comprehensiveness"] * 0.3 +
            quality_metrics["result_consistency"] * 0.3 +
            (1 - quality_metrics["error_severity"]) * 0.1
        )
        
        return {
            "quality_metrics": quality_metrics,
            "overall_quality": overall_quality,
            "validation_timestamp": datetime.now().isoformat(),
            "issues_found": self._identify_issues(quality_metrics, failure_analysis),
            "recommendations": self._generate_recommendations(quality_metrics, failure_analysis)
        }
    
    async def _integrate_results(self, task_results: Dict[str, Any], 
                               validation_result: Dict[str, Any], 
                               state: AgentState) -> Dict[str, Any]:
        """結果の統合と構造化"""
        logger.info("結果の統合を実行中...")
        
        user_input = state["user_input"]
        intent_analysis = state.get("intent_analysis", {})
        key_results = task_results.get("key_results", [])
        
        # LLMによる結果統合
        integration_prompt = f"""
        以下のタスク実行結果を統合し、ユーザーの要求に対する包括的な回答を構築してください：

        **ユーザーの元の要求:**
        {user_input}

        **意図分析:**
        - 主要意図: {intent_analysis.get('primary_intent', 'N/A')}
        - 複雑度: {intent_analysis.get('complexity', 'N/A')}

        **実行結果:**
        {self._format_results_for_integration(key_results)}

        **品質評価:**
        - 全体品質: {validation_result.get('overall_quality', 0):.2f}
        - 完了率: {validation_result.get('quality_metrics', {}).get('completion_rate', 0):.2f}

        以下の形式で統合結果を返してください：
        {{
            "main_findings": ["主要な発見や結果1", "主要な発見や結果2"],
            "supporting_evidence": ["根拠や詳細情報1", "根拠や詳細情報2"],
            "limitations": ["制限事項や注意点1", "制限事項や注意点2"],
            "actionable_items": ["実行可能な提案1", "実行可能な提案2"],
            "summary": "統合結果の要約"
        }}

        有効なJSONのみを返してください。
        """
        
        try:
            messages = [
                SystemMessage(content="あなたは結果統合の専門家です。複数のタスク結果を論理的に統合し、有用な洞察を提供してください。"),
                HumanMessage(content=integration_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # JSON解析
            integrated_data = json.loads(response.content)
            
            # 統合メタデータの追加
            integrated_data.update({
                "integration_timestamp": datetime.now().isoformat(),
                "source_task_count": len(key_results),
                "integration_method": "llm_synthesis"
            })
            
            return integrated_data
            
        except Exception as e:
            logger.warning(f"LLM統合に失敗、フォールバック使用: {str(e)}")
            
            # JSONブロック抽出を試行
            try:
                content = response.content
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    if end > start:
                        json_content = content[start:end].strip()
                        integrated_data = json.loads(json_content)
                        integrated_data.update({
                            "integration_timestamp": datetime.now().isoformat(),
                            "source_task_count": len(key_results),
                            "integration_method": "llm_synthesis_extracted"
                        })
                        logger.info("JSONブロック抽出で統合成功")
                        return integrated_data
            except Exception:
                pass
            
            return self._create_fallback_integration(key_results, user_input)
    
    async def _generate_insights(self, integrated_result: Dict[str, Any], 
                               state: AgentState) -> Dict[str, Any]:
        """推論と洞察の生成"""
        logger.info("洞察の生成を実行中...")
        
        user_input = state["user_input"]
        main_findings = integrated_result.get("main_findings", [])
        
        insight_prompt = f"""
        以下の統合結果から深い洞察と推論を生成してください：

        **ユーザーの要求:** {user_input}

        **主要な発見:**
        {chr(10).join(f"- {finding}" for finding in main_findings)}

        **統合結果:**
        {integrated_result.get('summary', '')}

        以下の観点から洞察を生成してください：
        1. パターンや傾向の特定
        2. 因果関係の分析
        3. 潜在的な影響や含意
        4. 将来の展望や予測
        5. 意外な発見や気付き

        以下の形式で返してください：
        {{
            "key_insights": ["洞察1", "洞察2", "洞察3"],
            "patterns_identified": ["パターン1", "パターン2"],
            "implications": ["含意1", "含意2"],
            "future_considerations": ["将来の検討事項1", "将来の検討事項2"],
            "confidence_indicators": ["信頼度を示す要因1", "信頼度を示す要因2"]
        }}

        有効なJSONのみを返してください。
        """
        
        try:
            messages = [
                SystemMessage(content="あなたは洞察生成の専門家です。データから深い理解と有用な推論を導き出してください。"),
                HumanMessage(content=insight_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            insights = json.loads(response.content)
            
            insights.update({
                "generation_timestamp": datetime.now().isoformat(),
                "insight_quality": self._assess_insight_quality(insights)
            })
            
            return insights
            
        except Exception as e:
            logger.warning(f"洞察生成に失敗、基本分析使用: {str(e)}")
            return self._create_basic_insights(main_findings)
    
    async def _assess_confidence(self, integrated_result: Dict[str, Any], 
                               insights: Dict[str, Any], 
                               validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """信頼度評価"""
        logger.info("信頼度評価を実行中...")
        
        # 各要素の信頼度評価
        data_quality_confidence = validation_result.get("overall_quality", 0.5)
        integration_confidence = self._assess_integration_confidence(integrated_result)
        insight_confidence = insights.get("insight_quality", 0.5)
        
        # 全体的な信頼度計算
        overall_confidence = (
            data_quality_confidence * 0.4 +
            integration_confidence * 0.3 +
            insight_confidence * 0.3
        )
        
        # 信頼度要因の分析
        confidence_factors = []
        if data_quality_confidence > 0.8:
            confidence_factors.append("高品質なデータソース")
        if integration_confidence > 0.7:
            confidence_factors.append("一貫性のある統合結果")
        if insight_confidence > 0.7:
            confidence_factors.append("信頼性の高い洞察")
        
        # 懸念事項の特定
        concerns = []
        if data_quality_confidence < 0.5:
            concerns.append("データ品質に課題")
        if integration_confidence < 0.5:
            concerns.append("統合結果に不整合")
        if overall_confidence < self.confidence_threshold:
            concerns.append("全体的信頼度が閾値未満")
        
        return {
            "overall_confidence": overall_confidence,
            "component_confidence": {
                "data_quality": data_quality_confidence,
                "integration": integration_confidence,
                "insights": insight_confidence
            },
            "confidence_factors": confidence_factors,
            "concerns": concerns,
            "reliability_level": self._categorize_reliability(overall_confidence),
            "assessment_timestamp": datetime.now().isoformat()
        }
    
    def _build_final_result(self, integrated_result: Dict[str, Any], 
                          insights: Dict[str, Any], 
                          confidence_assessment: Dict[str, Any], 
                          validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """最終結果の構築"""
        return {
            "integrated_findings": integrated_result,
            "insights_and_analysis": insights,
            "confidence_assessment": confidence_assessment,
            "quality_validation": validation_result,
            "processing_metadata": {
                "processed_at": datetime.now().isoformat(),
                "processing_quality": "high" if confidence_assessment["overall_confidence"] > 0.7 else "medium",
                "recommendation": self._generate_usage_recommendation(confidence_assessment)
            }
        }
    
    def _assess_comprehensiveness(self, key_results: List[Dict]) -> float:
        """結果の包括性評価"""
        if not key_results:
            return 0.0
        
        # 結果の多様性と詳細度を評価
        total_content_length = sum(len(str(result.get("result", ""))) for result in key_results)
        avg_content_length = total_content_length / len(key_results)
        
        # 正規化スコア (1000文字を基準とする)
        comprehensiveness = min(avg_content_length / 1000, 1.0)
        
        return comprehensiveness
    
    async def _assess_consistency(self, key_results: List[Dict], state: AgentState) -> float:
        """結果の一貫性評価"""
        if len(key_results) < 2:
            return 1.0  # 単一結果は一貫性問題なし
        
        # 簡単な一貫性チェック（実装を簡略化）
        # 実際にはより高度な自然言語処理やベクトル類似度を使用
        
        result_texts = [str(result.get("result", "")) for result in key_results]
        
        # 長さの一貫性チェック
        avg_length = sum(len(text) for text in result_texts) / len(result_texts)
        length_variance = sum((len(text) - avg_length) ** 2 for text in result_texts) / len(result_texts)
        length_consistency = 1.0 / (1.0 + length_variance / 1000)  # 正規化
        
        return min(length_consistency, 1.0)
    
    def _assess_error_severity(self, failure_analysis: List[Dict]) -> float:
        """エラーの重要度評価"""
        if not failure_analysis:
            return 0.0
        
        critical_errors = 0
        for failure in failure_analysis:
            error_msg = failure.get("error", "").lower()
            if any(keyword in error_msg for keyword in ["critical", "fatal", "security", "authentication"]):
                critical_errors += 1
        
        severity_ratio = critical_errors / len(failure_analysis)
        return severity_ratio
    
    def _identify_issues(self, quality_metrics: Dict, failure_analysis: List[Dict]) -> List[str]:
        """品質問題の特定"""
        issues = []
        
        if quality_metrics["completion_rate"] < 0.5:
            issues.append("タスク完了率が低い")
        
        if quality_metrics["result_comprehensiveness"] < 0.3:
            issues.append("結果の詳細度が不足")
        
        if quality_metrics["result_consistency"] < 0.5:
            issues.append("結果に一貫性の問題")
        
        if quality_metrics["error_severity"] > 0.3:
            issues.append("重要なエラーが発生")
        
        return issues
    
    def _generate_recommendations(self, quality_metrics: Dict, failure_analysis: List[Dict]) -> List[str]:
        """改善推奨事項の生成"""
        recommendations = []
        
        if quality_metrics["completion_rate"] < 0.7:
            recommendations.append("タスクの複雑度を下げるか、分割を検討")
        
        if quality_metrics["result_comprehensiveness"] < 0.5:
            recommendations.append("より詳細な分析パラメータの設定を推奨")
        
        if failure_analysis:
            recommendations.append("失敗タスクの再実行または代替手法を検討")
        
        return recommendations
    
    def _format_results_for_integration(self, key_results: List[Dict]) -> str:
        """統合用の結果フォーマット"""
        if not key_results:
            return "実行結果なし"
        
        formatted = []
        for i, result in enumerate(key_results[:5], 1):  # 最大5件
            task_desc = result.get("description", "N/A")[:100]
            result_content = str(result.get("result", ""))[:200]
            formatted.append(f"{i}. {task_desc}\n   結果: {result_content}")
        
        return "\n".join(formatted)
    
    def _create_fallback_integration(self, key_results: List[Dict], user_input: str) -> Dict[str, Any]:
        """フォールバック統合結果"""
        main_findings = []
        for result in key_results[:3]:
            if result.get("result"):
                main_findings.append(f"タスク「{result.get('description', 'N/A')[:50]}」の実行結果")
        
        return {
            "main_findings": main_findings or ["基本的な処理を実行しました"],
            "supporting_evidence": ["タスク実行ログ", "処理結果データ"],
            "limitations": ["部分的な結果のみ", "詳細分析は制限的"],
            "actionable_items": ["結果の詳細確認を推奨"],
            "summary": f"ユーザーの要求「{user_input[:100]}」に対して基本的な処理を実行しました。",
            "integration_timestamp": datetime.now().isoformat(),
            "source_task_count": len(key_results),
            "integration_method": "fallback_basic"
        }
    
    def _create_basic_insights(self, main_findings: List[str]) -> Dict[str, Any]:
        """基本的な洞察生成"""
        return {
            "key_insights": main_findings[:3] if main_findings else ["基本的な処理を完了"],
            "patterns_identified": ["標準的な処理パターン"],
            "implications": ["要求に応じた基本対応"],
            "future_considerations": ["より詳細な分析の検討"],
            "confidence_indicators": ["基本処理の完了"],
            "generation_timestamp": datetime.now().isoformat(),
            "insight_quality": 0.5
        }
    
    def _assess_integration_confidence(self, integrated_result: Dict[str, Any]) -> float:
        """統合結果の信頼度評価"""
        # 統合結果の完全性を評価
        required_fields = ["main_findings", "supporting_evidence", "summary"]
        completeness = sum(1 for field in required_fields if integrated_result.get(field)) / len(required_fields)
        
        # 内容の充実度を評価
        content_richness = 0.5
        if integrated_result.get("main_findings") and len(integrated_result["main_findings"]) > 2:
            content_richness = 0.8
        if integrated_result.get("actionable_items"):
            content_richness = min(content_richness + 0.2, 1.0)
        
        return (completeness + content_richness) / 2
    
    def _assess_insight_quality(self, insights: Dict[str, Any]) -> float:
        """洞察の品質評価"""
        quality_score = 0.5
        
        if insights.get("key_insights") and len(insights["key_insights"]) >= 3:
            quality_score += 0.2
        
        if insights.get("patterns_identified"):
            quality_score += 0.15
        
        if insights.get("implications"):
            quality_score += 0.15
        
        return min(quality_score, 1.0)
    
    def _categorize_reliability(self, confidence: float) -> str:
        """信頼度のカテゴリ化"""
        if confidence >= 0.8:
            return "高信頼度"
        elif confidence >= 0.6:
            return "中信頼度"
        elif confidence >= 0.4:
            return "低信頼度"
        else:
            return "要注意"
    
    def _generate_usage_recommendation(self, confidence_assessment: Dict[str, Any]) -> str:
        """使用推奨事項の生成"""
        confidence = confidence_assessment["overall_confidence"]
        
        if confidence >= 0.8:
            return "結果は高い信頼度を持ち、そのまま使用できます"
        elif confidence >= 0.6:
            return "結果は中程度の信頼度です。重要な決定には追加検証を推奨"
        elif confidence >= 0.4:
            return "結果は低信頼度です。参考程度の使用に留めることを推奨"
        else:
            return "結果の信頼度が非常に低いため、再実行または別手法を検討してください"
    
    def _create_empty_result(self, state: AgentState) -> AgentState:
        """空の結果処理"""
        empty_result = {
            "integrated_findings": {
                "main_findings": ["処理可能な結果がありませんでした"],
                "summary": "タスクの実行結果が得られませんでした"
            },
            "confidence_assessment": {
                "overall_confidence": 0.1,
                "reliability_level": "要注意"
            }
        }
        
        updated_state = state.copy()
        updated_state.update({
            "processed_result": empty_result,
            "current_phase": AgentPhase.RESPONSE_GENERATION.value
        })
        return updated_state 