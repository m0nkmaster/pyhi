"""
Function manager for handling AI function calls.
Loads functions from a directory and manages their execution.
"""

import json
import importlib.util
import logging
from pathlib import Path
from typing import Dict, Any, List

class FunctionManager:
    """Manages custom functions that can be called by the AI assistant."""
    
    def __init__(self, functions_dir: str = "functions"):
        """
        Initialize the function manager.
        
        Args:
            functions_dir: Directory containing function implementations
        """
        self.functions_dir = Path(functions_dir)
        self.functions: Dict[str, Any] = {}
        self.tools: List[dict] = []
        logging.info(f"Initializing FunctionManager with functions directory: {self.functions_dir}")
        self.load_functions()

    def load_functions(self) -> None:
        """Load all functions from the functions directory."""
        if not self.functions_dir.exists():
            logging.error(f"Functions directory not found: {self.functions_dir}")
            raise FileNotFoundError(f"Functions directory not found: {self.functions_dir}")

        logging.info(f"Loading functions from directory: {self.functions_dir}")
        for func_dir in self.functions_dir.iterdir():
            if func_dir.is_dir():
                self._load_function(func_dir)

    def _load_function(self, func_dir: Path) -> None:
        """
        Load a single function from the given directory.
        
        Args:
            func_dir: Path to the function directory
        """
        config_file = func_dir / "config.json"
        implementation_file = func_dir / "implementation.py"

        if not config_file.exists() or not implementation_file.exists():
            logging.warning(f"Skipping invalid function in {func_dir}: missing config or implementation file")
            return

        # Load config (OpenAI function schema)
        with open(config_file) as f:
            config = json.load(f)

        # Validate the config follows OpenAI's schema
        required_fields = ["name", "description", "parameters"]
        if not all(field in config for field in required_fields):
            logging.warning(f"Skipping invalid function config in {func_dir}: missing required fields")
            return

        # Load implementation module
        spec = importlib.util.spec_from_file_location(
            f"functions.{func_dir.name}.implementation",
            implementation_file
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Store function implementation
        self.functions[config["name"]] = module.implementation
        logging.info(f"Loaded function: {config['name']} from {func_dir}")

        # Store OpenAI tool definition
        self.tools.append({
            "type": "function",
            "function": config
        })

    def get_tools(self) -> List[dict]:
        """
        Return all functions in OpenAI's tool format.
        
        Returns:
            List of function definitions in OpenAI's tool format
        """
        logging.debug(f"Returning {len(self.tools)} tools")
        return self.tools

    def call_function(self, function_name: str, **params) -> Any:
        """
        Call a function by name with the given parameters.
        
        Args:
            function_name: Name of the function to call
            **params: Parameters to pass to the function
            
        Returns:
            Result of the function call
            
        Raises:
            ValueError: If function_name is not found
        """
        if function_name not in self.functions:
            logging.error(f"Function {function_name} not found")
            raise ValueError(f"Function {function_name} not found")
        
        logging.debug(f"Calling function {function_name} with parameters: {params}")
        result = self.functions[function_name](**params)
        logging.debug(f"Function {function_name} returned: {result}")
        
        return result

    def get_system_prompt_snippet(self) -> str:
        """
        Generate a system prompt snippet describing available functions.
        
        Returns:
            A string describing the available functions
        """
        if not self.tools:
            logging.debug("No tools available")
            return ""
            
        logging.debug(f"Generating system prompt snippet for {len(self.tools)} tools")
        prompt = "Available functions:\n\n"
        for tool in self.tools:
            func = tool["function"]
            prompt += f"- {func['name']}: {func['description']}\n"
        return prompt