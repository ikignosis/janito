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
    
    if temperature != 0.0:
        console.print(f"[dim]🌡️ Using temperature: {temp_to_use} (from command line)[/dim]")
    else:
        console.print(f"[dim]🌡️ Using temperature: {temp_to_use} (from configuration){' (via profile)' if config.profile else ''}[/dim]")
        
    # Display top_k and top_p only if they come from a profile
    if profile_data:
        if "top_k" in profile_data and profile_data["top_k"] != 0:
            console.print(f"[dim]🔝 Using top_k: {profile_data['top_k']} (via profile {config.profile})[/dim]")
        if "top_p" in profile_data and profile_data["top_p"] != 0.0:
            console.print(f"[dim]📊 Using top_p: {profile_data['top_p']} (via profile {config.profile})[/dim]")