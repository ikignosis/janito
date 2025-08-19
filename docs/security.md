# Path Security in Janito

Janito enforces path security for all file and directory arguments passed to tools. This is designed to prevent accidental or malicious access to files outside the intended working directory.

## How Path Security Works
- By default, any tool argument that looks like a file or directory path is checked to ensure it is within the allowed working directory (`workdir`).
- If a path is outside the allowed `workdir`, the operation is blocked and a security error is raised.
- This enforcement is automatic for all tools executed via the tools adapter if a `workdir` is set.

## Disabling Path Security
You can disable this restriction using the `-u` or `--unrestricted` CLI flag. **Disabling path security is dangerous and should only be done if you trust your prompt, tools, and environment.**

```sh
janito -u "Do something with C:/Windows/System32/hosts"
```

- When path security is disabled, tools can access any file or directory path, including sensitive system files.
- Only use this option for trusted workflows or debugging.

## Example
If `workdir` is `/home/user/project` and a tool is called with `{ "path": "/etc/passwd" }`, the call will be rejected unless `-u` is specified.

## Implementation Details
- Path security is implemented in `janito/tools/path_security.py` and integrated in the tools adapter.
- See the [Developer Guide](guides/tools-developer-guide.md) for more technical details.

## See Also
- [CLI Options](reference/cli-options.md)
- [Tools Developer Guide](guides/tools-developer-guide.md)
