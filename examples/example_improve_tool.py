# examples/example_improve_tool.py
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tool_creation_tool import ToolManager, LLMInterface, ToolStorage

# --- Configuration ---
from dotenv import load_dotenv
load_dotenv()
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

# --- Initialization ---
try:
    llm_interface = LLMInterface(provider=LLM_PROVIDER)
    storage = ToolStorage()
    tool_manager = ToolManager(llm_interface, storage)
except Exception as e:
    print(f"Error during initialization: {e}")
    sys.exit(1)

# --- Use Case: Create a simple tool, then ask the LLM to improve it ---

# 1. Create or ensure a simple tool exists
tool_name = "simple_adder"
initial_code = """
def simple_adder(a, b):
  \"\"\"Adds two numbers together.\"\"\"
  return a + b
"""
initial_description = "Adds two numbers a and b."
initial_params = {
    "a": {"description": "First number", "type": "number", "required": True},
    "b": {"description": "Second number", "type": "number", "required": True}
}

storage.add_or_update_tool(
    tool_name=tool_name,
    code=initial_code,
    description=initial_description,
    parameters=initial_params,
    version=1
)
print(f"Ensured tool '{tool_name}' (version 1) exists.")

# 2. Define an improvement request
improvement_request = """
Modify the 'simple_adder' tool to also handle subtraction.
Add an optional 'operation' parameter (string).
If operation is 'subtract', perform a - b.
If operation is 'add' or not provided, perform a + b (default behavior).
Update the docstring, description, and parameters accordingly.
"""
print(f"\n--- Requesting improvement for '{tool_name}' ---")
print(f"Request: {improvement_request}")

# 3. Attempt the improvement
improved_tool_data = tool_manager.improve_tool(tool_name, improvement_request)

# 4. Check the result
if improved_tool_data:
    print(f"\nImprovement successful! Tool '{tool_name}' updated to version {improved_tool_data.get('version')}.")
    print("New Description:", improved_tool_data.get("description"))
    print("New Parameters:", improved_tool_data.get("parameters"))
    print("New Code:")
    print(improved_tool_data.get("code"))
    print("Improvement Summary:", improved_tool_data.get("improvement_summary"))

    # 5. Test the improved tool
    print("\n--- Testing the improved tool ---")
    print("Testing addition (default):")
    result_add, _, err_add = tool_manager.execute_tool(tool_name, args=[10, 5], attempt_repair=False)
    if not err_add: print(f"Result: {result_add}")
    else: print(f"Error: {err_add}")

    print("\nTesting subtraction:")
    result_sub, _, err_sub = tool_manager.execute_tool(tool_name, kwargs={'a': 10, 'b': 5, 'operation': 'subtract'}, attempt_repair=False)
    if not err_sub: print(f"Result: {result_sub}")
    else: print(f"Error: {err_sub}")

    print("\nTesting addition (explicit):")
    result_add_explicit, _, err_add_explicit = tool_manager.execute_tool(tool_name, kwargs={'a': 10, 'b': 5, 'operation': 'add'}, attempt_repair=False)
    if not err_add_explicit: print(f"Result: {result_add_explicit}")
    else: print(f"Error: {err_add_explicit}")

else:
    print("\nImprovement attempt failed.")
    # Check logs or LLM response for reasons why

print("\n--- Example Finished ---")

