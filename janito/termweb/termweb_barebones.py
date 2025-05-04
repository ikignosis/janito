import sys

try:
    print("SERVER STARTED", flush=True)
    from barebones import run_server, route
    import os
    import json
except Exception as e:
    print("SERVER CRASHED:", e, file=sys.stderr, flush=True)
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Path to your static frontend files (adjust if needed)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))


def list_directory(abs_path, rel_path):
    entries = []
    try:
        for entry in sorted(os.listdir(abs_path)):
            full_entry = os.path.join(abs_path, entry)
            entries.append({"name": entry, "is_dir": os.path.isdir(full_entry)})
        return {"type": "dir", "path": rel_path, "entries": entries}
    except Exception as e:
        return {"error": str(e)}


@route("/api/explorer/", methods=["GET"])
def explorer_root(self, body=None):
    abs_path = PROJECT_ROOT
    rel_path = "."
    result = list_directory(abs_path, rel_path)
    print(f"EXPLORER_ROOT RETURN: {result}", flush=True)
    return result


@route("/api/explorer/<path>", methods=["GET", "POST"])
def explorer(self, path, body=None):
    print(f"DEBUG: explorer CALLED with path={path}", flush=True)
    abs_path = os.path.abspath(os.path.join(PROJECT_ROOT, path))
    print(
        f"DEBUG: explorer abs_path={abs_path} (PROJECT_ROOT={PROJECT_ROOT}, path={path})",
        flush=True,
    )
    # Security: Only allow files/dirs within PROJECT_ROOT
    if not abs_path.startswith(PROJECT_ROOT):
        return {"error": "Acesso negado."}
    if self.command == "GET":
        if os.path.isdir(abs_path):
            return list_directory(abs_path, path)
        elif os.path.isfile(abs_path):
            try:
                with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                return {"type": "file", "path": path, "content": content}
            except Exception as e:
                return {"error": str(e)}
        else:
            print(
                f"DEBUG: File not found. abs_path={abs_path} (should exist? {os.path.exists(abs_path)})",
                flush=True,
            )
            return {"error": "Not found."}
    elif self.command == "POST":
        if os.path.isdir(abs_path):
            return {"error": "Não é possível gravar em um diretório."}
        try:
            data = json.loads(body.decode("utf-8")) if body else {}
            content = data.get("content", "")
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "Método não suportado."}


@route("/", html_file="index.html")
def index(self, body=None):
    pass


# Catch-all for SPA routing: serve index.html for any unknown route not starting with /api or /static
@route("/<catchall>", methods=["GET"], html_file="index.html")
def spa_catchall(self, catchall, body=None):
    # Only serve index.html if not an API or static route
    if catchall.startswith("api/") or catchall.startswith("static/"):
        return {"error": "Not found"}
    # index.html will be served by the decorator
    return None


if __name__ == "__main__":
    run_server(host="127.0.0.1", port=8088, root_dir=PROJECT_ROOT, static=["."])
