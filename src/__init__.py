import os
from dotenv import load_dotenv
import pvporcupine
import pyaudio
import struct
import vosk
import json
import time
from openai import OpenAI
from google.cloud import texttospeech

class TARS:
    def __init__(self):
        # Load environment variables first
        load_dotenv()
        
        # Verify required environment variables
        self._check_environment()
        
        # Initialize components
        self._initialize_audio()
        self._initialize_wake_word()
        self._initialize_speech_recognition()
        self._initialize_ai()
        self._initialize_tts()
        
    def _check_environment(self):
        required_vars = ['PICOVOICE_KEY', 'OPENAI_API_KEY', 'GOOGLE_APPLICATION_CREDENTIALS']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def _initialize_audio(self):
        self.pa = pyaudio.PyAudio()
        self.device_index = 3  # ReSpeaker device

    def _initialize_wake_word(self):
        self.porcupine = pvporcupine.create(
            access_key=os.getenv('PICOVOICE_KEY'),
            keywords=['porcupine']
        )

    def _initialize_speech_recognition(self):
        vosk.SetLogLevel(-1)
        self.vosk_model = vosk.Model("vosk-model")
        self.vosk_rec = vosk.KaldiRecognizer(self.vosk_model, 16000)

    def _initialize_ai(self):
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def _initialize_tts(self):
        self.tts_client = texttospeech.TextToSpeechClient()

    def setup_audio_stream(self):
        return self.pa.open(
            rate=16000,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=4096,
            input_device_index=self.device_index
        )

    def listen_for_command(self, audio_stream):
        print("Listening for command...")
        start_time = time.time()
        text = ""
        
        while time.time() - start_time < 5:  # 5 second timeout
            data = audio_stream.read(4096, exception_on_overflow=False)
            if self.vosk_rec.AcceptWaveform(data):
                result = json.loads(self.vosk_rec.Result())
                if result["text"]:
                    text = result["text"]
                    break
        return text

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
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16
            )

            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            # Play using aplay with the correct device
            with open("response.wav", "wb") as out:
                out.write(response.audio_content)
            os.system(f'aplay -D plughw:{self.device_index},0 response.wav')

        except Exception as e:
            print(f"TTS Error: {e}")
            # Fallback to espeak
            os.system(f'espeak "{text}"')

    def run(self):
        audio_stream = self.setup_audio_stream()
        print("TARS is listening for wake word 'porcupine'...")
        
        try:
            while True:
                # Wake word detection
                pcm = audio_stream.read(self.porcupine.frame_length)
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                
                if self.porcupine.process(pcm) >= 0:
                    print("Wake word detected!")
                    
                    # Get voice command
                    command = self.listen_for_command(audio_stream)
                    if command:
                        print(f"Command: {command}")
                        
                        # Get AI response
                        response = self.get_ai_response(command)
                        print(f"AI Response: {response}")
                        
                        # Speak response
                        self.speak_response(response)
                    
                    print("Listening for wake word...")

        except KeyboardInterrupt:
            print("Stopping TARS...")
        finally:
            audio_stream.close()
            self.pa.terminate()
            self.porcupine.delete()
