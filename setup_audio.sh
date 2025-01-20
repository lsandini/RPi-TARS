#!/bin/bash

# Check if amixer is installed
if ! command -v amixer &> /dev/null; then
  echo "amixer is not installed. Please install alsa-utils and try again."
  exit 1
fi

# Set audio card name
CARD="seeed2micvoicec"

echo "Configuring audio settings for $CARD..."

# Your custom settings
amixer -c $CARD set Playback 180
amixer -c $CARD set Speaker 180
amixer -c $CARD set 'Speaker AC' 4
amixer -c $CARD set 'Speaker DC' 4

# General playback settings
amixer -c $CARD set 'Headphone' 127
amixer -c $CARD set 'Headphone Playback ZC' on
amixer -c $CARD set 'Speaker Playback ZC' on
amixer -c $CARD set 'PCM Playback -6dB' on

# Capture settings
amixer -c $CARD set 'Capture' 63
amixer -c $CARD set 'Capture' cap
amixer -c $CARD set 'ADC PCM' 195
amixer -c $CARD set 'Left Input Boost Mixer LINPUT1' 3
amixer -c $CARD set 'Right Input Boost Mixer RINPUT1' 3
amixer -c $CARD set 'Left Input Mixer Boost' on
amixer -c $CARD set 'Right Input Mixer Boost' on

# Optional advanced settings
amixer -c $CARD set '3D' 15
amixer -c $CARD set '3D Filter Lower Cut-Off' High
amixer -c $CARD set '3D Filter Upper Cut-Off' High
amixer -c $CARD set 'ALC Function' 'Stereo'

echo "Audio configuration complete for $CARD!"
