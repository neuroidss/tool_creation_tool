# tool_creation_tool/tool_manager.py

from .llm_interface import LLMInterface
from .storage import ToolStorage
from .utils import safe_execute_tool, parse_llm_tool_creation_response, validate_python_code
from .repair import attempt_tool_repair, attempt_tool_improvement
from typing import Optional, List, Dict, Any, Tuple

class ToolManager:
    """
    Manages the lifecycle of LLM-driven tools: creation, retrieval, execution,
    repair, and improvement.
    """
    def __init__(self, llm_interface: LLMInterface, storage: ToolStorage):
        self.llm = llm_interface
        self.storage = storage

    def _generate_creation_prompt(self, task_description: str, similar_tools: Optional[List[Dict]] = None) -> str:
        """Generates a prompt for the LLM to create a new tool."""
        prompt = f"""
Objective: Create a Python tool (a single function) to accomplish the following task.

Task Description:
{task_description}

Requirements:
1.  The tool MUST be implemented as a single Python function.
2.  Include necessary imports within the function code string if they are not standard Python libraries (though prefer standard libraries if possible).
3.  The function should have a descriptive name (snake_case).
4.  Include a clear docstring explaining what the function does, its parameters, and what it returns.
5.  Define the function's parameters clearly. If possible, include type hints.
6.  Respond ONLY with a JSON object containing the tool information. The JSON object must have the following keys:
    - "tool_name": (string) The name of the Python function created.
    - "code": (string) The complete Python code for the function, including imports if necessary and the docstring.
    - "description": (string) A concise natural language description of what the tool does.
    - "parameters": (dict) A dictionary describing the function's parameters. Use a simple format, e.g., {{"param_name": {{"description": "...", "type": "string", "required": true}}}}.

"""
        if similar_tools:
            prompt += "\nFound existing tools that might be relevant (do not reuse directly unless the task is identical):\n"
            for i, tool in enumerate(similar_tools):
                 prompt += f"{i+1}. {tool.get('tool_name')}: {tool.get('description')}\n"
            prompt += "\nConsider if the new tool is genuinely needed or if an existing one could be adapted (outside this creation step).\n"


        prompt += """
Example JSON Response Format:
```json
{
  "tool_name": "calculate_area",
  "code": "import math\\n\\ndef calculate_area(radius):\\n  \"\"\"Calculates the area of a circle.\\n\\n  Args:\\n    radius (float): The radius of the circle.\\n\\n  Returns:\\n    float: The area of the circle.\\n  \"\"\"\\n  if radius < 0:\\n    raise ValueError(\"Radius cannot be negative\")\\n  return math.pi * radius ** 2",
  "description": "Calculates the area of a circle given its radius.",
  "parameters": {
    "radius": {
      "description": "The radius of the circle.",
      "type": "float",
      "required": True
    }
  }
}
content_copy
download
Use code with caution.
Provide ONLY the JSON object in your response.
"""
return prompt.strip()
def create_tool(self, task_description: str) -> Optional[Dict[str, Any]]:
    """
    Attempts to create a new tool using the LLM based on a task description.

    Args:
        task_description: A natural language description of the desired tool functionality.

    Returns:
        A dictionary containing the new tool's data if creation and validation
        are successful, otherwise None.
    """
    print(f"Attempting to create tool for task: {task_description[:100]}...")

    # Optional: Find similar tools first to provide context to LLM
    similar_tools = self.storage.find_similar_tools(task_description, n_results=2)

    prompt = self._generate_creation_prompt(task_description, similar_tools)
    messages = [{"role": "user", "content": prompt}]

    # Request JSON mode if possible
    llm_response = self.llm.get_completion(messages, json_mode=True, max_tokens=2000) # Allow more tokens for code

    if not llm_response:
        print("Error: Failed to get tool creation suggestion from LLM.")
        return None

    parsed_response = parse_llm_tool_creation_response(llm_response)

    if not parsed_response or not all(k in parsed_response for k in ["tool_name", "code", "description"]):
        print("Error: Failed to parse LLM creation response or missing required keys.")
        print(f"LLM raw response snippet: {llm_response[:200]}...")
        # Optionally: Attempt fallback parsing or ask user for clarification
        return None

    tool_name = parsed_response["tool_name"]
    code = parsed_response["code"]
    description = parsed_response["description"]
    parameters = parsed_response.get("parameters", {})

    # Basic validation
    if not tool_name or not code or not description:
         print("Error: Parsed response missing essential tool components (name, code, or description).")
         return None
    if not validate_python_code(code):
        print(f"Error: LLM generated syntactically invalid Python code for tool '{tool_name}'.")
        # Optionally: Could try to ask the LLM to fix the syntax error
        return None

    # Check if a tool with this name already exists
    existing_tool = self.storage.get_tool(tool_name)
    if existing_tool:
        print(f"Warning: Tool with name '{tool_name}' already exists. Overwriting.")
        # Or could implement versioning / renaming logic here

    # Store the newly created tool
    self.storage.add_or_update_tool(
        tool_name=tool_name,
        code=code,
        description=description,
        parameters=parameters,
        version=1, # Initial version
        error_log=[]
    )

    print(f"Successfully created and stored tool: '{tool_name}'")
    new_tool_data = {
         "tool_name": tool_name,
         "code": code,
         "description": description,
         "parameters": parameters,
         "version": 1,
         "error_log": []
    }
    return new_tool_data

def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves tool details from storage."""
    return self.storage.get_tool(tool_name)

def find_tool(self, description: str, threshold: float = 0.5) -> Optional[Dict[str, Any]]:
     """
     Finds the most relevant existing tool based on a description.

     Args:
         description: The description of the needed functionality.
         threshold: The maximum acceptable distance (lower is more similar).
                    Adjust based on embedding model and use case.

     Returns:
         The data of the most similar tool if found and within threshold, else None.
     """
     similar_tools = self.storage.find_similar_tools(description, n_results=1)
     if similar_tools:
         best_match = similar_tools[0]
         # Distance check (ChromaDB cosine distance is 1 - similarity)
         if best_match.get("distance") is not None and best_match["distance"] <= threshold:
             print(f"Found relevant tool '{best_match['tool_name']}' with distance {best_match['distance']:.4f}")
             return best_match
         else:
              print(f"Found tool '{best_match['tool_name']}' but distance {best_match.get('distance', 'N/A')} exceeds threshold {threshold}")
     return None


def execute_tool(
    self,
    tool_name: str,
    args: Optional[list] = None,
    kwargs: Optional[dict] = None,
    attempt_repair: bool = True,
    max_repair_attempts: int = 1
) -> Tuple[Any, Optional[str], Optional[str]]:
    """
    Executes a tool by name, with optional automatic repair on failure.

    Args:
        tool_name: The name of the tool to execute.
        args: Positional arguments for the tool function.
        kwargs: Keyword arguments for the tool function.
        attempt_repair: If True, try to repair the tool using the LLM if execution fails.
        max_repair_attempts: Maximum number of repair attempts for a single execution call.

    Returns:
    A tuple containing:
    - The result of the function execution (or None if execution failed).
    - Captured standard output (stdout) as a string (or None).
    - Captured standard error (stderr) or exception traceback as a string (or None if no error).
    """
    if args is None: args = []
    if kwargs is None: kwargs = {}

    current_attempt = 0
    while current_attempt <= max_repair_attempts:
        tool_data = self.storage.get_tool(tool_name)
        if not tool_data:
            error_msg = f"Tool '{tool_name}' not found in storage."
            print(error_msg)
            return None, None, error_msg

        code = tool_data.get("code")
        if not code:
             error_msg = f"Tool '{tool_name}' found but has no code."
             print(error_msg)
             return None, None, error_msg

        print(f"Executing tool '{tool_name}' (Version: {tool_data.get('version', 'N/A')}, Attempt: {current_attempt + 1})")
        result, stdout, stderr = safe_execute_tool(code, tool_name, args, kwargs)

        if stderr:
            print(f"Execution of '{tool_name}' failed.")
            print(f"Stderr/Error:\n{stderr}")

            # Log the error persistently with the tool
            error_log = tool_data.get("error_log", [])
            error_log.append(stderr) # Add the latest error
             # Keep only the last N errors (e.g., 5)
            max_log_entries = 5
            tool_data["error_log"] = error_log[-max_log_entries:]
            self.storage.add_or_update_tool(
                 tool_name=tool_name,
                 code=tool_data["code"],
                 description=tool_data["description"],
                 parameters=tool_data.get("parameters",{}),
                 version=tool_data.get("version", 1), # Keep current version on error log update
                 error_log=tool_data["error_log"]
            )


            if attempt_repair and current_attempt < max_repair_attempts:
                print(f"Attempting automated repair for tool '{tool_name}'...")
                repaired_tool_data = attempt_tool_repair(self.llm, self.storage, tool_name, stderr)
                if repaired_tool_data:
                    print(f"Repair attempt {current_attempt + 1} successful. Retrying execution...")
                    current_attempt += 1
                    continue # Retry execution with the repaired code
                else:
                    print(f"Automated repair for tool '{tool_name}' failed. Aborting execution.")
                    return None, stdout, f"Original Error:\n{stderr}\n\nRepair Failed."
            else:
                # No repair attempted or max attempts reached
                return result, stdout, stderr # Return the original failure result
        else:
            # Execution successful
            print(f"Execution of '{tool_name}' successful.")
            if stdout:
                print(f"Stdout:\n{stdout}")
            # Optionally clear error log on success? Or keep it for history?
            # Let's keep it for now.
            return result, stdout, None # Success

    # Should only be reached if max repair attempts were exceeded and all failed
    return None, None, f"Tool '{tool_name}' failed execution after {max_repair_attempts} repair attempts."


def improve_tool(self, tool_name: str, improvement_request: str) -> Optional[Dict[str, Any]]:
    """
    Attempts to improve an existing tool based on a user request, using the LLM.

    Args:
        tool_name: The name of the tool to improve.
        improvement_request: Natural language description of the desired improvement.

    Returns:
        A dictionary containing the improved tool's data if successful, otherwise None.
    """
    return attempt_tool_improvement(self.llm, self.storage, tool_name, improvement_request)

def use_tool_or_create(
    self,
    task_description: str,
    args: Optional[list] = None,
    kwargs: Optional[dict] = None,
    similarity_threshold: float = 0.3, # Lower means more strict similarity needed
    attempt_repair: bool = True,
    max_repair_attempts: int = 1
    ) -> Tuple[Any, Optional[str], Optional[str]]:
    """
    High-level function to either use an existing tool or create a new one for a task,
    then execute it.

    Args:
        task_description: The description of the task to accomplish.
        args: Positional arguments for the tool function.
        kwargs: Keyword arguments for the tool function.
        similarity_threshold: Threshold for finding an existing tool.
        attempt_repair: Whether to attempt repair if execution fails.
        max_repair_attempts: Max repair attempts during execution.

    Returns:
       The result tuple from execute_tool (result, stdout, stderr).
       Returns (None, None, "Tool creation failed.") if creation fails.
       Returns (None, None, "Tool finding/creation failed.") if no suitable tool action occurs.
    """
    print(f"\n--- Requesting tool for task: {task_description[:100]}... ---")
    # 1. Try to find a suitable existing tool
    tool_to_use = self.find_tool(task_description, threshold=similarity_threshold)
    tool_name = None

    if tool_to_use:
        tool_name = tool_to_use.get("tool_name")
        print(f"Found potentially suitable tool: '{tool_name}'. Proceeding with execution.")
    else:
        print(f"No suitable existing tool found (threshold: {similarity_threshold}). Attempting to create a new one.")
        # 2. If not found, try to create it
        created_tool = self.create_tool(task_description)
        if created_tool:
            tool_name = created_tool.get("tool_name")
            print(f"Successfully created tool '{tool_name}'. Proceeding with execution.")
        else:
            print("Failed to create a new tool for the task.")
            return None, None, "Tool creation failed for the task."

    # 3. Execute the chosen or newly created tool
    if tool_name:
        return self.execute_tool(
            tool_name=tool_name,
            args=args,
            kwargs=kwargs,
            attempt_repair=attempt_repair,
            max_repair_attempts=max_repair_attempts
        )
    else:
         # This case should ideally not be reached if create_tool returns properly
         print("Error: Could not determine tool name after finding or creating.")
         return None, None, "Tool finding/creation failed unexpectedly."

# --- Methods related to library self-repair/upgrade (Conceptual) ---

def get_library_component_code(self, component_name: str) -> Optional[str]:
     """Retrieves the source code of a component of this library."""
     # Warning: This is powerful and potentially dangerous. Needs careful implementation.
     module_map = {
         "tool_manager": "tool_creation_tool.tool_manager",
         "llm_interface": "tool_creation_tool.llm_interface",
         "storage": "tool_creation_tool.storage",
         "utils": "tool_creation_tool.utils",
         "repair": "tool_creation_tool.repair",
     }
     if component_name not in module_map:
         print(f"Error: Unknown library component '{component_name}'")
         return None

     try:
         module = __import__(module_map[component_name], fromlist=[''])
         import inspect
         return inspect.getsource(module)
     except Exception as e:
         print(f"Error retrieving source code for '{component_name}': {e}")
         return None

def attempt_library_self_repair(self, component_name: str, issue_description: str):
    """
    Conceptual: Attempts to repair a component of the library itself using the LLM.
    **This is highly experimental and requires extreme caution.**
    """
    print(f"\n--- WARNING: Attempting self-repair of library component: {component_name} ---")
    print(f"Issue: {issue_description}")

    current_code = self.get_library_component_code(component_name)
    if not current_code:
        print("Self-repair failed: Could not retrieve component source code.")
        return False

    prompt = f"""
    Objective: You are an expert Python developer tasked with repairing a component of an AI library.
    The library (`tool_creation_tool`) allows LLMs to create, manage, and repair *other* Python tools.
    Now, you need to repair a part of the library *itself*.

    Component to Repair: `{component_name}.py`

    Issue Description:
    {issue_description}

    Current Code of `{component_name}.py`:
    ```python
    {current_code}
    ```

    Task:
    1. Analyze the issue description and the current code.
    2. Identify the necessary changes to fix the issue.
    3. Provide the *complete, corrected* Python code for the *entire* `{component_name}.py` file.
    4. Ensure the corrected code is syntactically valid and maintains the overall functionality and purpose of the component within the library.
    5. Respond ONLY with the raw, corrected Python code for the file. Do not include explanations, markdown formatting, or anything else. Just the code.

    Example Response (Only the code):
    ```python
    # tool_creation_tool/{component_name}.py - Corrected Code
    import necessary_modules
    # ... (rest of the corrected code for the entire file) ...
    class CorrectedClass:
        # ... methods ...
    def corrected_function():
        # ... logic ...
    ```

    Provide ONLY the Python code block.
    """

    messages = [{"role": "user", "content": prompt.strip()}]
    # Use a capable model, maybe lower temperature for code generation consistency
    llm_response = self.llm.get_completion(messages, max_tokens=4000, temperature=0.3, json_mode=False) # Max tokens high for full file

    if not llm_response:
        print("Self-repair failed: No response from LLM.")
        return False

    # Clean potential markdown fences if present
    corrected_code = re.sub(r"^```(?:python)?\s*", "", llm_response, flags=re.MULTILINE)
    corrected_code = re.sub(r"\s*```$", "", corrected_code)
    corrected_code = corrected_code.strip()


    if not validate_python_code(corrected_code):
        print("Self-repair failed: LLM generated invalid Python syntax.")
        print(f"Generated code snippet:\n{corrected_code[:500]}...")
        # TODO: Could add a retry loop here asking the LLM to fix the syntax error.
        return False

    # **DANGER ZONE:** Applying the changes
    # This needs extreme caution. Should involve backups, validation, maybe human confirmation.
    # For this example, we'll just print the proposed change.
    print(f"\n--- Proposed Code for {component_name}.py ---")
    print(corrected_code)
    print("--- End Proposed Code ---")

    # In a real scenario, you would:
    # 1. Backup the original file.
    # 2. Write the `corrected_code` to the component's file path.
    # 3. Potentially run tests or validation checks.
    # 4. Have a mechanism to revert if things break.
    # For now, we stop here.
    print(f"\nSelf-repair suggestion generated for {component_name}. Apply manually or with extreme caution.")
    return True # Indicates suggestion was generated

