"""
Script que recopila ataques recientes de guerras de clanes activos.
Los ataques se borran de la base de datos de CoC regularmente, así que, si se quiere recopilar muchos datos, hay que ejecutar el script frecuentemente para no perder ataques.
"""

import requests
import json
import time
from datetime import datetime
from stats import calculate_offensive_power

class AttackCollector:
    def __init__(self, token, output_file="ataques_recientes.jsonl"):
        self.api_token = token
        self.output_file = output_file
        self.base_url = "https://api.clashofclans.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json"
        }
        # Mantener registro de clanes ya procesados
        self.processed_clans = set()
        self.last_cursors = {}  # Guardar cursores por ubicación

    def get_clans_unified(self, max_pages_per_location=50):
        """Método unificado: agota cada ubicación antes de pasar a la siguiente"""
        all_tags = set()
        
        # Ubicaciones ordenadas por prioridad
        locations = [
            

            # Europa
            
            ("32000014", "Rusia"),
            ("32000025", "Polonia"),
            ("32000031", "Rumanía"),
            ("32000033", "Suecia"),
            ("32000034", "Suiza"),
            ("32000037", "Ucrania"),
            ("32000017", "Países Bajos"),
            ("32000015", "Noruega"),
            ("32000016", "Portugal"),
            ("32000032", "Grecia"),
            ("32000035", "República Checa"),
            ("32000249", "España"),
            ("32000008", "Reino Unido"),
            ("32000009", "Francia"),
            ("32000010", "Alemania"),
            ("32000011", "Italia"),

            # Brasil separado porque es gigante
            ("32000021", "Brasil"),

            # América Latina
            ("32000022", "México"),
            ("32000027", "Colombia"),
            ("32000024", "Argentina"),
            ("32000023", "Perú"),
            ("32000029", "Chile"),
            ("32000020", "Venezuela"),
            ("32000165", "Latinoamérica"),

            

            # Asia
            ("32000110", "Filipinas"),
            ("32000019", "Malasia"),
            ("32000018", "Bangladesh"),
            ("32000036", "Pakistán"),
            ("32000028", "Nepal"),
            ("32000030", "Singapur"),
            ("32000026", "Sri Lanka"),
            ("32000039", "Vietnam"),
            ("32000040", "Tailandia"),
            ("32000041", "Afganistán"),

            # India
            ("32000023", "India"),

            # Otros grandes
            ("32000007", "Estados Unidos"),
            ("32000012", "Canadá"),
            ("32000006", "Australia"),
            ("32000013", "Nueva Zelanda"),

            # Global
            ("32000000", "Global")
        ]
        
        for location_id, name in locations:
            print(f"\n=== Procesando {name} ({location_id}) ===")
            
            # Usar cursor guardado si existe para esta ubicación
            after = self.last_cursors.get(location_id)
            location_new_clans = 0
            pages_processed = 0
            
            # Procesar páginas hasta alcanzar límite por ubicación (máximo 15 clanes)
            while pages_processed < max_pages_per_location:
                params = {
                    "locationId": location_id,
                    "limit": 50,
                    "minMembers": 45,
                    "minClanPoints": 30000
                }
                if after:
                    params["after"] = after

                res = requests.get(f"{self.base_url}/clans", headers=self.headers, params=params)
                
                print(f"{name} página {pages_processed + 1}: Status {res.status_code}")
                
                if res.status_code != 200:
                    print(f"Error en {name}: {res.status_code}")
                    break

                data = res.json()
                clans = data.get("items", [])
                
                if not clans:
                    print(f"No más clanes en {name}")
                    break

                page_new_clans = 0
                for clan in clans:
                    
                        
                    tag = clan.get("tag")
                    if (tag and 
                        tag not in self.processed_clans and 
                        clan.get("warFrequency", "") == "always"):
                        all_tags.add(tag)
                        self.processed_clans.add(tag)
                        page_new_clans += 1
                        location_new_clans += 1

                print(f"   {len(clans)} clanes en página, {page_new_clans} nuevos ({location_new_clans})")
                
                # Actualizar cursor para la siguiente página
                paging = data.get("paging", {})
                cursors = paging.get("cursors", {})
                after = cursors.get("after")
                
                # Guardar cursor para futuras búsquedas
                if after:
                    self.last_cursors[location_id] = after
                else:
                    print(f"🏁 {name} completamente procesado")
                    # Limpiar cursor si ya no hay más páginas
                    if location_id in self.last_cursors:
                        del self.last_cursors[location_id]
                    break
                
                pages_processed += 1
                time.sleep(0.5)
            
            print(f"{name}: {location_new_clans} clanes nuevos en {pages_processed} páginas")
            
            # Si encontramos suficientes clanes de esta ubicación, pasar a la siguiente
            if location_new_clans >= 15:  # Límite alcanzado para esta ubicación
                print(f"Límite de {name} alcanzado con {location_new_clans} clanes, pasando a la siguiente")
            
            # Si ya tenemos muchos clanes en total, parar
            if len(all_tags) >= 100:  # Límite total
                print(f"Límite total alcanzado con {len(all_tags)} clanes")
                break
        
        print(f"\nTotal clanes únicos encontrados: {len(all_tags)}")
        print(f"Total clanes procesados historicamente: {len(self.processed_clans)}")
        return list(all_tags)

    def get_current_war(self, clan_tag):
        tag = clan_tag.replace("#", "%23")
        url = f"{self.base_url}/clans/{tag}/currentwar"
        res = requests.get(url, headers=self.headers)
        if res.status_code == 200:
            return res.json()
        return None

    def extraer_ataques(self, war):
        if war["state"] != "inWar":
            return []

        ataques = []
        miembros_clan = {m["tag"]: m for m in war["clan"]["members"]}
        miembros_rival = {m["tag"]: m for m in war["opponent"]["members"]}
        
        # Determinar tipo de guerra
        war_type = "cwl" if war.get("warType") == "cwl" else "normal"

        for side, miembros, defensores in [
            ("clan", war["clan"]["members"], miembros_rival),
            ("opponent", war["opponent"]["members"], miembros_clan)
        ]:
            for atacante in miembros:
                for atk in atacante.get("attacks", []):
                    defensor = defensores.get(atk["defenderTag"], {})
                    offensive_power = calculate_offensive_power(atacante["tag"], self.api_token)
                    copas_at = atacante.get("trophies", 0)
                    copas_def = defensor.get("trophies", 0)
                    entrada = {
                        "attacker_name": atacante["name"],
                        "attacker_tag": atacante["tag"],
                        "attacker_th": atacante.get("townhallLevel"),
                        "attacker_map_pos": atacante.get("mapPosition"),
                        "attacker_trophies": copas_at,
                        "attacker_offensive_power": offensive_power,
                        "defender_name": defensor.get("name", "Desconocido"),
                        "defender_tag": atk["defenderTag"],
                        "defender_th": defensor.get("townhallLevel"),
                        "defender_map_pos": defensor.get("mapPosition"),
                        "defender_trophies": copas_def,
                        "stars": atk["stars"],
                        "destruction": atk["destructionPercentage"],
                        "order": atk["order"],
                        "team_size": war["teamSize"],
                        "clan_tag": war["clan"]["tag"],
                        "opponent_tag": war["opponent"]["tag"],
                        "war_type": war_type
                    }
                    ataques.append(entrada)
        return ataques

    def guardar_ataques(self, ataques):
        with open(self.output_file, "a", encoding="utf-8") as f:
            for atk in ataques:
                f.write(json.dumps(atk) + "\n")

    def run(self, iteraciones=5, max_pages_per_location=10, espera=1.2, max_clanes_por_iteracion = 10000):
        total_guardados = 0
        
        for i in range(iteraciones):
            print(f"\n=== ITERACIÓN {i+1}/{iteraciones} ===")
            
            # Usar el método unificado con límites más bajos para diversidad
            clan_tags = self.get_clans_unified(max_pages_per_location=max_pages_per_location)
            
            if not clan_tags:
                print("No se encontraron clanes nuevos. Fin del programa.")
                break
            
            # Limitar el número de clanes a procesar por iteración
            if len(clan_tags) > max_clanes_por_iteracion:
                clan_tags = clan_tags[:max_clanes_por_iteracion]
                print(f"Limitando a {max_clanes_por_iteracion} clanes por velocidad")
            
            print(f"\nProcesando {len(clan_tags)} clanes nuevos encontrados")

            wars_found = 0
            ataques_esta_iteracion = 0
            clanes_procesados = 0
            
            for i, tag in enumerate(clan_tags):
                try:
                    clanes_procesados += 1
                    
                    # Mostrar progreso cada 10 clanes
                    if clanes_procesados % 10 == 0:
                        print(f"Progreso: {clanes_procesados}/{len(clan_tags)} clanes ({wars_found} guerras encontradas)")
                    
                    war = self.get_current_war(tag)
                    if war and (war["state"] == "inWar" or war["state"] == "warEnded"):
                        wars_found += 1
                        ataques = self.extraer_ataques(war)
                        if ataques:
                            self.guardar_ataques(ataques)
                            ataques_esta_iteracion += len(ataques)
                            print(f"{len(ataques)} ataques guardados del clan {tag} (Guerra {wars_found})")
                            total_guardados += len(ataques)
                        else:
                            print(f"Guerra sin ataques en {tag}")
                    else:
                        # Solo mostrar cada 20 clanes sin guerra para no saturar
                        if clanes_procesados % 20 == 0:
                            print(f"{tag}: Sin guerra activa")
                    
                    # Reducir tiempo de espera para acelerar
                    time.sleep(espera * 0.5)  # Espera reducida a la mitad
                    
                except Exception as e:
                    print(f"Error con clan {tag}: {e}")
                    # Continuar sin esperar en caso de error
                    continue
            
            print(f"\nResumen iteración {i+1}:")
            print(f"   Clanes procesados: {clanes_procesados}")
            print(f"   Guerras encontradas: {wars_found}")
            print(f"   Ataques en esta iteración: {ataques_esta_iteracion}")
            print(f"   Tiempo estimado: {clanes_procesados * espera * 0.5:.1f} segundos")
            
        print(f"\n=== RESUMEN FINAL ===")
        print(f"Total ataques guardados: {total_guardados}")
        print(f"Total clanes únicos procesados: {len(self.processed_clans)}")
        print(f"Ubicaciones con cursores guardados: {list(self.last_cursors.keys())}")
        


    def save_attacks_from_clan(self, clan_tag, file):
        # Guardamos los ataques de la guerra actual del clan dado
        war = self.get_current_war(clan_tag)
        if war and (war["state"] == "inWar" or war["state"] == "warEnded"):
            ataques = self.extraer_ataques(war)
            if ataques:
                with open(file, "a", encoding="utf-8") as f:
                    for atk in ataques:
                        f.write(json.dumps(atk) + "\n")
                print(f"{len(ataques)} ataques guardados del clan {clan_tag}")
            else:
                print(f"Guerra sin ataques en {clan_tag}")
        else:
            print(f"{clan_tag}: Sin guerra activa")


    
if __name__ == "__main__":
    TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6ImIyMzVjN2VhLTQyZmItNGJkYy05ZmNjLTk3NTY2ZDJlMTEwYSIsImlhdCI6MTc1NTMzMzI3Nywic3ViIjoiZGV2ZWxvcGVyL2EzMDM4ZTcwLTM3ZWMtNzExMi1jZDI1LTVlMGMzZmQwMDUyZiIsInNjb3BlcyI6WyJjbGFzaCJdLCJsaW1pdHMiOlt7InRpZXIiOiJkZXZlbG9wZXIvc2lsdmVyIiwidHlwZSI6InRocm90dGxpbmcifSx7ImNpZHJzIjpbIjk1LjEyMy4xNTAuNjkiXSwidHlwZSI6ImNsaWVudCJ9XX0.KFxwLRVDowJjQ5ia3-xGYK6lxk93ev1gbZgqJr8n_D8N8-QQdoz6gSIvj_GMIRYojx-16MmzJmvpjZhqOI4zjg"
    
    collector = AttackCollector(TOKEN)
    collector.run(iteraciones=5, max_pages_per_location=10, espera=1.2, max_clanes_por_iteracion=10000)



    

    
