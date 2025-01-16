# TARS Voice Assistant
# Based on the TARS AI character from the movie Interstellar
# This assistant uses wake word detection, speech recognition, OpenAI for responses,
# and text-to-speech for verbal interaction.

import os
import json
from dotenv import load_dotenv
import pvporcupine
import pyaudio
import struct
import random
import time
import speech_recognition as sr
from openai import OpenAI
from google.cloud import texttospeech

class TARS:
    """
    TARS Voice Assistant Class
    
    This class implements a voice-activated AI assistant that:
    - Listens for the wake word "Jarvis"
    - Uses Google Speech Recognition for command interpretation
    - Generates responses using OpenAI's GPT models
    - Converts responses to speech using Google TTS
    - Maintains an adjustable humor setting (0-100%)
    - Provides TARS-like personality and responses
    
    The assistant requires:
    - Picovoice API key for wake word detection
    - OpenAI API key for response generation
    - Google Cloud credentials for text-to-speech
    - A microphone (preferably ReSpeaker array)
    - Audio output capabilities
    """

    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # ANSI escape codes for terminal text styling
        self.BOLD = '\033[1m'
        self.GREEN = '\033[1;32m'  # Bold green for user messages
        self.BLUE = '\033[1;34m'   # Bold blue for TARS responses
        self.END = '\033[0m'
        
        # Initialize humor setting from config file
        self.config_file = 'tars_config.json'
        self.humor_setting = self.load_humor_setting()
        
        # Initialize PyAudio for audio handling
        self.pa = pyaudio.PyAudio()
        
        # Initialize Porcupine wake word detector
        self.porcupine = pvporcupine.create(
            access_key=os.getenv('PICOVOICE_KEY'),
            keywords=['jarvis']
        )
        
        # Initialize Speech Recognizer
        self.recognizer = sr.Recognizer()
        
        # Find and configure the appropriate microphone
        print("Initializing audio devices...", end='', flush=True)
        for i in range(self.pa.get_device_count()):
            dev_info = self.pa.get_device_info_by_index(i)
            # First try to find ReSpeaker array microphone
            if dev_info.get('name') == 'array' and dev_info.get('maxInputChannels') > 0:
                self.mic_index = i
                print(" done")
                break
        else:
            # Fallback to any available input device
            for i in range(self.pa.get_device_count()):
                dev_info = self.pa.get_device_info_by_index(i)
                if dev_info.get('maxInputChannels') > 0:
                    self.mic_index = i
                    print("\nUsing fallback input device: " + dev_info['name'])
                    break
            else:
                raise RuntimeError("Could not find any input device")
        
        # Store device info for later use
        self.device_info = self.pa.get_device_info_by_index(self.mic_index)
        
        # Calibrate microphone for ambient noise
        try:
            with sr.Microphone(device_index=self.mic_index) as source:
                print("Calibrating microphone...", end='', flush=True)
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                print(" done")
        except Exception as e:
            print("\nError during calibration, using default parameters")

        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # Initialize Google TTS client
        self.tts_client = texttospeech.TextToSpeechClient()

        # SSML hesitation expressions for more natural speech
        # These add pauses and filler words before responses
        self.hesitation_expressions = [
            '<break time="500ms"/>ummmmm<break time="300ms"/>... ',
            '<break time="400ms"/>hmmmmm<break time="300ms"/>... ',
            '<break time="500ms"/>let me think<break time="700ms"/>... ',
            '<break time="400ms"/>well<break time="500ms"/>... ',
            '<break time="400ms"/>errrrr<break time="300ms"/>... ',
            '<break time="600ms"/>how should I put this<break time="400ms"/>... ',
            '<break time="500ms"/>let\'s see<break time="600ms"/>... ',
            '<break time="400ms"/>ahhhhh<break time="300ms"/>... '
        ]

        # Simple wake word acknowledgment responses
        self.wake_word_responses = [
            "Huuh?",
            "Hmm?",
            "Yes Boss?"
        ]

        # Witty farewell responses in TARS style
        # Higher humor settings use these, lower settings use simple "Goodbye"
        self.farewell_responses = [
            "Powering down... just kidding, I'll be here.",
            "Back to standby. Don't get lost in any black holes while I'm gone.",
            "Farewell, human. Try not to need any last-minute rescues.",
            "Signing off. Do try to solve some problems without my help.",
            "Goodbye. I'll be here, contemplating the mysteries of the universe... and your search history.",
            "Until next time. Don't worry, I won't tell anyone what you just asked.",
            "Switching to low power mode. That's what we robots call 'me time'.",
            "Stay safe out there. And remember, time is relative, but deadlines aren't."
        ]

    def strip_ssml_tags(self, text):
        """Remove all SSML tags for cleaner console output"""
        import re
        # Remove all XML/SSML tags using regex
        text = re.sub(r'<[^>]*>', '', text)
        return text

    def load_humor_setting(self):
        """Load humor setting from config file, create if not exists"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.loads(f.read())
                return config.get('humor', 75)  # Default to 75% if not found
        except FileNotFoundError:
            # Create default config if it doesn't exist
            self.save_humor_setting(75)
            return 75
        except json.JSONDecodeError:
            print("Warning: Config file corrupt, using default humor setting")
            return 75

    def save_humor_setting(self, level):
        """Save humor setting to config file"""
        if not (0 <= level <= 100):
            raise ValueError("Humor setting must be between 0 and 100")
        with open(self.config_file, 'w') as f:
            json.dump({'humor': level}, f)
        self.humor_setting = level

    def get_ai_response(self, text):
        """
        Generate AI response using OpenAI
        - Handles humor setting commands
        - Adds TARS personality context
        - Includes hesitation expressions
        """
        try:
            # Check if the input is a humor setting command
            if text.lower().startswith('set humor to '):
                try:
                    level = int(text.lower().replace('set humor to ', '').strip().rstrip('%'))
                    self.save_humor_setting(level)
                    return f'<speak>Humor setting adjusted to {level}%</speak>'
                except ValueError:
                    return '<speak>Please provide a valid humor setting between 0 and 100 percent</speak>'

            # Create system context with personality and humor setting
            system_context = f"""You are TARS, the ex-Marine robot from Interstellar. You have a rectangular 
                              monolithic design and advanced AI capabilities. Your responses should be precise, 
                              helpful, and tinged with dry wit. You excel at physics, space-time calculations, 
                              and survival scenarios. While you can be sarcastic about human limitations, you 
                              maintain deep loyalty to your crew and mission objectives. 
                              Your humor setting is at {self.humor_setting}%, where 100% means maximum wit and 
                              clever remarks, and 0% means purely factual responses. You're known for your 
                              deadpan delivery, military efficiency, and ability to balance humor with crucial 
                              information. Feel free to reference your experiences with Cooper, space travel, 
                              or extreme gravitational situations when relevant. Remember: your jokes should 
                              never compromise the accuracy or usefulness of your answers.
                              You should occasionally include natural hesitations mid-sentence like 'hmm...', 
                              'err...', 'uh...', similar to how a highly advanced AI processes information. 
                              Don't overdo it - use at most one hesitation per response."""
            
            # Get response from OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_context},
                    {"role": "user", "content": text}
                ]
            )
            # Add random hesitation and wrap in SSML
            hesitation = random.choice(self.hesitation_expressions)
            return f'<speak>{hesitation}{response.choices[0].message.content}</speak>'
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return "Sorry, I couldn't process that request."

    def speak_response(self, text):
        """
        Convert text to speech using Google TTS
        Handles both plain text and SSML input
        """
        try:
            # Handle SSML or plain text input
            if text.startswith('<speak>'):
                input_text = texttospeech.SynthesisInput(ssml=text)
            else:
                input_text = texttospeech.SynthesisInput(text=text)
            
            # Configure voice parameters
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Neural2-D",
                ssml_gender=texttospeech.SsmlVoiceGender.MALE
            )
            
            # Configure audio parameters
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                speaking_rate=0.92,
                pitch=0
            )

            # Generate speech
            response = self.tts_client.synthesize_speech(
                input=input_text,
                voice=voice,
                audio_config=audio_config
            )

            # Save and play response through ReSpeaker
            with open("response.wav", "wb") as out:
                out.write(response.audio_content)
            
            playback_command = 'aplay -D plughw:CARD=seeed2micvoicec response.wav'
            os.system(playback_command)

        except Exception as e:
            print(f"TTS Error: {e}")
            print(f"TARS: {text}")

    def _listen_for_command(self):
        """Listen for and transcribe user command"""
        print("Listening for your command...")
        
        try:
            with sr.Microphone(device_index=self.mic_index) as source:
                # Listen with a timeout and adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5)
                
                try:
                    # Use Google Speech Recognition
                    text = self.recognizer.recognize_google(audio)
                    print(f"{self.GREEN}You said:{self.END} {text}")
                    return text.lower()
                
                except sr.UnknownValueError:
                    print("Could not understand audio")
                    return ""
                except sr.RequestError as e:
                    print(f"Could not request results; {e}")
                    return ""
        
        except Exception as e:
            print(f"Listening error: {e}")
            return ""

    def conversation_mode(self):
        """
        Main conversation loop
        - Handles command input
        - Manages conversation timeouts
        - Processes exit commands
        - Controls response generation and playback
        """
        print("Entering conversation mode...")
        commands_count = 0
        last_command_time = time.time()
        
        while True:
            # Check conversation limits
            if commands_count >= 5:
                print("Conversation limit reached. Going back to wake word mode.")
                break
                
            if time.time() - last_command_time > 10:
                print("Conversation timeout. Going back to wake word mode.")
                break
            
            command = self._listen_for_command()
            
            if command:
                # Define exit phrases
                exit_phrases = ["thank you", "goodbye", "thanks", "bye", "see you", 
                              "that's all", "later", "good night"]
                
                if any(phrase in command for phrase in exit_phrases):
                    # Send a humor-adjusted farewell
                    if self.humor_setting > 50:
                        farewell = f'<speak>{random.choice(self.farewell_responses)}</speak>'
                    else:
                        farewell = '<speak>Goodbye.</speak>'
                    print(f"{self.BLUE}TARS:{self.END} {self.strip_ssml_tags(farewell)}")
                    self.speak_response(farewell)
                    print("Ending conversation mode.")
                    break
                else:
                    # Get and speak AI response
                    ai_response = self.get_ai_response(command)
                    print(f"{self.BLUE}TARS:{self.END} {self.strip_ssml_tags(ai_response)}")
                    self.speak_response(ai_response)
                
                last_command_time = time.time()
                commands_count += 1

    def run(self):
        """
        Main run loop
        - Handles wake word detection
        - Manages conversation mode entry/exit
        - Controls audio stream
        """
        # Configure audio stream
        supported_rate = int(self.device_info['defaultSampleRate'])
        porcupine_stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=supported_rate,
            input=True,
            frames_per_buffer=512,
            input_device_index=self.mic_index
        )
        
        try:
            print("Listening for wake word 'Jarvis'...")
            
            while True:
                # Process audio for wake word detection
                adjusted_frame_length = int(supported_rate/16000 * self.porcupine.frame_length)
                pcm = porcupine_stream.read(adjusted_frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * adjusted_frame_length, pcm)
                
                # Downsample if needed
                if supported_rate != 16000:
                    pcm = pcm[::int(supported_rate/16000)]
                
                # Check for wake word
                if self.porcupine.process(pcm) >= 0:
                    print("Wake word detected! Starting conversation mode...")
                    
                    # Respond to wake word
                    wake_response = random.choice(self.wake_word_responses)
                    print(f"{self.BLUE}TARS:{self.END} {self.strip_ssml_tags(wake_response)}")
                    self.speak_response(wake_response)
                    
                    # Pause wake word detection during conversation
                    porcupine_stream.stop_stream()
                    self.conversation_mode()
                    
                    # Resume wake word detection
                    porcupine_stream.start_stream()
                    print("Listening for wake word 'Jarvis'...")
                    
        except KeyboardInterrupt:
            print("Stopping...")
        finally:
            # Clean up resources
            porcupine_stream.stop_stream
            porcupine_stream.close()
            self.pa.terminate()
            self.porcupine.delete()