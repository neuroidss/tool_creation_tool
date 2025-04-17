#!/bin/bash

# Ensure Python 3.8+ and pip are installed

# 1. Clone the repository (replace with your actual URL if different)
echo "Cloning repository..."
git clone https://github.com/neuroidss/tool_creation_tool.git
cd tool_creation_tool

# 2. Create a virtual environment (recommended)
echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate # On Windows use `.\venv\Scripts\activate`

# 3. Install the library and dependencies
echo "Installing library and dependencies..."
pip install --upgrade pip
pip install -e . # Install in editable mode for development

# 4. Prepare environment variables
echo "Setting up environment variables (using .env file)..."
echo "Please create a '.env' file in the 'tool_creation_tool' directory"
echo "with your LLM provider details (API keys, endpoints, models)."
echo "Example .env content:"
echo '
# --- Example .env ---
LLM_PROVIDER="ollama" # Or "openai", "vllm", etc.

# Ollama Example (if Ollama running locally)
OLLAMA_API_KEY="None"
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="qwen2.5-coder:7b-instruct-q8_0" # Replace with your model

# vLLM Example (replace with your endpoint and model)
# VLLM_API_KEY="None"
# VLLM_BASE_URL="http://localhost:8000" # Your vLLM server
# VLLM_MODEL="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF"

# Path for ChromaDB storage (optional)
# CHROMA_PATH="./my_tool_db"
' > .env_example
echo "Please copy/rename .env_example to .env and fill in your actual details."
read -p "Press Enter after you have created and configured your .env file..."

# 5. Run the example scripts
echo "Running example: Create and Execute..."
python examples/example_create_execute.py

echo -e "\n---------------------------------------------\n"
echo "Running example: Repair Tool..."
python examples/example_repair_tool.py

echo -e "\n---------------------------------------------\n"
echo "Running example: Improve Tool..."
python examples/example_improve_tool.py

echo -e "\n---------------------------------------------\n"
echo "Running example: Self-Repair (Conceptual)..."
# Note: This example only prints the proposed code, it doesn't modify files.
python examples/example_self_repair.py

echo -e "\n---------------------------------------------\n"
echo "Examples finished."
echo "To deactivate the virtual environment, run: deactivate"

