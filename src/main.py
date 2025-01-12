import logging
import os
import sys
from assistant import TARS

# Completely suppress all loggers initially
logging.root.setLevel(logging.CRITICAL)

# Then enable only our specific logger
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    force=True
)

# Redirect stderr (ALSA messages) to devnull
stderr = sys.stderr
sys.stderr = open(os.devnull, 'w')

def main():
    device_index = 1  # Update this with the correct device index from the list_audio_devices output
    tars = TARS(device_index)
    tars.run()

if __name__ == '__main__':
    main()