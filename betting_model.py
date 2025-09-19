import pandas as pd
import numpy as np
from scipy.stats import poisson
import logging
from typing import Optional, Dict, Tuple
import os

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KillsBettingModel:
    """
    Modelo probabilístico para calcular Expected Value (EV) de apuestas 
    de kills en League of Legends usando distribución de Poisson.
    """
    
    def __init__(self):
        """Inicializar el modelo"""
        self.required_columns = [
            'player', 'avg_kills', 'odds_over', 'line_over', 
            'odds_under', 'line_under'
        ]
        
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, list]:
        """
        Valida la estructura y contenido del DataFrame de entrada.
        
        Args:
            df: DataFrame con los datos de entrada
            
        Returns:
            Tuple (es_válido, lista_errores)
        """
        errors = []
        
        # Verificar columnas requeridas
        missing_cols = set(self.required_columns) - set(df.columns)
        if missing_cols:
            errors.append(f"Columnas faltantes: {', '.join(missing_cols)}")
            return False, errors
        
        # Verificar que no esté vacío
        if df.empty:
            errors.append("DataFrame vacío")
            return False, errors
        
        # Validar tipos de datos numéricos
        numeric_cols = ['avg_kills', 'odds_over', 'line_over', 'odds_under', 'line_under']
        
        for col in numeric_cols:
            # Convertir a numérico y verificar errores
            numeric_values = pd.to_numeric(df[col], errors='coerce')
            
            if numeric_values.isnull().any():
                null_indices = df[numeric_values.isnull()].index.tolist()
                errors.append(f"Valores no numéricos en columna '{col}' (filas: {null_indices})")
        
        # Validaciones específicas de negocio
        try:
            # avg_kills debe ser positivo
            if (df['avg_kills'] <= 0).any():
                errors.append("avg_kills debe ser mayor que 0")
            
            # Las cuotas deben ser > 1.0
            if (df['odds_over'] <= 1.0).any() or (df['odds_under'] <= 1.0).any():
                errors.append("Las cuotas (odds) deben ser mayores que 1.0")
            
            # Las líneas deben ser positivas
            if (df['line_over'] < 0).any() or (df['line_under'] < 0).any():
                errors.append("Las líneas deben ser no negativas")
            
            # Verificar que line_over = line_under (misma línea)
            if not np.allclose(df['line_over'], df['line_under'], atol=1e-6):
                errors.append("line_over y line_under deben ser iguales")
                
        except (TypeError, ValueError) as e:
            errors.append(f"Error en validación de valores: {str(e)}")
        
        return len(errors) == 0, errors
    
    def odds_to_implied_probability(self, odds: float) -> float:
        """
        Convierte cuotas decimales a probabilidad implícita.
        
        Args:
            odds: Cuota decimal (ej: 1.85)
            
        Returns:
            Probabilidad implícita (entre 0 y 1)
        """
        return 1.0 / odds
    
    def calculate_poisson_probabilities(self, avg_kills: float, line: float) -> Dict[str, float]:
        """
        Calcula probabilidades Over/Under usando distribución de Poisson.
        
        Args:
            avg_kills: Media histórica de kills (parámetro λ de Poisson)
            line: Línea de apuesta (ej: 3.5)
            
        Returns:
            Diccionario con probabilidades p_over y p_under
        """
        # Para líneas decimales (ej: 3.5), usamos el floor para el cálculo
        # Over = kills > line, Under = kills <= line
        line_floor = int(np.floor(line))
        
        # P(X <= line_floor) para under
        # Como line es decimal (ej: 3.5), P(X <= 3.5) = P(X <= 3)
        p_under = poisson.cdf(line_floor, avg_kills)
        
        # P(X > line_floor) = 1 - P(X <= line_floor) para over
        # P(X > 3.5) = P(X >= 4) = 1 - P(X <= 3)
        p_over = 1 - p_under
        
        return {
            'p_over': p_over,
            'p_under': p_under
        }
    
    def calculate_expected_value(self, prob_real: float, odds: float) -> float:
        """
        Calcula el Expected Value (EV) de una apuesta.
        
        Formula: EV = (probabilidad_real * cuota) - 1
        
        Args:
            prob_real: Probabilidad real calculada con nuestro modelo
            odds: Cuota ofrecida por la casa de apuestas
            
        Returns:
            Expected Value (EV). Positivo = apuesta favorable, Negativo = desfavorable
        """
        return (prob_real * odds) - 1.0
    
    def determine_best_bet(self, ev_over: float, ev_under: float) -> Dict[str, any]:
        """
        Determina cuál es la mejor apuesta basándose en el EV.
        
        Args:
            ev_over: Expected Value de la apuesta Over
            ev_under: Expected Value de la apuesta Under
            
        Returns:
            Diccionario con la mejor apuesta y su EV
        """
        if ev_over > ev_under:
            return {
                'best_bet': 'Over',
                'best_ev': ev_over,
                'is_profitable': ev_over > 0
            }
        else:
            return {
                'best_bet': 'Under',
                'best_ev': ev_under,
                'is_profitable': ev_under > 0
            }
    
    def analyze_betting_opportunities(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Función principal que analiza las oportunidades de apuesta.
        
        Args:
            df: DataFrame con datos de entrada
            
        Returns:
            DataFrame con análisis completo o None si hay errores
        """
        logger.info("Iniciando análisis de oportunidades de apuesta")
        
        # Validar datos de entrada
        is_valid, errors = self.validate_data(df)
        if not is_valid:
            logger.error("Datos de entrada inválidos:")
            for error in errors:
                logger.error(f"  - {error}")
            return None
        
        logger.info(f"Analizando {len(df)} jugadores")
        
        # Lista para almacenar resultados
        results = []
        
        # Procesar cada jugador
        for idx, row in df.iterrows():
            try:
                player = row['player']
                avg_kills = float(row['avg_kills'])
                odds_over = float(row['odds_over'])
                odds_under = float(row['odds_under'])
                line = float(row['line_over'])  # Usamos line_over (debería ser igual a line_under)
                
                logger.debug(f"Procesando {player}: avg_kills={avg_kills}, line={line}")
                
                # Calcular probabilidades con Poisson
                probs = self.calculate_poisson_probabilities(avg_kills, line)
                p_over = probs['p_over']
                p_under = probs['p_under']
                
                # Calcular Expected Values
                ev_over = self.calculate_expected_value(p_over, odds_over)
                ev_under = self.calculate_expected_value(p_under, odds_under)
                
                # Determinar mejor apuesta
                best_bet_info = self.determine_best_bet(ev_over, ev_under)
                
                # Calcular probabilidades implícitas (para información adicional)
                implied_prob_over = self.odds_to_implied_probability(odds_over)
                implied_prob_under = self.odds_to_implied_probability(odds_under)
                
                # Agregar resultado
                results.append({
                    'player': player,
                    'avg_kills': avg_kills,
                    'line': line,
                    'p_over': round(p_over, 4),
                    'p_under': round(p_under, 4),
                    'EV_over': round(ev_over, 4),
                    'EV_under': round(ev_under, 4),
                    'best_bet': best_bet_info['best_bet'],
                    'best_ev': round(best_bet_info['best_ev'], 4),
                    'is_profitable': best_bet_info['is_profitable'],
                    'implied_prob_over': round(implied_prob_over, 4),
                    'implied_prob_under': round(implied_prob_under, 4),
                    'edge_over': round(p_over - implied_prob_over, 4),  # Ventaja sobre la casa
                    'edge_under': round(p_under - implied_prob_under, 4)
                })
                
            except Exception as e:
                logger.warning(f"Error procesando jugador en fila {idx}: {str(e)}")
                continue
        
        if not results:
            logger.error("No se pudieron procesar datos válidos")
            return None
        
        # Convertir a DataFrame
        results_df = pd.DataFrame(results)
        
        # Ordenar por mejor EV descendente
        results_df = results_df.sort_values('best_ev', ascending=False).reset_index(drop=True)
        
        logger.info(f"Análisis completado para {len(results_df)} jugadores")
        
        return results_df
    
    def get_summary_statistics(self, results_df: pd.DataFrame) -> Dict[str, any]:
        """
        Calcula estadísticas resumidas del análisis.
        
        Args:
            results_df: DataFrame con resultados del análisis
            
        Returns:
            Diccionario con estadísticas resumidas
        """
        if results_df.empty:
            return {}
        
        profitable_bets = results_df[results_df['is_profitable']]
        
        return {
            'total_players': len(results_df),
            'profitable_opportunities': len(profitable_bets),
            'profitability_rate': len(profitable_bets) / len(results_df),
            'best_ev': results_df['best_ev'].max(),
            'worst_ev': results_df['best_ev'].min(),
            'avg_ev': results_df['best_ev'].mean(),
            'over_bets': len(results_df[results_df['best_bet'] == 'Over']),
            'under_bets': len(results_df[results_df['best_bet'] == 'Under']),
            'avg_line': results_df['line'].mean(),
            'avg_kills': results_df['avg_kills'].mean()
        }

def load_betting_data(csv_path: str) -> Optional[pd.DataFrame]:
    """
    Carga datos desde un archivo CSV.
    
    Args:
        csv_path: Ruta al archivo CSV
        
    Returns:
        DataFrame con los datos o None si hay error
    """
    try:
        if not os.path.exists(csv_path):
            logger.error(f"Archivo no encontrado: {csv_path}")
            return None
        
        df = pd.read_csv(csv_path)
        logger.info(f"Archivo cargado: {len(df)} filas")
        return df
        
    except Exception as e:
        logger.error(f"Error cargando archivo: {str(e)}")
        return None

def create_sample_data(filename: str = 'betting_data_example.csv') -> None:
    """
    Crea un archivo CSV de ejemplo con datos de apuestas.
    
    Args:
        filename: Nombre del archivo a crear
    """
    sample_data = [
        {
            'player': 'Carzzy',
            'avg_kills': 3.8,
            'odds_over': 1.85,
            'line_over': 3.5,
            'odds_under': 1.95,
            'line_under': 3.5
        },
        {
            'player': 'Caps',
            'avg_kills': 5.2,
            'odds_over': 1.75,
            'line_over': 4.5,
            'odds_under': 2.05,
            'line_under': 4.5
        },
        {
            'player': 'Rekkles',
            'avg_kills': 4.1,
            'odds_over': 2.10,
            'line_over': 4.5,
            'odds_under': 1.70,
            'line_under': 4.5
        },
        {
            'player': 'Humanoid',
            'avg_kills': 3.5,
            'odds_over': 2.20,
            'line_over': 3.5,
            'odds_under': 1.65,
            'line_under': 3.5
        },
        {
            'player': 'Hans Sama',
            'avg_kills': 6.2,
            'odds_over': 1.90,
            'line_over': 5.5,
            'odds_under': 1.85,
            'line_under': 5.5
        }
    ]
    
    df = pd.DataFrame(sample_data)
    df.to_csv(filename, index=False)
    logger.info(f"Archivo de ejemplo creado: {filename}")

def display_results(results_df: pd.DataFrame, show_details: bool = True) -> None:
    """
    Muestra los resultados del análisis de forma legible.
    
    Args:
        results_df: DataFrame con resultados
        show_details: Si mostrar detalles completos
    """
    if results_df.empty:
        print("No hay resultados para mostrar")
        return
    
    print("\n" + "="*80)
    print("ANÁLISIS DE OPORTUNIDADES DE APUESTA - KILLS LOL")
    print("="*80)
    
    # Resumen general
    model = KillsBettingModel()
    stats = model.get_summary_statistics(results_df)
    
    print(f"Total de jugadores analizados: {stats['total_players']}")
    print(f"Oportunidades rentables: {stats['profitable_opportunities']} ({stats['profitability_rate']:.1%})")
    print(f"Mejor EV: {stats['best_ev']:.4f} ({stats['best_ev']*100:.2f}%)")
    print(f"EV promedio: {stats['avg_ev']:.4f} ({stats['avg_ev']*100:.2f}%)")
    print(f"Apuestas Over: {stats['over_bets']}, Under: {stats['under_bets']}")
    
    print(f"\n" + "="*80)
    print("MEJORES OPORTUNIDADES (ordenadas por EV)")
    print("="*80)
    
    # Mostrar mejores oportunidades
    top_opportunities = results_df.head(10)
    
    if show_details:
        columns_to_show = ['player', 'avg_kills', 'line', 'best_bet', 'best_ev', 'is_profitable']
        print(top_opportunities[columns_to_show].to_string(index=False))
        
        print(f"\n" + "="*80)
        print("DETALLES COMPLETOS (Top 5)")
        print("="*80)
        
        for idx, row in top_opportunities.head(5).iterrows():
            print(f"\n{row['player']}:")
            print(f"  Promedio histórico: {row['avg_kills']} kills")
            print(f"  Línea: {row['line']}")
            print(f"  Probabilidades modelo: Over {row['p_over']:.3f} ({row['p_over']*100:.1f}%) | Under {row['p_under']:.3f} ({row['p_under']*100:.1f}%)")
            print(f"  Expected Values: Over {row['EV_over']:.4f} | Under {row['EV_under']:.4f}")
            print(f"  ➤ Mejor apuesta: {row['best_bet']} (EV: {row['best_ev']:.4f} = {row['best_ev']*100:.2f}%)")
            print(f"  Rentable: {'✓' if row['is_profitable'] else '✗'}")
    else:
        columns_simple = ['player', 'best_bet', 'best_ev', 'is_profitable']
        print(top_opportunities[columns_simple].to_string(index=False))

def main():
    """Función principal para demostrar el uso del módulo"""
    
    # Crear archivo de ejemplo si no existe
    example_file = 'betting_data_example.csv'
    if not os.path.exists(example_file):
        print("Creando archivo de ejemplo...")
        create_sample_data(example_file)
    
    # Cargar datos
    print(f"Cargando datos desde {example_file}...")
    df = load_betting_data(example_file)
    
    if df is None:
        print("Error: No se pudieron cargar los datos")
        return
    
    # Crear modelo y analizar
    model = KillsBettingModel()
    results = model.analyze_betting_opportunities(df)
    
    if results is None:
        print("Error: No se pudo completar el análisis")
        return
    
    # Mostrar resultados
    display_results(results, show_details=True)
    
    # Guardar resultados
    output_file = 'betting_analysis_results.csv'
    results.to_csv(output_file, index=False)
    print(f"\nResultados guardados en: {output_file}")

if __name__ == "__main__":
    main()