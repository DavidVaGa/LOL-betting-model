import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from typing import List, Dict, Optional
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_html(url: str, max_retries: int = 3, delay: float = 1.0) -> Optional[BeautifulSoup]:
    """
    Descarga el contenido HTML de una URL y devuelve un objeto BeautifulSoup.
    
    Args:
        url: URL a descargar
        max_retries: Número máximo de intentos
        delay: Tiempo de espera entre requests
    
    Returns:
        BeautifulSoup object o None si falla
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Descargando: {url} (intento {attempt + 1}/{max_retries})")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            time.sleep(delay)  # Ser respetuoso con el servidor
            return soup
            
        except requests.RequestException as e:
            logger.warning(f"Error en intento {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                logger.error(f"Falló la descarga después de {max_retries} intentos")
                return None

def extract_team_links(soup: BeautifulSoup) -> Dict[str, str]:
    """
    Extrae los enlaces a las páginas de equipos desde la página principal de la competición.
    
    Args:
        soup: BeautifulSoup object de la página principal
    
    Returns:
        Diccionario con nombre_equipo: url_equipo
    """
    team_links = {}
    
    # Buscar tabla de equipos participantes
    teams_sections = soup.find_all(['div', 'section'], class_=re.compile(r'team|participant', re.I))
    
    # También buscar en tablas generales
    tables = soup.find_all('table')
    
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            for cell in cells:
                # Buscar enlaces a equipos
                team_links_in_cell = cell.find_all('a', href=re.compile(r'/wiki/.+'))
                for link in team_links_in_cell:
                    if link.get('title') and '/wiki/' in link.get('href', ''):
                        team_name = link.get('title').strip()
                        # Filtrar enlaces que parezcan de equipos (evitar fechas, jugadores sueltos, etc.)
                        if not re.search(r'\d{4}|Season|Spring|Summer|Championship|/\d+/', team_name):
                            full_url = f"https://lol.fandom.com{link['href']}"
                            team_links[team_name] = full_url
    
    logger.info(f"Encontrados {len(team_links)} equipos: {list(team_links.keys())}")
    return team_links

def parse_match_data(soup: BeautifulSoup, team_name: str) -> List[Dict]:
    """
    Extrae datos de kills de jugadores desde la página de un equipo.
    
    Args:
        soup: BeautifulSoup object de la página del equipo
        team_name: Nombre del equipo
    
    Returns:
        Lista de diccionarios con datos de kills por jugador y partida
    """
    match_data = []
    
    # Buscar tablas de match history o game stats
    tables = soup.find_all('table')
    
    for table in tables:
        # Buscar tabla que contenga estadísticas de partidas
        headers = table.find('tr')
        if not headers:
            continue
            
        header_texts = [th.get_text().strip().lower() for th in headers.find_all(['th', 'td'])]
        
        # Verificar si es una tabla de estadísticas de partidas
        if any(keyword in ' '.join(header_texts) for keyword in ['kill', 'death', 'assist', 'kda', 'player']):
            rows = table.find_all('tr')[1:]  # Saltar header
            
            for i, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue
                
                # Intentar extraer nombre de jugador
                player_name = None
                kills = None
                
                for j, cell in enumerate(cells):
                    cell_text = cell.get_text().strip()
                    
                    # Buscar enlaces a jugadores
                    player_link = cell.find('a', href=re.compile(r'/wiki/.+'))
                    if player_link and not re.search(r'\d{4}|Season|Spring|Summer|vs', player_link.get_text()):
                        player_name = player_link.get_text().strip()
                    
                    # Buscar número de kills (buscar números que podrían ser kills)
                    if re.match(r'^\d+$', cell_text) and int(cell_text) < 30:  # Kills raramente > 30
                        if 'kill' in header_texts[j] if j < len(header_texts) else False:
                            kills = int(cell_text)
                        elif player_name and kills is None:  # Si ya tenemos jugador, probablemente esto son kills
                            kills = int(cell_text)
                
                if player_name and kills is not None:
                    match_data.append({
                        'equipo': team_name,
                        'jugador': player_name,
                        'kills_partida': kills
                    })
    
    # Si no encontramos datos en tablas, buscar en otras estructuras
    if not match_data:
        # Buscar divs o secciones con estadísticas
        stat_sections = soup.find_all(['div', 'section'], class_=re.compile(r'stat|score|match', re.I))
        
        for section in stat_sections:
            # Buscar nombres de jugadores y kills
            player_elements = section.find_all('a', href=re.compile(r'/wiki/.+'))
            
            for player_elem in player_elements:
                player_name = player_elem.get_text().strip()
                
                # Buscar kills cerca de este jugador
                parent = player_elem.parent
                if parent:
                    numbers = re.findall(r'\b(\d+)\b', parent.get_text())
                    for num_str in numbers:
                        num = int(num_str)
                        if 0 <= num <= 30:  # Rango razonable para kills
                            match_data.append({
                                'equipo': team_name,
                                'jugador': player_name,
                                'kills_partida': num
                            })
                            break
    
    logger.info(f"Extraídos {len(match_data)} registros de kills para {team_name}")
    return match_data

def get_kill_averages(url: str) -> pd.DataFrame:
    """
    Función principal que obtiene los promedios de kills de todos los jugadores
    de una competición.
    
    Args:
        url: URL de la página principal de la competición
    
    Returns:
        DataFrame con columnas: equipo, jugador, media_kills
    """
    logger.info(f"Iniciando scraping de: {url}")
    
    # 1. Descargar página principal
    soup = fetch_html(url)
    if not soup:
        logger.error("No se pudo descargar la página principal")
        return pd.DataFrame()
    
    # 2. Extraer enlaces de equipos
    team_links = extract_team_links(soup)
    if not team_links:
        logger.warning("No se encontraron equipos, intentando extraer datos directamente de la página principal")
        all_match_data = parse_match_data(soup, "Unknown_Team")
    else:
        # 3. Extraer datos de cada equipo
        all_match_data = []
        
        for team_name, team_url in team_links.items():
            logger.info(f"Procesando equipo: {team_name}")
            
            team_soup = fetch_html(team_url)
            if team_soup:
                team_data = parse_match_data(team_soup, team_name)
                all_match_data.extend(team_data)
            else:
                logger.warning(f"No se pudo descargar datos de {team_name}")
    
    # 4. Crear DataFrame y calcular promedios
    if not all_match_data:
        logger.warning("No se encontraron datos de kills")
        return pd.DataFrame(columns=['equipo', 'jugador', 'media_kills'])
    
    df = pd.DataFrame(all_match_data)
    
    # Calcular promedio de kills por jugador
    kill_averages = df.groupby(['equipo', 'jugador'])['kills_partida'].mean().reset_index()
    kill_averages.rename(columns={'kills_partida': 'media_kills'}, inplace=True)
    kill_averages['media_kills'] = kill_averages['media_kills'].round(2)
    
    logger.info(f"Procesados {len(kill_averages)} jugadores únicos")
    
    return kill_averages

def main():
    """Función principal para probar el script"""
    # URL de ejemplo: LEC 2024 Spring
    url = "https://lol.fandom.com/wiki/LEC/2024_Season/Spring_Season"
    
    try:
        # Obtener datos de kills
        df_averages = get_kill_averages(url)
        
        if df_averages.empty:
            logger.error("No se obtuvieron datos")
            return
        
        # Mostrar resultados
        print("\n=== PROMEDIOS DE KILLS POR JUGADOR ===")
        print(df_averages.to_string(index=False))
        
        # Guardar en CSV
        csv_filename = "kills_stats.csv"
        df_averages.to_csv(csv_filename, index=False, encoding='utf-8')
        logger.info(f"Datos guardados en: {csv_filename}")
        
        # Estadísticas adicionales
        print(f"\n=== ESTADÍSTICAS ===")
        print(f"Total jugadores: {len(df_averages)}")
        print(f"Total equipos: {df_averages['equipo'].nunique()}")
        print(f"Promedio general de kills: {df_averages['media_kills'].mean():.2f}")
        
        # Top 5 jugadores con más kills
        top_killers = df_averages.nlargest(5, 'media_kills')
        print(f"\n=== TOP 5 KILLERS ===")
        print(top_killers.to_string(index=False))
        
    except Exception as e:
        logger.error(f"Error en la ejecución principal: {e}")
        raise

if __name__ == "__main__":
    main()