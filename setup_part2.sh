#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[1;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Adding AI and Wake Word components...${NC}"

# Create AI handler
cat << 'EOF' > src/ai/openai_handler.py
from openai import OpenAI
import os
import logging

class OpenAIHandler:
    def __init__(self):
        try:
            self.client = OpenAI()  # This will use OPENAI_API_KEY from environment by default
            logging.info("OpenAI handler initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing OpenAI client: {e}")
            raise

    def process_text(self, text):  # Removed async since the example doesn't use it
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": text,
                    }
                ],
                model="gpt-3.5-turbo",  # Using 3.5 instead of gpt-4
            )
            return chat_completion.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Error in OpenAI processing: {e}")
            return None
EOF

cat << 'EOF' > src/speech/wake_word.py
import pvporcupine
from pvrecorder import PvRecorder
import logging

class WakeWordDetector:
    def __init__(self, access_key, keyword_paths=None, keywords=None, sensitivities=None):
        self.porcupine = None
        self.recorder = None
        self.access_key = access_key
        self.keyword_paths = keyword_paths
        self.keywords = keywords or ["jarvis"]
        self.sensitivities = sensitivities or [0.5]
        self.stop_flag = False
        
    def cleanup(self):
        """Cleanup Porcupine resources"""
        if self.recorder is not None:
            self.recorder.delete()
            self.recorder = None
        if self.porcupine is not None:
            self.porcupine.delete()
            self.porcupine = None
        self.stop_flag = True
        logging.info("Porcupine resources cleaned up")
        
    def start(self, callback_fn):
        try:
            self.stop_flag = False
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keyword_paths=self.keyword_paths,
                keywords=self.keywords,
                sensitivities=self.sensitivities
            )
            
            devices = PvRecorder.get_audio_devices()
            logging.info(f"Available audio devices: {devices}")
            
            # Try to find seeed-2mic-voicecard
            device_index = None
            for i, device in enumerate(devices):
                logging.info(f"Device {i}: {device}")
                if 'seeed' in device.lower():
                    device_index = i
                    break
            
            # If not found, use device 1 (which we know works with ALSA)
            if device_index is None:
                device_index = 1
                logging.info(f"Using default device index: {device_index}")

            # Create recorder with just device index and frame length
            self.recorder = PvRecorder(
                device_index=device_index,
                frame_length=self.porcupine.frame_length
            )
            self.recorder.start()
            
            while not self.stop_flag:
                pcm = self.recorder.read()
                result = self.porcupine.process(pcm)
                if result >= 0:
                    callback_fn()
                    break  # Exit after wake word detection
                    
        except Exception as e:
            logging.error(f"Error in wake word detection: {e}")
            raise
            
        finally:
            self.cleanup()
EOF

# Modify the main.py script 
cat << 'EOF' > src/main.py
import os
import threading
import time
from datetime import datetime
import logging
from dotenv import load_dotenv
from speech.stt import SpeechToText
from speech.tts import TextToSpeech
from speech.wake_word import WakeWordDetector
from ai.openai_handler import OpenAIHandler
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/voice_assistant.log"),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

class AssistantState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"

class VoiceAssistant:
    def __init__(self, model_path, sample_rate=16000, device=None):
        logging.info("Initializing Voice Assistant")
        
        try:
            self.state = AssistantState.IDLE
            
            # Initialize components
            self.stt_engine = SpeechToText(model_path, sample_rate, device)
            self.tts_engine = TextToSpeech()
            self.ai_handler = OpenAIHandler()
            
            # Initialize wake word detector if key is available
            picovoice_key = os.getenv('PICOVOICE_ACCESS_KEY')
            if picovoice_key:
                self.wake_word_detector = WakeWordDetector(
                    access_key=picovoice_key,
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
        """Start the voice assistant."""
        logging.info("Starting voice assistant")
        
        try:
            while not self.stop_event.is_set():
                if self.wake_word_detector:
                    # Start wake word detection
                    self.wake_word_detector.start(self.on_wake_word)
                    time.sleep(1)  # Small delay before restarting wake word detection
                else:
                    self.on_wake_word()
                
        except Exception as e:
            logging.error(f"Error in assistant main loop: {e}")
            self.state = AssistantState.ERROR
            raise
        
        finally:
            self.stop()

    def stop(self):
        """Stop the voice assistant."""
        logging.info("Stopping voice assistant")
        self.stop_event.set()
        self.stt_engine.stop_recognition()

    def on_wake_word(self):
        """Callback for wake word detection."""
        logging.info("Wake word detected!")
        self.state = AssistantState.LISTENING
        
        # Cleanup wake word detector resources
        if self.wake_word_detector:
            self.wake_word_detector.cleanup()
        
        # Wake word responses are predefined
        wake_responses = [
            "Yes?", 
            "How can I help you?", 
            "I'm listening.", 
            "What can I do for you?"
        ]
        import random
        response = random.choice(wake_responses)
        
        # Log the wake word response
        logging.info(f"WAKE WORD RESPONSE: {response}")
        
        # Speak the response
        self.tts_engine.synthesize_speech(response)
        
        # Start speech recognition
        self.stt_engine.start_recognition(callback_fn=self.process_command)

    def process_command(self, text):
        """Process recognized text commands."""
        try:
            self.state = AssistantState.PROCESSING
            text = text.lower().strip()
            
            # Log what Vosk heard
            logging.info(f"YOU SAID: {text}")
            
            # Prevent repeated processing of the same text
            if not hasattr(self, '_last_processed_text'):
                self._last_processed_text = None

            if text == self._last_processed_text:
                return

            self._last_processed_text = text
            
            # Handle commands
            if "hello" in text or "hi" in text:
                response = "Hello! How can I help you?"
            elif "time" in text:
                current_time = datetime.now().strftime("%I:%M %p")
                response = f"The current time is {current_time}"
            elif "goodbye" in text or "bye" in text:
                response = "Goodbye! Have a great day."
                self.tts_engine.synthesize_speech(response)
                self.stop()
                return
            else:
                # Process with AI
                response = self.ai_handler.process_text(text)
                response = response if response else f"I heard: {text}"
            
            # Log OpenAI's response
            logging.info(f"OPENAI REPLIED: {response}")
            
            # Speak the response
            self.tts_engine.synthesize_speech(response)
                    
        except Exception as e:
            logging.error(f"Error processing command: {e}")
            self.state = AssistantState.ERROR
            self.tts_engine.synthesize_speech("Sorry, I encountered an error processing your request.")
            
        finally:
            self.state = AssistantState.IDLE

def main():
    try:
        # Get model path from environment or use default
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, 'models/vosk-model-small-en-us-0.15')
        
        # Initialize and start voice assistant
        assistant = VoiceAssistant(model_path)
        assistant.start()
    
    except Exception as e:
        logging.error(f"Fatal error in main: {e}")
        raise

if __name__ == "__main__":
    main()
EOF

# Create utils
cat << 'EOF' > src/utils/logger.py
import logging
import os

def setup_logger(log_file='logs/assistant.log'):
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Create logger instance
    logger = logging.getLogger('VoiceAssistant')
    return logger
EOF

# Update .gitignore
cat << 'EOF' > .gitignore
# Ignore everything
*

# But not these files...
!.gitignore
!setup_part1.sh
!setup_part2.sh
!setup_part3.sh
!deploy.sh
!README.md

# Even if they are in subdirectories
!*/

# But still ignore everything in any directory
/**/
EOF

# Create a models directory
mkdir -p models

echo -e "${GREEN}AI and Wake Word components added successfully!${NC}"
echo -e "${BLUE}Additional steps:${NC}"
echo "1. Download Vosk model to models/vosk-model-small-en-us"
echo "2. Set up Picovoice access key in .env"
echo "3. Configure Google Cloud credentials"
echo "4. Set up OpenAI API key in .env"

# Run part 3 if part 2 was successful
if [ $? -eq 0 ]; then
    echo -e "${BLUE}Part 2 completed successfully, starting Part 3...${NC}"
    ./setup_part3.sh
else
    echo -e "${RED}Part 2 failed, stopping setup${NC}"
    exit 1
fi