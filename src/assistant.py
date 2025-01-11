import os
import argparse
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
    def __init__(self, model_version='22'):
        # Load environment variables
        load_dotenv()
        
        # Initialize PyAudio
        self.pa = pyaudio.PyAudio()
        
        # Initialize Porcupine with Jarvis wake word
        self.porcupine = pvporcupine.create(
            access_key=os.getenv('PICOVOICE_KEY'),
            keywords=['jarvis']
        )
        
        # Initialize Vosk with selected model
        vosk.SetLogLevel(-1)
        
        # Determine model path based on version
        if model_version == '15':
            model_path = "vosk-model-15"
        elif model_version == '22':
            model_path = "vosk-model-22"
        else:
            raise ValueError(f"Invalid model version: {model_version}. Choose '15' or '22'.")
        
        # Construct full model path
        full_model_path = os.path.join(os.getcwd(), model_path)
        
        # Validate model exists
        if not os.path.exists(full_model_path):
            raise FileNotFoundError(f"Vosk model not found at {full_model_path}. "
                                    f"Ensure you have downloaded the {model_version} model.")
        
        # Initialize Vosk model
        self.vosk_model = vosk.Model(full_model_path)
        self.vosk_rec = vosk.KaldiRecognizer(self.vosk_model, 16000)

        # Initialize OpenAI
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # Initialize Google TTS
        self.tts_client = texttospeech.TextToSpeechClient()

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
        print("Listening...")
        
        # Create new stream for Vosk with larger buffer
        vosk_stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=8192,
            input_device_index=8
        )
        
        text = ""
        start_time = time.time()
        accumulated_data = b''
        
        try:
            while time.time() - start_time < 10:
                data = vosk_stream.read(8192, exception_on_overflow=False)
                accumulated_data += data
                
                # Process accumulated data when we have enough
                if len(accumulated_data) >= 32768:  # Process in larger chunks
                    if self.vosk_rec.AcceptWaveform(accumulated_data):
                        result = json.loads(self.vosk_rec.Result())
                        if result["text"]:
                            text = result["text"]
                            break
                    accumulated_data = b''  # Reset accumulator
                    
            # Process any remaining data
            if accumulated_data and not text:
                if self.vosk_rec.AcceptWaveform(accumulated_data):
                    result = json.loads(self.vosk_rec.Result())
                    if result["text"]:
                        text = result["text"]
                    
        finally:
            vosk_stream.stop_stream()
            vosk_stream.close()
            
        return text.lower()

    def conversation_mode(self):
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
            input_device_index=8
        )
        
        try:
            print("Listening for wake word 'Jarvis'...")
            
            while True:
                # Wake word detection phase
                pcm = porcupine_stream.read(self.porcupine.frame_length)
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                
                if self.porcupine.process(pcm) >= 0:
                    print("Wake word detected! Starting conversation mode...")
                    
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
    # Set up argument parser
    parser = argparse.ArgumentParser(description='TARS Voice Assistant')
    parser.add_argument(
        '-m', 
        '--model', 
        choices=['15', '22'], 
        default='22', 
        help='Vosk speech recognition model version (default: 22)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Initialize and run TARS with selected model
    tars = TARS(model_version=args.model)
    tars.run()

if __name__ == '__main__':
    main()