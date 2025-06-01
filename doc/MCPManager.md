# MCPManager クラス設計書

## 概要
Model Context Protocol（MCP）を通じた外部ツール統合を管理するフェーズ4の処理エンジン。5つの外部ツールとの連携を提供する。

## クラス情報
- **ファイル**: `src/external/mcp_manager.py`
- **レイヤ**: External（外部連携）
- **責務**: 外部ツール管理、MCP通信、リソース制御

## 統合ツール

### 1. ファイル操作ツール
- **機能**: ファイル読み書き、ディレクトリ操作
- **用途**: ドキュメント処理、設定ファイル管理
- **制限**: セキュリティサンドボックス内

### 2. ウェブ検索ツール
- **機能**: リアルタイム情報検索
- **用途**: 最新情報取得、事実確認
- **API**: 検索エンジンAPI連携

### 3. コード実行ツール
- **機能**: Python/JavaScript実行
- **用途**: 計算処理、データ変換
- **制限**: 安全な実行環境

### 4. データ分析ツール
- **機能**: CSV/JSON解析、統計処理
- **用途**: データ可視化、レポート生成
- **ライブラリ**: pandas, numpy, matplotlib

### 5. テキスト処理ツール
- **機能**: 自然言語処理、翻訳
- **用途**: 文書要約、言語変換
- **エンジン**: 専用NLPライブラリ

## 主要機能

### 1. 接続初期化
```python
async def initialize_connections(self, state: AgentState) -> AgentState
```
- MCP接続の確立
- ツール可用性の確認
- フォールバック設定

### 2. ツール実行
```python
async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]
```
- 指定ツールの実行
- パラメータ検証
- 結果の正規化

### 3. 並列実行
```python
async def execute_tools_parallel(self, tool_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]
```
- 複数ツールの同時実行
- 依存関係の解決
- 効率的なリソース利用

### 4. 接続管理
```python
async def cleanup_connections(self) -> None
```
- 接続のクリーンアップ
- リソースの解放
- 安全な終了処理

## 動作モード

### 1. 本格モード（Production）
- 実際の外部サービス連携
- 完全な機能提供
- 認証・課金対応

### 2. モックモード（Mock）
- シミュレーション実行
- 開発・テスト用
- 外部依存なし

### 3. ハイブリッドモード
- 利用可能ツールのみ実行
- 自動フォールバック
- 部分的機能提供

## セキュリティ

### 1. サンドボックス実行
- 隔離された実行環境
- ファイルシステム制限
- ネットワークアクセス制御

### 2. 入力検証
- パラメータの厳格チェック
- インジェクション攻撃防止
- 型安全性の確保

### 3. 出力サニタイゼーション
- 機密情報の除去
- 安全な結果返却
- ログの匿名化

## エラーハンドリング

### 1. 接続エラー
- タイムアウト処理
- 再試行メカニズム
- フォールバック実行

### 2. 実行エラー
- 例外の適切な処理
- 部分的失敗の対応
- エラー情報の構造化

### 3. リソースエラー
- メモリ不足の対応
- CPU使用率制限
- 同時実行数制御

## パフォーマンス最適化

### 1. 接続プール
- 再利用可能な接続
- 効率的なリソース管理
- 接続数の最適化

### 2. キャッシュ機能
- 結果のキャッシュ
- 重複実行の回避
- TTL管理

### 3. 並列処理
- 非同期実行
- 依存関係の最適化
- スループット向上

## 監視・ログ

### 1. 実行統計
- ツール使用頻度
- 実行時間の測定
- 成功/失敗率

### 2. パフォーマンス監視
- レスポンス時間
- リソース使用量
- ボトルネック検出

### 3. セキュリティログ
- アクセス記録
- 異常検知
- 監査証跡

## 使用例

```python
# マネージャーの初期化
manager = MCPManager()

# 接続の初期化
state = await manager.initialize_connections(state)

# 単一ツール実行
result = await manager.execute_tool("file_operations", {
    "action": "read",
    "path": "document.txt"
})

# 並列実行
results = await manager.execute_tools_parallel([
    {"tool": "web_search", "query": "最新ニュース"},
    {"tool": "data_analysis", "data": "sales.csv"}
])

# クリーンアップ
await manager.cleanup_connections()
```

## 設定パラメータ

### 1. 接続設定
- `connection_timeout`: 接続タイムアウト（30秒）
- `max_retries`: 最大再試行回数（3回）
- `pool_size`: 接続プールサイズ（10）

### 2. 実行制限
- `max_parallel_tools`: 最大並列数（5）
- `execution_timeout`: 実行タイムアウト（300秒）
- `memory_limit`: メモリ制限（1GB）

## 拡張ポイント

### 1. 新ツール追加
- ツール定義の追加
- 実行ロジックの実装
- テストケースの作成

### 2. プロトコル拡張
- 新しいMCPバージョン対応
- カスタムプロトコルの実装
- 互換性の維持

## 関連クラス
- `AgentState`: 状態管理
- `TaskOrchestrator`: タスク実行制御
- `PlanGenerator`: 実行計画生成 