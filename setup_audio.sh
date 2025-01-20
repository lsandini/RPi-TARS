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
amixer -c $CARD set Playback 200
amixer -c $CARD set Speaker 200
amixer -c $CARD set 'Speaker AC' 5
amixer -c $CARD set 'Speaker DC' 5

# General playback settings
amixer -c $CARD set 'Headphone' 127
amixer -c $CARD set 'Headphone Playback ZC' on
amixer -c $CARD set 'Speaker Playback ZC' on
amixer -c $CARD set 'PCM Playback -6dB' off

# Capture settings
amixer -c $CARD set 'Capture' 63
amixer -c $CARD set 'ADC PCM' 195
amixer -c $CARD set 'Left Input Boost Mixer LINPUT1' 3
amixer -c $CARD set 'Right Input Boost Mixer RINPUT1' 3
amixer -c $CARD set 'ALC Max Gain' 7
amixer -c $CARD set 'ALC Min Gain' 0
amixer -c $CARD set 'Noise Gate' off
amixer -c $CARD set 'Left Input Mixer Boost' on
amixer -c $CARD set 'Right Input Mixer Boost' on

echo "Audio configuration complete for $CARD!"
