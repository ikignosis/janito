"""
Output formatting and display for Janito CLI.
"""
from rich.console import Console
from janito.config import get_config

console = Console()

def display_generation_params(
    temp_to_use: float, 
    profile_data: dict = None,
    temperature: float = 0.0
) -> None:
    """
    Display generation parameters in verbose mode.
    
    Args:
        temp_to_use: The temperature value being used
        profile_data: The profile data if a profile is being used
        temperature: The temperature value from command line
    """
    # Show profile information if one is active
    config = get_config()
    if config.profile:
        if not profile_data:
            profile_data = config.get_available_profiles()[config.profile]
        console.print(f"[dim]👤 Using profile: {config.profile} - {profile_data['description']}[/dim]")
    
    # Temperature, top_k, and top_p information is hidden