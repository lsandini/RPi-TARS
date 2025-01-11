# TARS: Voice-Activated AI Assistant

## Overview

TARS is an advanced voice-activated AI assistant that leverages multiple cutting-edge technologies to provide an interactive conversational experience. The assistant uses wake word detection, speech recognition, AI-powered responses, and text-to-speech capabilities.

## Key Features

- Wake word detection using Porcupine
- Speech recognition with Vosk
- AI responses powered by OpenAI
- Text-to-speech output using Google Cloud Text-to-Speech
- Continuous conversation mode
- Automatic timeout and conversation limit management

## Prerequisites

### Hardware Requirements
- Microphone input device
- Speaker or audio output device

### Software Requirements
- Python 3.8+
- Linux operating system (tested on Ubuntu)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/tars-assistant.git
cd tars-assistant
```

### 2. Install System Dependencies
Before installing Python dependencies, you may need to install some system packages:

For Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y \
    python3-pip \
    portaudio19-dev \
    python3-pyaudio \
    python3-dev \
    libportaudio2 \
    libasound2-dev
```

For Fedora/RHEL:
```bash
sudo dnf install -y \
    python3-pip \
    portaudio-devel \
    python3-pyaudio \
    alsa-lib-devel
```

### 3. Install Python Dependencies
```bash
pip3 install -r requirements.txt
```

**Note:** If you encounter permission issues, use `pip3 install --user -r requirements.txt`

### 4. Download Required Models

#### Vosk Model
1. Download Vosk speech recognition models:
   ```bash
   # Full Version 22 (Recommended, Default)
   wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip
   unzip vosk-model-en-us-0.22.zip
   mv vosk-model-en-us-0.22 vosk-model-22

   # Small Version (Lightweight Alternative)
   wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
   unzip vosk-model-small-en-us-0.15.zip
   mv vosk-model-small-en-us-0.15 vosk-model-15
   ```

2. Ensure you have two model directories:
   - `vosk-model-22/` for full version 0.22 (recommended)
   - `vosk-model-15/` for small version

### Running with Different Models

```bash
# Use Version 22 (default)
python3 src/main.py

# Use Small Version
python3 src/main.py -m 15
```

**Note:** 
- The full version (0.22) provides better accuracy
- The small version (0.15) is more lightweight and faster
- Make sure to download and place both model versions in their respective directories before switching

### 5. Set Up API Keys

Create a `.env` file in the project root with the following keys:
```
PICOVOICE_KEY=your_picovoice_access_key
OPENAI_API_KEY=your_openai_api_key
GOOGLE_APPLICATION_CREDENTIALS=google-service-account.json
```

#### Obtaining API Keys

1. **Picovoice Access Key**
   - Visit [Picovoice Console](https://console.picovoice.ai/)
   - Create an account and obtain your Porcupine wake word engine access key

2. **OpenAI API Key**
   - Go to [OpenAI Platform](https://platform.openai.com/)
   - Create an account or log in
   - Navigate to API keys section and generate a new key

3. **Google Cloud Service Account**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Text-to-Speech API
   - Create a service account
   - Download the JSON key file
   - Rename the downloaded file to `google-service-account.json`
   - Place the JSON file in your project root

## Configuration

### Audio Device Index
You may need to adjust the `input_device_index` in the code to match your system's audio input device. Use the following command to list audio devices:
```bash
python3 -c "import pyaudio; p = pyaudio.PyAudio(); print('\n'.join([f'{i}: {p.get_device_info_by_index(i)['name']}' for i in range(p.get_device_count())]))"
```

## Running the Assistant

### Basic Run
```bash
python3 src/main.py
```

### Specify Vosk Model Version
You can choose between two Vosk model versions:
- Version 22 (default): More accurate, larger size
- Version 15: Lighter, faster

```bash
# Use Version 22 (default)
python3 src/main.py

# Use Version 15
python3 src/main.py -m 15
```

### Using the Run Script
```bash
chmod +x run.sh
./run.sh
```
**Note:** Modify `run.sh` to include model version if needed.

### Usage
- Say "Jarvis" to activate the assistant
- Speak your command or question
- The assistant will respond verbally
- Say "thank you" or "goodbye" to end the conversation

## Dependencies

- pvporcupine: Wake word detection
- vosk: Speech recognition
- pyaudio: Audio input/output
- openai: AI response generation
- python-dotenv: Environment variable management
- google-cloud-texttospeech: Text-to-speech conversion

## Troubleshooting

- Ensure all API keys are correctly set
- Check microphone permissions
- Verify audio device index
- Make sure all dependencies are installed

## Limitations

- Requires a stable internet connection
- Performance depends on microphone quality
- Limited to English language
- Conversation has a 5-command or 10-second timeout

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Insert your license here]

## Acknowledgments

- Picovoice for Porcupine wake word engine
- OpenAI for language model
- Vosk for speech recognition
- Google Cloud for Text-to-Speech