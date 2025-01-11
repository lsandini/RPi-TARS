import os
import vosk
import json
import pyaudio
import struct
import random
import pvporcupine
import time
from dotenv import load_dotenv
from openai import OpenAI
from google.cloud import texttospeech

class TARS:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize PyAudio
        self.pa = pyaudio.PyAudio()
        
        # Identify correct audio input device
        self.input_device_index = self._find_input_device()
        
        # Initialize Porcupine with Jarvis wake word
        self.porcupine = pvporcupine.create(
            access_key=os.getenv('PICOVOICE_KEY'),
            keywords=['jarvis']
        )
        
        # Initialize Vosk
        vosk.SetLogLevel(-1)
        self.vosk_model = vosk.Model("vosk-model")

        # Initialize OpenAI
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # Initialize Google TTS
        self.tts_client = texttospeech.TextToSpeechClient()

        # Funny wake word responses
        self.wake_word_responses = [
            "Huh?",
            "Did you say something?",
            "Hmm?",
            "Yes?",
            "I'm listening...",
            "What's up?",
            "At your service!"
        ]

    def _find_input_device(self):
        """Find a suitable input device with the right specifications."""
        for i in range(self.pa.get_device_count()):
            dev = self.pa.get_device_info_by_index(i)
            print(f"Device {i}: {dev['name']} - Channels: {dev['maxInputChannels']}")
            
            # Look for a device with exactly 1 input channel
            if dev['maxInputChannels'] == 1:
                return i
        
        # Fallback to default
        return 0

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
            os.system(f'aplay response.wav')

        except Exception as e:
            print(f"TTS Error: {e}")
            print(f"TARS: {text}")

    def conversation_mode(self):
        print("Entering conversation mode...")
        
        # Create a new recognizer for conversation mode
        recognizer = vosk.KaldiRecognizer(self.vosk_model, 16000)
        
        # Open audio stream
        stream = self.pa.open(
            rate=16000,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=8192,
            input_device_index=self.input_device_index
        )

        print("Listening for your command...")
        
        try:
            while True:
                data = stream.read(4096)
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    command = result.get("text", "").strip()
                    
                    if command:
                        print(f"You said: {command}")
                        
                        # Check for end of conversation
                        if any(word in command.lower() for word in ["thank you", "goodbye", "thanks"]):
                            print("Ending conversation mode.")
                            break
                        
                        # Get and speak AI response
                        ai_response = self.get_ai_response(command)
                        print(f"TARS: {ai_response}")
                        self.speak_response(ai_response)
        
        except KeyboardInterrupt:
            print("Conversation mode interrupted.")
        
        finally:
            stream.stop_stream()
            stream.close()

    def run(self):
        # Set up initial audio stream for Porcupine
        porcupine_stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=512,
            input_device_index=self.input_device_index
        )
        
        try:
            print("Listening for wake word 'Jarvis'...")
            
            while True:
                # Wake word detection phase
                pcm = porcupine_stream.read(self.porcupine.frame_length)
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                
                if self.porcupine.process(pcm) >= 0:
                    print("Wake word detected! Starting conversation mode...")
                    
                    # Randomly choose and speak a wake word response
                    wake_response = random.choice(self.wake_word_responses)
                    print(f"TARS: {wake_response}")
                    self.speak_response(wake_response)
                    
                    # Pause wake word detection
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

def main():
    tars = TARS()
    tars.run()

if __name__ == "__main__":
    main()