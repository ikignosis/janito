#!/usr/bin/env python3
"""
ASCII Art Penguin Generator
"""

def show_penguin():
    """Display a cute ASCII art penguin"""
    penguin = r"""
    .-.
   (o o)
   |O|
  /   \
 ( === )
  ^^^^^
    """
    print(penguin)

def show_detailed_penguin():
    """Display a more detailed ASCII art penguin"""
    penguin = r"""
         .-.
        (o o)
        |O|
       /   \
      ( === )
       ^^^^^
    .-"-"-"-"-.
   /  \     /  \
  |    |   |    |
   \  /     \  /
    `-`-----`-`
    """
    print(penguin)

def show_cute_penguin():
    """Display a cute cartoon-style penguin"""
    penguin = r"""
       __
      /  \
     /    \
    |  o  o|
    |   <  |
    |  ___ |
    \_____/
   /     \
  /       \
 |         |
  \_______/
   |     |
   |     |
   |_____|
  /       \
 /         \
|___________|
    """
    print(penguin)

if __name__ == "__main__":
    print("🐧 Here are some ASCII art penguins for you! 🐧\n")
    
    print("Simple Penguin:")
    show_penguin()
    print("\n" + "="*50 + "\n")
    
    print("Detailed Penguin:")
    show_detailed_penguin()
    print("\n" + "="*50 + "\n")
    
    print("Cute Cartoon Penguin:")
    show_cute_penguin()
    print("\n" + "="*50 + "\n")
    
    print("Hope you enjoyed these penguins! 🐧")