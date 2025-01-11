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

### 3. Install Python Dependencies
```bash
pip3 install -r requirements.txt
```

### 4. Download Vosk Model
```bash
# Download Small Version
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 vosk-model
```

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
   - Place the JSON file in your project root

### Configuration

#### Audio Device Index
You may need to adjust the `input_device_index` in the code to match your system's audio input device. Use the following command to list audio devices:
```bash
python3 -c "import pyaudio; p = pyaudio.PyAudio(); print('\n'.join([f'{i}: {p.get_device_info_by_index(i)['name']}' for i in range(p.get_device_count())]))"
```

## Running the Assistant

```bash
chmod +x run.sh
./run.sh
```

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