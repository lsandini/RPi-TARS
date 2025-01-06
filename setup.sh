#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[1;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Error handling
set -e
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
trap 'echo "\"${last_command}\" command failed with exit code $?."' EXIT

log_info() {
   echo -e "${BLUE}[INFO] $1${NC}"
}

log_success() {
   echo -e "${GREEN}[SUCCESS] $1${NC}"
}

log_warning() {
   echo -e "${YELLOW}[WARNING] $1${NC}"
}

log_error() {
   echo -e "${RED}[ERROR] $1${NC}"
}

check_dependencies() {
   log_info "Checking system dependencies..."
   local deps=("python3" "python3-pip" "git" "wget" "portaudio19-dev" "libasound2-dev" "libatlas-base-dev")
   local missing_deps=()

   for dep in "${deps[@]}"; do
       if ! dpkg -l | grep -q "^ii  $dep "; then
           missing_deps+=("$dep")
       fi
   done

   if [ ${#missing_deps[@]} -ne 0 ]; then
       log_warning "Missing dependencies: ${missing_deps[*]}"
       read -p "Install missing dependencies? [Y/n] " -n 1 -r
       echo
       if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
           log_info "Installing dependencies..."
           sudo apt-get update
           sudo apt-get install -y "${missing_deps[@]}"
       else
           log_error "Cannot proceed without dependencies"
           exit 1
       fi
   fi
}

backup_existing() {
   if [ -d "venv" ] || [ -d "src" ] || [ -d "models" ]; then
       local timestamp=$(date +%Y%m%d_%H%M%S)
       local backup_dir="backup_$timestamp"
       log_warning "Existing installation found. Creating backup in $backup_dir"
       mkdir -p "$backup_dir"
       [ -d "venv" ] && mv venv "$backup_dir/"
       [ -d "src" ] && mv src "$backup_dir/"
       [ -d "models" ] && mv models "$backup_dir/"
       [ -f ".env" ] && mv .env "$backup_dir/"
   fi
}

create_directory_structure() {
   log_info "Creating project structure..."
   mkdir -p {src/{core,audio,speech,ai,tts,utils},config,tests,models,logs}
   
   touch src/__init__.py
   touch src/core/__init__.py
   touch src/audio/__init__.py
   touch src/speech/__init__.py
   touch src/ai/__init__.py
   touch src/tts/__init__.py
   touch src/utils/__init__.py
   touch tests/__init__.py
}

setup_virtual_environment() {
   log_info "Setting up virtual environment..."
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install wheel
}

download_vosk_model() {
   log_info "Downloading Vosk model..."
   local model_dir="models/vosk-model-small-en-us-0.15"
   if [ ! -d "$model_dir" ]; then
       wget -P models/ https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
       unzip models/vosk-model-small-en-us-0.15.zip -d models/
       rm models/vosk-model-small-en-us-0.15.zip
   else
       log_warning "Vosk model already exists, skipping download"
   fi
}

echo -e "${BLUE}Starting Voice Assistant Setup${NC}"
echo "==============================="

backup_existing
check_dependencies
create_directory_structure

cat << 'EOF' > requirements.txt
pvporcupine==2.2.0
pvrecorder==1.1.1
vosk==0.3.45
openai==1.59.3
anthropic==0.3.0
google-cloud-texttospeech==2.14.1
python-dotenv==1.0.0
sounddevice==0.4.6
numpy==1.23.5
pytest==7.4.0
EOF
# Core State Management
cat << 'EOF' > src/core/state.py
from enum import Enum
from dataclasses import dataclass
import logging

class AssistantState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"

@dataclass
class AudioConfig:
    device_id: int
    sample_rate: int = 16000
    channels: int = 1
    frame_length: int = 512

class StateManager:
    def __init__(self):
        self.state = AssistantState.IDLE
        self._previous_state = None
        self._setup_logging()
        
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("logs/assistant.log"),
                logging.StreamHandler()
            ]
        )
        
    def transition_to(self, new_state: AssistantState):
        if self.can_transition_to(new_state):
            self._previous_state = self.state
            self.state = new_state
            logging.info(f"State transition: {self._previous_state} -> {self.state}")
        else:
            logging.warning(f"Invalid state transition: {self.state} -> {new_state}")
        
    @property
    def current_state(self) -> AssistantState:
        return self.state
        
    def can_transition_to(self, new_state: AssistantState) -> bool:
        valid_transitions = {
            AssistantState.IDLE: [AssistantState.LISTENING, AssistantState.ERROR],
            AssistantState.LISTENING: [AssistantState.PROCESSING, AssistantState.ERROR, AssistantState.IDLE],
            AssistantState.PROCESSING: [AssistantState.SPEAKING, AssistantState.ERROR, AssistantState.IDLE],
            AssistantState.SPEAKING: [AssistantState.IDLE, AssistantState.ERROR],
            AssistantState.ERROR: [AssistantState.IDLE]
        }
        return new_state in valid_transitions.get(self.state, [])
EOF

# Device Selector
cat << 'EOF' > src/audio/device_selector.py
import sounddevice as sd
import json
import logging
from pathlib import Path
from typing import Optional, Dict

class DeviceSelector:
    def __init__(self, config_path: str = 'config/audio_config.json'):
        self.config_path = Path(config_path)
        self.devices = {}
        self.selected_device = None
        self._load_saved_config()

    def _load_saved_config(self):
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    config = json.load(f)
                    self.selected_device = config.get('selected_device')
                    logging.info(f"Loaded saved device configuration: {self.selected_device}")
            except Exception as e:
                logging.error(f"Error loading device configuration: {e}")

    def _save_config(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump({'selected_device': self.selected_device}, f)
        logging.info(f"Saved device configuration: {self.selected_device}")

    def list_devices(self) -> Dict[int, str]:
        devices = sd.query_devices()
        print("\nAvailable Audio Input Devices:")
        print("------------------------------")
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                self.devices[i] = f"{dev['name']} (channels: {dev['max_input_channels']})"
                print(f"{i}: {self.devices[i]}")
        return self.devices

    def select_device(self, use_saved: bool = True) -> Optional[int]:
        if use_saved and self.selected_device is not None:
            if self.test_device(self.selected_device):
                print(f"\nUsing saved device: {self.devices.get(self.selected_device)}")
                return self.selected_device

        if not self.devices:
            self.list_devices()
        
        if not self.devices:
            logging.error("No input devices found!")
            return None

        while True:
            try:
                choice = input("\nSelect audio device number (or 'q' to quit): ")
                if choice.lower() == 'q':
                    return None
                
                device_num = int(choice)
                if device_num in self.devices:
                    if self.test_device(device_num):
                        self.selected_device = device_num
                        self._save_config()
                        return device_num
                    else:
                        print("Device test failed. Please select another device.")
                else:
                    print("Invalid device number. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

    def test_device(self, device_num: int) -> bool:
        try:
            print(f"\nTesting device {device_num}...")
            with sd.InputStream(device=device_num, channels=1, samplerate=16000) as stream:
                data = stream.read(1000)
                print("Device test successful!")
                return True
        except Exception as e:
            print(f"Error testing device: {e}")
            return False
EOF

# Wake Word Detection
cat << 'EOF' > src/speech/wake_word.py
import pvporcupine
from pvrecorder import PvRecorder
import logging
from core.state import AssistantState, StateManager
from audio.device_selector import DeviceSelector

class WakeWordDetector:
   def __init__(self, access_key: str, state_manager: StateManager, 
                keyword_paths=None, keywords=None, sensitivities=None):
       self.access_key = access_key
       self.keyword_paths = keyword_paths
       self.keywords = keywords or ["jarvis"]
       self.sensitivities = sensitivities or [0.5]
       self.state_manager = state_manager
       self.stop_flag = False
       self.porcupine = None
       self.recorder = None
       self.device_selector = DeviceSelector()
       
   def initialize(self):
       device = self.device_selector.select_device()
       if device is None:
           raise RuntimeError("No audio device selected")
           
       self.porcupine = pvporcupine.create(
           access_key=self.access_key,
           keyword_paths=self.keyword_paths,
           keywords=self.keywords,
           sensitivities=self.sensitivities
       )
       
       self.recorder = PvRecorder(
           device_index=device,
           frame_length=self.porcupine.frame_length
       )
       return device

   def cleanup(self):
       if self.recorder is not None:
           self.recorder.delete()
       if self.porcupine is not None:
           self.porcupine.delete()
       self.stop_flag = True
       logging.info("Wake word detector cleaned up")
       
   def start(self, callback_fn):
       try:
           if not self.recorder:
               self.initialize()
               
           self.recorder.start()
           logging.info("Wake word detection started")
           
           while not self.stop_flag:
               pcm = self.recorder.read()
               result = self.porcupine.process(pcm)
               if result >= 0:
                   if self.state_manager.can_transition_to(AssistantState.LISTENING):
                       self.state_manager.transition_to(AssistantState.LISTENING)
                       callback_fn()
                       break
                       
       except Exception as e:
           logging.error(f"Error in wake word detection: {e}")
           self.state_manager.transition_to(AssistantState.ERROR)
           raise
           
       finally:
           self.cleanup()
EOF

# Speech Recognition
cat << 'EOF' > src/speech/stt.py
import vosk
import sounddevice as sd
import json
import numpy as np
import logging
import queue
import threading
from core.state import AssistantState, StateManager
from audio.device_selector import DeviceSelector

class SpeechToText:
   def __init__(self, model_path: str, state_manager: StateManager):
       logging.info("Initializing Speech-to-Text")
       self.state_manager = state_manager
       self.device_selector = DeviceSelector()
       
       try:
           vosk.SetLogLevel(-1)
           self.model = vosk.Model(model_path)
           self.text_queue = queue.Queue()
           self.stop_event = threading.Event()
           logging.info("Speech-to-Text initialized successfully")
       except Exception as e:
           logging.error(f"STT initialization error: {e}")
           self.state_manager.transition_to(AssistantState.ERROR)
           raise

   def start_recognition(self, callback_fn=None):
       if not self.state_manager.can_transition_to(AssistantState.LISTENING):
           logging.error("Invalid state transition to LISTENING")
           return
           
       self.state_manager.transition_to(AssistantState.LISTENING)
       logging.info("Starting speech recognition")
       
       device = self.device_selector.select_device()
       if device is None:
           raise RuntimeError("No audio device selected")
           
       rec = vosk.KaldiRecognizer(self.model, 16000)
       
       def audio_callback(indata, frames, time, status):
           if status:
               logging.warning(f"Audio input status: {status}")
               return
           data = indata.astype(np.int16).tobytes()
           if rec.AcceptWaveform(data):
               result = json.loads(rec.Result())
               text = result.get('text', '').strip()
               if text:
                   logging.info(f"Recognized speech: {text}")
                   self.text_queue.put(text)
                   if callback_fn:
                       callback_fn(text)

       try:
           with sd.InputStream(samplerate=16000, device=device,
                             dtype='int16', channels=1,
                             callback=audio_callback):
               logging.info("Microphone stream opened")
               print("Listening... Speak now.")
               while not self.stop_event.is_set():
                   threading.Event().wait(0.1)
       except Exception as e:
           logging.error(f"Error in speech recognition: {e}")
           self.state_manager.transition_to(AssistantState.ERROR)
           raise

   def stop_recognition(self):
       self.stop_event.set()
       logging.info("Speech recognition stopped")

   def get_recognized_text(self, timeout=1):
       try:
           return self.text_queue.get(timeout=timeout)
       except queue.Empty:
           return None
EOF

# AI Handler
cat << 'EOF' > src/ai/openai_handler.py
from openai import OpenAI
import logging
from core.state import AssistantState, StateManager

class OpenAIHandler:
   def __init__(self, state_manager: StateManager):
       try:
           self.client = OpenAI()
           self.state_manager = state_manager
           logging.info("OpenAI handler initialized successfully")
       except Exception as e:
           logging.error(f"Error initializing OpenAI client: {e}")
           self.state_manager.transition_to(AssistantState.ERROR)
           raise

   def process_text(self, text: str) -> str:
       if not self.state_manager.can_transition_to(AssistantState.PROCESSING):
           logging.error("Invalid state transition to PROCESSING")
           return None
           
       self.state_manager.transition_to(AssistantState.PROCESSING)
       
       try:
           chat_completion = self.client.chat.completions.create(
               messages=[{"role": "user", "content": text}],
               model="gpt-3.5-turbo",
           )
           response = chat_completion.choices[0].message.content
           return response
           
       except Exception as e:
           logging.error(f"Error in OpenAI processing: {e}")
           self.state_manager.transition_to(AssistantState.ERROR)
           return None
       finally:
           if self.state_manager.current_state == AssistantState.PROCESSING:
               self.state_manager.transition_to(AssistantState.SPEAKING)
EOF

# Text to Speech
cat << 'EOF' > src/tts/synthesizer.py
from google.cloud import texttospeech
import os
import logging
from core.state import AssistantState, StateManager

class TextToSpeech:
   def __init__(self, state_manager: StateManager, credentials_path: str = None):
       self.state_manager = state_manager
       
       if credentials_path:
           os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
       elif 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
           credentials_path = os.path.join(os.path.dirname(__file__), 
                                         'google-service-account.json')
           if os.path.exists(credentials_path):
               os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
           else:
               raise FileNotFoundError("Google Cloud credentials not found")
               
       try:
           self.client = texttospeech.TextToSpeechClient()
           logging.info("Text-to-Speech initialized successfully")
       except Exception as e:
           logging.error(f"Error initializing TTS: {e}")
           self.state_manager.transition_to(AssistantState.ERROR)
           raise

   def synthesize_speech(self, text: str, 
                        output_file: str = '/tmp/google_tts_output.wav',
                        language_code: str = 'en-US'):
       if not self.state_manager.can_transition_to(AssistantState.SPEAKING):
           logging.error("Invalid state transition to SPEAKING")
           return
           
       self.state_manager.transition_to(AssistantState.SPEAKING)
       
       try:
           synthesis_input = texttospeech.SynthesisInput(text=text)
           voice = texttospeech.VoiceSelectionParams(
               language_code=language_code,
               ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
           )
           audio_config = texttospeech.AudioConfig(
               audio_encoding=texttospeech.AudioEncoding.LINEAR16
           )
           
           response = self.client.synthesize_speech(
               input=synthesis_input,
               voice=voice,
               audio_config=audio_config
           )
           
           with open(output_file, 'wb') as out:
               out.write(response.audio_content)
               logging.info(f'Audio content written to {output_file}')
           
           volume = os.getenv('AUDIO_VOLUME', '50')
           os.system(f'amixer -q sset PCM {volume}%')
           os.system(f'aplay {output_file}')
           
       except Exception as e:
           logging.error(f"Error in speech synthesis: {e}")
           self.state_manager.transition_to(AssistantState.ERROR)
           raise
           
       finally:
           if self.state_manager.current_state == AssistantState.SPEAKING:
               self.state_manager.transition_to(AssistantState.IDLE)
EOF

# Main Application
cat << 'EOF' > src/main.py
import os
import threading
import time
from datetime import datetime
import logging
from dotenv import load_dotenv
from core.state import StateManager
from speech.stt import SpeechToText
from tts.synthesizer import TextToSpeech
from speech.wake_word import WakeWordDetector
from ai.openai_handler import OpenAIHandler

# Load environment variables
load_dotenv()

class VoiceAssistant:
   def __init__(self, model_path):
       logging.info("Initializing Voice Assistant")
       
       try:
           # Initialize state manager
           self.state_manager = StateManager()
           
           # Initialize components
           self.stt_engine = SpeechToText(model_path, self.state_manager)
           self.tts_engine = TextToSpeech(self.state_manager)
           self.ai_handler = OpenAIHandler(self.state_manager)
           
           # Initialize wake word detector if key is available
           picovoice_key = os.getenv('PICOVOICE_ACCESS_KEY')
           if picovoice_key:
               self.wake_word_detector = WakeWordDetector(
                   access_key=picovoice_key,
                   state_manager=self.state_manager,
                   keywords=["jarvis"]
               )
           else:
               self.wake_word_detector = None
               logging.warning("No Picovoice key found, wake word detection disabled")
           
           # Events for control
           self.stop_event = threading.Event()
           
           logging.info("Voice Assistant initialized successfully")
           
       except Exception as e:
           logging.error(f"Initialization error: {e}")
           raise

   def start(self):
       logging.info("Starting voice assistant")
       
       try:
           if self.wake_word_detector:
               # Start wake word detection in a separate thread
               wake_thread = threading.Thread(
                   target=self.wake_word_detector.start,
                   args=(self.on_wake_word,)
               )
               wake_thread.daemon = True
               wake_thread.start()
           else:
               # Start in listening mode if no wake word detector
               self.on_wake_word()
           
           # Keep the assistant running
           while not self.stop_event.is_set():
               time.sleep(0.1)
               
       except Exception as e:
           logging.error(f"Error in assistant main loop: {e}")
           self.state_manager.transition_to(AssistantState.ERROR)
           raise
       
       finally:
           self.stop()

   def stop(self):
       logging.info("Stopping voice assistant")
       self.stop_event.set()
       self.stt_engine.stop_recognition()

   def on_wake_word(self):
       logging.info("Wake word detected or starting in listening mode")
       self.speak("Yes?")
       self.stt_engine.start_recognition(callback_fn=self.process_command)

   def process_command(self, text):
       try:
           text = text.lower().strip()
           
           # Prevent repeated processing of the same text
           if not hasattr(self, '_last_processed_text'):
               self._last_processed_text = None

           if text == self._last_processed_text:
               return

           self._last_processed_text = text
           
           # Handle commands
           if "goodbye" in text or "bye" in text:
               self.speak("Goodbye!")
               self.stop()
           else:
               # Process with AI
               response = self.ai_handler.process_text(text)
               if response:
                   self.speak(response)
               else:
                   self.speak("I'm sorry, I couldn't process that request.")
               
       except Exception as e:
           logging.error(f"Error processing command: {e}")
           self.state_manager.transition_to(AssistantState.ERROR)
           self.speak("Sorry, I encountered an error processing your request.")

   def speak(self, text):
       try:
           self.tts_engine.synthesize_speech(text)
       finally:
           self.state_manager.transition_to(AssistantState.IDLE)

def main():
   try:
       # Get model path from environment or use default
       base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
       model_path = os.getenv('VOSK_MODEL_PATH', 
                            os.path.join(base_dir, 'models/vosk-model-small-en-us-0.15'))
       
       # Initialize and start voice assistant
       assistant = VoiceAssistant(model_path)
       assistant.start()
   
   except Exception as e:
       logging.error(f"Fatal error in main: {e}")
       raise

if __name__ == "__main__":
   main()
EOF

# Environment template
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
AUDIO_VOLUME=50

# Paths
VOSK_MODEL_PATH=models/vosk-model-small-en-us-0.15

# Wake Word Settings
WAKE_WORD=jarvis
WAKE_WORD_SENSITIVITY=0.5
EOF

# Start script
cat << 'EOF' > start_assistant.sh
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
PYTHONPATH=. python3 src/main.py
EOF
chmod +x start_assistant.sh

# Setup virtual environment and install dependencies
setup_virtual_environment
pip install -r requirements.txt

# Download Vosk model
download_vosk_model

# Final setup steps
cp .env.template .env
log_success "Setup completed successfully!"
echo
log_info "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Place your Google Cloud credentials JSON file"
echo "3. Run ./start_assistant.sh to start the assistant"

# Remove error trap
trap - EXIT