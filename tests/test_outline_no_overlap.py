from janito.agent.tools.outline.python_outline import parse_python_outline


def test_no_overlap_top_level_functions_classes():
    code = [
        "def foo():",  # 1
        "    pass",  # 2
        "def bar():",  # 3
        "    pass",  # 4
        "class Baz:",  # 5
        "    def method(self):",  # 6
        "        pass",  # 7
        "def qux():",  # 8
        "    pass",  # 9
    ]
    outline = parse_python_outline(code)
    # Filter only top-level functions and classes
    tops = [
        x for x in outline if x["type"] in ("function", "class") and not x["parent"]
    ]
    # Sort by start
    tops.sort(key=lambda x: x["start"])
    for i in range(len(tops) - 1):
        assert (
            tops[i]["end"] < tops[i + 1]["start"]
        ), f"Overlap: {tops[i]} and {tops[i+1]}"
    print("test_no_overlap_top_level_functions_classes passed.")


if __name__ == "__main__":
    test_no_overlap_top_level_functions_classes()
