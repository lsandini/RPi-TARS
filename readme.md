# TARS: Voice-Activated AI Assistant

## Overview

TARS is an advanced voice-activated AI assistant inspired by the TARS robot from Interstellar. It leverages multiple cutting-edge technologies to provide an interactive conversational experience with adjustable humor settings and space-themed responses.

## Key Features

- Dual wake word detection ('Jarvis' and custom 'TARS') using Porcupine
- Speech recognition using Google Speech Recognition
- AI responses powered by OpenAI with TARS personality
- Text-to-speech output using Google Cloud Text-to-Speech
- Adjustable humor settings (0-100%)
- Continuous conversation mode
- Automatic timeout and conversation limit management

## Prerequisites

### Hardware Requirements
- Raspberry Pi 4 (recommended)
- ReSpeaker 4-Mic Array (recommended) or USB microphone
- Speaker or audio output device

### Software Requirements
- Raspberry Pi OS (64-bit recommended)
- Python 3.8+

## Installation

### 1. Install System Dependencies
```bash
# Update package lists
sudo apt-get update

# Install audio and speech recognition dependencies
sudo apt-get install -y \
    python3-pip \
    portaudio19-dev \
    python3-pyaudio \
    python3-dev \
    libportaudio2 \
    libasound2-dev \
    flac \
    git

# Install seeed-voicecard drivers (for ReSpeaker 4-Mic Array)
git clone https://github.com/HinTak/seeed-voicecard
cd seeed-voicecard
sudo ./install.sh
sudo reboot
```

### 2. Clone and Setup Repository
```bash
git clone https://github.com/yourusername/RPi-TARS.git
cd RPi-TARS
```

### 3. Install Python Dependencies
```bash
pip3 install -r requirements.txt
```

### 4. Set Up Configuration Files

#### Create .env File
Create a `.env` file in the project root with the following keys:
```
PICOVOICE_KEY=your_picovoice_access_key
OPENAI_API_KEY=your_openai_api_key
GOOGLE_APPLICATION_CREDENTIALS=google-service-account.json
```

#### Setup Google Cloud Credentials
1. Place your `google-service-account.json` file in the project root
2. Ensure the file path matches the GOOGLE_APPLICATION_CREDENTIALS in .env

### 5. Obtain Required API Keys

#### Picovoice Access Key
1. Visit [Picovoice Console](https://console.picovoice.ai/)
2. Create an account and obtain your access key
3. Train your custom wake word (optional)
4. Download and place the .ppn file in project root (if using custom wake word)

#### OpenAI API Key
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Create an account or log in
3. Navigate to API keys section
4. Generate a new key

#### Google Cloud Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Text-to-Speech API
4. Create a service account
5. Download the JSON key file
6. Place it in project root as google-service-account.json

### 6. Run the Assistant
```bash
chmod +x run.sh
./run.sh
```

## Usage

### Wake Words
- Say "Jarvis" or your custom wake word to activate
- Wait for acknowledgment sound

### Commands
- Speak naturally after wake word activation
- You can adjust humor with "set humor to X%" (0-100)
- End conversation with "thank you" or "goodbye"
- Max 5 commands per conversation
- 10-second timeout between commands

### Audio Setup
If using different microphone hardware:
```bash
# List available audio devices
python3 -c "import speech_recognition as sr; print('\n'.join([f'{index}: {name}' for index, name in enumerate(sr.Microphone.list_microphone_names())]))"
```

## Troubleshooting

### Audio Issues
- Verify microphone is recognized: `arecord -l`
- Check speaker output: `aplay -l`
- Test microphone recording: `arecord -D plughw:CARD=seeed4micvoicec,DEV=0 -f S16_LE -r 16000 -c 4 test.wav`
- Test playback: `aplay test.wav`

### Common Problems
- No sound: Check audio output device in playback_command
- Wake word not detected: Verify Picovoice key and .ppn file
- Speech not recognized: Check internet connection
- No response: Verify OpenAI API key
- No voice output: Check Google Cloud credentials

## Limitations

- Requires stable internet connection
- English language only
- 5-command conversation limit
- 10-second timeout between commands
- API rate limits apply (Google Speech, OpenAI)
- Wake word sensitivity may need adjustment

## License

[Insert your license here]

## Acknowledgments

- Interstellar movie for TARS character inspiration
- Picovoice for Porcupine wake word engine
- OpenAI for GPT language model
- Google for Speech Recognition and Text-to-Speech
- Seeed Studio for ReSpeaker hardware/drivers