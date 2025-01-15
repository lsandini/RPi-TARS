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
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize humor setting
        self.config_file = 'tars_config.json'
        self.humor_setting = self.load_humor_setting()
        
        # Initialize PyAudio
        self.pa = pyaudio.PyAudio()
        
        # Initialize Porcupine with Jarvis wake word
        self.porcupine = pvporcupine.create(
            access_key=os.getenv('PICOVOICE_KEY'),
            keywords=['jarvis']
        )
        
        # Initialize Speech Recognizer
        self.recognizer = sr.Recognizer()
        
        # Find the correct microphone index
        print("Searching for input devices...")
        for i in range(self.pa.get_device_count()):
            dev_info = self.pa.get_device_info_by_index(i)
            print(f"Checking device {i}: {dev_info['name']}")
            # Look for the 'array' device which represents our ReSpeaker
            if dev_info.get('name') == 'array' and dev_info.get('maxInputChannels') > 0:
                self.mic_index = i
                print(f"Found microphone array at index {i}")
                break
        else:
            # Fallback to any device with input capabilities
            for i in range(self.pa.get_device_count()):
                dev_info = self.pa.get_device_info_by_index(i)
                if dev_info.get('maxInputChannels') > 0:
                    self.mic_index = i
                    print(f"Using fallback input device at index {i}: {dev_info['name']}")
                    break
            else:
                raise RuntimeError("Could not find any input device")
        
        # Store device info for later use
        self.device_info = self.pa.get_device_info_by_index(self.mic_index)
        print(f"Using device with sample rate: {self.device_info['defaultSampleRate']}")
        
        # Adjust for ambient noise
        try:
            with sr.Microphone(device_index=self.mic_index) as source:
                print("Calibrating ambient noise... Please wait.")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
        except Exception as e:
            print(f"Error during ambient noise calibration: {e}")
            print("Continuing with default parameters...")

        # Initialize OpenAI
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # Initialize Google TTS
        self.tts_client = texttospeech.TextToSpeechClient()

        # Add SSML hesitation expressions
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

        # Funny wake word responses
        self.wake_word_responses = [
            "Huuh?",
            "Hmm?",
            "Yes Boss?"
        ]

        # TARS-style farewell responses
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

    def load_humor_setting(self):
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
        if not (0 <= level <= 100):
            raise ValueError("Humor setting must be between 0 and 100")
        with open(self.config_file, 'w') as f:
            json.dump({'humor': level}, f)
        self.humor_setting = level

    def get_ai_response(self, text):
        try:
            # Check if the input is a humor setting command
            if text.lower().startswith('set humor to '):
                try:
                    level = int(text.lower().replace('set humor to ', '').strip().rstrip('%'))
                    self.save_humor_setting(level)
                    return f'<speak>Humor setting adjusted to {level}%</speak>'
                except ValueError:
                    return '<speak>Please provide a valid humor setting between 0 and 100 percent</speak>'

            system_context = f"""You are TARS from the movie Interstellar. You're witty, knowledgeable, 
                              and a bit sarcastic about human ignorance, but always helpful. 
                              Your humor setting is currently set to {self.humor_setting}%. Adjust your 
                              responses accordingly - higher humor means more jokes and wit, lower means 
                              more straightforward responses. At 0% humor, you're completely serious,
                              at 100% you're highly entertaining but still informative."""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_context},
                    {"role": "user", "content": text}
                ]
            )
            # Add random hesitation before the response
            hesitation = random.choice(self.hesitation_expressions)
            # Wrap the entire response in SSML
            ssml_response = f'<speak>{hesitation}{response.choices[0].message.content}</speak>'
            return ssml_response
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return "Sorry, I couldn't process that request."

    def speak_response(self, text):
        try:
            # Check if the text is SSML (starts with <speak>)
            if text.startswith('<speak>'):
                input_text = texttospeech.SynthesisInput(ssml=text)
            else:
                input_text = texttospeech.SynthesisInput(text=text)
            
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Neural2-D",
                ssml_gender=texttospeech.SsmlVoiceGender.MALE
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                speaking_rate=1.0,
                pitch=0
            )

            response = self.tts_client.synthesize_speech(
                input=input_text,
                voice=voice,
                audio_config=audio_config
            )

            # Save and play response
            with open("response.wav", "wb") as out:
                out.write(response.audio_content)
                
            # Use the ReSpeaker's playback device by name
            playback_command = 'aplay -D plughw:CARD=seeed2micvoicec response.wav'
            os.system(playback_command)

        except Exception as e:
            print(f"TTS Error: {e}")
            print(f"TARS: {text}")

    def _listen_for_command(self):
        print("Listening for your command...")
        
        try:
            with sr.Microphone(device_index=self.mic_index) as source:
                # Listen with a timeout and adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5)
                
                try:
                    # Use Google Speech Recognition
                    text = self.recognizer.recognize_google(audio)
                    print(f"You said: {text}")
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
        print("Entering conversation mode...")
        commands_count = 0
        last_command_time = time.time()
        
        while True:
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
                    print(f"TARS: {farewell}")
                    self.speak_response(farewell)
                    print("Ending conversation mode.")
                    break
                else:
                    # Get and speak AI response
                    ai_response = self.get_ai_response(command)
                    print(f"TARS: {ai_response}")
                    self.speak_response(ai_response)
                
                last_command_time = time.time()
                commands_count += 1
                

    def run(self):
        # Get the supported sample rate from the device
        supported_rate = int(self.device_info['defaultSampleRate'])
        
        # Set up initial audio stream for Porcupine
        porcupine_stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=supported_rate,  # Use the device's supported rate
            input=True,
            frames_per_buffer=512,
            input_device_index=self.mic_index
        )
        
        try:
            print(f"Listening for wake word 'Jarvis' (using sample rate: {supported_rate})...")
            
            while True:
                # Wake word detection phase
                # Adjust frame length based on sample rate ratio
                adjusted_frame_length = int(supported_rate/16000 * self.porcupine.frame_length)
                pcm = porcupine_stream.read(adjusted_frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * adjusted_frame_length, pcm)
                
                # Downsample to 16000 Hz for Porcupine if needed
                if supported_rate != 16000:
                    pcm = pcm[::int(supported_rate/16000)]
                
                if self.porcupine.process(pcm) >= 0:
                    print("Wake word detected! Starting conversation mode...")
                    
                    # Randomly choose and speak a wake word response
                    wake_response = random.choice(self.wake_word_responses)
                    print(f"TARS: {wake_response}")
                    self.speak_response(wake_response)
                    
                    # Temporarily stop wake word detection
                    porcupine_stream.stop_stream()
                    
                    # Enter conversation mode
                    self.conversation_mode()
                    
                    # Resume wake word detection
                    porcupine_stream.start_stream()
                    print("Listening for wake word 'Jarvis'...")
                    
        except KeyboardInterrupt:
            print("Stopping...")
        finally:
            porcupine_stream.stop_stream()
            porcupine_stream.close()
            self.pa.terminate()
            self.porcupine.delete()