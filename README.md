# Raspberry Pi Voice Assistant

A voice-controlled assistant running on Raspberry Pi that provides a complete voice interaction pipeline:

1. **Wake Word Detection** (Picovoice Porcupine)
   - Continuously listens for the wake phrase "Hey Computer"
   - Low resource usage while waiting for activation
   - Triggers the full speech recognition when detected

2. **Speech Recognition** (Vosk)
   - Activates after wake word detection
   - Captures user's speech through microphone
   - Converts speech to text locally
   - Provides real-time transcription

3. **AI Processing** (OpenAI/Claude)
   - Takes transcribed text as input
   - Sends as a prompt to AI model
   - Receives and processes AI response
   - Handles various types of queries and commands

4. **Text-to-Speech** (Google Cloud TTS)
   - Converts AI's text response to natural speech
   - Synthesizes human-like voice output
   - Supports multiple languages and voices

5. **Audio Playback**
   - Outputs synthesized speech through speakers
   - Completes the interaction loop

The system operates in a continuous loop:
```
[Waiting for Wake Word] 
    ↓
"Hey Computer" detected
    ↓
Speech Recognition activates
    ↓
Text sent to AI for processing
    ↓
AI response converted to speech
    ↓
Response played through speakers
    ↓
[Returns to waiting for Wake Word]
```

This creates a fluid, conversational interface that combines the reliability of local speech recognition with the intelligence of cloud-based AI processing.

## Features

- **Wake Word Detection**: Using Picovoice Porcupine for efficient wake word recognition
- **Speech Recognition**: Vosk for offline, reliable speech-to-text conversion
- **AI Processing**: Integration with OpenAI GPT for intelligent responses
- **Text-to-Speech**: Google Cloud TTS for natural-sounding voice output
- **Cross-Platform**: Developed and tested on both x86_64 (development) and ARM64 (Raspberry Pi)

## Prerequisites

### Hardware Requirements

- Raspberry Pi 3B+ or better (for deployment)
- Tested on Raspberry Pi 4 8GB
- Raspberry Pi OS Legacy 32-bit (Bullseye)
  Linux rpi4 6.1.21-v8+ #1642 SMP PREEMPT Mon Apr  3 17:24:16 BST 2023 aarch64
- USB Microphone or USB Sound Card (Seeedvoice ReSpeaker-2Mic-Pi-HAT)
- Speakers (JST/USB or 3.5mm audio output)
- Internet connection
- For SeeedVoice ReSpeaker 2-MICS Pi HAT, use these installation instructions:  
  [https://github.com/HinTak/seeed-voicecard](https://github.com/HinTak/seeed-voicecard)

- For Raspberry Pi OS 32/64-bit (Bookworm): there are issues with the Seeedvoice driver installation, I couldn't get the microphones to work !

### API Keys Required
- OpenAI API Key
- Google Cloud Service Account Key
- Picovoice Access Key (for wake word detection)

## Installation

The installation process is split into three automated parts for better control and error handling.

1. Clone the repository:
```bash
git clone https://github.com/lsandini/RPi-TARS.git
cd RPi-TARS
```

2. Make the setup scripts executable:
```bash
chmod +x setup_part1.sh setup_part2.sh setup_part3.sh
```

3. Run the installation:
```bash
./setup_part1.sh
```
This will automatically run all three parts of the setup in sequence.

### What Each Setup Part Does

#### Part 1 (setup_part1.sh)
- Creates project structure
- Sets up basic speech components
- Initializes git repository
- Creates configuration templates

#### Part 2 (setup_part2.sh)
- Adds AI processing components
- Implements wake word detection
- Creates main application logic
- Sets up logging

#### Part 3 (setup_part3.sh)
- Installs system dependencies
- Sets up Python virtual environment
- Downloads Vosk speech recognition model
- Tests audio configuration
- Handles architecture-specific setup (ARM/x86)

## Configuration

1. Copy the environment template:
```bash
cp .env.template .env
```

2. Edit .env and add your API keys:
```bash
# API Keys
OPENAI_API_KEY=your_key_here
PICOVOICE_ACCESS_KEY=your_key_here

# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=path_to_credentials.json
```

3. Place your Google Cloud service account JSON file in the project root.

## Usage

1. Activate the virtual environment:
```bash
source venv/bin/activate
```

2. Start the assistant:
```bash
./start_assistant.sh
```

3. Wake up the assistant by saying "Hey Computer" (default wake word)

### Voice Commands
- "Hello" - General greeting
- "What time is it?" - Get current time
- "Goodbye" - End the session
- Any other phrase will be processed by the AI for a response

## Project Structure
```
.
├── src/
│   ├── speech/
│   │   ├── stt.py         # Speech-to-text using Vosk
│   │   ├── tts.py         # Text-to-speech using Google Cloud
│   │   └── wake_word.py   # Wake word detection using Picovoice
│   ├── ai/
│   │   └── openai_handler.py  # AI processing
│   └── utils/
│       └── logger.py      # Logging utilities
├── models/                # Voice recognition models
├── logs/                  # Application logs
├── setup_part1.sh        # Initial setup script
├── setup_part2.sh        # AI components setup
├── setup_part3.sh        # Dependencies and models setup
└── start_assistant.sh    # Launch script
```

## Development vs Deployment

- The setup scripts automatically detect the system architecture
- Development can be done on x86_64 systems (like WSL2)
- Final deployment should be on Raspberry Pi (ARM64)
- Run the setup again when deploying to Raspberry Pi

## Troubleshooting

### Audio Issues
- Run `python3 -m sounddevice` to list available audio devices
- Check microphone permissions
- Verify audio output configuration

### Common Problems
1. **Wake word not detecting**:
   - Check Picovoice access key
   - Verify microphone input levels

2. **Speech recognition issues**:
   - Ensure Vosk model is downloaded correctly
   - Check microphone quality and position

3. **No audio output**:
   - Verify speaker connections
   - Check Google Cloud credentials
   - Test system audio

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Vosk](https://alphacephei.com/vosk/) for offline speech recognition
- [Picovoice](https://picovoice.ai/) for wake word detection
- [OpenAI](https://openai.com/) for AI processing
- [Google Cloud](https://cloud.google.com/) for text-to-speech

## Future Improvements

- [ ] Add more wake word options
- [ ] Implement offline fallback mode
- [ ] Add custom command handlers
- [ ] Improve error recovery
- [ ] Add web interface for configuration