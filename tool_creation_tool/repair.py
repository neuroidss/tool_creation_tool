# tool_creation_tool/repair.py

from .llm_interface import LLMInterface
from .storage import ToolStorage
from .utils import validate_python_code, parse_llm_tool_creation_response
from typing import Optional, Dict, Any
import json

def generate_repair_prompt(tool_data: Dict[str, Any], error_message: str) -> str:
    """Generates a prompt for the LLM to repair a tool based on an error."""
    prompt = f"""
Objective: Repair the following Python tool function based on the provided error message.

Tool Name: {tool_data.get('tool_name', 'Unknown')}
Current Version: {tool_data.get('version', 1)}
Description: {tool_data.get('description', 'No description provided.')}
Parameters: {json.dumps(tool_data.get('parameters', {}), indent=2)}
Current Code:
{tool_data.get('code', '# No code provided')}
Error Encountered:
{error_message}
Task:
Analyze the error message and the current code.
Identify the cause of the error.
Modify the Python code to fix the error and prevent it from happening again under similar circumstances.
Ensure the function signature (name and parameters) remains compatible if possible, unless the error necessitates a change.
Respond ONLY with a JSON object containing the corrected tool information. The JSON object should have the following keys:
"tool_name": (string) The original tool name.
"code": (string) The complete, corrected Python code for the function.
"description": (string) The original or slightly updated description if the fix changes behavior significantly.
"parameters": (dict) The original or updated parameter schema.
"fix_explanation": (string) A brief explanation of the fix applied.

Example JSON Response Format:
{{
  "tool_name": "{tool_data.get('tool_name', 'example_tool')}",
  "code": "def {tool_data.get('tool_name', 'example_tool')}(param1, param2=None):\\n    # Corrected code here\\n    # ...\\n    return result",
  "description": "Description of the tool (potentially updated).",
  "parameters": {{ "param1": {{"type": "string"}}, "param2": {{"type": "integer", "optional": true}} }},
  "fix_explanation": "Added a check for None before accessing attribute X."
}}

Provide ONLY the JSON object in your response.
"""
    return prompt.strip()
def generate_improvement_prompt(tool_data: Dict[str, Any], improvement_request: str) -> str:
    """Generates a prompt for the LLM to improve or modify a tool."""
    prompt = f"""
Objective: Improve or modify the following Python tool function based on the user's request.
Tool Name: {tool_data.get('tool_name', 'Unknown')}
Current Version: {tool_data.get('version', 1)}
Description: {tool_data.get('description', 'No description provided.')}
Parameters: {json.dumps(tool_data.get('parameters', {}), indent=2)}
Current Code:
{tool_data.get('code', '# No code provided')}
User's Improvement Request:
{improvement_request}
Task:
Understand the user's request and how it applies to the existing tool.
Modify the Python code to implement the requested improvement or modification.
Update the function signature (parameters) if necessary to accommodate the changes.
Update the description and parameter schema to accurately reflect the new functionality.
Respond ONLY with a JSON object containing the improved tool information. The JSON object should have the following keys:
"tool_name": (string) The original or potentially adjusted tool name if the change is significant.
"code": (string) The complete, improved Python code for the function.
"description": (string) The updated description reflecting the improvements.
"parameters": (dict) The updated parameter schema.
"improvement_summary": (string) A brief summary of the changes made.

Example JSON Response Format:
{{
  "tool_name": "{tool_data.get('tool_name', 'example_tool')}",
  "code": "def {tool_data.get('tool_name', 'example_tool')}(param1, new_param='default'):\\n    # Improved code here\\n    # ...\\n    return result",
  "description": "Updated description reflecting the new feature.",
  "parameters": {{ "param1": {{"type": "string"}}, "new_param": {{"type": "string", "optional": true}} }},
  "improvement_summary": "Added an optional parameter 'new_param' and corresponding logic."
}}

Provide ONLY the JSON object in your response.
"""
    return prompt.strip()
def attempt_tool_repair(
    llm_interface: LLMInterface,
    storage: ToolStorage,
    tool_name: str,
    error_message: str
    ) -> Optional[Dict[str, Any]]:
    """
Attempts to repair a tool using the LLM.
Args:
    llm_interface: The LLM interface instance.
    storage: The ToolStorage instance.
    tool_name: The name of the tool to repair.
    error_message: The error message encountered.

Returns:
    A dictionary with the details of the repaired tool (including new code, version, etc.)
    if successful and validated, otherwise None.
"""
    print(f"Attempting to repair tool: {tool_name}")
    original_tool = storage.get_tool(tool_name)
    if not original_tool:
        print(f"Error: Tool '{tool_name}' not found for repair.")
        return None

    prompt = generate_repair_prompt(original_tool, error_message)
    messages = [{"role": "user", "content": prompt}]

    # Request JSON mode if possible
    llm_response = llm_interface.get_completion(messages, json_mode=True)

    if not llm_response:
        print("Error: Failed to get repair suggestion from LLM.")
        return None

    parsed_response = parse_llm_tool_creation_response(llm_response) # Use the same parser

    if not parsed_response or "code" not in parsed_response:
        print("Error: Failed to parse LLM repair response or missing 'code'.")
        print(f"LLM raw response snippet: {llm_response[:200]}...")
        return None

    repaired_code = parsed_response["code"]
    if not validate_python_code(repaired_code):
        print("Error: LLM generated repaired code with invalid syntax.")
        # Optionally: Could try to ask the LLM to fix the syntax error here
        return None

    # Prepare the updated tool data for storage
    updated_tool_data = {
        "tool_name": original_tool["tool_name"], # Keep original name
        "code": repaired_code,
        "description": parsed_response.get("description", original_tool["description"]),
        "parameters": parsed_response.get("parameters", original_tool["parameters"]),
        "version": original_tool.get("version", 1) + 1, # Increment version
        "error_log": [], # Clear error log after successful repair attempt
        "fix_explanation": parsed_response.get("fix_explanation", "No explanation provided.")
    }

    # Store the updated tool
    storage.add_or_update_tool(
        tool_name=updated_tool_data["tool_name"],
        code=updated_tool_data["code"],
        description=updated_tool_data["description"],
        parameters=updated_tool_data["parameters"],
        version=updated_tool_data["version"],
        error_log=updated_tool_data["error_log"]
    )

    print(f"Tool '{tool_name}' successfully repaired and updated to version {updated_tool_data['version']}.")
    print(f"LLM Fix Explanation: {updated_tool_data['fix_explanation']}")
    return updated_tool_data # Return the full data of the repaired tool
def attempt_tool_improvement(
    llm_interface: LLMInterface,
    storage: ToolStorage,
    tool_name: str,
    improvement_request: str
    ) -> Optional[Dict[str, Any]]:
    """
Attempts to improve a tool using the LLM based on a request.
Args:
    llm_interface: The LLM interface instance.
    storage: The ToolStorage instance.
    tool_name: The name of the tool to improve.
    improvement_request: The user's request for improvement.

Returns:
    A dictionary with the details of the improved tool (including new code, version, etc.)
    if successful and validated, otherwise None.
"""
    print(f"Attempting to improve tool: {tool_name}")
    original_tool = storage.get_tool(tool_name)
    if not original_tool:
        print(f"Error: Tool '{tool_name}' not found for improvement.")
        return None

    prompt = generate_improvement_prompt(original_tool, improvement_request)
    messages = [{"role": "user", "content": prompt}]

    # Request JSON mode if possible
    llm_response = llm_interface.get_completion(messages, json_mode=True)

    if not llm_response:
        print("Error: Failed to get improvement suggestion from LLM.")
        return None

    parsed_response = parse_llm_tool_creation_response(llm_response)

    if not parsed_response or "code" not in parsed_response:
        print("Error: Failed to parse LLM improvement response or missing 'code'.")
        print(f"LLM raw response snippet: {llm_response[:200]}...")
        return None

    improved_code = parsed_response["code"]
    if not validate_python_code(improved_code):
        print("Error: LLM generated improved code with invalid syntax.")
        return None

    # Prepare the updated tool data for storage
    updated_tool_data = {
         # Allow LLM to potentially suggest a name change if significant
        "tool_name": parsed_response.get("tool_name", original_tool["tool_name"]),
        "code": improved_code,
        "description": parsed_response.get("description", original_tool["description"]),
        "parameters": parsed_response.get("parameters", original_tool["parameters"]),
        "version": original_tool.get("version", 1) + 1, # Increment version
        "error_log": original_tool.get("error_log", []), # Keep existing error log unless cleared
        "improvement_summary": parsed_response.get("improvement_summary", "No summary provided.")
    }

     # If name changed, potentially delete old entry? Or handle as rename?
     # For now, upsert will overwrite if ID matches, or create new if name (and thus ID) changes.
     # Let's force using the *original* name for the update to avoid proliferation unless explicitly renaming.
    update_name = original_tool["tool_name"]
    if updated_tool_data["tool_name"] != update_name:
        print(f"Warning: LLM suggested renaming tool to '{updated_tool_data['tool_name']}', but sticking to original name '{update_name}' for update.")
        updated_tool_data["tool_name"] = update_name


    # Store the updated tool
    storage.add_or_update_tool(
        tool_name=updated_tool_data["tool_name"],
        code=updated_tool_data["code"],
        description=updated_tool_data["description"],
        parameters=updated_tool_data["parameters"],
        version=updated_tool_data["version"],
        error_log=updated_tool_data["error_log"] # Persist error log
    )

    print(f"Tool '{update_name}' successfully improved and updated to version {updated_tool_data['version']}.")
    print(f"LLM Improvement Summary: {updated_tool_data['improvement_summary']}")
    return updated_tool_data

