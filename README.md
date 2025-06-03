# LangGraph Autonomous Agent

## セットアップ

### 必要なパッケージのインストール

```bash
# 仮想環境の作成（推奨）
python -m venv venv
source venv/bin/activate  # Linuxの場合
.\venv\Scripts\activate   # Windowsの場合

# パッケージのインストール
pip install -r requirements.txt
```

### 環境変数の設定

`.env`ファイルを作成し、以下の環境変数を設定してください：

```env
# Azure OpenAI Service設定
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com
DEPLOY_MODEL_NAME=your-model-name
AZURE_OPENAI_API_VERSION=2024-02-15-preview  # オプション
```

## 使用方法

### LLM接続テスト

```bash
python -m src.test.test_llm_connection
``` 