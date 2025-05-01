# Natural Results: Human-Friendly Output from Janito Tools

## Why Janito Tools Use Unstructured, Line-Based Output

Janito's tools are designed to provide results in a natural, unstructured, line-based format—the same style commonly found in code examples, tutorials, and instructional materials. This approach is intentional and is based on several key considerations:

### 1. Familiarity and Clarity

- Most developers are accustomed to reading and understanding code in its natural, unannotated form. Code examples, documentation, and learning resources rarely use diff formats; instead, they present the code as it should appear after edits.
- By outputting results in this familiar format, Janito ensures that users can quickly understand and apply the changes without needing to mentally parse diff markers or context lines.

### 2. Avoiding Out-of-Context Patterns

- Diff-based formats (such as unified diffs with `+`, `-`, or `@@` markers) are excellent for code review and version control, but they introduce artificial patterns and symbols that are not part of the actual code.
- When these patterns are present in the editing or code generation flow, they can inadvertently influence the language model or the user's perception, potentially leading to lower-quality code or confusion.
- Janito optimizes for clean, context-free code generation, reducing the risk of such artifacts affecting the output.

### 3. Optimized for Human Editing

- The primary goal of Janito's output is to facilitate smooth, human-friendly editing. Users can copy, paste, and apply changes directly, just as they would with code snippets from trusted documentation.
- This approach streamlines the workflow for developers who want to quickly update their codebase without extra processing or translation steps.

### 4. Review Remains Easy with Standard Tools

- While Janito does not output diffs directly, users can still perform thorough code reviews using standard version control tools (like `git diff`) after applying the changes.
- This separation of concerns ensures that code generation and review are both optimized for their respective contexts: natural output for editing, and diff-based tools for review.

## Summary

Janito's natural, line-based output format is designed to:

- Maximize clarity and usability for developers.
- Avoid introducing out-of-context patterns that could degrade code quality.
- Support efficient, human-friendly editing flows.
- Allow for robust reviews using existing diff tools after changes are applied.

This philosophy ensures that Janito remains a seamless, developer-centric assistant—helping you write, edit, and improve code in the most natural way possible.
