import sys
from . import app


def main():
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}")
            sys.exit(1)
    app.app.run(host="0.0.0.0", port=port, debug=True)


if __name__ == "__main__":
    main()
