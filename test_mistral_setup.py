"""
Test script to verify Mistral AI setup and API connectivity
"""
import os
from mistral_config import MistralConfig

def test_mistral_connection():
    print("🔧 Testing Mistral AI Setup...")
    
    # Check if API key is available from environment variable
    api_key = os.getenv('MISTRAL_API_KEY')
    if not api_key:
        print("❌ MISTRAL_API_KEY environment variable not found.")
        print("📋 Please set your API key:")
        print("   export MISTRAL_API_KEY='your_api_key_here'")
        print("   Or add it to your .env file")
        return False
    
    try:
        # Initialize Mistral config with the API key
        config = MistralConfig(api_key=api_key)
        print("✅ Mistral client initialized successfully")
        
        # Test API connection
        print("🌐 Testing API connection...")
        success, response = config.test_connection()
        
        if success:
            print(f"✅ API Connection successful!")
            print(f"📝 Response: {response}")
            return True
        else:
            print(f"❌ API Connection failed: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Error initializing Mistral: {e}")
        return False

def test_translation_compatibility():
    print("\n🔧 Testing translation handler...")
    try:
        from translation_handler import TranslationHandler
        translator = TranslationHandler()
        result = translator.translate_text("Hello", src='en', dest='hi')
        print(f"✅ Translation handler working: 'Hello' -> '{result}'")
        return True
    except Exception as e:
        print(f"❌ Translation handler issue: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Edith Assistant - Mistral AI Integration Test")
    print("=" * 50)
    
    # Test translation first
    translation_ok = test_translation_compatibility()
    
    # Test Mistral
    mistral_ok = test_mistral_connection()
    
    print("\n" + "=" * 50)
    if mistral_ok and translation_ok:
        print("🎉 All systems ready! You can proceed with AI integration.")
    else:
        print("⚠️  Some issues found. Please resolve them before proceeding.")
        
    print("\n📋 Next steps:")
    print("1. Set your Mistral API key: export MISTRAL_API_KEY='your_key'")
    print("2. Run this test again to verify everything works")
    print("3. Then we'll integrate AI into your assistant")
