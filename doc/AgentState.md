# AgentState クラス設計書

## 概要
自律型AIエージェントの状態管理を行う中核データ構造クラス。エージェントの実行フェーズ、処理データ、メタデータを統合管理する。

## クラス情報
- **ファイル**: `src/core/agent_state.py`
- **レイヤ**: Core（コア）
- **責務**: 状態管理、データ構造定義、フェーズ制御

## 主要コンポーネント

### 1. AgentState (TypedDict)
エージェントの全体状態を表現する型定義

**フィールド**:
- `session_metadata`: セッション情報
- `current_phase`: 現在の実行フェーズ
- `user_input`: ユーザー入力
- `messages`: 会話履歴
- `intent_analysis`: 意図分析結果
- `execution_plan`: 実行計画
- `mcp_tools`: 利用可能ツール
- `task_results`: タスク実行結果
- `processed_results`: 処理済み結果
- `final_response`: 最終応答
- `error_context`: エラー情報

### 2. AgentPhase (Enum)
エージェントの実行フェーズを定義

**フェーズ**:
- `INPUT_PROCESSING`: 入力処理
- `INTENT_ANALYSIS`: 意図分析
- `PLAN_GENERATION`: 計画生成
- `MCP_INITIALIZATION`: MCP初期化
- `TASK_EXECUTION`: タスク実行
- `RESULT_PROCESSING`: 結果処理
- `RESPONSE_GENERATION`: 応答生成
- `COMPLETED`: 完了
- `ERROR_HANDLING`: エラー処理

### 3. データ構造クラス

#### SubTask
個別タスクの定義
- `task_id`: タスクID
- `description`: タスク説明
- `tool_name`: 使用ツール
- `parameters`: パラメータ
- `dependencies`: 依存関係
- `priority`: 優先度
- `estimated_duration`: 推定実行時間
- `status`: 実行状態

#### ExecutionPlan
実行計画の定義
- `plan_id`: 計画ID
- `subtasks`: サブタスクリスト
- `execution_order`: 実行順序
- `estimated_duration`: 推定総実行時間
- `parallel_groups`: 並列実行グループ

#### MCPTool
外部ツールの定義
- `name`: ツール名
- `description`: 説明
- `parameters`: パラメータスキーマ
- `is_available`: 利用可能性

## 主要機能

### 1. 状態初期化
```python
def create_initial_state(session_id: Optional[str] = None) -> AgentState
```
新しいエージェント状態を初期化

### 2. エラーコンテキスト追加
```python
def add_error_context(state: AgentState, phase: str, error: str) -> AgentState
```
エラー情報を状態に追加

### 3. フェーズ遷移
各フェーズ間の状態遷移を管理

## 設計原則

### 1. 不変性
- TypedDictによる型安全性
- 状態変更は新しいオブジェクト生成で実現

### 2. 拡張性
- 新しいフェーズやデータ構造の追加が容易
- プラグイン形式でのツール追加対応

### 3. 可観測性
- 全ての状態変更が追跡可能
- デバッグとモニタリングに対応

## 使用例

```python
# 初期状態の作成
state = create_initial_state("session_001")

# フェーズ遷移
state["current_phase"] = AgentPhase.INTENT_ANALYSIS.value

# エラー処理
state = add_error_context(state, "input_processing", "入力が無効です")
```

## 関連クラス
- `AutonomousAgent`: メイン制御クラス
- 各Processorクラス: 状態を更新する処理クラス群
- `MCPManager`: 外部ツール管理クラス 