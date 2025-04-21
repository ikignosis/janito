from janito.agent.tools.get_file_outline import GetFileOutlineTool


def main():
    tool = GetFileOutlineTool()
    result = tool.call("tests/sample_markdown.md")
    print(result)


if __name__ == "__main__":
    main()
