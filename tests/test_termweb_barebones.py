import subprocess
import time
import requests
import os
import sys
import threading

SERVER_SCRIPT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../janito/termweb/termweb_barebones.py")
)
SERVER_URL = "http://127.0.0.1:8088"


def stream_output(pipe, label):
    for line in iter(pipe.readline, b""):
        print(f'[{label}] {line.decode(errors="replace").rstrip()}', flush=True)
    pipe.close()


def start_server():
    # Capture stdout and stderr for debugging
    proc = subprocess.Popen(
        [sys.executable, "-u", SERVER_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    threading.Thread(
        target=stream_output, args=(proc.stdout, "SERVER STDOUT"), daemon=True
    ).start()
    threading.Thread(
        target=stream_output, args=(proc.stderr, "SERVER STDERR"), daemon=True
    ).start()
    return proc


def wait_for_server(timeout=5):
    for _ in range(timeout * 10):
        try:
            r = requests.get(SERVER_URL + "/")
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.1)
    return False


def test_explorer_root():
    r = requests.get(SERVER_URL + "/api/explorer/")
    assert r.status_code == 200
    data = r.json()
    assert "entries" in data and isinstance(data["entries"], list)


def test_explorer_file():
    # Pick a known file in the static dir (index.html)
    r = requests.get(SERVER_URL + "/api/explorer/index.html")
    if r.status_code != 200:
        print(f"DEBUG: Status code: {r.status_code}")
        print(f"DEBUG: Response text: {r.text}")
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "file" and "content" in data


def test_explorer_save_and_read():
    testfile = "test_barebones.txt"
    testpath = os.path.join(os.path.dirname(SERVER_SCRIPT), "static", testfile)
    test_content = "barebones test content"
    # Save file
    r = requests.post(
        SERVER_URL + f"/api/explorer/{testfile}", json={"content": test_content}
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("success")
    # Read file
    r = requests.get(SERVER_URL + f"/api/explorer/{testfile}")
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "file" and data["content"] == test_content
    # Cleanup
    os.remove(testpath)


def test_spa_routing():
    r = requests.get(SERVER_URL + "/some/unknown/route")
    assert r.status_code == 200
    assert "html" in r.text.lower()


def main():
    proc = start_server()
    import time

    time.sleep(1)  # Give server time to crash and print errors
    print("--- SERVER STARTUP COMPLETE ---", flush=True)
    try:
        assert wait_for_server(), "Server did not start in time."
        test_explorer_root()
        print("test_explorer_root passed")
        test_explorer_file()
        print("test_explorer_file passed")
        test_explorer_save_and_read()
        print("test_explorer_save_and_read passed")
        test_spa_routing()
        print("test_spa_routing passed")
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait()
        # No need to print logs here; already streamed live


if __name__ == "__main__":
    main()
