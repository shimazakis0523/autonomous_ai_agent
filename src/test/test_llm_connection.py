"""
LLM接続テストスクリプト
Azure OpenAI Serviceへの接続と基本的な応答をテストします
"""
import os
import asyncio
import logging
from urllib.parse import urlparse
from dotenv import load_dotenv
from openai import AzureOpenAI
from openai.types.chat import ChatCompletion

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_azure_endpoint(endpoint: str) -> tuple[bool, str]:
    """
    Azure OpenAI Serviceのエンドポイントを検証
    
    Args:
        endpoint: エンドポイントURL
        
    Returns:
        (is_valid, error_message)
    """
    try:
        parsed = urlparse(endpoint)
        
        # 基本的な形式チェック
        if not parsed.netloc.endswith('.openai.azure.com'):
            return False, "Azure OpenAI Serviceのエンドポイントは .openai.azure.com で終わる必要があります"
        
        return True, ""
    except Exception as e:
        return False, f"URLの解析中にエラーが発生: {str(e)}"

async def test_llm_connection():
    """LLM接続テストの実行"""
    try:
        # 環境変数の読み込み
        load_dotenv()
        
        # 必要な環境変数の確認
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        model_name = os.getenv("DEPLOY_MODEL_NAME")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        # 環境変数の検証
        if not api_key:
            logger.error("❌ AZURE_OPENAI_API_KEYが設定されていません")
            print("💡 .envファイルでAPIキーを設定してください")
            return False
            
        if not endpoint:
            logger.error("❌ AZURE_OPENAI_ENDPOINTが設定されていません")
            print("💡 .envファイルでエンドポイントを設定してください")
            return False
            
        if not model_name:
            logger.error("❌ DEPLOY_MODEL_NAMEが設定されていません")
            print("💡 .envファイルでモデル名を設定してください")
            return False
        
        logger.info(f"🔑 APIキー確認済み（最初の10文字）: {api_key[:10]}...")
        logger.info(f"🌐 エンドポイント: {endpoint}")
        logger.info(f"📝 モデル名: {model_name}")
        logger.info(f"📝 APIバージョン: {api_version}")
        
        # エンドポイントの検証
        is_valid, error_message = validate_azure_endpoint(endpoint)
        if not is_valid:
            logger.error(f"❌ Azure OpenAI Serviceのエンドポイントが無効: {error_message}")
            print("\n💡 Azure OpenAI Serviceの正しいエンドポイント形式:")
            print("https://{リソース名}.openai.azure.com")
            return False
        
        # Azure OpenAIクライアントの初期化
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        
        # テストメッセージの送信
        logger.info("🤖 LLMにテストメッセージを送信中...")
        test_message = "こんにちは！これは接続テストです。1+1=?"
        
        response: ChatCompletion = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": test_message}],
            max_tokens=100
        )
        
        # 結果の表示
        logger.info("✅ LLMからの応答を受信")
        print("\n" + "="*50)
        print("📝 テスト結果:")
        print(f"入力: {test_message}")
        print(f"出力: {response.choices[0].message.content}")
        print("="*50 + "\n")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ テスト中にエラーが発生: {str(e)}")
        import traceback
        logger.error(f"詳細なエラー情報:\n{traceback.format_exc()}")
        return False

async def main():
    """メイン関数"""
    print("\n🚀 Azure OpenAI Service接続テストを開始します...\n")
    
    success = await test_llm_connection()
    
    if success:
        print("✨ テスト完了: Azure OpenAI Service接続は正常に機能しています")
    else:
        print("❌ テスト失敗: Azure OpenAI Service接続に問題があります")
        print("\n💡 以下を確認してください:")
        print("  1. .envファイルの設定:")
        print("     - AZURE_OPENAI_API_KEY: APIキー")
        print("     - AZURE_OPENAI_ENDPOINT: https://{リソース名}.openai.azure.com")
        print("     - DEPLOY_MODEL_NAME: モデル名")
        print("     - AZURE_OPENAI_API_VERSION: APIバージョン（オプション、デフォルト: 2024-02-15-preview）")
        print("  2. インターネット接続が正常か")
        print("  3. APIキーが有効か")
        print("  4. エンドポイントのURLが正しいか")
        print("  5. モデル名が正しいか")

if __name__ == "__main__":
    asyncio.run(main()) 