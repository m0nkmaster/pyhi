# test_harness.py
import json
import os
from dotenv import load_dotenv
from pathlib import Path
import importlib.util
from typing import Dict, List, Any

def load_function_configs() -> Dict[str, Any]:
    """Load all function configurations from the functions directory."""
    functions = {}
    functions_dir = Path("src/functions")
    
    for function_dir in functions_dir.iterdir():
        if function_dir.is_dir():
            config_file = function_dir / "config.json"
            if config_file.exists():
                with open(config_file) as f:
                    config = json.load(f)
                    functions[config["name"]] = {
                        "config": config,
                        "path": function_dir / "implementation.py"
                    }
    
    return functions

def load_implementation(path: Path):
    """Dynamically load the implementation module."""
    spec = importlib.util.spec_from_file_location("implementation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.implementation

def get_user_input(param_config: Dict[str, Any]) -> Any:
    """Get user input based on parameter configuration."""
    if param_config.get("type") == "object":
        result = {}
        for name, prop in param_config.get("properties", {}).items():
            if name in param_config.get("required", []) or input(f"Include {name}? (y/N): ").lower() == 'y':
                if prop.get("type") == "object":
                    result[name] = get_user_input(prop)
                else:
                    default = prop.get("default", "")
                    default_str = f" (default: {default})" if default else ""
                    value = input(f"Enter {name}{default_str}: ") or default
                    
                    # Convert to appropriate type
                    if prop.get("type") == "integer":
                        value = int(value)
                    result[name] = value
        return result
    return input(f"Enter value ({param_config.get('type', 'string')}): ")

def main():
    """Main function to run the test harness."""
    # Load environment variables
    load_dotenv()
    
    # Load available functions
    functions = load_function_configs()
    
    if not functions:
        print("No functions found in src/functions directory!")
        return
    
    # Display available functions
    print("\nAvailable functions:")
    for i, name in enumerate(functions.keys(), 1):
        print(f"{i}. {name}")
    
    # Get function choice
    while True:
        try:
            choice = int(input("\nEnter function number to test: ")) - 1
            if 0 <= choice < len(functions):
                break
            print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a number.")
    
    function_name = list(functions.keys())[choice]
    function_info = functions[function_name]
    
    print(f"\nTesting function: {function_name}")
    print(f"Description: {function_info['config']['description']}")
    
    # Get parameters from user
    params = get_user_input(function_info['config']['parameters'])
    
    # Load and execute the implementation
    try:
        implementation = load_implementation(function_info['path'])
        print("\nExecuting function...")
        print("-" * 40)
        
        # Call implementation with unpacked parameters
        result = implementation(**params)
        
        print("\nResult:")
        try:
            # Try to pretty print if it's JSON
            formatted_result = json.dumps(json.loads(result), indent=2)
            print(formatted_result)
        except:
            # Otherwise print as is
            print(result)
            
    except Exception as e:
        print(f"\nError executing function: {str(e)}")

if __name__ == "__main__":
    main()