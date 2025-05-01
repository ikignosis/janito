from janito.agent.tools.outline.python_outline import parse_python_outline


def test_outline_on_complex_python_file():
    file_path = "tests/sample_outline_complex.py"
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    outline = parse_python_outline([line.rstrip("\n") for line in lines])
    print("RAW OUTLINE:")
    for item in outline:
        doc = item.get("docstring", "")
        doc_short = (doc[:40] + "...") if doc and len(doc) > 40 else doc
        print(
            f"<{item['type']} {item['name']} [{item['start']}-{item['end']}] parent={item['parent']} docstring={doc_short!r}>"
        )
    # Check for constants and globals
    _ = next(x for x in outline if x["type"] == "const" and x["name"] == "CONSTANT")
    _ = next(x for x in outline if x["type"] == "var" and x["name"] == "global_var")
    # Check for top-level functions
    _ = next(
        x for x in outline if x["type"] == "function" and x["name"] == "outer_function"
    )
    _ = next(
        x
        for x in outline
        if x["type"] == "function" and x["name"] == "another_function"
    )
    # Check for classes and methods
    _ = next(x for x in outline if x["type"] == "class" and x["name"] == "OuterClass")
    _ = next(x for x in outline if x["type"] == "class" and x["name"] == "InnerClass")
    _ = next(x for x in outline if x["type"] == "method" and x["name"] == "method_one")
    _ = next(x for x in outline if x["type"] == "method" and x["name"] == "method_two")
    _ = next(
        x for x in outline if x["type"] == "method" and x["name"] == "inner_method"
    )
    # Check for nested function inside method (should be classified as method)
    _ = next(
        x
        for x in outline
        if x["type"] == "method" and x["name"] == "nested_method_func"
    )
    # Check for nested function inside function
    _ = next(
        x for x in outline if x["type"] == "function" and x["name"] == "inner_function"
    )
    # Check for main block
    _ = next(x for x in outline if x["type"] == "main" and x["name"] == "__main__")
    print("test_outline_on_complex_python_file passed.")


if __name__ == "__main__":
    test_outline_on_complex_python_file()
