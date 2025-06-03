"""
Azure OpenAI Serviceの動作確認用テストスクリプト
基本的なチャット機能をテストします
"""
import os
from dotenv import load_dotenv
from openai import AzureOpenAI

def test_chat_completion():
    """チャット補完のテスト"""
    try:
        # 環境変数の読み込み
        load_dotenv()
        
        # 環境変数の確認
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        model_name = os.getenv("DEPLOY_MODEL_NAME")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        print("\n🔍 環境変数の確認:")
        print(f"APIキー: {api_key[:10]}..." if api_key else "❌ APIキーが設定されていません")
        print(f"エンドポイント: {endpoint}" if endpoint else "❌ エンドポイントが設定されていません")
        print(f"モデル名: {model_name}" if model_name else "❌ モデル名が設定されていません")
        print(f"APIバージョン: {api_version}")
        
        if not all([api_key, endpoint, model_name]):
            print("\n❌ 必要な環境変数が設定されていません")
            return
        
        # クライアントの初期化
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        
        # テストメッセージ（systemロールを使用せず、userロールのみを使用）
        messages = [
            {"role": "user", "content": "あなたは親切なアシスタントです。こんにちは！1+1は何ですか？"}
        ]
        
        print("\n🤖 チャットリクエスト送信中...")
        print(f"ユーザーメッセージ: {messages[0]['content']}")
        
        # チャット補完の実行（temperatureパラメータを削除）
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_completion_tokens=65536  # より長い応答を可能にするため65536に設定
        )
        
        # 結果の表示
        print("\n✨ レスポンス:")
        print(f"回答: {response.choices[0].message.content}")
        print(f"\n📊 使用トークン数:")
        print(f"入力トークン: {response.usage.prompt_tokens}")
        print(f"出力トークン: {response.usage.completion_tokens}")
        print(f"合計トークン: {response.usage.total_tokens}")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
        import traceback
        print(f"\n詳細なエラー情報:\n{traceback.format_exc()}")

if __name__ == "__main__":
    print("\n🚀 Azure OpenAI Serviceテストを開始します...")
    test_chat_completion()
    print("\n✨ テスト完了") 