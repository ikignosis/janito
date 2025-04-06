import sys
import app as flask_app


def main():
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}")
            sys.exit(1)
    flask_app.app.run(host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()
