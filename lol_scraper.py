import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
import re

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_page(url: str):
    """
    Descarga una página web y devuelve el objeto BeautifulSoup
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        logger.info(f"Descargando: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        time.sleep(1)  # Pausa entre requests
        return soup
        
    except Exception as e:
        logger.error(f"Error descargando {url}: {e}")
        return None

def extract_team_players(soup, team_name):
    """
    Extrae los nombres de los jugadores actuales del equipo desde la sección superior
    """
    players = []
    
    # MÉTODO 1: Buscar específicamente en la tabla navbox current-top
    # que contiene el roster actual del equipo
    navbox_table = soup.find('table', class_='navbox current-top')
    
    if navbox_table:
        logger.info("✅ Encontrada tabla navbox current-top")
        # Buscar el div con padding dentro de esta tabla específica
        roster_div = navbox_table.find('div', style=lambda style: style and 'padding:0em 0.25em' in style)
        
        if roster_div:
            logger.info("✅ Encontrado div del roster dentro de navbox")
            # Buscar todos los enlaces dentro de este div
            roster_links = roster_div.find_all('a', class_='to_hasTooltip')
            
            for link in roster_links:
                href = link.get('href', '')
                text = link.get_text().strip()
                
                # Solo tomar enlaces que van a páginas de Statistics/2025
                if '/Statistics/2025' in href and text:
                    # Filtrar equipos (que tienen palabras como "FEARX", "KIA", etc.)
                    if not any(word in text.upper() for word in ['FEARX', 'KIA', 'GEN.G', 'HANWHA', 'LIFE', 'T1', 'BILIBILI', 'CTBC', 'FLYING', 'OYSTER']):
                        players.append(text)
                        logger.info(f"✅ Jugador del roster: {text}")
    
    # MÉTODO 2: Si el método 1 no funciona, buscar en elementos spstats-player
    if not players:
        logger.info("Método 1 falló, probando método 2...")
        player_cells = soup.find_all('td', class_='spstats-player')
        
        for cell in player_cells:
            link = cell.find('a', class_='catlink-players')
            if link:
                text = link.get_text().strip()
                if text and len(text) > 1 and len(text) < 20:
                    # Filtrar nombres de equipos
                    if not any(word in text.upper() for word in ['FEARX', 'KIA', 'GEN.G', 'HANWHA', 'LIFE', 'T1']):
                        players.append(text)
                        logger.info(f"✅ Jugador de tabla: {text}")
    
    # MÉTODO 3: Buscar directamente por nombre conocidos de jugadores de KT Rolster
    if not players and 'KT' in team_name.upper():
        logger.info("Método 2 falló, buscando jugadores conocidos de KT Rolster...")
        known_kt_players = ['PerfecT', 'Cuzz', 'Bdd', 'deokdam', 'Peter']
        
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            text = link.get_text().strip()
            href = link.get('href', '')
            
            if text in known_kt_players and '/Statistics/2025' in href:
                players.append(text)
                logger.info(f"✅ Jugador conocido encontrado: {text}")
    
    # MÉTODO 4: Fallback general para cualquier equipo
    if not players:
        logger.info("Todos los métodos anteriores fallaron, usando búsqueda general...")
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text().strip()
            
            # Buscar enlaces específicos a Statistics/2025 de jugadores individuales
            if (text and 
                len(text) > 1 and 
                len(text) < 20 and
                '/Statistics/2025' in href and
                text not in ['History', 'Purge', 'Talk (0)'] and
                not any(team in text.upper() for team in ['BNK', 'FEARX', 'KIA', 'GEN.G', 'HANWHA', 'LIFE', 'T1', 'BILIBILI', 'CTBC']) and
                not text.isdigit()):
                
                players.append(text)
                logger.info(f"✅ Jugador por enlace directo: {text}")
                
                # Solo tomar los primeros 5-6 para evitar jugadores de otros equipos
                if len(players) >= 6:
                    break
    
    # Eliminar duplicados manteniendo orden
    unique_players = []
    seen = set()
    for player in players:
        if player not in seen:
            unique_players.append(player)
            seen.add(player)
    
    # Limitar a máximo 6 jugadores (roster típico)
    unique_players = unique_players[:6]
    
    logger.info(f"Jugadores identificados para {team_name}: {unique_players}")
    return unique_players

def extract_player_kills(soup, team_name, team_players):
    """
    Extrae kills solo de los jugadores específicos del equipo
    """
    if not team_players:
        logger.warning(f"No se encontraron jugadores para {team_name}")
        return []
    
    players_data = []
    
    # Buscar todas las tablas
    tables = soup.find_all('table')
    logger.info(f"Encontradas {len(tables)} tablas")
    
    for table_idx, table in enumerate(tables):
        logger.info(f"Analizando tabla {table_idx + 1}")
        
        # Buscar header con columna K
        all_rows = table.find_all('tr')
        if not all_rows:
            continue
        
        header_found = False
        k_column_idx = None
        header_row_idx = None
        
        for row_idx, row in enumerate(all_rows):
            cells = row.find_all(['th', 'td'])
            headers = [cell.get_text().strip() for cell in cells]
            
            # Buscar la columna K
            for i, header in enumerate(headers):
                if header.upper() == 'K' and len(header) == 1:
                    k_column_idx = i
                    header_row_idx = row_idx
                    header_found = True
                    logger.info(f"Columna K encontrada en tabla {table_idx + 1}, posición {i}")
                    break
            
            if header_found:
                break
        
        if not header_found:
            continue
        
        # Procesar filas de datos
        data_rows = all_rows[header_row_idx + 1:]
        logger.info(f"Procesando {len(data_rows)} filas de datos")
        
        valid_players_found = 0
        
        for row_idx, row in enumerate(data_rows):
            cells = row.find_all(['td', 'th'])
            
            if len(cells) <= k_column_idx:
                continue
            
            try:
                # Extraer nombre del jugador
                player_name = None
                for cell in cells[:3]:  # Buscar en las primeras 3 columnas
                    player_link = cell.find('a')
                    if player_link:
                        potential_name = player_link.get_text().strip()
                        if potential_name in team_players:  # ¡AQUÍ ESTÁ LA CLAVE!
                            player_name = potential_name
                            break
                
                # Si no hay enlace, revisar texto directo
                if not player_name:
                    first_cell_text = cells[0].get_text().strip()
                    if first_cell_text in team_players:  # ¡Y AQUÍ TAMBIÉN!
                        player_name = first_cell_text
                
                # Solo procesar si es un jugador del equipo
                if not player_name:
                    continue
                
                # Extraer kills
                kills_cell = cells[k_column_idx]
                kills_text = kills_cell.get_text().strip()
                
                logger.info(f"✅ Jugador del equipo encontrado: '{player_name}', Kills: '{kills_text}'")
                
                try:
                    kills_clean = kills_text.replace(',', '.')
                    avg_kills = float(kills_clean)
                    
                    if 0 <= avg_kills <= 20:  # Rango más amplio pero razonable
                        players_data.append({
                            'team': team_name,
                            'player': player_name,
                            'avg_kills': avg_kills
                        })
                        valid_players_found += 1
                        logger.info(f"✅ {player_name}: {avg_kills} kills promedio")
                    else:
                        logger.warning(f"Kills fuera de rango para {player_name}: {avg_kills}")
                        
                except ValueError:
                    logger.warning(f"No se pudo convertir kills '{kills_text}' para {player_name}")
                    
            except Exception as e:
                logger.warning(f"Error procesando fila {row_idx}: {e}")
                continue
        
        logger.info(f"Tabla {table_idx + 1}: {valid_players_found} jugadores del equipo encontrados")
        
        # Si ya encontramos jugadores del equipo, probablemente esta es la tabla correcta
        if valid_players_found > 0:
            break
    
    return players_data

def scrape_team_stats(url: str):
    """
    Función principal mejorada: scraping de estadísticas de un equipo
    """
    # Extraer nombre del equipo de la URL
    team_name = url.split('/')[-2].replace('_', ' ')
    
    logger.info(f"=== SCRAPING DE {team_name.upper()} ===")
    
    # Descargar página
    soup = fetch_page(url)
    if not soup:
        logger.error("No se pudo descargar la página")
        return []
    
    # PASO 1: Identificar jugadores del equipo
    team_players = extract_team_players(soup, team_name)
    
    if not team_players:
        logger.error(f"No se pudieron identificar jugadores para {team_name}")
        return []
    
    logger.info(f"Buscando estadísticas para jugadores: {team_players}")
    
    # PASO 2: Extraer datos solo de esos jugadores
    players_data = extract_player_kills(soup, team_name, team_players)
    
    logger.info(f"Extraídos datos de {len(players_data)} jugadores del equipo")
    return players_data

def test_single_team():
    """
    Función de prueba para un solo equipo - versión mejorada
    """
    url = "https://lol.fandom.com/wiki/KT_Rolster/Statistics/2025"
    
    print("="*60)
    print("PRUEBA DE SCRAPING MEJORADO - SOLO JUGADORES DEL EQUIPO")
    print("="*60)
    
    players_data = scrape_team_stats(url)
    
    if not players_data:
        print("❌ No se extrajeron datos")
        return
    
    # Mostrar resultados
    df = pd.DataFrame(players_data)
    print("\n✅ RESULTADOS (Solo jugadores del equipo):")
    print(df.to_string(index=False))
    
    # Guardar CSV
    filename = 'team_stats_filtered.csv'
    df.to_csv(filename, index=False)
    print(f"\n💾 Guardado en: {filename}")
    
    return df

def test_two_teams():
    """
    Prueba con dos equipos - solo jugadores de cada equipo
    """
    teams = [
        "https://lol.fandom.com/wiki/KT_Rolster/Statistics/2025",
        "https://lol.fandom.com/wiki/Hanwha_Life_Esports/Statistics/2025"
    ]
    
    print("="*60)
    print("PRUEBA MEJORADA - DOS EQUIPOS (SOLO SUS JUGADORES)")
    print("="*60)
    
    all_players = []
    
    for team_url in teams:
        team_players = scrape_team_stats(team_url)
        all_players.extend(team_players)
    
    if not all_players:
        print("❌ No se extrajeron datos de ningún equipo")
        return
    
    # Mostrar resultados
    df = pd.DataFrame(all_players)
    print("\n✅ RESULTADOS FILTRADOS:")
    print(df.to_string(index=False))
    
    # Guardar CSV
    filename = 'match_stats_filtered.csv'
    df.to_csv(filename, index=False)
    print(f"\n💾 Guardado en: {filename}")
    
    # Resumen por equipo
    print(f"\n📊 RESUMEN:")
    for team in df['team'].unique():
        team_df = df[df['team'] == team]
        avg_kills = team_df['avg_kills'].mean()
        print(f"  {team}: {len(team_df)} jugadores, promedio {avg_kills:.2f} kills")
        for _, player in team_df.iterrows():
            print(f"    - {player['player']}: {player['avg_kills']} kills")
    
    return df

def main():
    """
    Función principal mejorada
    """
    print("🎮 LoL SCRAPER MEJORADO - SOLO JUGADORES DEL EQUIPO")
    print("="*55)
    
    try:
        print("\n1️⃣ PROBANDO UN SOLO EQUIPO (KT Rolster)...")
        test_single_team()
        
        print("\n" + "="*55)
        
        print("\n2️⃣ PROBANDO DOS EQUIPOS...")  
        test_two_teams()
        
    except Exception as e:
        logger.error(f"Error en main: {e}")
        print(f"❌ Error general: {e}")

if __name__ == "__main__":
    main()