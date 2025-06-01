# AutonomousAgent クラス設計書

## 概要
自律型AIエージェントのメイン統合クラス。全7フェーズの処理を統合し、自律的な対話セッションを管理する中核システム。

## クラス情報
- **ファイル**: `src/core/autonomous_agent.py`
- **レイヤ**: Core（コア）
- **責務**: 全体制御、フェーズ統合、セッション管理

## アーキテクチャ

### 1. 7フェーズ処理パイプライン
1. **INPUT_PROCESSING**: ユーザー入力受付・検証
2. **INTENT_ANALYSIS**: 意図分析・分類
3. **PLAN_GENERATION**: 実行計画生成
4. **MCP_INITIALIZATION**: 外部ツール初期化
5. **TASK_EXECUTION**: 並列タスク実行
6. **RESULT_PROCESSING**: 結果統合・品質評価
7. **RESPONSE_GENERATION**: 最終応答生成

### 2. 統合コンポーネント
- `InputProcessor`: 入力処理エンジン
- `IntentAnalyzer`: 意図分析エンジン
- `PlanGenerator`: 計画生成エンジン
- `MCPManager`: 外部ツール管理
- `TaskOrchestrator`: タスク実行制御
- `ResultProcessor`: 結果処理エンジン
- `ResponseGenerator`: 応答生成エンジン

## 主要機能

### 1. セッション管理
```python
async def run_session(self, session_id: Optional[str] = None) -> None
```
- 対話セッションの開始から終了まで管理
- 状態の初期化とクリーンアップ
- エラーハンドリングと復旧処理

### 2. メイン処理ループ
```python
async def _execute_main_loop(self, state: AgentState) -> AgentState
```
- フェーズ別処理の実行
- 状態遷移の制御
- 繰り返し処理の管理

### 3. エラーハンドリング
```python
async def _handle_error(self, state: AgentState) -> AgentState
```
- 復旧可能/不可能エラーの判定
- エラー応答の生成
- 適切な復旧処理の実行

### 4. セッション制御
```python
def stop_session(self) -> None
```
- セッションの安全な停止
- リソースのクリーンアップ

## 設定パラメータ

### 1. 実行制限
- `max_iterations`: 最大繰り返し回数（デフォルト: 10）
- `session_timeout`: セッションタイムアウト（デフォルト: 3600秒）

### 2. エラー制御
- 最大エラー回数: 3回
- 復旧可能エラーパターンの定義

## 状態管理

### 1. セッション状態
- `is_running`: 実行状態フラグ
- `iteration_count`: 繰り返し回数
- `error_count`: エラー発生回数

### 2. メタデータ追跡
- セッション開始時刻
- 入力回数
- 最終フェーズ
- 実行統計

## エラー処理戦略

### 1. 復旧可能エラー
- 入力検証エラー
- 一時的なAPI障害
- 部分的な処理失敗

### 2. 復旧不可能エラー
- 認証エラー
- APIキー無効
- システム停止

### 3. エラー応答生成
- フェーズ別対処方法の提示
- ユーザーフレンドリーなメッセージ
- 具体的な解決策の提案

## 並行処理

### 1. 非同期実行
- 全フェーズでasync/await使用
- ノンブロッキング処理
- 効率的なリソース利用

### 2. タスク管理
- 並列タスク実行（最大5並列）
- 依存関係の解決
- 進捗追跡

## 監視・ログ

### 1. 詳細ログ
- フェーズ遷移の記録
- エラー詳細の出力
- パフォーマンス情報

### 2. セッション要約
- 実行統計の表示
- タスク実行結果
- エラー発生状況

## 使用例

```python
# エージェントの初期化
agent = AutonomousAgent(model_name="gpt-4.1")

# セッション実行
await agent.run_session("session_001")

# セッション停止
agent.stop_session()
```

## 拡張ポイント

### 1. 新フェーズ追加
- `AgentPhase`への追加
- `_execute_main_loop`での処理追加

### 2. カスタム処理エンジン
- 各Processorクラスの置き換え
- プラグイン形式での拡張

### 3. 監視機能強化
- メトリクス収集
- 外部監視システム連携

## 関連クラス
- `AgentState`: 状態管理
- 各Processorクラス: フェーズ別処理
- `MCPManager`: 外部ツール統合 