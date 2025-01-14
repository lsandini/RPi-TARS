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

def main():
    try:
        tars = TARS()
        print("Listening for wake word 'Jarvis'...")
        tars.run()
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()