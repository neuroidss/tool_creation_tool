# tool_creation_tool/llm_interface.py

import os
import requests
import json
from openai import OpenAI, OpenAIError
from typing import List, Dict, Optional, Literal

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

LLMProvider = Literal["openai", "ollama", "vllm", "generic_openai"]

class LLMInterface:
    """
    Provides a unified interface to interact with different LLM providers
    supporting the OpenAI API format.
    """
    def __init__(
        self,
        provider: LLMProvider = "openai",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.provider = provider or os.getenv("LLM_PROVIDER", "openai")
        self.api_key = api_key or os.getenv(f"{self.provider.upper()}_API_KEY")
        self.base_url = base_url or os.getenv(f"{self.provider.upper()}_BASE_URL")
        self.model = model or os.getenv(f"{self.provider.upper()}_MODEL")

        if not self.model:
            # Provide default models if not specified
            if self.provider == "openai":
                self.model = "gpt-4-turbo-preview"
            elif self.provider == "ollama":
                self.model = "llama3" # Common default, adjust as needed
            elif self.provider == "vllm":
                self.model = "meta-llama/Llama-2-7b-chat-hf" # Example, adjust
            else: # generic_openai
                 self.model = os.getenv("GENERIC_OPENAI_MODEL", "default-model")


        if self.provider in ["openai", "vllm", "generic_openai"] and not self.base_url:
             if self.provider == "openai":
                 self.base_url = "https://api.openai.com/v1"
             elif self.provider == "vllm":
                  # vLLM typically runs locally, requires user-set base URL
                  raise ValueError("VLLM_BASE_URL must be set in environment or passed for vLLM provider")
             # For generic_openai, base_url is expected

        if self.provider == "ollama" and not self.base_url:
            self.base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434") # Common Ollama default

        self.client = None
        if self.provider in ["openai", "vllm", "generic_openai"]:
            # Use OpenAI client for compatible APIs
             # For OpenAI, key is required. For others, it might be optional ("None", "no_key", etc.)
            effective_api_key = self.api_key if self.api_key else "None"
            if self.provider == "openai" and effective_api_key == "None":
                 raise ValueError("OPENAI_API_KEY must be set for OpenAI provider")

            self.client = OpenAI(
                api_key=effective_api_key,
                base_url=self.base_url
            )

    def get_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1500,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> Optional[str]:
        """
        Gets a completion from the configured LLM provider.

        Args:
            messages: A list of message dictionaries (e.g., [{"role": "user", "content": "..."}]).
            max_tokens: Maximum number of tokens to generate.
            temperature: Sampling temperature.
            json_mode: Whether to request JSON output (if supported by the model/API).

        Returns:
            The LLM's response content as a string, or None if an error occurs.
        """
        try:
            if self.provider == "ollama":
                return self._get_ollama_completion(messages, max_tokens, temperature, json_mode)
            elif self.client: # OpenAI, vLLM, generic_openai
                return self._get_openai_compatible_completion(messages, max_tokens, temperature, json_mode)
            else:
                print(f"Error: Provider '{self.provider}' not properly configured.")
                return None
        except OpenAIError as e:
            print(f"OpenAI API Error: {e}")
            return None
        except requests.RequestException as e:
            print(f"Ollama Request Error: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during LLM call: {e}")
            return None

    def _get_openai_compatible_completion(
        self, messages: List[Dict[str, str]], max_tokens: int, temperature: float, json_mode: bool
    ) -> Optional[str]:
        """Handles OpenAI and compatible API calls."""
        completion_kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        # Check if json_mode is supported and requested
        # Note: Actual support depends on the specific model and API version
        if json_mode:
             try:
                 completion_kwargs["response_format"] = {"type": "json_object"}
             except Exception:
                 print("Warning: JSON mode might not be supported by this model/endpoint.")

        completion = self.client.chat.completions.create(**completion_kwargs)
        return completion.choices[0].message.content

    def _get_ollama_completion(
        self, messages: List[Dict[str, str]], max_tokens: int, temperature: float, json_mode: bool
    ) -> Optional[str]:
        """Handles Ollama API calls."""
        headers = {'Content-Type': 'application/json'}
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens, # Ollama uses num_predict for max_tokens
            }
        }
        if json_mode:
            payload["format"] = "json"

        api_url = f"{self.base_url}/api/chat" # Standard Ollama chat endpoint
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        response_data = response.json()
        content = response_data.get("message", {}).get("content")
        # Ollama sometimes returns JSON as a string within the content if format=json
        if json_mode and isinstance(content, str):
             try:
                 # Attempt to parse, but return raw if it fails
                 json.loads(content)
                 return content # Return the string representation of JSON
             except json.JSONDecodeError:
                 print("Warning: Ollama response content is not valid JSON despite requesting JSON format.")
                 return content # Return raw string anyway
        return content
