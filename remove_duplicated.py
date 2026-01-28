import os
import hashlib
from pathlib import Path
from collections import defaultdict

def remove_duplicate_files(directory_path):
    """
    Analiza todos los archivos en un directorio y elimina los duplicados.
    Los duplicados se identifican por su contenido (hash).
    
    Args:
        directory_path (str): Ruta del directorio a analizar
    """
    if not os.path.isdir(directory_path):
        print(f"Error: {directory_path} no es un directorio válido")
        return
    
    file_hashes = defaultdict(list)
    
    # Calcular hash de cada archivo
    for filename in os.listdir(directory_path):
        filepath = os.path.join(directory_path, filename)
        
        if os.path.isfile(filepath):
            try:
                file_hash = calculate_file_hash(filepath)
                file_hashes[file_hash].append(filepath)
            except Exception as e:
                print(f"Error al procesar {filepath}: {e}")
    
    # Eliminar duplicados
    deleted_count = 0
    for file_hash, files in file_hashes.items():
        if len(files) > 1:
            # Mantener el primero, eliminar el resto
            for duplicate in files[1:]:
                try:
                    os.remove(duplicate)
                    print(f"Eliminado: {duplicate}")
                    deleted_count += 1
                except Exception as e:
                    print(f"Error al eliminar {duplicate}: {e}")
    
    print(f"\nTotal de archivos eliminados: {deleted_count}")

def calculate_file_hash(filepath):
    """
    Calcula el hash MD5 de un archivo.
    
    Args:
        filepath (str): Ruta del archivo
        
    Returns:
        str: Hash MD5 del archivo
    """
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

# Ejemplo de uso
if __name__ == "__main__":
    directorio = r"C:\Users\melok\OneDrive\Documentos\REMAA\H1 _ HPIC - HOTEL PRESIDENTE INTER. CANCUN"
    remove_duplicate_files(directorio)