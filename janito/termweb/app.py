from bottle import Bottle, static_file, request, response
import os

app = Bottle()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


@app.route("/")
def index():
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return static_file("index.html", root=static_dir)


@app.route("/file")
def file_view():
    # Only allow AJAX/XHR requests for file content (not direct browser navigation)
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        response.status = 403
        return "Direct access to /file is disabled. Use /?path=... for file view/edit."
    file_path = request.query.get("path")
    if not file_path:
        response.status = 400
        return "Missing file path."
    abs_path = os.path.abspath(os.path.join(BASE_DIR, file_path))
    # Security: Only allow files within BASE_DIR
    if not abs_path.startswith(BASE_DIR):
        response.status = 403
        return "Access denied."
    if not os.path.isfile(abs_path):
        response.status = 404
        return "File not found."
    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    response.content_type = "text/plain; charset=utf-8"
    return content


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
    # No rich spinner or console here, just run the app
    print(f"Starting web server on http://localhost:{port}")
    app.run(host="localhost", port=port, debug=True)
