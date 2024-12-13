import os
import sys

# Set UTF-8 encoding for standard output
sys.stdout.reconfigure(encoding='utf-8')

# Define the extensions for which content should be printed
EXT_TO_PRINT = {'.py', '.yml', '.config', 'dockerfile'}

def print_tree_structure(path):
    """Print the tree structure of the codespace."""
    print("--- Codespace Structure ---")
    for root, dirs, files in os.walk(path):
        level = root.replace(path, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f'{indent}{os.path.basename(root)}/')
        sub_indent = ' ' * 4 * (level + 1)
        for file in files:
            print(f'{sub_indent}{file}')
    print("-" * 40)

def print_directory_contents(path):
    """Print the contents of files with specified extensions."""
    print(f"--- PATH: {path} ---")
    for root, dirs, files in os.walk(path):
        level = root.replace(path, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f'{indent}{os.path.basename(root)}/')
        sub_indent = ' ' * 4 * (level + 1)
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, path)
            file_ext = os.path.splitext(file)[1]
            print(f'{sub_indent}{file}')

            if file_ext.lower() in EXT_TO_PRINT:  # Check if the file extension matches
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Print separator with the relative path of the file
                        print("\n" + "-" * 40)
                        print(f"--- FILE: {relative_path} ---")
                        print(content)
                        print("-" * 40 + "\n")
                except Exception as e:
                    print(f'{sub_indent}Error reading file: {e}')

if __name__ == "__main__":
    directory = "."
    print_tree_structure(directory)
    print_directory_contents(directory)