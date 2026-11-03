"""
================================================================================
 BrachioDiag - Herramienta de Administración y Diagnóstico para Windows
 Desarrolladora: Angélica Serracín
 Materia: Sistemas Operativos (UTP - Centro Regional de Chiriquí)
================================================================================
"""

import sys
import importlib.util
from pathlib import Path

def main():
    """Lanzador de consola que inicia la aplicación de escritorio nativa."""
    app_path = Path(__file__).resolve().parent / "BrachioDiag.pyw"
    if not app_path.exists():
        print(f"Error: No se encontró el archivo de la aplicación en {app_path}")
        sys.exit(1)

    spec = importlib.util.spec_from_file_location("BrachioDiagAppMain", app_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()

if __name__ == "__main__":
    main()
