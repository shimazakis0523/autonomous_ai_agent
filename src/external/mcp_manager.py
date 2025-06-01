"""
自律型AIエージェント - MCP（Model Context Protocol）管理
フェーズ4: 外部ツール統合とリソース管理
トレーシング機能付き
"""
import asyncio
import json
import logging
import os
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from serpapi import GoogleSearch

from ..core.agent_state import AgentState, AgentPhase, MCPTool, add_error_context

# 環境変数の読み込み
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# MCP関連のインポート（オプショナル）
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    logger.warning("MCP ライブラリが見つかりません。模擬実行モードで動作します。")
    logger.info("MCPを使用するには: pip install mcp")


class MCPManager:
    """Model Context Protocol (MCP) 管理クラス（トレーシング対応）"""
    
    def __init__(self, trace_logger=None):
        """
        MCPマネージャーの初期化
        
        Args:
            trace_logger: トレーシングロガー（オプション）
        """
        self.trace_logger = trace_logger
        self.active_connections = {}
        self.tool_registry = {}
        self.connection_pool = {}
        self.session_stats = {
            'connections_established': 0,
            'tools_executed': 0,
            'errors_occurred': 0
        }
        self.max_retries = 3
        self.execution_timeout = 30
        
        # SerpAPIキーの確認
        self.serpapi_key = os.getenv("SERPAPI_API_KEY")
        if not self.serpapi_key:
            logger.warning("SERPAPI_API_KEYが設定されていません。モック実行になります。")
            logger.info("MCP ライブラリが見つかりません。模擬実行モードで動作します。")
            self.mock_mode = True
            self._register_mock_tools()
        else:
            logger.info("SerpAPI設定完了。リアル検索を実行します。")
            self.mock_mode = False
            self._register_real_tools()
        
        if self.trace_logger:
            self.trace_logger.log_custom_event(
                "MCP_MANAGER_INIT",
                "MCPManager初期化完了",
                {
                    "mock_mode": self.mock_mode,
                    "has_serpapi": bool(self.serpapi_key),
                    "has_mcp_lib": HAS_MCP,
                    "tools_registered": len(self.tool_registry),
                    "max_retries": self.max_retries,
                    "execution_timeout": self.execution_timeout
                }
            )
        
        logger.info(f"MCPマネージャー初期化完了")
    
    async def initialize_connections(self, state: AgentState) -> AgentState:
        """
        必要なMCP接続の初期化
        
        Args:
            state: 現在のエージェント状態
            
        Returns:
            MCP接続情報を含む更新された状態
        """
        try:
            execution_plan = state["execution_plan"]
            if not execution_plan:
                logger.info("実行計画がないため、MCP初期化をスキップ")
                return self._update_state_to_execution(state, {})
            
            # 必要なツールの特定
            required_tools = self._identify_required_tools(execution_plan)
            
            if not required_tools:
                logger.info("外部ツールが不要なため、MCP初期化をスキップ")
                return self._update_state_to_execution(state, {})
            
            logger.info(f"MCP接続を初期化中: {required_tools}")
            
            # MCP接続の確立
            mcp_connections = {}
            
            if self.mock_mode:
                # モックモードでの接続
                mcp_connections = await self._initialize_mock_connections(required_tools)
            else:
                # 実際のMCP接続
                mcp_connections = await self._initialize_real_connections(required_tools)
            
            logger.info(f"MCP接続完了: {len(mcp_connections)}個のツール")
            
            return self._update_state_to_execution(state, mcp_connections)
            
        except Exception as e:
            logger.error(f"MCP初期化エラー: {str(e)}")
            return add_error_context(state, "mcp_initialization", str(e))
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """ツールの実行"""
        if tool_name not in self.tool_registry:
            raise ValueError(f"未知のツール: {tool_name}")
        
        try:
            # モックモードの場合
            if self.mock_mode:
                if tool_name == "file_operations":
                    # file_operationsの場合は特別な処理
                    operation = kwargs.get("operation", "read")
                    path = kwargs.get("path", "")
                    content = kwargs.get("content", "")
                    return await self._mock_file_operations(operation, path, content)
                elif tool_name == "text_processing":
                    # text_processingの場合は特別な処理
                    text = kwargs.get("text", "")
                    operation = kwargs.get("operation", "summarize")
                    return await self._mock_text_processing(text, operation)
                else:
                    # その他のツールは通常のモック処理
                    return await self._mock_tool_execution(tool_name, **kwargs)
            
            # 実際のツール実行
            tool = self.tool_registry[tool_name]
            if hasattr(tool, "_arun"):
                result = await tool._arun(**kwargs)
            else:
                result = tool._run(**kwargs)
            
            return {
                "status": "success",
                "result": result,
                "tool": tool_name
            }
            
        except Exception as e:
            logger.error(f"ツール実行エラー [{tool_name}]: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "tool": tool_name
            }
    
    def _identify_required_tools(self, execution_plan) -> List[str]:
        """実行計画から必要なツールを特定"""
        required_tools = set()
        
        for subtask in execution_plan.subtasks:
            if subtask.tool_name and subtask.tool_name in self.tool_registry:
                required_tools.add(subtask.tool_name)
        
        return list(required_tools)
    
    async def _initialize_mock_connections(self, required_tools: List[str]) -> Dict[str, Any]:
        """モック接続の初期化"""
        mock_connections = {}
        
        for tool_name in required_tools:
            mock_connections[tool_name] = {
                "type": "mock",
                "tool_name": tool_name,
                "connected": True,
                "initialized_at": datetime.now().isoformat()
            }
            logger.info(f"モックMCP接続確立: {tool_name}")
        
        return mock_connections
    
    async def _initialize_real_connections(self, required_tools: List[str]) -> Dict[str, Any]:
        """実際のMCP接続の初期化"""
        real_connections = {}
        
        for tool_name in required_tools:
            if tool_name not in self.tool_registry:
                logger.warning(f"未登録のツール: {tool_name}")
                continue
            
            try:
                connection = await self._establish_mcp_connection(
                    self.tool_registry[tool_name]
                )
                real_connections[tool_name] = connection
                logger.info(f"実MCP接続確立: {tool_name}")
                
            except Exception as e:
                logger.error(f"MCP接続失敗 ({tool_name}): {str(e)}")
                # フォールバックとしてモック接続を使用
                real_connections[tool_name] = {
                    "type": "fallback_mock",
                    "tool_name": tool_name,
                    "error": str(e),
                    "initialized_at": datetime.now().isoformat()
                }
        
        return real_connections
    
    async def _establish_mcp_connection(self, tool: MCPTool) -> Dict[str, Any]:
        """個別のMCP接続確立"""
        if not HAS_MCP:
            raise ImportError("MCP ライブラリが必要です")
        
        # サーバーパラメータ設定
        server_params = StdioServerParameters(
            command=tool.server_path,
            args=[],
            env=None
        )
        
        # クライアントセッション作成
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # サーバー初期化
                await session.initialize()
                
                # ツール一覧取得
                tools_result = await session.list_tools()
                available_tools = [t.name for t in tools_result.tools]
                
                logger.info(f"利用可能ツール ({tool.name}): {available_tools}")
                
                # 接続情報を返す
                connection_info = {
                    "type": "real",
                    "session": session,
                    "tool_name": tool.name,
                    "available_tools": available_tools,
                    "connected": True,
                    "initialized_at": datetime.now().isoformat()
                }
                
                # 接続をプールに保存
                self.active_connections[tool.name] = connection_info
                return connection_info
    
    async def _execute_mock_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """モックツール実行"""
        # シミュレーション遅延
        await asyncio.sleep(0.5)
        
        # ツール別のモック結果
        mock_results = {
            "file_operations": {
                "status": "success",
                "action": "mock_file_operation",
                "files_processed": ["mock_file1.txt", "mock_file2.txt"],
                "result": "ファイル操作を模擬実行しました。"
            },
            "web_search": {
                "status": "success",
                "query": parameters.get("query", "mock query"),
                "results": [
                    {"title": "模擬検索結果1", "url": "https://example.com/1", "snippet": "模擬検索スニペット1"},
                    {"title": "模擬検索結果2", "url": "https://example.com/2", "snippet": "模擬検索スニペット2"}
                ],
                "result": "ウェブ検索を模擬実行しました。"
            },
            "code_execution": {
                "status": "success",
                "code": parameters.get("code", "print('Hello Mock')"),
                "output": "Hello Mock\n",
                "execution_time": 0.5,
                "result": "コード実行を模擬実行しました。"
            },
            "data_analysis": {
                "status": "success",
                "data_points": 100,
                "analysis_type": "mock_analysis",
                "statistics": {"mean": 50.5, "std": 28.9, "min": 1, "max": 100},
                "result": "データ分析を模擬実行しました。"
            },
            "text_processing": {
                "status": "success",
                "input_length": len(str(parameters.get("text", ""))),
                "output": "処理されたテキスト（模擬）",
                "processing_time": 0.3,
                "result": "テキスト処理を模擬実行しました。"
            }
        }
        
        result = mock_results.get(tool_name, {
            "status": "success",
            "tool": tool_name,
            "result": f"{tool_name}を模擬実行しました。"
        })
        
        # パラメータ情報を追加
        result["parameters"] = parameters
        result["executed_at"] = datetime.now().isoformat()
        result["mock_execution"] = True
        
        return result
    
    async def _execute_real_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """実際のMCPツール実行"""
        if tool_name not in self.active_connections:
            raise ValueError(f"MCP接続が見つかりません: {tool_name}")
        
        connection = self.active_connections[tool_name]
        
        if connection["type"] == "fallback_mock":
            logger.warning(f"フォールバックモック実行: {tool_name}")
            return await self._execute_mock_tool(tool_name, parameters)
        
        session = connection["session"]
        
        # ツール実行リクエスト
        result = await asyncio.wait_for(
            session.call_tool(name=tool_name, arguments=parameters),
            timeout=self.execution_timeout
        )
        
        # 実行結果の処理
        if result.isError:
            raise RuntimeError(f"ツール実行エラー: {result.content}")
        
        return {
            "status": "success",
            "result": result.content,
            "parameters": parameters,
            "executed_at": datetime.now().isoformat(),
            "mock_execution": False
        }
    
    def _update_state_to_execution(self, state: AgentState, mcp_connections: Dict[str, Any]) -> AgentState:
        """実行フェーズへの状態更新"""
        updated_state = state.copy()
        updated_state.update({
            "mcp_connections": mcp_connections,
            "current_phase": AgentPhase.TASK_EXECUTION.value
        })
        return updated_state
    
    def register_tool(self, tool: MCPTool) -> None:
        """新しいツールの登録"""
        self.tool_registry[tool.name] = tool
    
    def get_available_tools(self) -> List[str]:
        """利用可能なツール一覧の取得"""
        return list(self.tool_registry.keys())
    
    def get_tool_info(self, tool_name: str) -> Optional[MCPTool]:
        """ツール情報の取得"""
        return self.tool_registry.get(tool_name)
    
    async def cleanup_connections(self) -> None:
        """全MCP接続のクリーンアップ"""
        cleanup_tasks = []
        
        for name, connection in self.active_connections.items():
            if connection.get("type") == "real" and "session" in connection:
                cleanup_tasks.append(self._cleanup_single_connection(name, connection))
        
        if cleanup_tasks:
            try:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            except Exception as e:
                logger.warning(f"接続クリーンアップ中にエラー: {str(e)}")
        
        self.active_connections.clear()
        logger.info("全MCP接続をクリーンアップしました")
    
    async def _cleanup_single_connection(self, name: str, connection: Dict[str, Any]) -> None:
        """個別接続のクリーンアップ"""
        try:
            if "session" in connection:
                await connection["session"].close()
            logger.info(f"MCP接続クリーンアップ: {name}")
        except Exception as e:
            logger.warning(f"接続クリーンアップ失敗 ({name}): {str(e)}")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """接続ステータスの取得"""
        status = {
            "total_connections": len(self.active_connections),
            "mock_mode": self.mock_mode,
            "registered_tools": len(self.tool_registry),
            "connections": {}
        }
        
        for name, connection in self.active_connections.items():
            status["connections"][name] = {
                "type": connection.get("type"),
                "connected": connection.get("connected", False),
                "initialized_at": connection.get("initialized_at")
            }
        
        return status

    def _register_real_tools(self):
        """実際の外部ツールを登録"""
        self.tool_registry = {
            'web_search': {
                'name': 'web_search',
                'description': 'SerpAPIを使用したGoogle検索',
                'parameters': ['query', 'location', 'hl'],
                'handler': self._real_web_search
            },
            'text_processing': {
                'name': 'text_processing',
                'description': '基本的なテキスト処理',
                'parameters': ['text', 'operation'],
                'handler': self._mock_text_processing
            },
            'file_operations': {
                'name': 'file_operations',
                'description': 'ファイル操作ユーティリティ',
                'parameters': ['operation', 'path', 'content'],
                'handler': self._mock_file_operations
            },
            'data_analysis': {
                'name': 'data_analysis',
                'description': 'データ分析ツール',
                'parameters': ['data', 'analysis_type'],
                'handler': self._mock_data_analysis
            },
            'code_execution': {
                'name': 'code_execution',
                'description': 'コード実行環境',
                'parameters': ['code', 'language'],
                'handler': self._mock_code_execution
            }
        }
        
        logger.info(f"実際のツール登録完了: {list(self.tool_registry.keys())}")
    
    def _register_mock_tools(self):
        """モックツールを登録（SerpAPIキーがない場合）"""
        self.tool_registry = {
            'web_search': {
                'name': 'web_search',
                'description': 'モック Google検索',
                'parameters': ['query', 'location', 'hl'],
                'handler': self._mock_web_search
            },
            'text_processing': {
                'name': 'text_processing',
                'description': '基本的なテキスト処理',
                'parameters': ['text', 'operation'],
                'handler': self._mock_text_processing
            },
            'file_operations': {
                'name': 'file_operations',
                'description': 'ファイル操作ユーティリティ',
                'parameters': ['operation', 'path', 'content'],
                'handler': self._mock_file_operations
            },
            'data_analysis': {
                'name': 'data_analysis',
                'description': 'データ分析ツール',
                'parameters': ['data', 'analysis_type'],
                'handler': self._mock_data_analysis
            },
            'code_execution': {
                'name': 'code_execution',
                'description': 'コード実行環境',
                'parameters': ['code', 'language'],
                'handler': self._mock_code_execution
            }
        }
        
        logger.info(f"デフォルトツール登録完了: {list(self.tool_registry.keys())}")
    
    async def _real_web_search(self, query: str, **kwargs) -> Dict[str, Any]:
        """実際のSerpAPIを使用したGoogle検索"""
        try:
            params = {
                "q": query,
                "hl": kwargs.get('hl', 'ja'),  # 日本語
                "gl": kwargs.get('gl', 'jp'),  # 日本
                "api_key": self.serpapi_key
            }
            
            # ロケーション指定がある場合
            if kwargs.get('location'):
                params['location'] = kwargs['location']
            
            logger.info(f"SerpAPI検索実行: {query}")
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # 結果の整形
            formatted_results = {
                "query": query,
                "organic_results": [],
                "knowledge_graph": results.get("knowledge_graph", {}),
                "people_also_ask": results.get("people_also_ask", []),
                "related_searches": results.get("related_searches", [])
            }
            
            # オーガニック検索結果の処理
            organic_results = results.get("organic_results", [])
            for result in organic_results[:10]:  # 上位10件
                formatted_results["organic_results"].append({
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "position": result.get("position", 0)
                })
            
            logger.info(f"SerpAPI検索完了: {len(formatted_results['organic_results'])}件の結果")
            return {
                'success': True,
                'data': formatted_results,
                'source': 'SerpAPI',
                'timestamp': datetime.now().isoformat(),
                'cost_info': {
                    'api_calls': 1,
                    'provider': 'SerpAPI'
                }
            }
            
        except Exception as e:
            logger.error(f"SerpAPI検索エラー: {str(e)}")
            # エラー時はモック結果を返す
            return await self._mock_web_search(query, **kwargs)
    
    async def _mock_text_processing(self, text: str, operation: str = "summarize", **kwargs) -> Dict[str, Any]:
        """
        テキスト処理のモック実装
        
        Args:
            text: 処理対象のテキスト
            operation: 処理タイプ（summarize, extract, analyze等）
            **kwargs: 追加パラメータ
            
        Returns:
            処理結果の辞書
        """
        if not text:
            return {
                "error": "テキストが空です",
                "status": "error"
            }
            
        try:
            if self.serpapi_key is None:
                return {
                    "error": "SERPAPI_API_KEYが設定されていません",
                    "status": "error"
                }
            
            # 処理タイプに応じたプロンプト生成
            prompts = {
                "summarize": "以下のテキストを要約してください：\n\n{text}",
                "extract": "以下のテキストから重要な情報を抽出してください：\n\n{text}",
                "analyze": "以下のテキストを分析し、主要なポイントを箇条書きで示してください：\n\n{text}"
            }
            
            prompt = prompts.get(operation, prompts["summarize"]).format(text=text)
            
            messages = [
                SystemMessage(content="あなたはテキスト処理の専門家です。与えられたテキストを適切に処理し、構造化された結果を返してください。"),
                HumanMessage(content=prompt)
            ]
            
            response = await self._call_serpapi(messages)
            
            # 結果の構造化
            return {
                "status": "success",
                "operation": operation,
                "result": response.content,
                "metadata": {
                    "text_length": len(text),
                    "operation_type": operation,
                    "processing_time": "0.5秒"  # モック値
                }
            }
            
        except Exception as e:
            logger.error(f"テキスト処理エラー: {str(e)}")
            return {
                "error": str(e),
                "status": "error",
                "operation": operation
            }
    
    async def _mock_file_operations(self, operation: str, path: str = "", content: str = "") -> Dict[str, Any]:
        """モックファイル操作"""
        try:
            # パスの正規化
            normalized_path = os.path.normpath(path)
            if not os.path.isabs(normalized_path):
                # 相対パスの場合、ワークスペースルートからのパスに変換
                workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                normalized_path = os.path.join(workspace_root, normalized_path)
            
            logger.info(f"ファイル操作: {operation} - パス: {normalized_path}")
            
            if operation == "read":
                if not os.path.exists(normalized_path):
                    logger.error(f"ファイルが見つかりません: {normalized_path}")
                    return {
                        "status": "error",
                        "error": f"ファイルが見つかりません: {path}",
                        "operation": operation,
                        "path": normalized_path
                    }
                
                try:
                    with open(normalized_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    logger.info(f"ファイル読み込み成功: {normalized_path}")
                    return {
                        "status": "success",
                        "operation": operation,
                        "content": content,
                        "path": normalized_path
                    }
                except Exception as e:
                    logger.error(f"ファイル読み込みエラー: {str(e)}")
                    return {
                        "status": "error",
                        "error": f"ファイル読み込みエラー: {str(e)}",
                        "operation": operation,
                        "path": normalized_path
                    }
            
            elif operation == "write":
                try:
                    os.makedirs(os.path.dirname(normalized_path), exist_ok=True)
                    with open(normalized_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"ファイル書き込み成功: {normalized_path}")
                    return {
                        "status": "success",
                        "operation": operation,
                        "path": normalized_path,
                        "bytes_written": len(content)
                    }
                except Exception as e:
                    logger.error(f"ファイル書き込みエラー: {str(e)}")
                    return {
                        "status": "error",
                        "error": f"ファイル書き込みエラー: {str(e)}",
                        "operation": operation,
                        "path": normalized_path
                    }
            
            elif operation == "list":
                try:
                    dir_path = os.path.dirname(normalized_path)
                    if not os.path.exists(dir_path):
                        logger.error(f"ディレクトリが見つかりません: {dir_path}")
                        return {
                            "status": "error",
                            "error": f"ディレクトリが見つかりません: {dir_path}",
                            "operation": operation,
                            "path": dir_path
                        }
                    
                    files = os.listdir(dir_path)
                    logger.info(f"ディレクトリ一覧取得成功: {dir_path}")
                    return {
                        "status": "success",
                        "operation": operation,
                        "path": dir_path,
                        "files": files
                    }
                except Exception as e:
                    logger.error(f"ディレクトリ読み込みエラー: {str(e)}")
                    return {
                        "status": "error",
                        "error": f"ディレクトリ読み込みエラー: {str(e)}",
                        "operation": operation,
                        "path": dir_path
                    }
            
            else:
                logger.error(f"未サポートの操作: {operation}")
                return {
                    "status": "error",
                    "error": f"未サポートの操作: {operation}",
                    "operation": operation
                }
                
        except Exception as e:
            logger.error(f"ファイル操作エラー: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "operation": operation
            }
    
    async def _mock_data_analysis(self, data: Any, analysis_type: str = "basic", **kwargs) -> Dict[str, Any]:
        """モックデータ分析"""
        await asyncio.sleep(0.4)
        
        if analysis_type == "statistical":
            result = {
                "count": 100,
                "mean": 50.5,
                "median": 51.0,
                "std": 15.2
            }
        elif analysis_type == "trend":
            result = {
                "trend": "increasing",
                "growth_rate": "5.2%",
                "confidence": 0.85
            }
        else:
            result = {
                "data_points": 100,
                "categories": 5,
                "summary": "基本的な分析結果"
            }
        
        return {
            'success': True,
            'data': {
                'analysis_type': analysis_type,
                'result': result
            },
            'source': 'mock',
            'timestamp': datetime.now().isoformat()
        }
    
    async def _mock_code_execution(self, code: str, language: str = "python", **kwargs) -> Dict[str, Any]:
        """モックコード実行"""
        await asyncio.sleep(0.5)
        
        if language == "python":
            result = f"Python実行結果（模擬）: {len(code)}行のコードを実行"
        elif language == "javascript":
            result = f"JavaScript実行結果（模擬）: {len(code)}文字のコードを実行"
        else:
            result = f"{language}実行結果（模擬）"
        
        return {
            'success': True,
            'data': {
                'language': language,
                'output': result,
                'exit_code': 0
            },
            'source': 'mock',
            'timestamp': datetime.now().isoformat()
        } 