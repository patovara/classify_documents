import os
import shutil
from pathlib import Path
from collections import defaultdict

def classify_documents(root_path):
    """
    Classifies documents in a directory and its subdirectories by extension.
    Creates folders named after file extensions and moves files accordingly.
    
    Args:
        root_path (str): Root directory path to classify
    """
    root = Path(r"C:\Users\melok\OneDrive\Documentos\REMAA\H1 _ HPIC - HOTEL PRESIDENTE INTER. CANCUN")
    
    if not root.exists():
        print(f"Error: Path {root_path} does not exist")
        return
    
    # Dictionary to store files by extension
    files_by_extension = defaultdict(list)
    
    # Walk through all directories and subdirectories
    for dirpath, dirnames, filenames in os.walk(root):
        for filename in filenames:
            file_path = Path(dirpath) / filename
            
            # Skip if it's a directory
            if file_path.is_dir():
                continue
            
            # Get file extension (without the dot)
            extension = file_path.suffix.lstrip('.').lower()
            
            # Use 'sin_extension' for files without extension
            if not extension:
                extension = 'sin_extension'
            
            files_by_extension[extension].append(file_path)
    
    # Create folders and move files
    for extension, files in files_by_extension.items():
        folder_path = root / extension
        folder_path.mkdir(exist_ok=True)
        
        for file_path in files:
            try:
                destination = folder_path / file_path.name
                shutil.move(str(file_path), str(destination))
                print(f"Moved: {file_path.name} -> {extension}/")
            except Exception as e:
                print(f"Error moving {file_path.name}: {e}")
    
    print(f"\nClassification complete! Total extensions found: {len(files_by_extension)}")

# Usage
if __name__ == "__main__":
    classify_documents("./")