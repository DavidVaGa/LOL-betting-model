import pandas as pd
import os
import logging
from typing import Optional, List
import numpy as np

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Columnas esperadas en el CSV
REQUIRED_COLUMNS = ['partido', 'jugador', 'linea', 'cuota_over', 'cuota_under']

def create_sample_csv(filename: str = 'cuotas_ejemplo.csv') -> None:
    """
    Crea un archivo CSV de ejemplo con datos ficticios de cuotas.
    
    Args:
        filename: Nombre del archivo a crear
    """
    sample_data = [
        {
            'partido': 'G2 vs FNC',
            'jugador': 'Caps',
            'linea': 5.5,
            'cuota_over': 1.85,
            'cuota_under': 1.85
        },
        {
            'partido': 'G2 vs FNC',
            'jugador': 'Rekkles',
            'linea': 3.5,
            'cuota_over': 1.90,
            'cuota_under': 1.80
        },
        {
            'partido': 'G2 vs FNC',
            'jugador': 'Jankos',
            'linea': 2.5,
            'cuota_over': 2.10,
            'cuota_under': 1.70
        },
        {
            'partido': 'MAD vs RGE',
            'jugador': 'Humanoid',
            'linea': 4.5,
            'cuota_over': 1.95,
            'cuota_under': 1.75
        },
        {
            'partido': 'MAD vs RGE',
            'jugador': 'Hans Sama',
            'linea': 6.5,
            'cuota_over': 1.80,
            'cuota_under': 1.90
        },
        {
            'partido': 'BDS vs VIT',
            'jugador': 'Crownie',
            'linea': 4.0,
            'cuota_over': 2.00,
            'cuota_under': 1.75
        },
        {
            'partido': 'BDS vs VIT',
            'jugador': 'Photon',
            'linea': 7.5,
            'cuota_over': 1.75,
            'cuota_under': 1.95
        },
        {
            'partido': 'SK vs XL',
            'jugador': 'Irrelevant',
            'linea': 3.0,
            'cuota_over': 2.20,
            'cuota_under': 1.60
        }
    ]
    
    df = pd.DataFrame(sample_data)
    df.to_csv(filename, index=False, encoding='utf-8')
    logger.info(f"Archivo de ejemplo creado: {filename}")

def validate_columns(df: pd.DataFrame) -> tuple[bool, List[str]]:
    """
    Valida que el DataFrame tenga las columnas requeridas.
    
    Args:
        df: DataFrame a validar
        
    Returns:
        Tupla (es_válido, lista_errores)
    """
    errors = []
    
    # Verificar columnas requeridas
    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_columns:
        errors.append(f"Columnas faltantes: {', '.join(missing_columns)}")
    
    # Verificar columnas extra (advertencia, no error)
    extra_columns = set(df.columns) - set(REQUIRED_COLUMNS)
    if extra_columns:
        logger.warning(f"Columnas adicionales encontradas (se ignorarán): {', '.join(extra_columns)}")
    
    return len(errors) == 0, errors

def validate_data_types(df: pd.DataFrame) -> tuple[bool, List[str]]:
    """
    Valida los tipos de datos y valores en las columnas numéricas.
    
    Args:
        df: DataFrame a validar
        
    Returns:
        Tupla (es_válido, lista_errores)
    """
    errors = []
    
    # Verificar que las columnas existan antes de validar
    if not all(col in df.columns for col in REQUIRED_COLUMNS):
        return False, ["No se pueden validar tipos de datos: faltan columnas requeridas"]
    
    # Validar columnas de texto
    text_columns = ['partido', 'jugador']
    for col in text_columns:
        if df[col].isnull().any():
            errors.append(f"La columna '{col}' contiene valores nulos")
        if (df[col].astype(str).str.strip() == '').any():
            errors.append(f"La columna '{col}' contiene valores vacíos")
    
    # Validar columnas numéricas
    numeric_columns = ['linea', 'cuota_over', 'cuota_under']
    for col in numeric_columns:
        # Intentar convertir a numérico
        try:
            numeric_values = pd.to_numeric(df[col], errors='coerce')
            
            # Verificar valores no numéricos
            if numeric_values.isnull().any() and not df[col].isnull().any():
                invalid_indices = df[numeric_values.isnull() & df[col].notnull()].index.tolist()
                errors.append(f"La columna '{col}' contiene valores no numéricos en filas: {invalid_indices}")
            
            # Verificar valores nulos originales
            if df[col].isnull().any():
                errors.append(f"La columna '{col}' contiene valores nulos")
            
            # Validaciones específicas para cada tipo de columna
            valid_numeric = numeric_values.dropna()
            
            if col == 'linea':
                if (valid_numeric < 0).any():
                    errors.append(f"La columna '{col}' contiene valores negativos")
                if (valid_numeric > 50).any():  # Línea muy alta, probablemente error
                    errors.append(f"La columna '{col}' contiene valores excesivamente altos (>50)")
            
            elif col in ['cuota_over', 'cuota_under']:
                if (valid_numeric <= 1).any():
                    errors.append(f"La columna '{col}' contiene cuotas <= 1.0 (no válidas)")
                if (valid_numeric > 10).any():  # Cuota muy alta, probablemente error
                    errors.append(f"La columna '{col}' contiene cuotas excesivamente altas (>10)")
                    
        except Exception as e:
            errors.append(f"Error al validar columna '{col}': {str(e)}")
    
    return len(errors) == 0, errors

def clean_and_convert_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y convierte los datos a los tipos correctos.
    
    Args:
        df: DataFrame original
        
    Returns:
        DataFrame limpio
    """
    df_clean = df.copy()
    
    # Limpiar columnas de texto
    text_columns = ['partido', 'jugador']
    for col in text_columns:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].astype(str).str.strip()
    
    # Convertir columnas numéricas
    numeric_columns = ['linea', 'cuota_over', 'cuota_under']
    for col in numeric_columns:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    
    # Seleccionar solo las columnas requeridas en el orden correcto
    df_clean = df_clean[REQUIRED_COLUMNS]
    
    return df_clean

def load_cuotas(path: str) -> Optional[pd.DataFrame]:
    """
    Carga un archivo CSV con cuotas y valida su estructura y contenido.
    
    Args:
        path: Ruta al archivo CSV
        
    Returns:
        DataFrame con las cuotas o None si hay errores
    """
    try:
        # Verificar que el archivo existe
        if not os.path.exists(path):
            logger.error(f"Error: El archivo '{path}' no existe")
            return None
        
        logger.info(f"Cargando archivo de cuotas: {path}")
        
        # Cargar CSV
        try:
            df = pd.read_csv(path, encoding='utf-8')
        except UnicodeDecodeError:
            # Intentar con otra codificación
            df = pd.read_csv(path, encoding='latin-1')
            logger.warning("Archivo cargado con codificación latin-1")
        
        logger.info(f"Archivo cargado: {len(df)} filas, {len(df.columns)} columnas")
        
        # Verificar que no esté vacío
        if df.empty:
            logger.error("Error: El archivo está vacío")
            return None
        
        # Validar estructura de columnas
        is_valid_structure, column_errors = validate_columns(df)
        if not is_valid_structure:
            logger.error("Error de estructura:")
            for error in column_errors:
                logger.error(f"  - {error}")
            return None
        
        # Limpiar y convertir datos
        df_clean = clean_and_convert_data(df)
        
        # Validar tipos de datos
        is_valid_data, data_errors = validate_data_types(df_clean)
        if not is_valid_data:
            logger.error("Error de validación de datos:")
            for error in data_errors:
                logger.error(f"  - {error}")
            return None
        
        logger.info(f"Datos validados correctamente: {len(df_clean)} filas válidas")
        
        # Mostrar resumen de datos
        partidos_unicos = df_clean['partido'].nunique()
        jugadores_unicos = df_clean['jugador'].nunique()
        logger.info(f"Resumen: {partidos_unicos} partidos únicos, {jugadores_unicos} jugadores únicos")
        
        return df_clean
        
    except pd.errors.EmptyDataError:
        logger.error("Error: El archivo CSV está vacío o mal formateado")
        return None
    except pd.errors.ParserError as e:
        logger.error(f"Error al parsear el CSV: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al cargar el archivo: {str(e)}")
        return None

def display_cuotas_summary(df: pd.DataFrame) -> None:
    """
    Muestra un resumen de las cuotas cargadas.
    
    Args:
        df: DataFrame con las cuotas
    """
    print("\n" + "="*60)
    print("RESUMEN DE CUOTAS CARGADAS")
    print("="*60)
    
    print(f"Total de registros: {len(df)}")
    print(f"Partidos únicos: {df['partido'].nunique()}")
    print(f"Jugadores únicos: {df['jugador'].nunique()}")
    
    print(f"\nRango de líneas: {df['linea'].min():.1f} - {df['linea'].max():.1f}")
    print(f"Rango cuotas over: {df['cuota_over'].min():.2f} - {df['cuota_over'].max():.2f}")
    print(f"Rango cuotas under: {df['cuota_under'].min():.2f} - {df['cuota_under'].max():.2f}")
    
    print(f"\nPartidos disponibles:")
    for partido in sorted(df['partido'].unique()):
        jugadores_partido = df[df['partido'] == partido]['jugador'].nunique()
        print(f"  - {partido} ({jugadores_partido} jugadores)")
    
    print("\n" + "="*60)
    print("PRIMERAS 10 FILAS:")
    print("="*60)
    print(df.head(10).to_string(index=False))

def main():
    """Función principal para probar el módulo"""
    # Crear archivo de ejemplo si no existe
    example_file = 'cuotas_ejemplo.csv'
    
    if not os.path.exists(example_file):
        print(f"Creando archivo de ejemplo: {example_file}")
        create_sample_csv(example_file)
    else:
        print(f"Usando archivo existente: {example_file}")
    
    # Cargar y mostrar datos
    df = load_cuotas(example_file)
    
    if df is not None:
        display_cuotas_summary(df)
        
        # Mostrar algunas estadísticas adicionales
        print(f"\n" + "="*60)
        print("ESTADÍSTICAS ADICIONALES:")
        print("="*60)
        
        # Cuota promedio por tipo
        print(f"Cuota over promedio: {df['cuota_over'].mean():.2f}")
        print(f"Cuota under promedio: {df['cuota_under'].mean():.2f}")
        
        # Líneas más comunes
        print(f"\nLíneas más comunes:")
        lineas_comunes = df['linea'].value_counts().head(3)
        for linea, count in lineas_comunes.items():
            print(f"  - {linea}: {count} registros")
            
        # Jugador con más registros
        jugador_top = df['jugador'].value_counts().head(1)
        if not jugador_top.empty:
            print(f"\nJugador con más líneas: {jugador_top.index[0]} ({jugador_top.iloc[0]} líneas)")
            
    else:
        print("No se pudieron cargar los datos correctamente.")

if __name__ == "__main__":
    main()