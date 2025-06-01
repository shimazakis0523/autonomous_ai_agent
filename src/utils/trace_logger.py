#!/usr/bin/env python3
"""
包括的トレーシング・ログシステム
LangGraphエージェントの実行、ツール使用、Web検索の詳細ログを記録
"""
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from pathlib import Path
import uuid

# カスタムログフォーマッター
class TraceFormatter(logging.Formatter):
    """トレース用のカスタムログフォーマッター"""
    
    def format(self, record):
        # タイムスタンプをミリ秒付きで表示
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # ログレベル別の色付け
        colors = {
            'DEBUG': '\033[36m',     # シアン
            'INFO': '\033[32m',      # 緑
            'WARNING': '\033[33m',   # 黄色
            'ERROR': '\033[31m',     # 赤
            'CRITICAL': '\033[35m'   # マゼンタ
        }
        reset = '\033[0m'
        
        level_color = colors.get(record.levelname, '')
        
        # フォーマット
        formatted = f"{timestamp} | {level_color}{record.levelname:8}{reset} | {record.name:20} | {record.getMessage()}"
        
        # 例外情報がある場合は追加
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


@dataclass
class ExecutionStep:
    """実行ステップの詳細情報"""
    step_id: str
    step_name: str
    phase: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: str = "running"  # running, completed, failed
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_info: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ToolExecution:
    """ツール実行の詳細情報"""
    tool_id: str
    tool_name: str
    function_name: str
    parameters: Dict[str, Any]
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: str = "running"
    result: Optional[Any] = None
    error_info: Optional[Dict[str, Any]] = None


@dataclass
class WebSearchTrace:
    """Web検索の詳細トレース"""
    search_id: str
    query: str
    search_engine: str
    parameters: Dict[str, Any]
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    results_count: int = 0
    results: List[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    status: str = "running"
    error_info: Optional[Dict[str, Any]] = None


class TraceLogger:
    """包括的トレーシング・ログクラス"""
    
    def __init__(self, session_id: Optional[str] = None, log_dir: str = "logs"):
        """
        初期化
        
        Args:
            session_id: セッションID
            log_dir: ログディレクトリ
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 実行履歴
        self.execution_steps: List[ExecutionStep] = []
        self.tool_executions: List[ToolExecution] = []
        self.web_searches: List[WebSearchTrace] = []
        self.current_step: Optional[ExecutionStep] = None
        self.current_tool: Optional[ToolExecution] = None
        self.current_search: Optional[WebSearchTrace] = None
        
        # ログファイルの設定
        self.session_start_time = time.time()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = self.log_dir / f"trace_{timestamp}_{self.session_id[:8]}.log"
        self.json_log_file = self.log_dir / f"trace_{timestamp}_{self.session_id[:8]}.json"
        
        # ロガーの設定
        self.logger = logging.getLogger(f"TraceLogger.{self.session_id[:8]}")
        self.logger.setLevel(logging.DEBUG)
        
        # ハンドラーがまだ設定されていない場合のみ追加
        if not self.logger.handlers:
            # ファイルハンドラー
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setFormatter(TraceFormatter())
            self.logger.addHandler(file_handler)
            
            # コンソールハンドラー
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(TraceFormatter())
            self.logger.addHandler(console_handler)
        
        self.logger.info(f"🔍 トレーシングセッション開始 | セッションID: {self.session_id}")
    
    @contextmanager
    def trace_execution_step(self, step_name: str, phase: str, input_data: Optional[Dict] = None):
        """実行ステップのトレーシング"""
        step_id = str(uuid.uuid4())
        step = ExecutionStep(
            step_id=step_id,
            step_name=step_name,
            phase=phase,
            start_time=time.time(),
            input_data=input_data
        )
        
        self.current_step = step
        self.execution_steps.append(step)
        
        self.logger.info(f"📋 ステップ開始 | {phase} > {step_name} | ID: {step_id[:8]}")
        if input_data:
            self.logger.debug(f"   入力データ: {json.dumps(input_data, ensure_ascii=False, indent=2)}")
        
        try:
            yield step
            # 成功時
            step.end_time = time.time()
            step.duration = step.end_time - step.start_time
            step.status = "completed"
            self.logger.info(f"✅ ステップ完了 | {step_name} | 実行時間: {step.duration:.3f}秒")
            
        except Exception as e:
            # エラー時
            step.end_time = time.time()
            step.duration = step.end_time - step.start_time
            step.status = "failed"
            step.error_info = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self.logger.error(f"❌ ステップ失敗 | {step_name} | エラー: {str(e)} | 実行時間: {step.duration:.3f}秒")
            raise
        finally:
            self.current_step = None
    
    @contextmanager
    def trace_tool_execution(self, tool_name: str, function_name: str, parameters: Dict[str, Any]):
        """ツール実行のトレーシング"""
        tool_id = str(uuid.uuid4())
        tool_exec = ToolExecution(
            tool_id=tool_id,
            tool_name=tool_name,
            function_name=function_name,
            parameters=parameters,
            start_time=time.time()
        )
        
        self.current_tool = tool_exec
        self.tool_executions.append(tool_exec)
        
        self.logger.info(f"🔧 ツール実行開始 | {tool_name}.{function_name} | ID: {tool_id[:8]}")
        self.logger.debug(f"   パラメータ: {json.dumps(parameters, ensure_ascii=False, indent=2)}")
        
        try:
            yield tool_exec
            # 成功時
            tool_exec.end_time = time.time()
            tool_exec.duration = tool_exec.end_time - tool_exec.start_time
            tool_exec.status = "completed"
            self.logger.info(f"✅ ツール実行完了 | {tool_name}.{function_name} | 実行時間: {tool_exec.duration:.3f}秒")
            
        except Exception as e:
            # エラー時
            tool_exec.end_time = time.time()
            tool_exec.duration = tool_exec.end_time - tool_exec.start_time
            tool_exec.status = "failed"
            tool_exec.error_info = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self.logger.error(f"❌ ツール実行失敗 | {tool_name}.{function_name} | エラー: {str(e)}")
            raise
        finally:
            self.current_tool = None
    
    @contextmanager
    def trace_web_search(self, query: str, search_engine: str, parameters: Dict[str, Any]):
        """Web検索のトレーシング"""
        search_id = str(uuid.uuid4())
        search_trace = WebSearchTrace(
            search_id=search_id,
            query=query,
            search_engine=search_engine,
            parameters=parameters,
            start_time=time.time(),
            results=[]
        )
        
        self.current_search = search_trace
        self.web_searches.append(search_trace)
        
        self.logger.info(f"🔍 Web検索開始 | {search_engine} | クエリ: '{query}' | ID: {search_id[:8]}")
        self.logger.debug(f"   検索パラメータ: {json.dumps(parameters, ensure_ascii=False, indent=2)}")
        
        try:
            yield search_trace
            # 成功時
            search_trace.end_time = time.time()
            search_trace.duration = search_trace.end_time - search_trace.start_time
            search_trace.status = "completed"
            self.logger.info(f"✅ Web検索完了 | {search_engine} | 結果: {search_trace.results_count}件 | 実行時間: {search_trace.duration:.3f}秒")
            
            # 検索結果の詳細ログ
            if search_trace.results:
                self.logger.info(f"   🎯 検索結果詳細:")
                for i, result in enumerate(search_trace.results[:5], 1):  # 上位5件のみ表示
                    title = result.get('title', 'タイトルなし')[:100]
                    url = result.get('link', result.get('url', ''))
                    snippet = result.get('snippet', result.get('description', ''))[:150]
                    self.logger.info(f"      [{i}] {title}")
                    self.logger.info(f"          URL: {url}")
                    self.logger.info(f"          概要: {snippet}")
            
        except Exception as e:
            # エラー時
            search_trace.end_time = time.time()
            search_trace.duration = search_trace.end_time - search_trace.start_time
            search_trace.status = "failed"
            search_trace.error_info = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self.logger.error(f"❌ Web検索失敗 | {search_engine} | クエリ: '{query}' | エラー: {str(e)}")
            raise
        finally:
            self.current_search = None
    
    def log_search_result(self, result: Dict[str, Any]):
        """検索結果の追加記録"""
        if self.current_search:
            if self.current_search.results is None:
                self.current_search.results = []
            self.current_search.results.append(result)
            self.current_search.results_count = len(self.current_search.results)
    
    def log_tool_result(self, result: Any):
        """ツール実行結果の記録"""
        if self.current_tool:
            self.current_tool.result = result
            # 結果のサイズが大きい場合は要約
            if isinstance(result, (dict, list)) and len(str(result)) > 1000:
                summary = f"大きなデータ（タイプ: {type(result).__name__}, サイズ: {len(str(result))}文字）"
                self.logger.debug(f"   ツール結果（要約）: {summary}")
            else:
                self.logger.debug(f"   ツール結果: {result}")
    
    def log_step_output(self, output_data: Dict[str, Any]):
        """ステップ出力の記録"""
        if self.current_step:
            self.current_step.output_data = output_data
            self.logger.debug(f"   ステップ出力: {json.dumps(output_data, ensure_ascii=False, indent=2)}")
    
    def log_custom_event(self, event_type: str, message: str, data: Optional[Dict] = None):
        """カスタムイベントのログ"""
        timestamp = datetime.now().isoformat()
        log_message = f"📝 {event_type} | {message}"
        if data:
            log_message += f" | データ: {json.dumps(data, ensure_ascii=False)}"
        
        self.logger.info(log_message)
    
    def generate_summary(self) -> Dict[str, Any]:
        """セッションサマリーの生成"""
        current_time = time.time()
        total_duration = current_time - self.session_start_time
        
        # 統計情報
        completed_steps = len([s for s in self.execution_steps if s.status == "completed"])
        failed_steps = len([s for s in self.execution_steps if s.status == "failed"])
        completed_tools = len([t for t in self.tool_executions if t.status == "completed"])
        failed_tools = len([t for t in self.tool_executions if t.status == "failed"])
        completed_searches = len([s for s in self.web_searches if s.status == "completed"])
        failed_searches = len([s for s in self.web_searches if s.status == "failed"])
        
        summary = {
            "session_id": self.session_id,
            "total_duration": total_duration,
            "execution_summary": {
                "total_steps": len(self.execution_steps),
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "total_tools": len(self.tool_executions),
                "completed_tools": completed_tools,
                "failed_tools": failed_tools,
                "total_searches": len(self.web_searches),
                "completed_searches": completed_searches,
                "failed_searches": failed_searches
            },
            "phases_executed": list(set([s.phase for s in self.execution_steps])),
            "tools_used": list(set([f"{t.tool_name}.{t.function_name}" for t in self.tool_executions])),
            "search_queries": [s.query for s in self.web_searches],
            "timestamp": datetime.now().isoformat()
        }
        
        return summary
    
    def save_trace_data(self):
        """トレースデータのJSONファイル保存"""
        trace_data = {
            "session_info": {
                "session_id": self.session_id,
                "start_time": self.session_start_time,
                "end_time": time.time(),
                "total_duration": time.time() - self.session_start_time
            },
            "execution_steps": [asdict(step) for step in self.execution_steps],
            "tool_executions": [asdict(tool) for tool in self.tool_executions],
            "web_searches": [asdict(search) for search in self.web_searches],
            "summary": self.generate_summary()
        }
        
        with open(self.json_log_file, 'w', encoding='utf-8') as f:
            json.dump(trace_data, f, ensure_ascii=False, indent=2, default=str)
        
        self.logger.info(f"💾 トレースデータ保存完了: {self.json_log_file}")
    
    def print_final_summary(self):
        """最終サマリーの表示"""
        summary = self.generate_summary()
        
        self.logger.info("=" * 80)
        self.logger.info("📊 セッション実行サマリー")
        self.logger.info("=" * 80)
        self.logger.info(f"🆔 セッションID: {self.session_id}")
        self.logger.info(f"⏱️  総実行時間: {summary['total_duration']:.2f}秒")
        self.logger.info(f"📋 実行ステップ: {summary['execution_summary']['completed_steps']}/{summary['execution_summary']['total_steps']} 完了")
        self.logger.info(f"🔧 ツール実行: {summary['execution_summary']['completed_tools']}/{summary['execution_summary']['total_tools']} 完了")
        self.logger.info(f"🔍 Web検索: {summary['execution_summary']['completed_searches']}/{summary['execution_summary']['total_searches']} 完了")
        self.logger.info(f"🎯 実行フェーズ: {', '.join(summary['phases_executed'])}")
        self.logger.info(f"🛠️  使用ツール: {', '.join(summary['tools_used'])}")
        if summary['search_queries']:
            self.logger.info(f"🔍 検索クエリ:")
            for query in summary['search_queries']:
                self.logger.info(f"    • '{query}'")
        self.logger.info("=" * 80) 