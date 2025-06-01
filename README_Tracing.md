# 🔍 LangGraphエージェント - 詳細トレーシング機能

LangGraphエージェントの実行過程、ツール使用、Web検索の詳細ログを記録する包括的なトレーシングシステムです。

## 📋 機能概要

### 🎯 トレーシング対象
- **エージェント実行ステップ**: 各フェーズの開始/終了時刻、実行時間、入出力データ
- **ツール実行**: ツール名、パラメータ、結果、実行時間、エラー情報
- **Web検索**: 検索クエリ、検索条件、ヒット件数、各サイト詳細情報
- **LangGraphノード**: ノード間遷移、状態変化、判断プロセス
- **エラーハンドリング**: エラー種別、発生箇所、復旧プロセス

### 📊 出力形式
- **標準出力ログ**: リアルタイムでの詳細情報表示（色付き）
- **JSONファイル**: 構造化された完全なトレースデータ
- **実行サマリー**: セッション全体の統計情報

## 🚀 使用方法

### 1. 基本セットアップ

```bash
# 必要な環境変数を設定
cp env.example .env
# .envファイルでAPIキーを設定
```

必要な環境変数：
```env
OPENAI_API_KEY=your_openai_api_key_here
SERPAPI_API_KEY=your_serpapi_key_here  # Web検索用（オプション）
```

### 2. デモエージェントの実行

```bash
python traced_agent_demo.py
```

#### デモ機能
- **Web検索**: 最新のLangGraph情報やAI技術トレンド
- **計算**: 数式の計算処理
- **データ分析**: テキストの感情分析と統計

#### 利用可能な質問例
1. "LangGraphとは何ですか？最新情報を教えてください"
2. "2024年のAI技術トレンドについて調べてください"
3. "15 * 8 + 30 を計算してください"
4. "「今日は素晴らしい天気で、新しいプロジェクトが成功しました」というテキストを分析してください"

### 3. カスタムエージェントでの使用

```python
from src.utils.trace_logger import TraceLogger
from src.external.web_search_tool import WebSearchTool

# トレーシングロガーの初期化
trace_logger = TraceLogger(session_id="custom_session", log_dir="logs")

# Web検索ツールにトレーシングを統合
web_search = WebSearchTool(trace_logger=trace_logger)

# 実行ステップのトレーシング
with trace_logger.trace_execution_step("CUSTOM_STEP", "PROCESSING", {"input": "data"}):
    # 処理を実行
    result = your_processing_function()
    trace_logger.log_step_output({"result": result})

# ツール実行のトレーシング
with trace_logger.trace_tool_execution("CustomTool", "process", {"param": "value"}):
    tool_result = custom_tool.process()
    trace_logger.log_tool_result(tool_result)

# Web検索のトレーシング
with trace_logger.trace_web_search("Python tutorial", "Google", {"num": 10}):
    search_results = web_search.search_web("Python tutorial")
```

## 📈 トレーシング出力の詳細

### 標準出力ログ
```
2024-01-15 14:30:25.123 | INFO     | TraceLogger.a1b2c3d4 | 🔍 トレーシングセッション開始 | セッションID: a1b2c3d4-5e6f-7890-abcd-ef1234567890
2024-01-15 14:30:25.156 | INFO     | TraceLogger.a1b2c3d4 | 📋 ステップ開始 | USER_QUERY > PROCESSING | ID: f9e8d7c6
2024-01-15 14:30:25.234 | INFO     | TraceLogger.a1b2c3d4 | 🔧 ツール実行開始 | WebSearchTool.web_search | ID: b5a49283
2024-01-15 14:30:25.256 | DEBUG    | TraceLogger.a1b2c3d4 |    パラメータ: {"query": "LangGraph とは"}
2024-01-15 14:30:26.123 | INFO     | TraceLogger.a1b2c3d4 | 🔍 Web検索開始 | Google (SerpAPI) | クエリ: 'LangGraph とは' | ID: c7d8e9f0
2024-01-15 14:30:27.456 | INFO     | TraceLogger.a1b2c3d4 | ✅ Web検索完了 | Google (SerpAPI) | 結果: 10件 | 実行時間: 1.333秒
2024-01-15 14:30:27.478 | INFO     | TraceLogger.a1b2c3d4 |    🎯 検索結果詳細:
2024-01-15 14:30:27.479 | INFO     | TraceLogger.a1b2c3d4 |       [1] LangGraph: 次世代のマルチエージェントフレームワーク
2024-01-15 14:30:27.480 | INFO     | TraceLogger.a1b2c3d4 |           URL: https://langchain-ai.github.io/langgraph/
2024-01-15 14:30:27.481 | INFO     | TraceLogger.a1b2c3d4 |           概要: LangGraphは、LangChainの上に構築された状態ベースのマルチエージェント...
```

### Web検索の詳細ログ
```
📊 検索結果詳細:
   • オーガニック結果: 10件
   • ナレッジグラフ: あり
   • ニュース結果: 3件
   • 関連検索: 5件
   • 総結果数: 13件
   • 全体の検索結果数: 約 234,000 件
```

### JSONトレースファイル構造
```json
{
  "session_info": {
    "session_id": "a1b2c3d4-5e6f-7890-abcd-ef1234567890",
    "start_time": 1705312225.123,
    "end_time": 1705312285.456,
    "total_duration": 60.333
  },
  "execution_steps": [
    {
      "step_id": "f9e8d7c6-...",
      "step_name": "USER_QUERY",
      "phase": "PROCESSING",
      "start_time": 1705312225.156,
      "end_time": 1705312285.234,
      "duration": 60.078,
      "status": "completed",
      "input_data": {"query": "LangGraph とは"},
      "output_data": {"result": "..."}
    }
  ],
  "tool_executions": [
    {
      "tool_id": "b5a49283-...",
      "tool_name": "WebSearchTool",
      "function_name": "web_search",
      "parameters": {"query": "LangGraph とは"},
      "start_time": 1705312225.234,
      "end_time": 1705312227.567,
      "duration": 2.333,
      "status": "completed",
      "result": {"status": "success", "results_count": 10}
    }
  ],
  "web_searches": [
    {
      "search_id": "c7d8e9f0-...",
      "query": "LangGraph とは",
      "search_engine": "Google (SerpAPI)",
      "parameters": {
        "q": "LangGraph とは",
        "hl": "ja",
        "gl": "jp",
        "num": 10
      },
      "start_time": 1705312226.123,
      "end_time": 1705312227.456,
      "duration": 1.333,
      "results_count": 10,
      "results": [
        {
          "position": 1,
          "title": "LangGraph: 次世代のマルチエージェントフレームワーク",
          "link": "https://langchain-ai.github.io/langgraph/",
          "snippet": "LangGraphは、LangChainの上に構築された状態ベース...",
          "source": "organic"
        }
      ],
      "status": "completed"
    }
  ],
  "summary": {
    "session_id": "a1b2c3d4-5e6f-7890-abcd-ef1234567890",
    "total_duration": 60.333,
    "execution_summary": {
      "total_steps": 5,
      "completed_steps": 5,
      "failed_steps": 0,
      "total_tools": 3,
      "completed_tools": 3,
      "failed_tools": 0,
      "total_searches": 2,
      "completed_searches": 2,
      "failed_searches": 0
    },
    "phases_executed": ["PROCESSING", "DECISION_MAKING", "TOOL_EXECUTION"],
    "tools_used": ["WebSearchTool.web_search", "Calculator.calculate"],
    "search_queries": ["LangGraph とは", "AI技術トレンド 2024"]
  }
}
```

## 🔧 トレーシング設定のカスタマイズ

### ログレベルの変更
```python
# より詳細なログ（DEBUG）
trace_logger = TraceLogger(log_dir="logs")
trace_logger.logger.setLevel(logging.DEBUG)

# エラーのみ（ERROR）
trace_logger.logger.setLevel(logging.ERROR)
```

### カスタムイベントのログ記録
```python
# カスタムイベントの記録
trace_logger.log_custom_event(
    "CUSTOM_EVENT",
    "カスタム処理を実行しました",
    {
        "parameter1": "value1",
        "parameter2": 42,
        "timestamp": datetime.now().isoformat()
    }
)
```

### 検索結果の手動記録
```python
# 検索結果を手動で記録
for result in search_results:
    trace_logger.log_search_result({
        "title": result["title"],
        "url": result["url"],
        "relevance_score": result.get("score", 0)
    })
```

## 📁 出力ファイル

### ログファイル
- **場所**: `logs/` ディレクトリ
- **命名**: `trace_YYYYMMDD_HHMMSS_SessionID.log`
- **形式**: テキストファイル（リアルタイム書き込み）

### JSONファイル
- **場所**: `logs/` ディレクトリ
- **命名**: `trace_YYYYMMDD_HHMMSS_SessionID.json`
- **形式**: 構造化JSON（セッション終了時に生成）

## 🎯 実行サマリー例

```
================================================================================
📊 セッション実行サマリー
================================================================================
🆔 セッションID: a1b2c3d4-5e6f-7890-abcd-ef1234567890
⏱️  総実行時間: 60.33秒
📋 実行ステップ: 5/5 完了
🔧 ツール実行: 3/3 完了
🔍 Web検索: 2/2 完了
🎯 実行フェーズ: PROCESSING, DECISION_MAKING, TOOL_EXECUTION
🛠️  使用ツール: WebSearchTool.web_search, Calculator.calculate
🔍 検索クエリ:
    • 'LangGraph とは'
    • 'AI技術トレンド 2024'
================================================================================
```

## 🔍 トラブルシューティング

### APIキーエラー
```
❌ SERPAPI_API_KEYが設定されていません。Web検索機能は利用できません。
```
**解決方法**: `.env`ファイルでSERPAPI_API_KEYを設定

### ログファイルの権限エラー
```
❌ ログファイルの作成に失敗しました
```
**解決方法**: `logs/`ディレクトリの書き込み権限を確認

### メモリ使用量が多い場合
```python
# トレーシングを無効化
agent = AutonomousAgent(enable_tracing=False)
```

## 📚 技術詳細

### 使用ライブラリ
- **LangGraph**: エージェントフレームワーク
- **LangChain**: LLMとツールの統合
- **SerpAPI**: Web検索API
- **OpenAI**: GPT-4o-miniモデル

### パフォーマンス考慮事項
- **ログファイルサイズ**: 長時間実行では大きなファイルが生成される可能性
- **メモリ使用量**: トレースデータをメモリに保持
- **実行速度**: トレーシング処理による若干のオーバーヘッド

### セキュリティ
- **APIキー**: ログには記録されません
- **センシティブデータ**: パラメータ中の機密情報は自動マスク化
- **ファイル権限**: ログファイルは適切な権限で作成

## 🚀 応用例

### 1. デバッグ用途
- エージェントの判断プロセス分析
- ツール実行の失敗原因調査
- パフォーマンスボトルネックの特定

### 2. 監視・運用
- 本番環境でのエージェント動作監視
- SLA違反の検知と分析
- 使用状況の統計取得

### 3. 最適化
- 処理時間の詳細分析
- ツール使用パターンの最適化
- キャッシュ戦略の改善

---

**注意**: 本機能は詳細なログを生成するため、プロダクション環境では必要に応じてログレベルを調整してください。 