# 自律型AIエージェントシステム - プロジェクト概要

## システム概要
LangGraphベースの自律型AIエージェントシステム。7フェーズの処理パイプラインを通じて、ユーザーの自然言語入力を理解し、適切なタスクを実行して結果を返す高度なAIシステムです。

## プロジェクト構造

```
langgraph/
├── main.py                     # メインエントリーポイント
├── requirements.txt            # 依存関係
├── .env                        # 環境変数（APIキー等）
├── README.md                   # プロジェクト説明
│
├── src/                        # ソースコード（レイヤ分け）
│   ├── __init__.py
│   ├── core/                   # コアレイヤ
│   │   ├── __init__.py
│   │   ├── agent_state.py      # 状態管理
│   │   └── autonomous_agent.py # メインエージェント
│   ├── processors/             # プロセッサーレイヤ
│   │   ├── __init__.py
│   │   ├── input_processor.py  # 入力処理
│   │   ├── intent_analyzer.py  # 意図分析
│   │   ├── plan_generator.py   # 計画生成
│   │   ├── task_orchestrator.py # タスク実行
│   │   ├── result_processor.py # 結果処理
│   │   └── response_generator.py # 応答生成
│   ├── external/               # 外部連携レイヤ
│   │   ├── __init__.py
│   │   └── mcp_manager.py      # MCP管理
│   └── utils/                  # ユーティリティレイヤ
│       └── __init__.py
│
├── doc/                        # 設計書・ドキュメント
│   ├── ProjectOverview.md      # プロジェクト概要
│   ├── AgentState.md           # 状態管理設計書
│   ├── AutonomousAgent.md      # メインエージェント設計書
│   ├── InputProcessor.md       # 入力処理設計書
│   └── MCPManager.md           # MCP管理設計書
│
└── artifact/                   # エージェント生成ファイル
    ├── README.md               # artifact説明
    ├── generated/              # 生成ファイル
    │   ├── documents/          # 文書・レポート
    │   ├── code/               # 生成コード
    │   ├── data/               # データファイル
    │   └── images/             # 画像・図表
    ├── temp/                   # 一時ファイル
    ├── logs/                   # 実行ログ
    └── exports/                # エクスポート用
```

## アーキテクチャ

### レイヤ構成

#### 1. Core（コア）レイヤ
- **責務**: システムの中核機能
- **コンポーネント**: 
  - `AgentState`: 状態管理
  - `AutonomousAgent`: メイン制御

#### 2. Processors（プロセッサー）レイヤ
- **責務**: 各フェーズの処理エンジン
- **コンポーネント**:
  - `InputProcessor`: 入力処理
  - `IntentAnalyzer`: 意図分析
  - `PlanGenerator`: 計画生成
  - `TaskOrchestrator`: タスク実行
  - `ResultProcessor`: 結果処理
  - `ResponseGenerator`: 応答生成

#### 3. External（外部連携）レイヤ
- **責務**: 外部システムとの統合
- **コンポーネント**:
  - `MCPManager`: Model Context Protocol管理

#### 4. Utils（ユーティリティ）レイヤ
- **責務**: 共通機能・ヘルパー
- **コンポーネント**: 今後拡張予定

### 7フェーズ処理パイプライン

1. **INPUT_PROCESSING**: ユーザー入力の受付・検証・前処理
2. **INTENT_ANALYSIS**: 意図の理解・分類・エンティティ抽出
3. **PLAN_GENERATION**: タスク分解・実行計画の生成
4. **MCP_INITIALIZATION**: 外部ツールの初期化・接続確立
5. **TASK_EXECUTION**: 並列タスク実行・進捗管理
6. **RESULT_PROCESSING**: 結果統合・品質評価・洞察生成
7. **RESPONSE_GENERATION**: 最終応答の生成・最適化

## 主要機能

### 1. 自然言語理解
- 12カテゴリの意図分類
- エンティティ抽出
- 文脈理解
- 曖昧性解決

### 2. 自律的タスク実行
- 複雑タスクの自動分解
- 依存関係の解決
- 並列実行（最大5並列）
- 進捗追跡

### 3. 外部ツール統合
- ファイル操作
- ウェブ検索
- コード実行
- データ分析
- テキスト処理

### 4. 品質保証
- 結果の品質評価
- 信頼度スコアリング
- エラー検出・回復
- 一貫性チェック

### 5. 適応的応答
- ユーザーレベル別対応
- 文脈に応じた詳細度調整
- 多様な出力形式
- 継続的改善

## 技術スタック

### 基盤技術
- **Python 3.8+**: メイン言語
- **LangGraph 0.4.5**: ワークフロー管理
- **LangChain**: LLM統合
- **OpenAI GPT-4.1**: 言語モデル

### 主要ライブラリ
- `langchain-openai`: OpenAI統合
- `python-dotenv`: 環境変数管理
- `asyncio`: 非同期処理
- `typing`: 型安全性

### 開発・運用
- `logging`: ログ管理
- `datetime`: 時間処理
- `json`: データ交換
- `uuid`: 一意識別子

## セキュリティ

### 1. 入力検証
- 危険コマンドの検出
- インジェクション攻撃防止
- 入力サニタイゼーション

### 2. 実行制御
- サンドボックス実行
- リソース制限
- タイムアウト管理

### 3. データ保護
- 機密情報のマスキング
- ログの匿名化
- 安全なファイル操作

## パフォーマンス

### 1. 並列処理
- 非同期実行
- 効率的なリソース利用
- スケーラブルな設計

### 2. 最適化
- キャッシュ機能
- 重複処理の回避
- メモリ効率

### 3. 監視
- 実行時間の測定
- リソース使用量追跡
- ボトルネック検出

## 拡張性

### 1. 新フェーズ追加
- プラグイン形式
- 最小限の変更
- 後方互換性

### 2. 新ツール統合
- MCP準拠
- 標準化されたインターフェース
- 動的ロード

### 3. カスタマイズ
- 設定ベースの調整
- ユーザー定義ルール
- 業界特化対応

## 使用方法

### 1. 環境設定
```bash
# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定
cp env.example .env
# .envファイルでOPENAI_API_KEYを設定
```

### 2. 実行
```bash
# メインプログラムの実行
python main.py
```

### 3. 対話
```
🤖 自律型AIエージェントです。何をお手伝いしましょうか？
👤 あなた: データ分析のレポートを作成してください
```

## 今後の展開

### 1. 機能拡張
- 音声入出力対応
- 画像・動画処理
- リアルタイム学習

### 2. 統合強化
- 企業システム連携
- クラウドサービス統合
- API提供

### 3. 運用改善
- 監視ダッシュボード
- 自動スケーリング
- 障害復旧自動化

## 関連ドキュメント
- [AgentState設計書](./AgentState.md)
- [AutonomousAgent設計書](./AutonomousAgent.md)
- [InputProcessor設計書](./InputProcessor.md)
- [MCPManager設計書](./MCPManager.md)
- [Artifactディレクトリ説明](../artifact/README.md) 