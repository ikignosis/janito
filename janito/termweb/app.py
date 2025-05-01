from quart import Quart, send_from_directory, request, jsonify, websocket
import os
from janito.agent.tools_utils.dir_walk_utils import walk_dir_with_gitignore

app = Quart(__name__)

BASE_DIR = os.getcwd()


@app.route("/")
async def index():
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    file_path = request.args.get("path")
    if file_path:
        return await send_from_directory(static_dir, "editor.html")
    return await send_from_directory(static_dir, "index.html")


@app.route("/static/<path:filepath>")
async def server_static(filepath):
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return await send_from_directory(static_dir, filepath)


@app.route("/api/explorer/")
async def api_explorer_root():
    return await api_explorer(".")


@app.route("/api/explorer/<path:path>", methods=["GET", "POST"])
async def api_explorer(path="."):
    abs_path = os.path.abspath(os.path.join(BASE_DIR, path))
    # Security: Only allow files/dirs within BASE_DIR
    if not abs_path.startswith(BASE_DIR):
        return jsonify({"error": "Acesso negado."}), 403

    if request.method == "POST":
        # Gravação de arquivo
        if os.path.isdir(abs_path):
            return jsonify({"error": "Não é possível gravar em um diretório."}), 400
        try:
            data = await request.get_json()
            content = data.get("content", "")
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # GET: comportamento actual
    if os.path.isdir(abs_path):
        entries = []
        walker = walk_dir_with_gitignore(abs_path, max_depth=1)
        for root, dirs, files in walker:
            for entry in sorted(dirs):
                entries.append({"name": entry, "is_dir": True})
            for entry in sorted(files):
                entries.append({"name": entry, "is_dir": False})
        return jsonify({"type": "dir", "path": path, "entries": entries})
    elif os.path.isfile(abs_path):
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return jsonify({"type": "file", "path": path, "content": content})
    else:
        return jsonify({"error": "Não encontrado."}), 404


# Example WebSocket endpoint
@app.websocket("/ws")
async def ws():
    while True:
        data = await websocket.receive()
        await websocket.send(f"Echo: {data}")


# Catch-all route for SPA navigation (excluding /static and /api)
@app.route("/<path:catchall>")
async def spa_catch_all(catchall):
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return await send_from_directory(static_dir, "index.html")


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
    print(f"Iniciando servidor web Quart em http://localhost:{port}")
    app.run(host="localhost", port=port, debug=True)
