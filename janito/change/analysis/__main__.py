"""Main entry point for the analysis module."""

from .analyze import analyze_request
from janito.config import config
            

def main():
    """Main entry point"""
    config.set_verbose(True)
    config.set_debug(True)
    analysis = analyze_request("", "create helloy.py with an hello world print")
    print(analysis)

if __name__ == "__main__":
    main()