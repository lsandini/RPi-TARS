import os
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

        # Funny wake word responses
        self.wake_word_responses = [
            "Huuh?",
            "Hmm?",
            "Yes Boss?"
        ]

    def get_ai_response(self, text):
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": text}]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return "Sorry, I couldn't process that request."

    def speak_response(self, text):
        try:
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
                # Get and speak AI response
                if not any(word in command for word in ["thank you", "goodbye", "thanks"]):
                    ai_response = self.get_ai_response(command)
                    print(f"TARS: {ai_response}")
                    self.speak_response(ai_response)
                
                last_command_time = time.time()
                commands_count += 1
                
                if any(word in command for word in ["thank you", "goodbye", "thanks"]):
                    print("Ending conversation mode.")
                    break

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