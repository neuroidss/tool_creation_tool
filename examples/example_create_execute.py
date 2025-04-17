# examples/example_create_execute.py
import os
import sys
# Add the parent directory to sys.path to find the tool_creation_tool package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tool_creation_tool import ToolManager, LLMInterface, ToolStorage

# --- Configuration ---
# Load environment variables (ensure you have .env file or set environment variables)
# Required: LLM_PROVIDER, [PROVIDER]_API_KEY, [PROVIDER]_BASE_URL (if needed), [PROVIDER]_MODEL
# Optional: CHROMA_PATH (defaults to ./chroma_db)
from dotenv import load_dotenv
load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama") # Example: "openai", "ollama", "vllm"
# Add specific API keys/URLs/Models based on the provider in your .env file

# --- Initialization ---
try:
    llm_interface = LLMInterface(provider=LLM_PROVIDER)
    storage = ToolStorage() # Uses CHROMA_PATH from env or defaults
    tool_manager = ToolManager(llm_interface, storage)
except Exception as e:
    print(f"Error during initialization: {e}")
    sys.exit(1)

# --- Use Case: Create and Execute ---

# Task 1: A simple calculation tool
task1 = "Create a Python tool that calculates the nth Fibonacci number iteratively."
args1 = [10] # Calculate the 10th Fibonacci number

print(f"\n--- Running Task 1: {task1} ---")
result1, stdout1, stderr1 = tool_manager.use_tool_or_create(
    task_description=task1,
    args=args1,
    similarity_threshold=0.3 # Be relatively strict for finding existing tool
)

if stderr1:
    print(f"\nTask 1 Execution Failed!")
    print(f"Error:\n{stderr1}")
else:
    print(f"\nTask 1 Execution Succeeded!")
    print(f"Result: {result1}")
    if stdout1:
        print(f"Captured Stdout:\n{stdout1}")

print("\n" + "="*50 + "\n")

# Task 2: A tool requiring an external library (if allowed by LLM/execution)
task2 = "Create a Python tool using the 'requests' library to check if a website URL is reachable by sending a HEAD request."
args2 = []
kwargs2 = {"url": "https://httpbin.org/delay/1"} # Test with a valid URL

print(f"\n--- Running Task 2: {task2} ---")
result2, stdout2, stderr2 = tool_manager.use_tool_or_create(
    task_description=task2,
    args=args2,
    kwargs=kwargs2,
    similarity_threshold=0.3
)

if stderr2:
    print(f"\nTask 2 Execution Failed!")
    print(f"Error:\n{stderr2}")
    # Note: This might fail if 'requests' isn't installed in the execution environment
    # or if the LLM doesn't include the import statement correctly.
else:
    print(f"\nTask 2 Execution Succeeded!")
    print(f"Result (True if reachable, False otherwise): {result2}")
    if stdout2:
        print(f"Captured Stdout:\n{stdout2}")

print("\n--- Example Finished ---")

