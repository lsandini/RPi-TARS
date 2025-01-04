#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[1;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check architecture
check_architecture() {
    echo -e "${BLUE}Checking system architecture...${NC}"
    ARCH=$(uname -m)
    
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "armv7l" ]; then
        echo -e "${GREEN}Running on ARM architecture (Raspberry Pi)${NC}"
        # ARM-specific model URLs
        VOSK_MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
        
        # Additional ARM-specific setup if needed
        if command_exists apt; then
            echo -e "${YELLOW}Installing ARM-specific dependencies...${NC}"
            sudo apt-get update
            sudo apt-get install -y python3-numpy python3-scipy
        fi
    else
        echo -e "${YELLOW}Running on $ARCH architecture (development environment)${NC}"
        VOSK_MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    fi
    
    # Export for use in other functions
    export VOSK_MODEL_URL
    export SYSTEM_ARCH=$ARCH
}

# Function to check and install system dependencies
check_dependencies() {
    echo -e "${BLUE}Checking system dependencies...${NC}"
    
    # List of required system packages
    DEPS=("python3" "python3-pip" "wget" "unzip" "portaudio19-dev" "python3-venv")
    
    # Check if apt is available (Debian/Ubuntu)
    if command_exists apt; then
        for dep in "${DEPS[@]}"; do
            if ! dpkg -l | grep -q "^ii  $dep "; then
                echo -e "${YELLOW}Installing $dep...${NC}"
                sudo apt-get install -y "$dep"
            fi
        done
    else
        echo -e "${RED}This script requires apt package manager. Please install dependencies manually.${NC}"
        exit 1
    fi
}

# Function to download and extract Vosk model
setup_vosk_model() {
    echo -e "${BLUE}Setting up Vosk model...${NC}"
    
    MODELS_DIR="models"
    VOSK_MODEL_DIR="$MODELS_DIR/vosk-model-small-en-us-0.15"
    
    if [ ! -d "$VOSK_MODEL_DIR" ]; then
        echo -e "${YELLOW}Downloading Vosk model...${NC}"
        mkdir -p "$MODELS_DIR"
        if wget -O "$MODELS_DIR/vosk-model.zip" "$VOSK_MODEL_URL"; then
            echo -e "${YELLOW}Extracting model...${NC}"
            unzip "$MODELS_DIR/vosk-model.zip" -d "$MODELS_DIR"
            rm "$MODELS_DIR/vosk-model.zip"
            echo -e "${GREEN}Vosk model setup complete!${NC}"
        else
            echo -e "${RED}Failed to download Vosk model${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}Vosk model already exists.${NC}"
    fi
}

# Function to set up virtual environment
setup_venv() {
    echo -e "${BLUE}Setting up Python virtual environment...${NC}"
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo -e "${GREEN}Virtual environment created${NC}"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    echo -e "${YELLOW}Upgrading pip...${NC}"
    pip install --upgrade pip
    
    # Install requirements
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    if [ "$SYSTEM_ARCH" = "aarch64" ] || [ "$SYSTEM_ARCH" = "armv7l" ]; then
        # ARM-specific installation order
        echo -e "${YELLOW}Installing ARM-specific dependencies first...${NC}"
        pip install wheel
        pip install numpy
        pip install --only-binary :all: scipy
    fi
    
    pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Python dependencies installed successfully${NC}"
    else
        echo -e "${RED}Failed to install Python dependencies${NC}"
        exit 1
    fi
}

# Function to test audio setup
test_audio() {
    echo -e "${BLUE}Testing audio setup...${NC}"
    
    # Test microphone access
    python3 -c "import sounddevice as sd; print('Available audio devices:\n', sd.query_devices())"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Audio setup looks good!${NC}"
    else
        echo -e "${RED}Audio setup test failed. Please check your microphone configuration.${NC}"
    fi
}

# Main function
main() {
    echo -e "${BLUE}Starting setup part 3 - Models and Dependencies...${NC}"
    
    # Check architecture first
    check_architecture
    
    # Check system dependencies
    check_dependencies
    
    # Setup virtual environment and install requirements
    setup_venv
    
    # Download and setup Vosk model
    setup_vosk_model
    
    # Test audio setup
    test_audio
    
    echo -e "${GREEN}Setup part 3 completed!${NC}"
    echo -e "${BLUE}Complete installation successful!${NC}"
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Ensure your Google Cloud credentials file is in place"
    echo "2. Copy .env.template to .env if you haven't already"
    echo "3. Copy your google-service-account.json to the project root"
    echo "4. Run the assistant: ./start_assistant.sh"
    
    if [ "$SYSTEM_ARCH" = "aarch64" ] || [ "$SYSTEM_ARCH" = "armv7l" ]; then
        echo -e "${GREEN}Setup completed on Raspberry Pi (ARM) architecture${NC}"
    else
        echo -e "${YELLOW}Setup completed on development environment ($SYSTEM_ARCH)${NC}"
        echo "Note: When deploying to Raspberry Pi, run the setup again on the device"
    fi
}

# Run main function
main