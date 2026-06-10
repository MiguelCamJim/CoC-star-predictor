"""
Script simple de Python para buscar ataques específicos en un archivo de ataques recientes de Clash of Clans.
En este caso, busca ataques donde un TH16 atacó a un TH12, pero se puede modificar fácilmente para otras combinaciones de TH.
Este fichero es principalmente de prueba y análisis, no forma parte del planificador de guerras ni del modelo de predicción, pero puede ser útil para entender mejor los datos de ataques recientes.
"""
import json
import os

def find_attacks_th16_vs_th12(input_file):
    """
    Busca y muestra ataques donde TH16 atacó a TH12
    """
    
    if not os.path.exists(input_file):
        print(f"❌ El archivo {input_file} no existe")
        return
    
    th16_vs_th12_attacks = []
    total_lines = 0
    
    print("🔍 Buscando ataques TH16 vs TH12...")
    print("=" * 60)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            total_lines += 1
            line = line.strip()
            if not line:
                continue
            
            try:
                attack = json.loads(line)
                
                # Verificar si es TH16 vs TH12
                attacker_th = attack.get('attacker_th')
                defender_th = attack.get('defender_th')
                
                if attacker_th == 10 and defender_th == 16:
                    th16_vs_th12_attacks.append({
                        'line_num': line_num,
                        'attack': attack
                    })
                    
            except json.JSONDecodeError as e:
                print(f"Error en línea {line_num}: {e}")
                continue
            except Exception as e:
                print(f"Error inesperado en línea {line_num}: {e}")
                continue
    
    # Mostrar resultados
    print(f"RESULTADOS:")
    print(f"   - Total líneas procesadas: {total_lines}")
    print(f"   - Ataques TH16 vs TH12 encontrados: {len(th16_vs_th12_attacks)}")
    print("=" * 60)
    
    if th16_vs_th12_attacks:
        print("\nATAQUES TH16 vs TH12 ENCONTRADOS:")
        print("-" * 100)
        
        for i, entry in enumerate(th16_vs_th12_attacks, 1):
            attack = entry['attack']
            line_num = entry['line_num']
            
            print(f"\nAtaque #{i} (Línea {line_num}):")
            print(f"   Atacante: {attack.get('attacker_name', 'N/A')} (TH{attack.get('attacker_th')}) - Pos #{attack.get('attacker_map_pos', 'N/A')}")
            print(f"   Defensor: {attack.get('defender_name', 'N/A')} (TH{attack.get('defender_th')}) - Pos #{attack.get('defender_map_pos', 'N/A')}")
            print(f"   Resultado: {attack.get('stars', 'N/A')} estrellas - {attack.get('destruction', 'N/A')}% destrucción")
            print(f"   Guerra: {attack.get('team_size', 'N/A')}v{attack.get('team_size', 'N/A')} ({attack.get('war_type', 'N/A')})")
            print(f"   Orden: #{attack.get('order', 'N/A')} - {attack.get('timestamp', 'N/A')[:10]}")
            
            # Mostrar datos adicionales si existen
            if 'attacker_offensive_power' in attack:
                print(f"   Poder ofensivo atacante: {attack.get('attacker_offensive_power', 'N/A')}")
            if 'defender_defensive_power' in attack:
                print(f"   Poder defensivo defensor: {attack.get('defender_defensive_power', 'N/A')}")
        
        # Estadísticas de estrellas
        stars_distribution = {}
        destruction_total = 0
        destruction_count = 0
        
        for entry in th16_vs_th12_attacks:
            attack = entry['attack']
            stars = attack.get('stars', 0)
            destruction = attack.get('destruction', 0)
            
            if stars in stars_distribution:
                stars_distribution[stars] += 1
            else:
                stars_distribution[stars] = 1
            
            if destruction is not None and destruction > 0:
                destruction_total += destruction
                destruction_count += 1
        
        print(f"\nESTADÍSTICAS:")
        print("-" * 40)
        
        for stars in sorted(stars_distribution.keys()):
            count = stars_distribution[stars]
            percentage = (count / len(th16_vs_th12_attacks)) * 100
            print(f"   {stars} estrellas: {count} ataques ({percentage:.1f}%)")
        
        if destruction_count > 0:
            avg_destruction = destruction_total / destruction_count
            print(f"   Destrucción promedio: {avg_destruction:.1f}%")
        
    else:
        print("\nNo se encontraron ataques TH16 vs TH12")
        
        # Mostrar qué niveles de TH sí existen para referencia
        th_combinations = {}
        
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        attack = json.loads(line)
                        attacker_th = attack.get('attacker_th')
                        defender_th = attack.get('defender_th')
                        
                        if attacker_th and defender_th:
                            combo = f"TH{attacker_th} vs TH{defender_th}"
                            th_combinations[combo] = th_combinations.get(combo, 0) + 1
                    except:
                        continue
        
        print(f"\nCombinaciones de TH más comunes en tus datos:")
        sorted_combinations = sorted(th_combinations.items(), key=lambda x: x[1], reverse=True)
        
        for i, (combo, count) in enumerate(sorted_combinations[:10], 1):
            print(f"   {i:2d}. {combo}: {count} ataques")

def search_attacks_by_th(input_file, attacker_th=None, defender_th=None):
    """
    Función más general para buscar por cualquier combinación de TH
    """
    if not os.path.exists(input_file):
        print(f"❌ El archivo {input_file} no existe")
        return
    
    attacks_found = []
    
    search_desc = ""
    if attacker_th and defender_th:
        search_desc = f"TH{attacker_th} vs TH{defender_th}"
    elif attacker_th:
        search_desc = f"TH{attacker_th} atacando a cualquier TH"
    elif defender_th:
        search_desc = f"Cualquier TH atacando a TH{defender_th}"
    
    print(f"Buscando ataques: {search_desc}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    attack = json.loads(line)
                    
                    match = True
                    if attacker_th and attack.get('attacker_th') != attacker_th:
                        match = False
                    if defender_th and attack.get('defender_th') != defender_th:
                        match = False
                    
                    if match:
                        attacks_found.append({'line_num': line_num, 'attack': attack})
                        
                except:
                    continue
    
    print(f"Encontrados {len(attacks_found)} ataques")
    
    return attacks_found

if __name__ == "__main__":
    # Buscar específicamente TH16 vs TH12
    input_file = "ataques_recientes.jsonl"
    
    print("Script para buscar ataques TH16 vs TH12")
    print("=" * 50)
    
    find_attacks_th16_vs_th12(input_file)
    
    print(f"\n" + "="*50)
    print("Búsqueda completada")
