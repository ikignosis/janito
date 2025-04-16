# Tools Reference

This document provides detailed technical information about the available tools, their purposes, and all parameter details.

---

## 1. find_by_name
- **Purpose:** Search for files and subdirectories within a specified directory using glob patterns, extensions, and filters.
- **Parameters:**
  - `Excludes` (list of string, optional): Glob patterns to exclude from results.
  - `Extensions` (list of string, optional): File extensions to include (without dot).
  - `FullPath` (boolean, optional): If true, pattern matches the full path; otherwise, just the filename.
  - `MaxDepth` (integer, optional): Maximum directory depth to search.
  - `Pattern` (string, optional): Glob pattern to match filenames.
  - `SearchDirectory` (string, required): Directory to search within.
  - `Type` (string, optional): Filter by 'file', 'directory', or 'any'.

---

## 2. grep_search
- **Purpose:** Search for pattern matches within files or directories (like egrep, supporting regular expressions).
- **Parameters:**
  - `CaseInsensitive` (boolean): Perform a case-insensitive search.
  - `Includes` (list of string, optional): File patterns or paths to include.
  - `MatchPerLine` (boolean): If true, return each matching line; if false, only filenames.
  - `Query` (string): The pattern to search for.
  - `SearchPath` (string): Directory or file to search within.

---

## 3. codebase_search
- **Purpose:** Find code snippets most relevant to a search query.
- **Parameters:**
  - `Query` (string): Search query.
  - `TargetDirectories` (list of string): Directories to search within.

---

## 4. view_file
- **Purpose:** View contents of a file, optionally with a summary of lines outside the viewed range.
- **Parameters:**
  - `AbsolutePath` (string): Path to the file.
  - `EndLine` (integer): Last line to view (inclusive).
  - `IncludeSummaryOfOtherLines` (boolean): Include a summary of other lines.
  - `StartLine` (integer): First line to view.

---

## 5. view_code_item
- **Purpose:** View up to 5 code items (functions, classes) in a file.
- **Parameters:**
  - `File` (string): Path to the file.
  - `NodePaths` (list of string): List of code item paths (e.g., package.class.FunctionName).

---

## 6. write_to_file
- **Purpose:** Create new files and write code to them.
- **Parameters:**
  - `CodeContent` (string): Content to write.
  - `EmptyFile` (boolean): Create an empty file if true.
  - `TargetFile` (string): Path to the new file.

---

## 7. replace_file_content
- **Purpose:** Edit existing files by replacing specific chunks of code.
- **Parameters:**
  - `TargetFile` (string): File to modify.
  - `CodeMarkdownLanguage` (string): Language for syntax highlighting.
  - `Instruction` (string): Description of the change.
  - `ReplacementChunks` (list of object): Each chunk specifies a replacement:
    - `AllowMultiple` (boolean): If true, replace all occurrences of `TargetContent`.
    - `TargetContent` (string): Exact code/text to search for (must match exactly, including whitespace).
    - `ReplacementContent` (string): New code/text to replace `TargetContent`.
  - `TargetLintErrorIds` (list of string, optional): Lint error IDs to fix.

---

## 8. run_command
- **Purpose:** Propose and run terminal commands.
- **Parameters:**
  - `Blocking` (boolean): Wait for command to finish.
  - `CommandLine` (string): Exact command to run.
  - `Cwd` (string): Working directory.
  - `SafeToAutoRun` (boolean): True only for safe commands.
  - `WaitMsBeforeAsync` (integer): Wait time before making async (ms).

---

## 9. command_status
- **Purpose:** Get status and output of a previously executed command.
- **Parameters:**
  - `CommandId` (string): ID of the command.
  - `OutputCharacterCount` (integer): Number of characters to view.
  - `OutputPriority` (string): 'top', 'bottom', or 'split'.
  - `WaitDurationSeconds` (integer): Seconds to wait for completion.

---

## 10. read_url_content
- **Purpose:** Read content from a web URL.
- **Parameters:**
  - `Url` (string): The URL to read.

---

## 11. view_web_document_content_chunk
- **Purpose:** View a specific chunk of previously-read web document content.
- **Parameters:**
  - `position` (integer): Chunk position.
  - `url` (string): URL of the document.

---

## 12. search_web
- **Purpose:** Perform a web search for relevant documents.
- **Parameters:**
  - `domain` (string, optional): Domain to prioritize.
  - `query` (string): Search query.

---

## 13. read_deployment_config
- **Purpose:** Read deployment configuration for a web app.
- **Parameters:**
  - `ProjectPath` (string): Absolute path to the project.

---

## 14. deploy_web_app
- **Purpose:** Deploy a JavaScript web app to a provider like Netlify.
- **Parameters:**
  - `Framework` (string): E.g., nextjs, sveltekit, etc.
  - `ProjectId` (string): Existing project ID (empty for new).
  - `ProjectPath` (string): Absolute path.
  - `Subdomain` (string): Subdomain/project name (empty for existing).

---

## 15. check_deploy_status
- **Purpose:** Check status of a web app deployment.
- **Parameters:**
  - `WindsurfDeploymentId` (string): Deployment ID.

---

## 16. create_memory
- **Purpose:** Save, update, or delete important context/memories.
- **Parameters:**
  - `Action` (string): 'create', 'update', or 'delete'.
  - `Content` (string): Memory content (omit for delete).
  - `CorpusNames` (list of string): Workspaces associated.
  - `Id` (string): Memory ID (for update/delete).
  - `Tags` (list of string): Tags for filtering.
  - `Title` (string): Descriptive title.
  - `UserTriggered` (boolean): If user requested.

---

## 17. browser_preview
- **Purpose:** Spin up a browser preview for a local web server.
- **Parameters:**
  - `Name` (string): Short name for the server.
  - `Url` (string): Server URL (with scheme, domain, port).

---

## 18. list_dir
- **Purpose:** List contents of a directory.
- **Parameters:**
  - `DirectoryPath` (string): Absolute path to directory.

---

## 19. suggested_responses
- **Purpose:** Suggest short response options to the user.
- **Parameters:**
  - `Suggestions` (list of string): List of suggestions (short phrases).

---

## Notes on ReplacementChunks (replace_file_content only)
- `ReplacementChunks` is a list of objects, each with:
  - `AllowMultiple`: Replace all occurrences if true; otherwise, only the first occurrence.
  - `TargetContent`: The exact code/text to be replaced (must match exactly, including whitespace).
  - `ReplacementContent`: The new code/text to insert in place of `TargetContent`.

Other tools do not use these parameters.
