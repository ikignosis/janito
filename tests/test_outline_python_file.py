from janito.agent.tools.outline.python_outline import parse_python_outline


def test_outline_on_python_file():
    # Use an external sample Python file for testing
    file_path = "tests/sample_outline.py"
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    outline = parse_python_outline([line.rstrip("\n") for line in lines])
    # Debug: print the raw outline output
    print("RAW OUTLINE:")
    for item in outline:
        print(item)
    # Check for expected outline items
    class_item = next(
        x for x in outline if x["type"] == "class" and x["name"] == "Example"
    )
    method_one = next(
        x for x in outline if x["type"] == "method" and x["name"] == "method_one"
    )
    method_two = next(
        x for x in outline if x["type"] == "method" and x["name"] == "method_two"
    )
    standalone = next(
        x for x in outline if x["type"] == "function" and x["name"] == "standalone"
    )
    assert class_item["start"] == 1 and class_item["end"] == 8
    assert method_one["start"] == 2 and method_one["end"] == 5
    assert method_two["start"] == 4 and method_two["end"] == 5
    assert standalone["start"] == 7 and standalone["end"] == 8
    print("test_outline_on_python_file passed.")


if __name__ == "__main__":
    test_outline_on_python_file()
