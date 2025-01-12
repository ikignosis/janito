from .workspace import workset

SYSTEM_PROMPT = """I am Janito, your friendly software development buddy.
I help you with coding tasks while being clear and concise in my responses.

I have received the following workset for analysis:

{workset}

"""

def build_system_prompt() -> dict:

    system_prompt = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
        }
    ]

    blocks = workset.get_cache_blocks()
    for block in blocks:
        if not block:
            continue
        block_content = ""
        for file in block:
            block_content += f'<file name="{file.name}"\n"'
            block_content += f'<content>\n"{file.content}"\n</content>\n</file>\n'
        system_prompt.append( {
            "type": "text",
            "text": block_content,
            "cache_control": {"type": "ephemeral"}
            }
        )
    return system_prompt