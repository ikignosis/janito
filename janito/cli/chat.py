"""
CLI chat execution modes: interactive and single prompt.
"""

import os

from ..system_prompt import SYSTEM_PROMPT, GMAIL_SYSTEM_PROMPT, ONEDRIVE_SYSTEM_PROMPT, get_system_prompt_with_skills
from ..openai_client import send_prompt
from ..shell import InteractiveShell


def run_interactive_chat(args):
    """Run the interactive chat session.
    
    Args:
        args: Parsed command line arguments
    """
    # Set up Gmail mode if requested
    if args.gmail:
        from ..tooling.tools_registry import add_toolset
        add_toolset("gmail")
        print("✓ Gmail tools enabled")
    
    # Set up OneDrive mode if requested
    if args.onedrive:
        from ..tooling.tools_registry import add_toolset
        add_toolset("onedrive")
        print("✓ OneDrive tools enabled")
    
    # Check if any skills are installed
    from ..tooling.skills_provider import get_skills_provider
    skills = get_skills_provider().list_skills()
    if skills:
        print(f"✓ {len(skills)} skill(s) available")
    
    model = os.getenv("OPENAI_MODEL")
    print("Starting interactive chat session. Type '/exit' or CTRL-D to end the session")
    
    # Choose system prompt based on enabled modes
    if args.no_system_prompt:
        effective_system_prompt = None
    elif args.onedrive:
        effective_system_prompt = ONEDRIVE_SYSTEM_PROMPT
    elif args.gmail:
        effective_system_prompt = GMAIL_SYSTEM_PROMPT
    else:
        # Use system prompt with skills advertisement
        effective_system_prompt = get_system_prompt_with_skills()
    
    shell = InteractiveShell(model=model, no_history=args.no_history)
    shell.initialize_history(system_prompt=effective_system_prompt)
    shell.run(
        send_prompt_func=send_prompt,
        verbose=args.verbose,
        no_tools=args.no_system_prompt
    )


def run_single_prompt(args):
    """Run a single prompt.
    
    Args:
        args: Parsed command line arguments
    """
    import sys
    
    # Set up Gmail mode if requested
    if args.gmail:
        from ..tooling.tools_registry import add_toolset
        add_toolset("gmail")
        print("✓ Gmail tools enabled")
    
    # Set up OneDrive mode if requested
    if args.onedrive:
        from ..tooling.tools_registry import add_toolset
        add_toolset("onedrive")
        print("✓ OneDrive tools enabled")
    
    prompt = args.prompt
    
    if not prompt:
        print("Error: Empty prompt provided.", file=sys.stderr)
        sys.exit(1)
    
    # Initialize messages history (with or without system prompt based on -Z flag)
    if args.no_system_prompt:
        messages_history = []
        tools_to_use = []
    else:
        # Choose system prompt based on enabled modes
        if args.onedrive:
            effective_system_prompt = ONEDRIVE_SYSTEM_PROMPT
        elif args.gmail:
            effective_system_prompt = GMAIL_SYSTEM_PROMPT
        else:
            # Use system prompt with skills advertisement
            effective_system_prompt = get_system_prompt_with_skills()
        messages_history = [{"role": "system", "content": effective_system_prompt}]
        tools_to_use = None

    try:
        send_prompt(prompt, verbose=args.verbose, previous_messages=messages_history, tools=tools_to_use)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)
