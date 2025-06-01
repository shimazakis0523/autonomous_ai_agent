# InputProcessor クラス設計書

## 概要
ユーザー入力の受付、検証、前処理を担当するフェーズ1の処理エンジン。安全で信頼性の高い入力処理を提供する。

## クラス情報
- **ファイル**: `src/processors/input_processor.py`
- **レイヤ**: Processors（プロセッサー）
- **責務**: 入力受付、検証、前処理、履歴管理

## 主要機能

### 1. 入力処理メイン
```python
async def process_input(self, state: AgentState) -> AgentState
```
- ユーザー入力の受信
- 入力検証の実行
- 前処理の適用
- 状態の更新

### 2. 入力受信
```python
def _receive_user_input(self) -> str
```
- 標準入力からの受信
- ユーザーフレンドリーなプロンプト表示
- 中断処理の対応

### 3. 入力検証
```python
def _validate_input(self, user_input: str) -> None
```
- 長さ制限チェック
- 危険コマンド検出
- 空入力の拒否

### 4. 前処理
```python
def _preprocess_input(self, user_input: str) -> str
```
- 空白の正規化
- 文字エンコーディング統一
- 特殊文字の処理

## 設定パラメータ

### 1. 入力制限
- `max_input_length`: 最大入力長（デフォルト: 5000文字）
- `min_input_length`: 最小入力長（デフォルト: 1文字）
- `context_window`: 履歴保持数（デフォルト: 10件）

### 2. セキュリティ
- 危険コマンドパターンの定義
- 実行可能コードの検出
- インジェクション攻撃の防止

## 履歴管理

### 1. 入力履歴
```python
def _add_to_history(self, user_input: str, state: AgentState) -> None
```
- タイムスタンプ付き履歴保存
- セッションID関連付け
- 自動サイズ制限

### 2. 文脈要約
```python
def get_context_summary(self) -> str
```
- 最近の対話履歴要約
- 文脈継続性の提供
- 効率的な情報圧縮

### 3. 統計情報
```python
def get_input_statistics(self) -> Dict[str, Any]
```
- 入力回数・文字数統計
- 平均入力長の計算
- 最近のアクティビティ追跡

## セキュリティ機能

### 1. 危険コマンド検出
検出パターン:
- `rm -rf`: ファイル削除
- `del /`: Windows削除
- `format c:`: フォーマット
- `__import__`: Python実行
- `exec(`, `eval(`: コード実行

### 2. 入力サニタイゼーション
- SQLインジェクション防止
- XSS攻撃防止
- コマンドインジェクション防止

## エラーハンドリング

### 1. 入力エラー
- 空入力の処理
- 長すぎる入力の拒否
- 不正文字の検出

### 2. システムエラー
- 入力中断の処理
- I/Oエラーの対応
- メモリ不足の対応

## パフォーマンス

### 1. 効率的処理
- 最小限の文字列操作
- メモリ使用量の最適化
- 高速な検証処理

### 2. スケーラビリティ
- 大量入力への対応
- 長時間セッションの支援
- メモリリーク防止

## 使用例

```python
# プロセッサーの初期化
processor = InputProcessor()

# 入力処理の実行
state = await processor.process_input(initial_state)

# 履歴の取得
context = processor.get_context_summary()
stats = processor.get_input_statistics()

# 履歴のクリア
processor.clear_history()
```

## 設計原則

### 1. 安全性優先
- 全入力の厳格な検証
- セキュリティホールの排除
- 防御的プログラミング

### 2. ユーザビリティ
- 分かりやすいエラーメッセージ
- 直感的な入力プロンプト
- 適切なフィードバック

### 3. 拡張性
- 新しい検証ルールの追加
- カスタム前処理の実装
- プラグイン形式の対応

## 関連クラス
- `AgentState`: 状態管理
- `IntentAnalyzer`: 次フェーズ処理
- `AutonomousAgent`: 全体制御 