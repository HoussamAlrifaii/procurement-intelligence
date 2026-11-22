"""Connection to the LLM.

Uses the OpenAI-compatible chat API, which Groq, Google Gemini and others also
offer, so the provider is chosen in .env without code changes:
    LLM_API_KEY=...                                   (required)
    LLM_BASE_URL=https://api.groq.com/openai/v1       (optional, default Groq)
    LLM_MODEL=openai/gpt-oss-120b                     (optional)
"""
import json
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv
from openai import OpenAI

from procurement import config


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Reply:
    """What the LLM answered: plain text, or one or more tool calls to run first."""
    content: str = ""
    tool_calls: list = field(default_factory=list)


class LLM:
    def __init__(self):
        load_dotenv(config.PROJECT_ROOT / ".env")
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_API_KEY is not set. Copy .env.example to .env and add your key.")
        self.client = OpenAI(api_key=api_key, base_url=os.getenv("LLM_BASE_URL", config.DEFAULT_LLM_BASE_URL))
        self.model = os.getenv("LLM_MODEL", config.DEFAULT_LLM_MODEL)

    def __call__(self, messages, tools):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            temperature=0,   # same question, same answer: easier to evaluate
        )
        message = response.choices[0].message
        tool_calls = [
            ToolCall(call.id, call.function.name, json.loads(call.function.arguments or "{}"))
            for call in message.tool_calls or []
        ]
        return Reply(content=message.content or "", tool_calls=tool_calls)
