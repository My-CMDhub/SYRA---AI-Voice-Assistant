# SYRA - Smart Voice Assistant

**SYRA** (Smart Intelligent Response Assistant) is an advanced AI-powered voice assistant that combines natural language processing, intelligent command detection, and system integration to provide a seamless conversational experience.

## 🌟 Features

### Core Capabilities
- **🗣️ Natural Voice Interaction**: Advanced speech recognition with Google Speech API
- **🧠 AI-Powered Conversations**: Powered by Mistral AI with contextual understanding
- **🎯 Smart Command Detection**: 4-tier priority system for accurate intent recognition
- **🌐 Web & YouTube Integration**: Intelligent routing between web searches and video content
- **🌤️ Weather Integration**: Real-time weather data with automatic location extraction
- **📱 Application Control**: Open/close macOS applications with voice commands
- **🌍 Multi-language Support**: Hindi-English translation support
- **⚡ Optimized Performance**: Fast response times with smart caching

### Advanced Features
- **Contextual Conversations**: Maintains conversation history for natural dialogue flow
- **Intelligent Query Parsing**: Distinguishes between video searches, web searches, and app commands
- **Timeout Management**: Graceful handling of user inactivity with contextual check-ins
- **Location Extraction**: Automatically extracts locations from weather queries
- **Fallback Systems**: Multiple fallback mechanisms for reliability
- **Conversation Logging**: Detailed logs with performance metrics

## 🚀 Getting Started

### Prerequisites

- **Operating System**: macOS (due to AppleScript integration)
- **Python**: 3.8 or higher
- **Microphone**: Required for voice input
- **Internet Connection**: Required for AI services and APIs

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Assistance
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up API Key**
   - Get your Mistral AI API key from [Mistral AI](https://mistral.ai/)
   - Update the `MISTRAL_API_KEY` in `Assistance_SYRA_Final.py` or set as environment variable

4. **Configure microphone permissions** (macOS)
   - Go to System Preferences → Security & Privacy → Privacy
   - Click "Microphone" and enable access for Terminal/Python/VS Code

### Quick Start

1. **Run SYRA**
   ```bash
   python Assistance_SYRA_Final.py
   ```

2. **Wait for initialization**
   ```
   🤖 Initializing SYRA Final Version...
   Testing microphone access...
   ✅ Microphone access granted!
   ✅ SYRA Final Version ready!
   ```

3. **Start talking!**
   - "Hey SYRA, what's the weather in Melbourne?"
   - "Search for Tesla news on YouTube"
   - "Open Safari"
   - "Find out video of iPhone reviews"

## 🎯 Usage Examples

### Voice Commands

#### Weather Queries
```
"What's the weather in Sydney?"
"Find out weather of Melbourne"
"How's the weather in London today?"
```

#### Web Searches
```
"Search for Tesla stock price"
"Find information about climate change"
"Look up iPhone 15 reviews"
```

#### Video Searches
```
"Search video of funny cats on YouTube"
"Find out video of Tesla Model 3"
"Watch Avengers trailer"
```

#### Application Control
```
"Open Safari"
"Close YouTube"
"Launch Calculator"
"Open Gmail"
```

#### General Conversations
```
"How are you?"
"Tell me a joke"
"What can you do?"
```

## 🏗️ Architecture

### Core Components

1. **Voice Processing Layer**
   - Speech recognition using Google Speech API
   - Text-to-speech with Google TTS
   - Language detection and translation

2. **AI Intelligence Layer**
   - Mistral AI for natural language understanding
   - Context-aware conversation management
   - Intent classification with 4-tier priority system

3. **Command Execution Layer**
   - System integration via subprocess and AppleScript
   - Web browser automation
   - Application lifecycle management

4. **Data Integration Layer**
   - Open-Meteo API for weather data
   - YouTube integration for video searches
   - Web search via Google

### Query Processing Pipeline

```
Voice Input → Speech Recognition → Language Detection → AI Processing → Intent Classification → Command Execution → Response Generation → Text-to-Speech
```

## 🔧 Configuration

### API Configuration

Update `mistral_config.py` to customize AI behavior:

```python
# Model settings
self.model = "mistral-large-latest"
self.max_tokens = 150
self.temperature = 0.6
```

### Voice Settings

Modify speech settings in `Assistance_SYRA_Final.py`:

```python
# Speech recognition settings
recognizer.energy_threshold = 300
recognizer.pause_threshold = 0.6

# TTS speed settings
os.system('afplay -r 1.2 output.mp3')  # 1.2x speed
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Microphone Access Denied
**Problem**: `❌ Microphone access denied or not available!`

**Solution**:
1. Open System Preferences → Security & Privacy → Privacy
2. Click "Microphone" in the left sidebar
3. Find your terminal/Python application in the list
4. Check the box to enable microphone access
5. Restart the application

#### 2. API Key Error
**Problem**: `ValueError: Mistral API key is required`

**Solution**:
1. Ensure you have a valid Mistral AI API key
2. Update the key in `Assistance_SYRA_Final.py`:
   ```python
   MISTRAL_API_KEY = "your-api-key-here"
   ```
3. Or set as environment variable:
   ```bash
   export MISTRAL_API_KEY="your-api-key-here"
   ```

#### 3. Speech Recognition Issues
**Problem**: "Could not understand audio" or "Could not connect to the server"

**Solutions**:
- Check internet connection (required for Google Speech API)
- Ensure microphone is working properly
- Speak clearly and avoid background noise
- Try adjusting microphone sensitivity in system settings

#### 4. Application Not Opening
**Problem**: Applications fail to open with voice commands

**Solutions**:
- Ensure applications are installed in `/Applications/` folder
- Check application names match exactly (case-sensitive)
- Try using full application names: "Microsoft Word" instead of "Word"
- Verify macOS accessibility permissions

#### 5. Weather Data Not Available
**Problem**: Weather queries return errors

**Solutions**:
- Check internet connection
- Verify location name is correct and recognizable
- Try major city names if specific locations don't work
- Wait a moment and try again (API rate limiting)

#### 6. TTS/Audio Issues
**Problem**: No voice output or audio errors

**Solutions**:
- Check system audio settings
- Ensure speakers/headphones are connected
- Try installing `mpg123` as fallback: `brew install mpg123`
- Verify `afplay` is available (built into macOS)

### Performance Optimization

#### For Better Response Times
1. **Optimize internet connection** - AI requires internet access
2. **Close unnecessary applications** - Frees up system resources
3. **Speak clearly** - Reduces recognition retry attempts
4. **Use specific commands** - More direct commands process faster

#### For Better Accuracy
1. **Use natural language** - SYRA understands conversational queries
2. **Be specific with locations** - "Melbourne Australia" vs just "Melbourne"
3. **Include context** - "Search video of Tesla" vs just "Tesla"
4. **Wait for response** - Let SYRA finish before next command

### Debug Mode

Enable debug output by adding this to your command:
```bash
python Assistance_SYRA_Final.py --verbose
```

Check logs in `conversations.txt` for detailed interaction history.

## 🔄 Updates and Maintenance

### Updating Dependencies
```bash
pip install --upgrade -r requirements.txt
```

### Checking API Status
Test Mistral AI connection:
```bash
python test_mistral_setup.py
```

### Clearing Conversation History
Delete the log file to start fresh:
```bash
rm conversations.txt
```

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request


## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.



---

**Built with ❤️ by Dhruv** - Making AI assistance more natural and powerful.
