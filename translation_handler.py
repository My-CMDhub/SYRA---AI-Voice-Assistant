"""
Translation Handler that works with multiple translation services
"""
import requests
from langdetect import detect

class TranslationHandler:
    def __init__(self):
        self.google_translate_url = "https://translate.googleapis.com/translate_a/single"
        
    def translate_text(self, text, src='auto', dest='en'):
        """
        Translate text using Google Translate API directly
        Fallback when googletrans package has conflicts
        """
        if src == 'auto':
            try:
                src = detect(text)
            except:
                src = 'auto'
        
        if src == dest:
            return text
            
        try:
            # Using Google Translate's public API endpoint
            params = {
                'client': 'gtx',
                'sl': src,
                'tl': dest,
                'dt': 't',
                'q': text
            }
            
            response = requests.get(self.google_translate_url, params=params)
            
            if response.status_code == 200:
                result = response.json()
                translated_text = result[0][0][0]
                return translated_text
            else:
                return text  # Return original if translation fails
                
        except Exception as e:
            print(f"Translation error: {e}")
            return text  # Return original if translation fails
    
    def detect_language(self, text):
        """Detect the language of the input text"""
        try:
            return detect(text)
        except:
            return 'en'  # Default to English if detection fails

# Test the translation handler
if __name__ == "__main__":
    handler = TranslationHandler()
    
    # Test translation
    hindi_text = "नमस्ते"
    english_text = handler.translate_text(hindi_text, src='hi', dest='en')
    print(f"Hindi: {hindi_text} -> English: {english_text}")
    
    # Test language detection
    lang = handler.detect_language("Hello, how are you?")
    print(f"Detected language: {lang}")
