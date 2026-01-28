import os
import shutil
from pathlib import Path

def unpack_docs(root_path):
    """
    Move all documents from subfolders to the root folder and remove empty subfolders.
    
    Args:
        root_path (str): Path to the root folder
    """
    root_path = Path('C:\\Users\\melok\\Downloads\\test')
    
    if not root_path.exists():
        print(f"La ruta {root_path} no existe")
        return
    
    # Move all files from subfolders to root
    for item in root_path.rglob('*'):
        if item.is_file() and item.parent != root_path:
            destination = root_path / item.name
            
            # Handle duplicate filenames
            if destination.exists():
                base_name = item.stem
                extension = item.suffix
                counter = 1
                while destination.exists():
                    destination = root_path / f"{base_name}_{counter}{extension}"
                    counter += 1
            
            shutil.move(str(item), str(destination))
            print(f"Movido: {item} -> {destination}")
    
    # Remove empty subfolders
    for item in root_path.rglob('*'):
        if item.is_dir() and item != root_path:
            try:
                if not os.listdir(item):
                    os.rmdir(item)
                    print(f"Carpeta eliminada: {item}")
            except OSError:
                pass

# Ejemplo de uso
if __name__ == "__main__":
    unpack_docs("./")