# tool_creation_tool/storage.py

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional, Any
import os
import hashlib

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

class ToolStorage:
    """
    Manages storing, retrieving, and updating tools using ChromaDB.
    """
    def __init__(self, path: Optional[str] = None, collection_name: str = "llm_tools"):
        self.collection_name = collection_name
        db_path = path or os.getenv("CHROMA_PATH", "./chroma_db")
        # Ensure the directory exists
        os.makedirs(db_path, exist_ok=True)

        try:
            self.client = chromadb.PersistentClient(path=db_path)
            # Use get_or_create_collection for robustness
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"} # Cosine similarity is good for text
            )
            print(f"ChromaDB connection established. Path: {db_path}, Collection: {self.collection_name}")
        except Exception as e:
            print(f"Error initializing ChromaDB at path '{db_path}': {e}")
            raise

    def _generate_id(self, tool_name: str) -> str:
        """Generates a consistent ID for a tool based on its name."""
        # Using SHA256 hash for a consistent and relatively safe ID
        return hashlib.sha256(tool_name.encode()).hexdigest()[:16] # Shortened hash

    def add_or_update_tool(
        self,
        tool_name: str,
        code: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        version: int = 1,
        error_log: Optional[List[str]] = None
    ):
        """
        Adds a new tool or updates an existing one in the collection.

        Args:
            tool_name: The unique name of the tool.
            code: The Python source code of the tool function.
            description: Natural language description of what the tool does.
            parameters: Dictionary describing the function's parameters (e.g., OpenAPI schema).
            version: Version number of the tool code.
            error_log: A list of recent errors encountered by this tool.
        """
        tool_id = self._generate_id(tool_name)
        metadata = {
            "tool_name": tool_name,
            "description": description,
            "parameters_json": json.dumps(parameters) if parameters else "{}",
            "version": version,
            "error_log_json": json.dumps(error_log) if error_log else "[]"
        }
        # ChromaDB uses 'documents' for the text to be embedded and searched on.
        # We embed the description and maybe parts of the code signature for searching.
        # The full code is stored but might not be the primary embedding target.
        searchable_text = f"Tool Name: {tool_name}\nDescription: {description}\nCode:\n{code}"

        try:
            self.collection.upsert(
                ids=[tool_id],
                documents=[searchable_text], # Text used for similarity search
                metadatas=[metadata],
            )
            print(f"Tool '{tool_name}' (v{version}) added/updated in ChromaDB with ID: {tool_id}")
        except Exception as e:
            print(f"Error adding/updating tool '{tool_name}' to ChromaDB: {e}")

    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a tool by its exact name.

        Returns:
            A dictionary containing the tool's data (code, metadata) or None if not found.
        """
        tool_id = self._generate_id(tool_name)
        try:
            result = self.collection.get(ids=[tool_id], include=['metadatas', 'documents'])
            if result and result['ids']:
                metadata = result['metadatas'][0]
                # The full code is part of the document, we need to extract it reliably.
                # Assuming the format used in add_or_update_tool
                document_content = result['documents'][0]
                code_start_marker = "Code:\n"
                code_index = document_content.find(code_start_marker)
                code = document_content[code_index + len(code_start_marker):] if code_index != -1 else ""

                tool_data = {
                    "tool_name": metadata.get("tool_name", tool_name),
                    "code": code,
                    "description": metadata.get("description"),
                    "parameters": json.loads(metadata.get("parameters_json", "{}")),
                    "version": metadata.get("version"),
                    "error_log": json.loads(metadata.get("error_log_json", "[]")),
                    "id": result['ids'][0],
                }
                return tool_data
            else:
                return None
        except Exception as e:
            print(f"Error retrieving tool '{tool_name}' from ChromaDB: {e}")
            return None

    def find_similar_tools(self, query_description: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Finds tools with descriptions similar to the query.

        Returns:
            A list of dictionaries, each containing tool data.
        """
        try:
            results = self.collection.query(
                query_texts=[query_description],
                n_results=n_results,
                include=['metadatas', 'documents', 'distances']
            )

            similar_tools = []
            if results and results['ids'] and results['ids'][0]:
                 for i, tool_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i]
                    document_content = results['documents'][0][i]
                    code_start_marker = "Code:\n"
                    code_index = document_content.find(code_start_marker)
                    code = document_content[code_index + len(code_start_marker):] if code_index != -1 else ""

                    tool_data = {
                        "tool_name": metadata.get("tool_name"),
                        "code": code,
                        "description": metadata.get("description"),
                        "parameters": json.loads(metadata.get("parameters_json", "{}")),
                        "version": metadata.get("version"),
                        "error_log": json.loads(metadata.get("error_log_json", "[]")),
                        "id": tool_id,
                        "distance": results['distances'][0][i] if results['distances'] else None,
                    }
                    similar_tools.append(tool_data)
            return similar_tools

        except Exception as e:
            print(f"Error querying similar tools from ChromaDB: {e}")
            return []

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Retrieves all tools from the collection."""
        try:
            results = self.collection.get(include=['metadatas', 'documents'])
            all_tools = []
            if results and results['ids']:
                for i, tool_id in enumerate(results['ids']):
                    metadata = results['metadatas'][i]
                    document_content = results['documents'][i]
                    code_start_marker = "Code:\n"
                    code_index = document_content.find(code_start_marker)
                    code = document_content[code_index + len(code_start_marker):] if code_index != -1 else ""

                    tool_data = {
                        "tool_name": metadata.get("tool_name"),
                        "code": code,
                        "description": metadata.get("description"),
                        "parameters": json.loads(metadata.get("parameters_json", "{}")),
                        "version": metadata.get("version"),
                        "error_log": json.loads(metadata.get("error_log_json", "[]")),
                        "id": tool_id,
                    }
                    all_tools.append(tool_data)
            return all_tools
        except Exception as e:
            print(f"Error retrieving all tools from ChromaDB: {e}")
            return []

    def delete_tool(self, tool_name: str) -> bool:
        """Deletes a tool by its name."""
        tool_id = self._generate_id(tool_name)
        try:
            self.collection.delete(ids=[tool_id])
            print(f"Tool '{tool_name}' deleted from ChromaDB.")
            return True
        except Exception as e:
             # Catch potential key errors if the ID doesn't exist, etc.
            print(f"Error deleting tool '{tool_name}' (ID: {tool_id}) from ChromaDB: {e}")
            return False

