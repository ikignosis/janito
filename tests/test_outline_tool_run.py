import sys
import os

sys.path.insert(0, os.path.abspath("."))
from janito.agent.tools.get_file_outline.python_outline import parse_python_outline


def test_parse_python_outline_accuracy():
    code = [
        "class A:",  # 1
        "    def foo(self):",  # 2
        "        pass",  # 3
        "",  # 4
        "    def bar(self):",  # 5
        "        pass",  # 6
        "",  # 7
        "def top():",  # 8
        "    pass",  # 9
        "",  # 10
        "class B:",  # 11
        "    pass",  # 12
    ]
    outline = parse_python_outline(code)
    print("OUTLINE OUTPUT:")
    for item in outline:
        print(item)

    # Find by name/type for clarity
    def find(type_, name):
        return next(x for x in outline if x["type"] == type_ and x["name"] == name)

    a = find("class", "A")
    foo = find("method", "foo")
    bar = find("method", "bar")
    top = find("function", "top")
    b = find("class", "B")
    assert a["start"] == 1 and a["end"] == 7, f"A: {a}"
    assert foo["start"] == 2 and foo["end"] == 3, f"foo: {foo}"
    assert bar["start"] == 5 and bar["end"] == 6, f"bar: {bar}"
    assert top["start"] == 8 and top["end"] == 10, f"top: {top}"
    assert b["start"] == 11 and b["end"] == 12, f"B: {b}"
    print("parse_python_outline accuracy test passed.")


if __name__ == "__main__":
    test_parse_python_outline_accuracy()
