import sys
from . import app


def main():
    import os

    # Ensure PYTHONUTF8 is set for consistent UTF-8 behavior
    if os.environ.get("PYTHONUTF8") != "1":
        os.environ["PYTHONUTF8"] = "1"
        if os.name == "nt" and sys.argv[0]:
            print("[info] Restarting web server with PYTHONUTF8=1 for UTF-8 support...")
            os.execvpe(sys.executable, [sys.executable] + sys.argv, os.environ)
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
