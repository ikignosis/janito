from bottle import Bottle, static_file, response, request
import os
import json

app = Bottle()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


@app.route("/")
def index():
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    file_path = request.query.get("path")
    if file_path:
        return static_file("editor.html", root=static_dir)
    return static_file("index.html", root=static_dir)


@app.route("/explorer")
@app.route("/explorer/")
@app.route("/explorer/<path:path>")
def explorer(path="."):
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return static_file("explorer.html", root=static_dir)


@app.route("/explore")
def explore_query():
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return static_file("explorer.html", root=static_dir)


@app.route("/api/explorer/<path:path>")
def api_explorer(path="."):
    abs_path = os.path.abspath(os.path.join(BASE_DIR, path))
    # Security: Only allow files/dirs within BASE_DIR
    if not abs_path.startswith(BASE_DIR):
        response.status = 403
        return json.dumps({"error": "Access denied."})
    if os.path.isdir(abs_path):
        # List directory contents
        entries = []
        for entry in sorted(os.listdir(abs_path)):
            entry_path = os.path.join(abs_path, entry)
            entries.append({"name": entry, "is_dir": os.path.isdir(entry_path)})
        return json.dumps({"type": "dir", "path": path, "entries": entries})
    elif os.path.isfile(abs_path):
        # Return file content
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return json.dumps({"type": "file", "path": path, "content": content})
    else:
        response.status = 404
        return json.dumps({"error": "Not found."})


@app.route("/static/<filepath:path>")
def server_static(filepath):
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return static_file(filepath, root=static_dir)


if __name__ == "__main__":
    import sys

    port = 8088
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            try:
                port = int(sys.argv[idx + 1])
            except ValueError:
                pass
    print(f"Starting web server on http://localhost:{port}")
    app.run(host="localhost", port=port, debug=True)
