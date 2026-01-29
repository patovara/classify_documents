import os
import shutil
from pathlib import Path

def classify_documents_by_keyword(root_path, keyword):
    """
    Busca archivos que contengan una palabra en el título y los copia a un directorio clasificado.
    
    Args:
        root_path (str): Ruta local donde buscar archivos
        keyword (str): Palabra a buscar en los nombres de archivo
    """
    root_path = Path(root_path)
    
    # Crear directorio de destino
    output_dir = root_path / f"archivos_{keyword}"
    output_dir.mkdir(exist_ok=True)
    
    # Buscar archivos en el directorio y subdirectorios
    matched_files = root_path.rglob("*")
    count = 0
    
    for file_path in matched_files:
        # Validar que sea archivo y contenga la palabra en el nombre
        if file_path.is_file() and keyword.lower() in file_path.name.lower():
            try:
                shutil.copy2(file_path, output_dir / file_path.name)
                count += 1
                print(f"✓ Copiado: {file_path.name}")
            except Exception as e:
                print(f"✗ Error al copiar {file_path.name}: {e}")
    
    print(f"\nTotal de archivos encontrados y copiados: {count}")
    return output_dir

# Ejemplo de uso
if __name__ == "__main__":
    ruta = "/Users/patovara/Documents/ALURA/CodingBritanico"
    palabra_buscada = "invoice"
    classify_documents_by_keyword(ruta, palabra_buscada)