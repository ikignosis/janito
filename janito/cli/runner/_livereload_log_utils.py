def print_livereload_logs(stdout_path, stderr_path):
    print("\n[LiveReload stdout log]")
    try:
        with open(stdout_path, encoding="utf-8") as f:
            print(f.read())
    except Exception as e:
        print(f"[Error reading stdout log: {e}]")
    print("\n[LiveReload stderr log]")
    try:
        with open(stderr_path, encoding="utf-8") as f:
            print(f.read())
    except Exception as e:
        print(f"[Error reading stderr log: {e}]")
