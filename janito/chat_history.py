"""
Chat history module for Janito.
Handles storing and loading chat history.
"""
import json
import datetime
from pathlib import Path
from typing import List, Dict
from janito.config import get_config

def ensure_chat_history_dir() -> Path:
    """
    Ensure the chat history directory exists.
    
    Returns:
        Path: Path to the chat history directory
    """
    workspace_dir = get_config().workspace_dir
    chat_history_dir = Path(workspace_dir) / ".janito" / "chat_history"
    chat_history_dir.mkdir(parents=True, exist_ok=True)
    return chat_history_dir



def store_conversation(query: str, response: str, agent=None) -> None:
    """
    Store a conversation in the chat history.
    
    Args:
        query: The user's query
        response: The agent's response
        agent: Optional agent instance for using get_messages method
    """
    chat_history_dir = ensure_chat_history_dir()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}.json"
    
    # Create the conversation data
    conversation = {
        "timestamp": timestamp,
        "query": query,
        "response": response
    }
    
    # Write to file
    with open(chat_history_dir / filename, "w", encoding="utf-8") as f:
        json.dump(conversation, f, ensure_ascii=False, indent=2)

def load_recent_conversations(count: int = 5) -> List[Dict[str, str]]:
    """
    Load the most recent conversations from the chat history.
    
    Args:
        count: Number of conversations to load
        
    Returns:
        List[Dict[str, str]]: List of conversations
    """
    chat_history_dir = ensure_chat_history_dir()
    
    # Get all JSON files in the chat history directory
    history_files = list(chat_history_dir.glob("*.json"))
    
    # Sort by filename (which includes timestamp)
    history_files.sort(reverse=True)
    
    # Load the most recent conversations
    conversations = []
    for file_path in history_files[:count]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                conversation = json.load(f)
                conversations.append(conversation)
        except Exception as e:
            print(f"Error loading chat history file {file_path}: {e}")
    
    return conversations

def format_conversation_for_context(conversation: Dict[str, str]) -> str:
    """
    Format a conversation for inclusion in the context.
    
    Args:
        conversation: The conversation to format
        
    Returns:
        str: The formatted conversation
    """
    timestamp = conversation.get("timestamp", "Unknown time")
    query = conversation.get("query", "")
    response = conversation.get("response", "")
    
    formatted_time = datetime.datetime.strptime(timestamp, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    
    return f"--- Conversation from {formatted_time} ---\nUser: {query}\n\nAssistant: {response}\n\n"

def get_chat_history_context(count: int = 5) -> str:
    """
    Get the chat history formatted for inclusion in the agent's context.
    
    Args:
        count: Number of conversations to include
        
    Returns:
        str: The formatted chat history
    """
    conversations = load_recent_conversations(count)
    
    if not conversations:
        return ""
    
    context = "# Previous conversations:\n\n"
    for conversation in conversations:
        context += format_conversation_for_context(conversation)
    
    return context