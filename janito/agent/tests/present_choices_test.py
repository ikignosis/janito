"""
Test for present_choices tool.

Note: This test is for manual/interactive verification only, as prompt_toolkit dialogs require user interaction.
"""

from .present_choices import present_choices

if __name__ == "__main__":
    prompt = "Select your favorite fruits:"
    choices = ["Apple", "Banana", "Cherry", "Date"]
    print("Single-select test:")
    selected = present_choices(prompt, choices, multi_select=False)
    print(f"Selected: {selected}")

    print("\nMulti-select test:")
    selected_multi = present_choices(prompt, choices, multi_select=True)
    print(f"Selected: {selected_multi}")
