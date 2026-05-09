#!/usr/bin/env python3
"""
setup.py — Script de configuración e instalación de NOVA AI Agent
Ejecuta: python setup.py
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd: str, description: str) -> bool:
    """Ejecuta un comando y muestra el resultado."""
    print(f"\n{'='*50}")
    print(f"🔧 {description}")
    print(f"{'='*50}")
    
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, capture_output=False, text=True
        )
        print(f"✅ {description} — Completado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} — Error: {e}")
        return False


def check_python_version() -> bool:
    """Verifica la versión de Python."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    print(f"❌ Python {version.major}.{version.minor} — Se requiere 3.10+")
    return False


def create_directories():
    """Crea los directorios necesarios."""
    dirs = ["data", "data/conversations", "vector_store"]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    print("✅ Directorios creados")


def main():
    print("""
    ╔══════════════════════════════════════════╗
    ║    🚀 NOVA AI Agent — Instalación 🚀    ║
    ╚══════════════════════════════════════════╝
    """)

    # 1. Verificar Python
    print("📋 Verificando requisitos...")
    if not check_python_version():
        print("\n❌ Actualiza Python a la versión 3.10 o superior.")
        sys.exit(1)

    # 2. Crear directorios
    create_directories()

    # 3. Instalar dependencias
    if not run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Instalando dependencias Python"
    ):
        print("\n❌ Error instalando dependencias.")
        sys.exit(1)

    # 4. Verificar configuración
    print(f"\n{'='*50}")
    print("📋 Verificando configuración")
    print(f"{'='*50}")

    from config import validate_config
    errors = validate_config()

    if errors:
        print("\n⚠️  Configuración pendiente:")
        for error in errors:
            print(f"  ❌ {error}")
        
        print("""
📝 Para completar la configuración:

1. Obtén un token de HuggingFace (gratuito):
   → Ve a https://huggingface.co/settings/tokens
   → Crea un Access Token (tipo "Read")
   → Edita el archivo .env y reemplaza "tu_token_de_huggingface_aqui" con tu token

2. El token de Telegram ya está configurado.

3. Ejecuta NOVA:
   python main.py
""")
    else:
        print("✅ Todas las configuraciones están correctas")
        print("\n🚀 ¡Todo listo! Ejecuta NOVA con:")
        print("   python main.py")

    print("\n📚 Consulta agent.md para más información sobre las capacidades de NOVA.")


if __name__ == "__main__":
    main()
