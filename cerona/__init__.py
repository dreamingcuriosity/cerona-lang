"""
Cerona - A custom scripting language interpreter
"""

__version__ = "0.1.0"
__author__ = "ZaiperUnbound"

from .main import ifs

def main():
    """Main entry point for the CLI"""
    import sys
    if len(sys.argv) < 2:
        print("Usage: cerona <filename>")
        sys.exit(1)
    
    filename = sys.argv[1]
    try:
        with open(filename, 'r') as file:
            lines = file.read()
    except FileNotFoundError:
        print(f"File '{filename}' not found.")
        sys.exit(1)
    
    ifs(lines)

if __name__ == "__main__":
    main()
