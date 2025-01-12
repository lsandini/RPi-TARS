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
    def __init__(self, device_index):
        self.device_index = device_index

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
        
        # Adjust for ambient noise
        try:
            with sr.Microphone(device_index=device_index) as source:
                print("Calibrating ambient noise... Please wait.")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
        except Exception as e:
            print(f"Microphone initialization error: {e}")
            self.microphone_initialized = False
        else:
            self.microphone_initialized = True

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
                
            os.system(f'aplay -D plughw:3,0 response.wav')

        except Exception as e:
            print(f"TTS Error: {e}")
            print(f"TARS: {text}")

    def _listen_for_command(self):
        if not self.microphone_initialized:
            print("Microphone not initialized. Cannot listen for commands.")
            return ""
        
        print("Listening for your command...")
        
        try:
            # Use microphone as source
            with sr.Microphone(device_index=self.device_index) as source:
                audio = self.recognizer.listen(source)
                command = self.recognizer.recognize_google(audio)
                return command
        except Exception as e:
            print(f"Listening error: {e}")
            return ""

    def conversation_mode(self):
        if not self.microphone_initialized:
            print("Microphone not initialized. Cannot enter conversation mode.")
            return
        
        print("Entering conversation mode...")
        commands_count = 0
        last_command_time = time.time()
        
        while True:
            if commands_count >= 5:
                break
            
            command = self._listen_for_command()
            if command:
                response = self.get_ai_response(command)
                self.speak_response(response)
                commands_count += 1
                last_command_time = time.time()
            elif time.time() - last_command_time > 60:
                break

    def run(self):
        # Set up initial audio stream for Porcupine
        porcupine_stream = None
        try:
            porcupine_stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=512,
                input_device_index=self.device_index
            )
            
            print("Listening for wake word 'Jarvis'...")
            
            while True:
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
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if porcupine_stream is not None:
                print("Closing porcupine_stream...")
                try:
                    porcupine_stream.stop_stream()
                    porcupine_stream.close()
                except Exception as e:
                    print(f"Error closing porcupine_stream: {e}")
            else:
                print("porcupine_stream is None")
                
            if self.pa is not None:
                print("Terminating PyAudio...")
                try:
                    self.pa.terminate()
                except Exception as e:
                    print(f"Error terminating PyAudio: {e}")
            else:
                print("self.pa is None")
                
            if self.porcupine is not None:
                print("Deleting Porcupine instance...")
                try:
                    self.porcupine.delete()
                except Exception as e:
                    print(f"Error deleting Porcupine instance: {e}")
            else:
                print("self.porcupine is None")

def main():
    device_index = 3  # Update this with the correct device index from the list_audio_devices output
    tars = TARS(device_index)
    tars.run()

if __name__ == '__main__':
    main()