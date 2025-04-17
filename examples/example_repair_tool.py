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

# --- Use Case: Create a faulty tool, execute, trigger repair ---

# 1. Define a task for a potentially faulty tool
faulty_task = "Create a Python tool named 'safe_divide' that divides two numbers, but might fail on zero division."

print(f"\n--- Creating potentially faulty tool: {faulty_task} ---")
# We specifically ask for a name here to make it easier to reference later
# Normally create_tool derives the name from the code LLM generates
# Let's try creating it directly for more control in this example.

faulty_code_initial = """
import math # Unused import, just for example

def safe_divide(numerator, denominator):
  \"\"\"Divides numerator by denominator. May fail on zero division.\"\"\"
  # Potential bug: No check for zero denominator
  result = numerator / denominator
  print(f"Division result: {result}") # Example print statement
  return result
"""
faulty_description = "Divides two numbers. Might fail if denominator is zero."
faulty_params = {
    "numerator": {"description": "Number to be divided", "type": "float", "required": True},
    "denominator": {"description": "Number to divide by", "type": "float", "required": True}
}

# Add it directly to storage for this example
storage.add_or_update_tool(
    tool_name="safe_divide",
    code=faulty_code_initial,
    description=faulty_description,
    parameters=faulty_params,
    version=1
)
print("Added 'safe_divide' tool (version 1) to storage.")

# 2. Execute the tool with input that causes failure
print("\n--- Executing 'safe_divide' with input causing ZeroDivisionError ---")
result, stdout, stderr = tool_manager.execute_tool(
    tool_name="safe_divide",
    args=[10, 0], # numerator=10, denominator=0
    attempt_repair=True, # <<<<<< Enable automatic repair
    max_repair_attempts=1
)

# 3. Check the outcome
if stderr and "ZeroDivisionError" in stderr:
    print("\nExecution failed as expected, and repair was attempted.")
    # Check if repair was successful by trying again or checking the stored version
    print("\n--- Checking tool state after repair attempt ---")
    repaired_tool = storage.get_tool("safe_divide")
    if repaired_tool and repaired_tool.get("version", 1) > 1:
        print(f"Tool 'safe_divide' was updated to version {repaired_tool['version']}.")
        print("New code:")
        print(repaired_tool['code'])

        print("\n--- Retrying execution with the potentially repaired tool ---")
        # Execute again, this time repair should ideally not be needed if fixed
        result_retry, stdout_retry, stderr_retry = tool_manager.execute_tool(
            tool_name="safe_divide",
            args=[10, 0],
            attempt_repair=False # Don't repair again immediately
        )

        if not stderr_retry:
            print("\nRetry Execution Succeeded!")
            print(f"Result (should likely be None or specific error value): {result_retry}")
            if stdout_retry: print(f"Captured Stdout:\n{stdout_retry}")
        else:
            print("\nRetry Execution Failed! Repair might have been unsuccessful.")
            print(f"Error:\n{stderr_retry}")

    else:
        print("Repair attempt seems to have failed or did not update the tool.")
        print(f"Final error from first execution:\n{stderr}")

elif not stderr:
     print("\nExecution unexpectedly succeeded (maybe initial code handled the error?).")
     print(f"Result: {result}")

else:
     print("\nExecution failed with an unexpected error.")
     print(f"Error:\n{stderr}")


print("\n--- Example Finished ---")

