import sys
import os

# Add the bot folder to path so imports work without package structure
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bot"))

from app import main

if __name__ == "__main__":
    main()
