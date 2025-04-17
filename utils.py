# tool_creation_tool/utils.py

import sys
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Callable, Any, Dict, Optional, Tuple
import json
import re

def safe_execute_tool(code: str, function_name: str, args: Optional[list] = None, kwargs: Optional[dict] = None) -> Tuple[Any, Optional[str], Optional[str]]:
    """
    Safely executes dynamically generated Python code for a specific function.

    Args:
        code: The Python source code string containing the function definition.
        function_name: The name of the function to execute within the code.
        args: Positional arguments for the function.
        kwargs: Keyword arguments for the function.

    Returns:
        A tuple containing:
        - The result of the function execution (or None if execution failed).
        - Captured standard output (stdout) as a string (or None).
        - Captured standard error (stderr) or exception traceback as a string (or None if no error).
    """
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    local_scope = {}
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    result = None
    error_output = None

    try:
        # Execute the code in a specific scope
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, globals(), local_scope)

        # Check if the function exists in the created scope
        if function_name not in local_scope or not isinstance(local_scope[function_name], Callable):
            raise NameError(f"Function '{function_name}' not found or not callable in the provided code.")

        # Call the function within the captured I/O context
        tool_function = local_scope[function_name]
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            result = tool_function(*args, **kwargs)

    except Exception:
        # Capture the full traceback
        error_output = traceback.format_exc()
        result = None # Ensure result is None on error

    # Get captured output
    stdout_output = stdout_capture.getvalue()
    # Combine stderr capture and traceback if an exception occurred
    stderr_combined = stderr_capture.getvalue()
    if error_output:
        if stderr_combined:
            error_output = f"Captured stderr:\n{stderr_combined}\nException:\n{error_output}"
        else:
            error_output = f"Exception:\n{error_output}"
    elif stderr_combined: # If there was stderr output but no exception
        error_output = f"Captured stderr:\n{stderr_combined}"


    stdout_capture.close()
    stderr_capture.close()

    return result, stdout_output or None, error_output

def parse_llm_tool_creation_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Parses the LLM response expected to contain tool details (name, code, description, params).
    Assumes the LLM might return JSON directly, or Markdown containing a JSON block.
    """
    response_text = response_text.strip()

    # 1. Try direct JSON parsing
    try:
        data = json.loads(response_text)
        if all(k in data for k in ["tool_name", "code", "description"]):
            data.setdefault("parameters", {}) # Ensure parameters key exists
            return data
    except json.JSONDecodeError:
        pass # Not direct JSON, continue parsing

    # 2. Try finding JSON within Markdown code blocks
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL | re.IGNORECASE)
    if match:
        json_str = match.group(1)
        try:
            data = json.loads(json_str)
            if all(k in data for k in ["tool_name", "code", "description"]):
                data.setdefault("parameters", {}) # Ensure parameters key exists
                return data
        except json.JSONDecodeError:
            print(f"Warning: Found JSON block in Markdown, but failed to parse: {json_str[:100]}...")
            pass # Failed to parse the found JSON

    # 3. Fallback: Try to extract components using regex (less reliable)
    tool_name_match = re.search(r"tool_name[\s*:\s*]=?\s*['\"](\w+)['\"]", response_text, re.IGNORECASE)
    description_match = re.search(r"description[\s*:\s*]=?\s*['\"](.*?)['\"]", response_text, re.IGNORECASE | re.DOTALL)
    code_match = re.search(r"(?:```(?:python)?\s*(.*?)\s*```|code[\s*:\s*]=?\s*['\"](.*?)['\"])", response_text, re.DOTALL | re.IGNORECASE)

    if tool_name_match and description_match and code_match:
        tool_name = tool_name_match.group(1)
        description = description_match.group(1).strip()
        # Code might be in group 1 (markdown) or group 2 (assignment)
        code = code_match.group(1) or code_match.group(2)
        code = code.strip()
        # Attempt to extract function definition to guess name if needed
        def_match = re.search(r"def\s+(\w+)\s*\(", code)
        if def_match and not tool_name:
            tool_name = def_match.group(1)

        if tool_name and code and description:
             # Parameters are hard to guess reliably with regex, default to empty
            print("Warning: Parsed tool using regex fallback. Parameter extraction might be incomplete.")
            return {
                "tool_name": tool_name,
                "code": code,
                "description": description,
                "parameters": {} # Cannot reliably extract parameters via regex
            }

    print("Error: Could not parse LLM response into tool components.")
    print(f"Response received:\n{response_text[:500]}...") # Log snippet of failed response
    return None

def validate_python_code(code: str) -> bool:
    """Checks if the provided string is valid Python syntax."""
    try:
        compile(code, "<string>", "exec")
        return True
    except SyntaxError as e:
        print(f"Syntax validation failed: {e}")
        return False

