from janito.agent.tools.run_powershell_command import RunPowerShellCommandTool


def main():
    tool = RunPowerShellCommandTool()
    # Simple PowerShell command
    result = tool.run('Write-Output "Hello from PowerShell"')
    # Write result to file in utf-8 to avoid Windows console encoding issues
    with open("tests/powershell_test_output.txt", "w", encoding="utf-8") as f:
        f.write(result)
    print("✅ Output written to tests/powershell_test_output.txt (UTF-8)")


if __name__ == "__main__":
    main()
