import sys
import os
from livereload import Server


def main():
    port = 35729  # Default livereload port
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            try:
                port = int(sys.argv[idx + 1])
            except ValueError:
                pass
    watch_dir = os.path.abspath(os.getcwd())
    server = Server()
    server.watch(watch_dir, delay=1)
    print(
        f"Starting livereload server on http://localhost:{port}, watching {watch_dir}"
    )
    server.serve(root=watch_dir, port=port, open_url_delay=None)


if __name__ == "__main__":
    main()
