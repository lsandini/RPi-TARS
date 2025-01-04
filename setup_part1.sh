#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[1;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up Voice Assistant Project...${NC}"

# Create project structure
echo -e "${GREEN}Creating project structure...${NC}"
mkdir -p {src/{audio,speech,ai,utils},config,tests,logs}

# Create Python package files
touch src/__init__.py
touch src/audio/__init__.py
touch src/speech/__init__.py
touch src/ai/__init__.py
touch src/utils/__init__.py
touch tests/__init__.py

# Create Python source files
cat << 'EOF' > src/speech/stt.py
import vosk
import sounddevice as sd
import json
import numpy as np
import logging
import queue
import threading

class SpeechToText:
    def __init__(self, model_path, sample_rate=16000, device=None):
        logging.info("Initializing Speech-to-Text")
        try:
            vosk.SetLogLevel(-1)
            self.model = vosk.Model(model_path)
            self.sample_rate = sample_rate
            self.device = device
            self.text_queue = queue.Queue()
            self.stop_event = threading.Event()
            logging.info("Speech-to-Text initialized successfully")
        except Exception as e:
            logging.error(f"STT initialization error: {e}")
            raise

    def start_recognition(self, callback_fn=None):
        logging.info("Starting speech recognition")
        rec = vosk.KaldiRecognizer(self.model, self.sample_rate)
        def audio_callback(indata, frames, time, status):
            if status:
                logging.warning(f"Audio input status: {status}")
                return
            data_bytes = indata.astype(np.int16).tobytes()
            try:
                if rec.AcceptWaveform(data_bytes):
                    result = json.loads(rec.Result())
                    text = result.get('text', '').strip()
                    if text:
                        logging.info(f"Recognized speech: {text}")
                        self.text_queue.put(text)
                        if callback_fn:
                            callback_fn(text)
            except Exception as e:
                logging.error(f"Error processing audio: {e}")
        try:
            with sd.InputStream(samplerate=self.sample_rate, device=self.device,
                              dtype='int16', channels=1, callback=audio_callback):
                logging.info("Microphone stream opened. Listening...")
                print("Listening... Speak now.")
                while not self.stop_event.is_set():
                    threading.Event().wait(1)
        except Exception as e:
            logging.error(f"Speech recognition error: {e}")
            raise

    def stop_recognition(self):
        self.stop_event.set()

    def get_recognized_text(self, timeout=1):
        try:
            return self.text_queue.get(timeout=timeout)
        except queue.Empty:
            return None
EOF

cat << 'EOF' > src/speech/tts.py
from google.cloud import texttospeech
import os
import logging

class TextToSpeech:
    def __init__(self, credentials_path=None):
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        elif 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
            credentials_path = os.path.join(os.path.dirname(__file__), 'google-service-account.json')
            if os.path.exists(credentials_path):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
            else:
                raise FileNotFoundError("Google Cloud credentials not found")
        self.client = texttospeech.TextToSpeechClient()
        logging.info("Text-to-Speech initialized successfully")

    def synthesize_speech(self, text, output_file='/tmp/google_tts_output.wav', language_code='en-US'):
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16)
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config)
            with open(output_file, 'wb') as out:
                out.write(response.audio_content)
                logging.info(f'Audio content written to file {output_file}')
            volume = os.getenv('AUDIO_VOLUME', '50')
            os.system(f'amixer -q sset PCM {volume}%')
            os.system(f'aplay -D hw:seeed2micvoicec {output_file}')
        except Exception as e:
            logging.error(f"Error in speech synthesis: {e}")
            raise
EOF

cat << 'EOF' > requirements.txt
# Core functionality
pvporcupine==2.2.0
pvrecorder==1.1.1
vosk==0.3.45
openai==1.59.3
anthropic==0.3.0
google-cloud-texttospeech==2.14.1
python-dotenv==1.0.0
sounddevice==0.4.6
numpy==1.24.3
pytest==7.4.0

# OpenAI dependencies
httpx==0.25.2
httpcore==1.0.2
anyio==4.1.0
sniffio==1.3.0
pydantic==2.10.3
pydantic-core==2.27.1
tqdm==4.66.5
typing-extensions==4.12.2
distro==1.8.0
certifi==2023.7.22
EOF

cat << 'EOF' > .env.template
# API Keys
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
PICOVOICE_ACCESS_KEY=your_picovoice_key_here

# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=path_to_your_credentials.json

# Audio Settings
SAMPLE_RATE=16000
CHANNELS=1
FRAME_LENGTH=512

# Wake Word Settings
WAKE_WORD_SENSITIVITY=0.5

# Paths
VOSK_MODEL_PATH=path_to_vosk_model

# Audio Volume
AUDIO_VOLUME=50
EOF

# Create start script
cat << 'EOF' > start_assistant.sh
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python3 src/main.py
EOF
chmod +x start_assistant.sh

# Initialize git repository
git init
touch logs/.gitkeep

echo -e "${GREEN}Project structure created successfully!${NC}"
echo -e "${BLUE}Next steps:${NC}"
echo "1. Copy .env.template to .env and add your API keys"
echo "2. Create virtual environment: python -m venv venv"
echo "3. Activate virtual environment and install dependencies"
echo "4. Run the assistant: python src/main.py"

# Run part 2 if part 1 was successful
if [ $? -eq 0 ]; then
    echo -e "${BLUE}Part 1 completed successfully, starting Part 2...${NC}"
    ./setup_part2.sh
else
    echo -e "${RED}Part 1 failed, stopping setup${NC}"
    exit 1
fi