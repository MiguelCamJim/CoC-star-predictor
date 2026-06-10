"""
Funciones para obtener estadísticas de jugadores de CoC y calcular un coeficiente de poder ofensivo y defensivo basado en los niveles de tropas, hechizos, héroes y edificios defensivos.
"""

import requests
import json

def get_player_defensive_buildings(player_tag, api_token):
    """
    Obtiene los niveles de todos los edificios defensivos de un jugador
    """
    # Limpiar el tag del jugador
    clean_tag = player_tag.replace("#", "%23")
    
    # Headers para la API
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json"
    }
    
    # URL del endpoint del jugador
    url = f"https://api.clashofclans.com/v1/players/{clean_tag}"
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            player_data = response.json()
            
            # Extraer edificios defensivos
            defensive_buildings = {}
            
            # Los edificios están en la sección 'troops' -> 'defense'
            if 'troops' in player_data and len(player_data['troops']) > 2:
                defense_troops = player_data['troops'][2]  # Índice 2 son las defensas
                
                for building in defense_troops.get('items', []):
                    name = building.get('name', 'Unknown')
                    level = building.get('level', 0)
                    defensive_buildings[name] = level
            
            return defensive_buildings
            
        else:
            print(f"Error en API: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error obteniendo datos del jugador: {e}")
        return None

def calculate_defensive_power(player_tag, api_token):
    """
    Calcula el poder defensivo total basado en los niveles de edificios
    """
    buildings = get_player_defensive_buildings(player_tag, api_token)
    
    if not buildings:
        return 0
    
    # Pesos de importancia para cada edificio defensivo
    building_weights = {
        'Cannon': 1.0,
        'Archer Tower': 1.2,
        'Mortar': 0.8,
        'Air Defense': 1.5,
        'Wizard Tower': 1.3,
        'X-Bow': 2.0,
        'Inferno Tower': 2.5,
        'Eagle Artillery': 3.0,
        'Scattershot': 2.8,
        'Builder\'s Hut': 0.1,
        'Hidden Tesla': 1.4,
        'Bomb Tower': 1.1,
        'Air Sweeper': 0.5
    }
    
    total_power = 0
    
    print(f"🏰 Edificios defensivos encontrados:")
    for building_name, level in buildings.items():
        weight = building_weights.get(building_name, 1.0)
        power = level * weight
        total_power += power
        print(f"   {building_name}: Nivel {level} (Poder: {power:.1f})")
    
    print(f"\n🛡️ Poder defensivo total: {total_power:.1f}")
    return total_power

def get_player_offensive_units(player_tag, api_token):
    """
    Obtiene los niveles de todas las tropas, hechizos y héroes de un jugador
    """
    # Limpiar el tag del jugador
    clean_tag = player_tag.replace("#", "%23")
    
    # Headers para la API
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json"
    }
    
    # URL del endpoint del jugador
    url = f"https://api.clashofclans.com/v1/players/{clean_tag}"
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            player_data = response.json()
            
            offensive_data = {
                'troops': {},
                'spells': {},
                'heroes': {}
            }
            
            # Extraer tropas (índice 0)
            if 'troops' in player_data and len(player_data['troops']) > 0:
                troops_data = player_data['troops']
                
                for troop in troops_data:
                    name = troop.get('name', 'Unknown')
                    level = troop.get('level', 0)
                    village = troop.get('village', 'home')  # Default a 'home' si no especifica
                    
                    # Solo contar tropas de la aldea principal
                    if village == 'home':
                        offensive_data['troops'][name] = level

            # Extraer hechizos (índice 1)
            if 'spells' in player_data and len(player_data['spells']) > 1:
                spells_data = player_data['spells']
                
                for spell in spells_data:
                    name = spell.get('name', 'Unknown')
                    level = spell.get('level', 0)
                    village = spell.get('village', 'home')  # Default a 'home' si no especifica
                    
                    # Solo contar hechizos de la aldea principal
                    if village == 'home':
                        offensive_data['spells'][name] = level
            
            # Extraer héroes
            if 'heroes' in player_data:
                for hero in player_data['heroes']:
                    name = hero.get('name', 'Unknown')
                    level = hero.get('level', 0)
                    village = hero.get('village', 'home')  # Default a 'home' si no especifica
                    
                    # Solo contar héroes de la aldea principal
                    if village == 'home':
                        offensive_data['heroes'][name] = level
            
            return offensive_data
            
        else:
            print(f"Error en API: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error obteniendo datos ofensivos del jugador: {e}")
        return None

def calculate_offensive_power(player_tag, api_token):
    """
    Calcula el poder ofensivo total basado en tropas, hechizos y héroes
    """
    units = get_player_offensive_units(player_tag, api_token)
    
    if not units:
        return 0
    
    # Pesos para tropas (housing space y efectividad)
    troop_weights = {
        # Tropas Elixir (home village)
        'Barbarian': 0.8,
        'Archer': 0.9,
        'Goblin': 0.6,
        'Giant': 2.5,
        'Wall Breaker': 0.9,
        'Balloon': 2.2,
        'Wizard': 2.0,
        'Healer': 0.6,
        'Dragon': 4.5,
        'P.E.K.K.A': 4.0,
        'Baby Dragon': 2.0,
        'Miner': 2.8,
        'Electro Dragon': 5.0,
        'Yeti': 3.5,
        'Minion': 1.0,
        'Hog Rider': 2.5,
        'Valkyrie': 3.5,
        'Golem': 4.0,
        'Witch': 2.5,
        'Lava Hound': 4.5,
        'Bowler': 3.0,
        'Ice Golem': 2.0,
        'Headhunter': 2.2,
        'Dragon Rider': 3.5,
        'Log Launcher': 4.0,
        'Bomber': 1.0,
        'Bomb': 0.5,              # genérico si aparece

        # Siege machines & special vehicles (home village)
        'Wall Wrecker': 3.0,
        'Battle Blimp': 3.0,
        'Stone Slammer': 3.0,
        'Siege Barracks': 2.5,
        'Cannon Cart': 3.2,
        'Rocket Balloon': 3.0,
        'Stone Slammer': 3.0,

        # Builder/other named units (si aparecen en datos; les damos peso ligero o moderado)
        'Sneaky Archer': 0,
        'Beta Minion': 0,
        'Boxer Giant': 0,
        'Cannon Cart': 0,
        'Bomber': 0,
        'Sneaky Goblin': 0,
        'Headhunter': 0,
        'Ice Hound': 0,
        'Log Launcher': 0,
        'Apprentice Warden': 1,
        'Rocket Balloon': 0
    }

    # Pesos para hechizos (home village)
    spell_weights = {
        'Lightning Spell': 1.5,
        'Healing Spell': 1.0,
        'Rage Spell': 1.8,
        'Jump Spell': 1.2,
        'Freeze Spell': 1.6,
        'Clone Spell': 1.3,
        'Invisibility Spell': 1.4,
        'Poison Spell': 1.3,
        'Earthquake Spell': 1.4,
        'Haste Spell': 1.1,
        'Skeleton Spell': 0.8,
        'Bat Spell': 1.0,
        'Recall Spell': 1.0,
        'Overgrowth Spell': 2.0
    }

    # Pesos para héroes (home village) — muy importantes
    hero_weights = {
        'Barbarian King': 5.0,
        'Archer Queen': 5.5,
        'Grand Warden': 6.0,
        'Royal Champion': 5.8,
        # Si en algún dato aparecen otros "hero-like" del home village:
        'Battle Machine': 0.0,  # builder hero (no aplicar)
        'Battle Copter': 0.0  # builder hero (no aplicar)
    }
    
    total_power = 0
    
    # Calcular poder de tropas
    troops_power = 0
    for troop_name, level in units.get('troops', {}).items():
        weight = troop_weights.get(troop_name, 1.0)
        power = level * weight
        troops_power += power
    
    # Calcular poder de hechizos
    spells_power = 0
    for spell_name, level in units.get('spells', {}).items():
        weight = spell_weights.get(spell_name, 1.0)
        power = level * weight
        spells_power += power
    
    # Calcular poder de héroes
    heroes_power = 0
    for hero_name, level in units.get('heroes', {}).items():
        weight = hero_weights.get(hero_name, 3.0)
        power = level * weight * 0.1  # Los héroes tienen niveles muy altos, normalizamos
        heroes_power += power
    
    total_power = troops_power + spells_power + heroes_power
    
    
    return total_power



