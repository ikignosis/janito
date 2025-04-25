from janito.agent.tools.validate_file_syntax import ValidateFileSyntaxTool


def main():
    tool = ValidateFileSyntaxTool()
    print("Validating valid.ps1:")
    result_valid = tool.call("valid.ps1")
    print(result_valid)
    print("\nValidating invalid.ps1:")
    result_invalid = tool.call("invalid.ps1")
    print(result_invalid)


if __name__ == "__main__":
    main()
