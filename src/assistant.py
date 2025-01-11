import os
from dotenv import load_dotenv
import pvporcupine
import pyaudio
import struct
import vosk
import json
import time
import random
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
        
        # Initialize Vosk
        vosk.SetLogLevel(-1)
        self.vosk_model = vosk.Model("vosk-model")
        self.vosk_rec = vosk.KaldiRecognizer(self.vosk_model, 16000)

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

        # Audio device configuration
        self.input_device_index = 8  # You may need to adjust this

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
            os.system(f'aplay -D plughw:3,0 response.wav')

        except Exception as e:
            print(f"TTS Error: {e}")
            print(f"TARS: {text}")

    def _listen_for_command(self):
        print("Listening for your command...")
        
        # Create new stream specifically for Vosk
        vosk_stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4096,  # Smaller buffer
            input_device_index=self.input_device_index
        )
        
        text = ""
        start_time = time.time()
        self.vosk_rec = vosk.KaldiRecognizer(self.vosk_model, 16000)
        
        try:
            while time.time() - start_time < 5:  # Reduced listening time
                data = vosk_stream.read(4096, exception_on_overflow=False)
                
                # Process audio in real-time
                if self.vosk_rec.AcceptWaveform(data):
                    result = json.loads(self.vosk_rec.Result())
                    if result["text"]:
                        text = result["text"]
                        break
                
                # Optional: print partial results
                partial = json.loads(self.vosk_rec.PartialResult())
                if partial.get("partial"):
                    print(f"Partial: {partial['partial']}")
        
        except Exception as e:
            print(f"Listening error: {e}")
        
        finally:
            vosk_stream.stop_stream()
            vosk_stream.close()
            
        return text.lower().strip()

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
                print(f"You said: {command}")
                
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

def main():
    tars = TARS()
    tars.run()

if __name__ == '__main__':
    main()