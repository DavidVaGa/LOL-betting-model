#!/usr/bin/env python3
"""
Script de instalación para LoL Kills Betting Analyzer
====================================================

Este script automatiza la instalación y configuración inicial del proyecto.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Ejecutar comando con manejo de errores"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completado exitosamente")
            return True
        else:
            print(f"❌ Error en {description}: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error ejecutando {description}: {str(e)}")
        return False

def check_python_version():
    """Verificar versión de Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Se requiere Python 3.8 o superior")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detectado")
    return True

def create_directories():
    """Crear directorios necesarios"""
    directories = ['data', 'logs', 'exports']
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"📁 Directorio '{dir_name}' creado")

def main():
    """Función principal de instalación"""
    print("🎮 LoL Kills Betting Analyzer - Instalación")
    print("=" * 50)
    
    # Verificar Python
    if not check_python_version():
        sys.exit(1)
    
    # Crear directorios
    create_directories()
    
    # Verificar si pip está disponible
    if not run_command("pip --version", "Verificación de pip"):
        print("❌ pip no está disponible. Instala pip primero.")
        sys.exit(1)
    
    # Actualizar pip
    run_command("python -m pip install --upgrade pip", "Actualización de pip")
    
    # Instalar dependencias
    if not run_command("pip install -r requirements.txt", "Instalación de dependencias"):
        print("❌ Error instalando dependencias principales")
        sys.exit(1)
    
    # Verificar instalación de Streamlit
    if run_command("streamlit version", "Verificación de Streamlit"):
        print("✅ Streamlit instalado correctamente")
    
    # Crear archivos de ejemplo si no existen
    print("\n🔄 Creando archivos de ejemplo...")
    
    try:
        # Importar y crear datos de ejemplo
        from model import create_sample_data
        from cuotas import create_sample_csv
        
        create_sample_data("data/betting_data_example.csv")
        create_sample_csv("data/cuotas_ejemplo.csv")
        
        print("✅ Archivos de ejemplo creados en la carpeta 'data'")
        
    except Exception as e:
        print(f"⚠️ No se pudieron crear archivos de ejemplo: {str(e)}")
    
    # Instrucciones finales
    print("\n" + "=" * 50)
    print("🎉 ¡INSTALACIÓN COMPLETADA!")
    print("=" * 50)
    print("\n📋 Próximos pasos:")
    print("1. Ejecutar la aplicación:")
    print("   streamlit run app.py")
    print("\n2. Abrir en el navegador:")
    print("   http://localhost:8501")
    print("\n3. Usar datos de ejemplo en la carpeta 'data'")
    print("\n4. ¡Comenzar a analizar apuestas!")
    print("\n⚠️ Recordatorio: Apostar responsablemente")

if __name__ == "__main__":
    main()