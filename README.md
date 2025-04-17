# Tool Creation Tool (`tool_creation_tool`)

**Version:** 0.1.0

[![License: AGPL-3.0](https://img.shields.io/github/license/neuroidss/tool_creation_tool
)](https://opensource.org/licenses/agpl-v3)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A Python library empowering Large Language Models (LLMs) to dynamically create, use, store, repair, and improve their own tools (Python functions) during runtime. This moves beyond static, predefined toolsets towards adaptable, self-evolving AI agents.

## Motivation

Traditional LLM tool usage relies on a fixed set of functions provided by the developer. This limits the LLM's ability to handle novel tasks or recover from tool errors autonomously. `tool_creation_tool` addresses this by allowing the LLM itself to:

1.  **Create:** Generate new Python functions on-the-fly based on task descriptions.
2.  **Store & Retrieve:** Persistently store tools in a vector database (ChromaDB) for efficient retrieval based on semantic similarity.
3.  **Execute:** Safely execute the generated tools.
4.  **Repair:** Analyze execution errors (like exceptions) and attempt to fix the tool's code using the LLM.
5.  **Improve:** Modify existing tools based on new requirements or improvement suggestions.
6.  **(Experimental) Self-Repair:** The library includes conceptual methods for the LLM to attempt repairs on the library's *own* code, paving the way for truly self-maintaining systems.

## Features

*   **Dynamic Tool Creation:** LLM generates Python function code based on natural language requests.
*   **Persistent Storage:** Uses ChromaDB to store tool code, descriptions, parameters, versioning, and error logs.
*   **Semantic Search:** Find relevant tools using natural language descriptions via ChromaDB embeddings.
*   **Safe Execution:** Executes tool code in a controlled manner, capturing output and errors.
*   **Automated Repair:** Attempts to fix tools that throw exceptions during execution by feeding the error back to the LLM.
*   **Tool Improvement:** LLM can refactor or enhance existing tools based on requests.
*   **OpenAI API Compatibility:** Works with Ollama, vLLM, and other endpoints supporting the OpenAI chat completions API format.
*   **Self-Repair Capability (Conceptual):** Includes methods demonstrating how the library could potentially repair its own components (requires extreme caution).
*   **Extensible:** Designed with clear interfaces for LLM interaction and storage.

## Installation

1.  **Prerequisites:**
    *   Python 3.8+
    *   `pip` and `setuptools`

2.  **Clone the repository (if not installing from PyPI):**
```bash
    git clone https://github.com/neuroidss/tool_creation_tool.git # Replace with your repo URL
    cd tool_creation_tool
```

3.  **Install the library and dependencies:**
```bash
    pip install .
    # Or, for development (editable install):
    # pip install -e .
```

4.  **Install ChromaDB dependencies (if needed):**
    ChromaDB might require specific system dependencies depending on your OS (like a C++ compiler). Follow instructions on the [official ChromaDB website](https://docs.trychroma.com/getting-started). A common extra needed for full features is `hnswlib`:
    ```bash
    # pip install hnswlib # Uncomment if needed and installation fails
    ```

## Configuration

The library uses environment variables for configuration. Create a `.env` file in your project root or set the variables directly:

```dotenv
# .env file example

# --- Required ---
# Choose your LLM provider: "ollama", "vllm", "generic_openai"
LLM_PROVIDER="ollama"

# --- Provider Specific ---

# If LLM_PROVIDER="ollama"
OLLAMA_API_KEY="None" # Ollama usually doesn't need a key, use "None" or omit
OLLAMA_BASE_URL="http://localhost:11434" # Default Ollama address
OLLAMA_MODEL="qwen2.5-coder:7b-instruct-q8_0" # Specify your desired Ollama model

# If LLM_PROVIDER="vllm"
VLLM_API_KEY="None" # vLLM often doesn't need a key
VLLM_BASE_URL="http://localhost:8000" # REQUIRED: Set your vLLM server endpoint
VLLM_MODEL="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF" # Specify model served by vLLM

# If LLM_PROVIDER="generic_openai" (for other OpenAI-compatible APIs)
GENERIC_OPENAI_API_KEY="your_api_key_or_none" # API key if required by the service
GENERIC_OPENAI_BASE_URL="https://your-api-endpoint.com/v1" # REQUIRED: Endpoint URL
GENERIC_OPENAI_MODEL="model-name-served" # Model name expected by the endpoint

# --- Optional ---
# Path for ChromaDB persistent storage
CHROMA_PATH="./my_llm_tools_db" # Defaults to ./chroma_db
```

## Markdown

Important: Ensure the specified models are available and compatible with the chosen provider and endpoint (especially regarding JSON mode support for structured responses).

## Usage

```python
import os
from tool_creation_tool import ToolManager, LLMInterface, ToolStorage
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 1. Initialize components
# Provider/model details are loaded from environment variables by default
try:
    llm_interface = LLMInterface() # Reads config from .env
    storage = ToolStorage() # Reads CHROMA_PATH from .env or uses default
    tool_manager = ToolManager(llm_interface, storage)
except Exception as e:
    print(f"Initialization Error: {e}")
    exit()

# 2. Define a task
task_description = "Create a tool that takes a list of numbers and returns the average."
task_args = [[1, 2, 3, 4, 5]]

# 3. Use an existing tool or create & execute a new one
# This is the primary high-level function
result, stdout, stderr = tool_manager.use_tool_or_create(
    task_description=task_description,
    args=task_args,
    similarity_threshold=0.3, # How similar must an existing tool be? (Lower = stricter)
    attempt_repair=True      # Try to fix the tool if it fails?
)

if stderr:
    print(f"\nTask Failed!")
    print(f"Error:\n{stderr}")
else:
    print(f"\nTask Succeeded!")
    print(f"Result: {result}") # Expected: 3.0
    if stdout:
        print(f"Captured Stdout:\n{stdout}")

# --- Other Operations ---

# Explicitly create a tool (if needed)
# new_tool = tool_manager.create_tool("Generate a random password with specified length")

# Execute a known tool
# result, stdout, stderr = tool_manager.execute_tool("calculate_average", args=[[10, 20]])

# Attempt to repair a specific tool after an error
# repair_successful = tool_manager.repair_tool("faulty_tool_name", "Error message here")

# Attempt to improve a tool
# improved_tool = tool_manager.improve_tool("simple_adder", "Make it handle floats too")
```

## Python

See the examples/ directory for more detailed use cases:
*   **example_create_execute.py**: Demonstrates basic creation and execution.
*   **example_repair_tool.py**: Shows automatic repair triggering when a tool fails.
*   **example_improve_tool.py**: Illustrates modifying an existing tool based on a request.
*   **example_self_repair.py**: Conceptual demo of library self-repair (prints proposed code, does not apply it).

## Unique Competitive Advantage & Examples

Unlike libraries with static tool definitions (e.g., LangChain Tools, standard function calling), tool_creation_tool enables agents that can adapt and evolve their capabilities at runtime. Scenarios impossible without this library:
*   **Handling Truly Novel Tasks**: An agent encounters a request requiring a utility it's never seen (e.g., "Convert this Markdown table to a CSV string"). Instead of failing, it creates the markdown_to_csv tool and uses it.
*   **Autonomous Bug Fixing**: An agent uses a tool (e.g., fetch_weather_data) which suddenly fails due to an API change or an unhandled edge case (e.g., unexpected null value). The ToolManager catches the exception, feeds the code and error back to the LLM via attempt_tool_repair, gets a patched version, stores it, and retries the operation, potentially succeeding without human intervention.
*   **User-Driven Capability Enhancement**: A user tells an agent, "Your 'summarize_text' tool is good, but I need it to focus specifically on extracting action items." The agent uses improve_tool, modifies the underlying function's prompt or logic, and the tool's behavior changes for future use, without developer intervention.
*   **Adapting to Degraded Environments**: If a primary tool fails (e.g., a high-quality translation API goes offline), the agent could potentially create a new tool using a fallback library or a less accurate method to maintain partial functionality.

## Unique Future Project Ideas

This library serves as a foundation for advanced AI systems. Here are ideas uniquely enabled by dynamic tool creation and repair:
*   **Self-Healing Autonomous Agents**: Agents performing long-running, complex tasks (e.g., market analysis, scientific research) that can diagnose tool failures, attempt repairs, validate fixes, and continue their mission with increased robustness.
*   **Personalized Software Generators**: An LLM acts as a "personal programmer," iteratively building a suite of bespoke tools based entirely on conversations with a non-technical user about their workflow needs. The tools evolve as the user's needs change.
*   **Evolving Domain-Specific Toolkits**: An agent specialized in a field (e.g., bioinformatics) starts with basic tools. As it processes new research papers or datasets, it identifies gaps in its capabilities and proposes and creates new, highly specialized tools (e.g., a function to parse a specific gene database format it just encountered).
*   **Cross-Tool Optimization & Refactoring**: An LLM monitors the usage patterns, performance, and errors across multiple generated tools. It could then propose and implement refactorings – combining redundant tools, improving shared helper functions, or optimizing frequently used but inefficient tools as a system.
*   **Automated Library/SDK Client Generation**: Kickstart the development of a new Python library or an API client by providing the LLM with an API specification (e.g., OpenAPI/Swagger). The LLM uses tool_creation_tool to generate, test, and refine individual functions corresponding to API endpoints.
*   **Runtime Security Patching (Theoretical / High-Risk)**: In controlled environments, an LLM could potentially identify a security flaw in a generated tool (e.g., an injection vulnerability) based on external analysis or examples, and attempt to generate and apply a security patch dynamically. Requires extreme caution and validation.
*   **Competitive Self-Improving Systems**: Imagine two agents built with this library competing on a task. They could analyze each other's (or their own past) failures and successes to dynamically improve their own toolsets faster than their competitor.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs, feature requests, or improvements. Ensure code follows general Python best practices and includes docstrings. Adding examples for new features is highly encouraged.

## License

This project is licensed under the AGPL-3.0 License - see the LICENSE file for details.

## vibe coding prompt

```
turn tool_creation_tool https://github.com/neuroidss/create_function_chat/blob/main/create_tool_chat.py which previously named create_function https://github.com/neuroidss/create_function_chat into separate liblary. so all tools created and used by llm will be with ability to repair and improve by llm. use chromadb for tools storage. make llm calls compatible with openai api like for ollama, vllm for llm calls

provide examples which would not be possible without such library, to show unique competitive advantage of tool_creation_tool library, make sh block of how to install this library and run your examples
```
