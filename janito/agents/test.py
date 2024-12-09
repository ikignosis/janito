import unittest
import os
from unittest.mock import patch, MagicMock
from .openai import OpenAIAgent
from .claudeai import AIAgent

class TestAIAgents(unittest.TestCase):
    def setUp(self):
        self.system_prompt = "You are a helpful assistant."
        self.test_message = "Hello, how are you?"
        
    def test_openai_agent_initialization(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'}):
            agent = OpenAIAgent(system_prompt=self.system_prompt)

    def test_claudeai_agent_initialization(self):
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test_key'}):
            agent = AIAgent(system_prompt=self.system_prompt)

    def test_openai_agent_send_message(self):
        with patch('openai.OpenAI.chat.completions.create') as mock_create:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "I'm good, thank you!"
            mock_create.return_value = mock_response
            response = self.openai_agent.send_message(self.test_message)
            self.assertEqual(response, "I'm good, thank you!")

    def test_claudeai_agent_send_message(self):
        with patch('anthropic.Client.messages.create') as mock_create:
            mock_response = MagicMock()
            mock_response.content[0].text = "I'm Claude, how can I assist you?"
            mock_create.return_value = mock_response
            response = self.claudeai_agent.send_message(self.test_message)
            self.assertEqual(response, "I'm Claude, how can I assist you?")