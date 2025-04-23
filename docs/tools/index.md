# Tools Documentation

Tools provide a structured way to influence the model's behavior, enabling workflows that follow typical engineering patterns. By exposing explicit operations—such as file manipulation, code execution, or data retrieval—tools allow users to guide the assistant’s actions in a predictable and auditable manner.

## User-Level Control

Tools add a layer of user-level control over both the context and the actions performed by the model. This means users can:
- Directly specify which operations are available to the model.
- Constrain or extend the assistant’s capabilities to match project or organizational requirements.
- Observe and audit the assistant’s workflow, increasing transparency and trust.

## Limitations

While tools provide an extra level of control, the invocation of tools and their parameters are still delegated to the model’s inference process. This means:
- The model decides when and how to use tools, and may still make mistakes or select incorrect parameters.
- Tools do not prevent errors, but they do provide a framework for catching, constraining, or correcting them.

Tools are a key mechanism for aligning AI assistants with engineering best practices, offering both flexibility and oversight.

## Tools vs. Web Chat Agents

For a detailed comparison of how tool-based AI assistants like Janito differ from typical web chat agents, see [Janito vs Web Chat Agents](../about/vs_webchats.md). This page explains the interface, control, and transparency advantages of using tools for structured, auditable workflows.

_This section is under development._
