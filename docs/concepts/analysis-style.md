# Analysis Prompting Style: Declaring Role and Knowledge Domain

## Overview
For effective and reliable AI-driven analysis, prompts should begin by explicitly declaring the intended role and the relevant knowledge domain. This establishes context, sets expectations, and guides the model’s reasoning and language style.

## Why Declare Role and Domain?
- **Role Declaration**: Instructs the model to adopt a specific perspective (e.g., software engineer, security auditor, data scientist).
- **Domain Declaration**: Focuses the model’s attention on the relevant field or subject matter (e.g., Python projects, web security, machine learning).

Explicitly stating both helps:
- Reduce ambiguity
- Improve relevance and accuracy
- Align output with user intent

## Example Structure
```
You are a(n) [role] with expertise in [domain]. Your task is to...
```

### Example Prompts
- You are an expert software project analyst. Your task is to analyze the provided project files and identify the core technologies used in the project.
- You are a security auditor specializing in web applications. Review the configuration files for potential vulnerabilities.
- You are a data scientist with experience in time series analysis. Examine the dataset and summarize key trends.

## Extending with Analysis Actions
After declaring the role and domain, extend the prompt with clear, actionable analysis instructions. 
### Guidance:
- Clearly state the analysis objective (e.g., "identify core technologies", "summarize vulnerabilities", "extract key metrics").
- Specify the expected output format (e.g., bullet points, summary, table).
- Avoid ambiguity—list exactly what should be included or excluded.
- Use the condition-before-action (CBA) structure for any prerequisites or constraints.

## Best Practices
- Always start with a clear role and domain statement.
- Extend with explicit analysis actions and output requirements.
- Use precise, unambiguous language.
- Follow with condition-before-action (CBA) structure for instructions (see [Prompt Design Style](prompt-design-style.md)).
- Avoid vague roles (e.g., "expert"). Specify the field or context when possible.

---
