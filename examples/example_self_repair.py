# examples/example_self_repair.py
# WARNING: This demonstrates the *concept* of self-repair.
# Actually applying the changes requires extreme caution and is disabled by default.
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tool_creation_tool import ToolManager, LLMInterface, ToolStorage

# --- Configuration ---
from dotenv import load_dotenv
load_dotenv()
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
# Use a highly capable model for code modification
# Adjust LLM_INTERFACE_MODEL in .env if needed

# --- Initialization ---
try:
    # Use a more capable model if possible for self-repair tasks
    llm_interface = LLMInterface(provider=LLM_PROVIDER) # Model from .env
    storage = ToolStorage() # Not directly used for self-repair, but needed for ToolManager
    tool_manager = ToolManager(llm_interface, storage)
except Exception as e:
    print(f"Error during initialization: {e}")
    sys.exit(1)

# --- Use Case: Attempting self-repair on a library component ---

# Choose a component to "repair"
component_to_repair = "utils" # e.g., repair the utils.py file
issue_description = """
There's a potential minor inefficiency in the `safe_execute_tool` function in `utils.py`.
The `stdout_capture` and `stderr_capture` StringIO objects are created outside the try block.
It might be slightly cleaner or more idiomatic to create them inside the `try` block
or ensure they are always closed, even if `exec` fails early.
Refactor the function slightly to ensure resources are handled cleanly, perhaps using 'with' statements more extensively if applicable, without changing the core logic or return signature.
Also, add a small comment explaining the purpose of the local_scope dictionary.
"""

print(f"\n--- Attempting Self-Repair on component: '{component_to_repair}.py' ---")
print(f"Issue: {issue_description}")

# Call the conceptual self-repair method
# This will retrieve the code, prompt the LLM, and print the proposed new code.
# It will NOT automatically overwrite the file.
success = tool_manager.attempt_library_self_repair(component_to_repair, issue_description)

if success:
    print("\nSelf-repair suggestion was generated successfully.")
    print("Review the proposed code changes above.")
    print("Apply manually ONLY IF the changes are verified and understood.")
    print("WARNING: Automatically applying self-repair changes is HIGHLY RISKY.")
else:
    print("\nSelf-repair attempt failed. Check logs for errors.")

print("\n--- Conceptual Self-Repair Example Finished ---")

