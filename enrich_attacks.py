"""
Enriquecimiento de ataques con poderes ofensivos y defensivos
"""

import json
import requests
import time
import os
from datetime import datetime
from stats import calculate_offensive_power, calculate_defensive_power

class AttackEnricher:
    def __init__(self, api_token, input_file="ataques_recientes.jsonl", output_file=None):
        self.api_token = api_token
        self.input_file = input_file
        self.output_file = output_file or f"ataques_enriquecidos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        
        # Cache para evitar llamadas repetidas a la API
        self.offensive_cache = {}
        self.defensive_cache = {}
        self.clan_members_cache = {}  # Cache para miembros de clanes
        self.player_tag_cache = {}    # Cache para mapear nombre -> tag
        
        # Contadores
        self.processed_attacks = 0
        self.enriched_attacks = 0
        self.api_calls = 0
        self.cache_hits = 0
        self.tags_resolved = 0

    def get_offensive_power_cached(self, player_tag):
        """
        Obtiene poder ofensivo con cache para evitar llamadas repetidas
        """
        if player_tag in self.offensive_cache:
            self.cache_hits += 1
            return self.offensive_cache[player_tag]
        
        print(f"Obteniendo poder ofensivo de {player_tag}...")
        self.api_calls += 1
        
        try:
            power = calculate_offensive_power(player_tag, self.api_token)
            self.offensive_cache[player_tag] = power
            time.sleep(0.1)  # Pequeña pausa para no saturar la API
            return power
        except Exception as e:
            print(f"Error obteniendo poder ofensivo de {player_tag}: {e}")
            return None

    def get_defensive_power_cached(self, player_tag):
        """
        Obtiene poder defensivo con cache para evitar llamadas repetidas
        """
        if player_tag in self.defensive_cache:
            self.cache_hits += 1
            return self.defensive_cache[player_tag]
        
        print(f"Obteniendo poder defensivo de {player_tag}...")
        self.api_calls += 1
        
        try:
            power = calculate_defensive_power(player_tag, self.api_token)
            self.defensive_cache[player_tag] = power
            time.sleep(0.1)  # Pequeña pausa para no saturar la API
            return power
        except Exception as e:
            print(f"Error obteniendo poder defensivo de {player_tag}: {e}")
            return None

    def get_clan_members(self, clan_tag):
        """
        Obtiene los miembros de un clan y cachea el resultado
        """
        if clan_tag in self.clan_members_cache:
            self.cache_hits += 1
            return self.clan_members_cache[clan_tag]
        
        print(f"Obteniendo miembros del clan {clan_tag}...")
        self.api_calls += 1
        
        try:
            # Formatear tag del clan correctamente
            # Quitar # si existe y usar URL encoding apropiado
            clean_tag = clan_tag.replace('#', '') if clan_tag.startswith('#') else clan_tag
            formatted_tag = f"%23{clean_tag}"
            
            url = f"https://api.clashofclans.com/v1/clans/{formatted_tag}/members"
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Accept': 'application/json'
            }
            
            print(f"   URL: {url}")  # Debug: mostrar URL
            
            response = requests.get(url, headers=headers)
            
            print(f"   Status: {response.status_code}")  # Debug: mostrar status
            
            if response.status_code == 200:
                data = response.json()
                members = {}
                for member in data.get('items', []):
                    members[member['name']] = member['tag']
                
                print(f"   Encontrados {len(members)} miembros")
                self.clan_members_cache[clan_tag] = members
                time.sleep(0.1)  # Pequeña pausa para no saturar la API
                return members
            else:
                print(f"   Error API clan {clan_tag}: {response.status_code}")
                if response.status_code == 403:
                    print(f"   📄 Respuesta: {response.text}")
                return {}
                
        except Exception as e:
            print(f"Error obteniendo miembros del clan {clan_tag}: {e}")
            return {}

    def resolve_player_tag(self, player_name, clan_tag, fallback_clan_tag=None):
        """
        Resuelve el tag de un jugador usando su nombre y el tag de su clan
        Si no lo encuentra, puede buscar en un clan alternativo
        """
        cache_key = f"{player_name}@{clan_tag}"
        
        if cache_key in self.player_tag_cache:
            self.cache_hits += 1
            return self.player_tag_cache[cache_key]
        
        # Obtener miembros del clan principal
        clan_members = self.get_clan_members(clan_tag)
        
        # Buscar el jugador por nombre en el clan principal
        player_tag = clan_members.get(player_name)
        
        if player_tag:
            self.player_tag_cache[cache_key] = player_tag
            self.tags_resolved += 1
            print(f"Tag resuelto: {player_name} -> {player_tag} (clan {clan_tag})")
            return player_tag
        
        # Si no se encontró y hay un clan alternativo, buscar ahí
        if fallback_clan_tag and fallback_clan_tag != clan_tag:
            fallback_members = self.get_clan_members(fallback_clan_tag)
            player_tag = fallback_members.get(player_name)
            
            if player_tag:
                self.player_tag_cache[cache_key] = player_tag
                self.tags_resolved += 1
                print(f"Tag resuelto: {player_name} -> {player_tag} (clan alternativo {fallback_clan_tag})")
                return player_tag
        
        # No se encontró en ningún clan
        self.player_tag_cache[cache_key] = None
        print(f"No se encontró tag para: {player_name} en clan {clan_tag}" + 
              (f" ni en {fallback_clan_tag}" if fallback_clan_tag else ""))
        
        return None

    def test_api_connection(self):
        """
        Prueba la conexión a la API con un clan conocido
        """
        print("Probando conexión con la API...")
        
        # Usar el primer clan que encontremos en los datos
        test_clan_tag = None
        
        if os.path.exists(self.input_file):
            with open(self.input_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            attack = json.loads(line)
                            test_clan_tag = attack.get('clan_tag')
                            if test_clan_tag:
                                break
                        except:
                            continue
        
        if not test_clan_tag:
            print("No se encontró ningún clan para probar")
            return False
        
        print(f"🔍 Probando con clan: {test_clan_tag}")
        
        # Probar obtener miembros
        members = self.get_clan_members(test_clan_tag)
        
        if members:
            print(f"API funcionando correctamente")
            print(f"   Clan: {test_clan_tag}")
            print(f"   Miembros encontrados: {len(members)}")
            if members:
                sample_member = list(members.items())[0]
                print(f"   Ejemplo: {sample_member[0]} -> {sample_member[1]}")
            return True
        else:
            print(f"Error al conectar con la API")
            return False

    def enrich_attacks(self, max_attacks=None, skip_existing=True):
        """
        Enriquece los ataques con poder ofensivo y defensivo
        """
        if not os.path.exists(self.input_file):
            print(f"El archivo {self.input_file} no existe")
            return

        print(f"Iniciando enriquecimiento de ataques")
        print(f"Archivo entrada: {self.input_file}")
        print(f"Archivo salida: {self.output_file}")
        print("=" * 60)

        unique_attackers = set()
        unique_defenders = set()
        missing_attacker_tags = set()
        missing_defender_tags = set()
        
        # Primera pasada: contar jugadores únicos y tags faltantes
        with open(self.input_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        attack = json.loads(line)
                        
                        # Contar atacantes
                        if attack.get('attacker_tag'):
                            unique_attackers.add(attack['attacker_tag'])
                        elif attack.get('attacker_name') and attack.get('clan_tag'):
                            missing_attacker_tags.add((attack['attacker_name'], attack['clan_tag']))
                        
                        # Contar defensores
                        if attack.get('defender_tag'):
                            unique_defenders.add(attack['defender_tag'])
                        elif attack.get('defender_name') and attack.get('opponent_tag'):
                            missing_defender_tags.add((attack['defender_name'], attack['opponent_tag']))
                            
                    except:
                        continue
        
        print(f"Estadísticas previas:")
        print(f"   - Atacantes con tag: {len(unique_attackers)}")
        print(f"   - Defensores con tag: {len(unique_defenders)}")
        print(f"   - Atacantes sin tag (a resolver): {len(missing_attacker_tags)}")
        print(f"   - Defensores sin tag (a resolver): {len(missing_defender_tags)}")
        
        # Calcular clanes únicos para estimar llamadas API
        clanes_atacantes = set(clan_tag for _, clan_tag in missing_attacker_tags)
        clanes_defensores = set(clan_tag for _, clan_tag in missing_defender_tags)
        total_clanes_unicos = len(clanes_atacantes | clanes_defensores)
        
        print(f"   - Clanes únicos a consultar: {total_clanes_unicos}")
        print(f"   - Total jugadores únicos: {len(unique_attackers | unique_defenders) + len(missing_attacker_tags) + len(missing_defender_tags)}")
        print(f"   - Llamadas API estimadas: {total_clanes_unicos + len(unique_attackers | unique_defenders) + len(missing_attacker_tags) + len(missing_defender_tags)}")
        print()

        # Segunda pasada: enriquecer ataques
        with open(self.input_file, 'r', encoding='utf-8') as f_in:
            with open(self.output_file, 'w', encoding='utf-8') as f_out:
                
                for line_num, line in enumerate(f_in, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        attack = json.loads(line)
                        self.processed_attacks += 1
                        
                        # Verificar si ya tiene los campos (skip_existing)
                        has_offensive = 'attacker_offensive_power' in attack
                        has_defensive = 'defender_defensive_power' in attack
                        
                        if skip_existing and has_offensive and has_defensive:
                            # Ya está enriquecido, escribir tal como está
                            f_out.write(json.dumps(attack) + '\n')
                            continue
                        
                        # Mostrar progreso cada 10 ataques
                        if self.processed_attacks % 10 == 0:
                            print(f"Procesando ataque {self.processed_attacks}...")
                            print(f"   API calls: {self.api_calls}, Cache hits: {self.cache_hits}, Tags resueltos: {self.tags_resolved}")
                        
                        # Resolver tags de jugadores si faltan
                        attacker_tag = attack.get('attacker_tag')
                        defender_tag = attack.get('defender_tag')
                        
                        # Resolver tag del atacante si falta
                        if not attacker_tag and attack.get('attacker_name') and attack.get('clan_tag'):
                            # Intentar primero en el clan propio, luego en el clan oponente como fallback
                            attacker_tag = self.resolve_player_tag(
                                attack['attacker_name'], 
                                attack['clan_tag'], 
                                attack.get('opponent_tag')
                            )
                            if attacker_tag:
                                attack['attacker_tag'] = attacker_tag
                        
                        # Resolver tag del defensor si falta
                        if not defender_tag and attack.get('defender_name') and attack.get('opponent_tag'):
                            # Intentar primero en el clan oponente, luego en el clan propio como fallback
                            defender_tag = self.resolve_player_tag(
                                attack['defender_name'], 
                                attack['opponent_tag'], 
                                attack.get('clan_tag')
                            )
                            if defender_tag:
                                attack['defender_tag'] = defender_tag
                        
                        # Obtener poder ofensivo del atacante
                        if attacker_tag and not has_offensive:
                            offensive_power = self.get_offensive_power_cached(attacker_tag)
                            if offensive_power is not None:
                                attack['attacker_offensive_power'] = round(offensive_power, 1)
                        
                        # Obtener poder defensivo del defensor
                        if defender_tag and not has_defensive:
                            defensive_power = self.get_defensive_power_cached(defender_tag)
                            if defensive_power is not None:
                                attack['defender_defensive_power'] = round(defensive_power, 1)
                        
                        # Verificar si se enriqueció
                        if ('attacker_offensive_power' in attack or 'defender_defensive_power' in attack):
                            self.enriched_attacks += 1
                        
                        # Escribir ataque (enriquecido o no)
                        f_out.write(json.dumps(attack) + '\n')
                        
                        # Límite opcional
                        if max_attacks and self.processed_attacks >= max_attacks:
                            print(f"Límite alcanzado: {max_attacks} ataques")
                            break
                            
                    except json.JSONDecodeError as e:
                        print(f"Error JSON en línea {line_num}: {e}")
                        continue
                    except Exception as e:
                        print(f"Error procesando línea {line_num}: {e}")
                        continue

        # Resumen final
        self.print_summary()

    def print_summary(self):
        """
        Imprime resumen del enriquecimiento
        """
        print(f"\nENRIQUECIMIENTO COMPLETADO")
        print("=" * 60)
        print(f"Estadísticas finales:")
        print(f"   - Ataques procesados: {self.processed_attacks}")
        print(f"   - Ataques enriquecidos: {self.enriched_attacks}")
        print(f"   - Llamadas a API: {self.api_calls}")
        print(f"   - Cache hits: {self.cache_hits}")
        print(f"   - Tags de jugadores resueltos: {self.tags_resolved}")
        print(f"   - Jugadores en cache ofensivo: {len(self.offensive_cache)}")
        print(f"   - Jugadores en cache defensivo: {len(self.defensive_cache)}")
        print(f"   - Clanes en cache: {len(self.clan_members_cache)}")
        print(f"Archivo enriquecido guardado en: {self.output_file}")

    def analyze_power_distribution(self):
        """
        Analiza la distribución de poderes en el archivo enriquecido
        """
        if not os.path.exists(self.output_file):
            print(f"El archivo {self.output_file} no existe")
            return

        offensive_powers = []
        defensive_powers = []
        
        with open(self.output_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        attack = json.loads(line)
                        
                        if 'attacker_offensive_power' in attack:
                            offensive_powers.append(attack['attacker_offensive_power'])
                        
                        if 'defender_defensive_power' in attack:
                            defensive_powers.append(attack['defender_defensive_power'])
                            
                    except:
                        continue

        if offensive_powers:
            print(f"\nANÁLISIS PODER OFENSIVO:")
            print(f"   - Mínimo: {min(offensive_powers):.1f}")
            print(f"   - Máximo: {max(offensive_powers):.1f}")
            print(f"   - Promedio: {sum(offensive_powers)/len(offensive_powers):.1f}")
            print(f"   - Ataques con poder ofensivo: {len(offensive_powers)}")

        if defensive_powers:
            print(f"\nANÁLISIS PODER DEFENSIVO:")
            print(f"   - Mínimo: {min(defensive_powers):.1f}")
            print(f"   - Máximo: {max(defensive_powers):.1f}")
            print(f"   - Promedio: {sum(defensive_powers)/len(defensive_powers):.1f}")
            print(f"   - Ataques con poder defensivo: {len(defensive_powers)}")

    def analyze_missing_tags(self):
        """
        Analiza cuántos registros necesitan resolución de tags
        """
        if not os.path.exists(self.input_file):
            print(f"El archivo {self.input_file} no existe")
            return

        missing_attacker_tags = 0
        missing_defender_tags = 0
        total_attacks = 0
        
        with open(self.input_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        attack = json.loads(line)
                        total_attacks += 1
                        
                        if not attack.get('attacker_tag'):
                            missing_attacker_tags += 1
                        
                        if not attack.get('defender_tag'):
                            missing_defender_tags += 1
                            
                    except:
                        continue

        print(f"\nANÁLISIS DE TAGS FALTANTES:")
        print(f"   - Total ataques: {total_attacks}")
        print(f"   - Ataques sin tag de atacante: {missing_attacker_tags} ({missing_attacker_tags/total_attacks*100:.1f}%)")
        print(f"   - Ataques sin tag de defensor: {missing_defender_tags} ({missing_defender_tags/total_attacks*100:.1f}%)")
        print(f"   - Ataques que necesitan resolución: {max(missing_attacker_tags, missing_defender_tags)}")

        return missing_attacker_tags, missing_defender_tags

    def debug_specific_attacks(self):
        """
        Debug para revisar ataques específicos mencionados por el usuario
        """
        print("\nDEBUG - ANALIZANDO ATAQUES ESPECÍFICOS:")
        print("=" * 60)
        
        target_players = ['tony', 'ALE', 'barnzy', 'Filthy McNasty', 'Lurkan']
        target_clans = ['#2QVPCPU8R', '#2GPGGRU9Y']
        
        found_attacks = []
        
        if not os.path.exists(self.input_file):
            print(f"El archivo {self.input_file} no existe")
            return
        
        # Buscar ataques específicos
        with open(self.input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        attack = json.loads(line)
                        attacker = attack.get('attacker_name', '')
                        defender = attack.get('defender_name', '')
                        
                        if (attacker in target_players or defender in target_players):
                            found_attacks.append((line_num, attack))
                            
                    except:
                        continue
        
        print(f"Encontrados {len(found_attacks)} ataques relacionados:")
        print()
        
        for line_num, attack in found_attacks:
            print(f"Línea {line_num}:")
            print(f"   Atacante: {attack.get('attacker_name')} (clan: {attack.get('clan_tag')})")
            print(f"   Defensor: {attack.get('defender_name')} (clan: {attack.get('opponent_tag')})")
            print()
        
        # Ahora probar buscar estos jugadores en los clanes
        print("PROBANDO BÚSQUEDA EN CLANES:")
        print()
        
        for clan_tag in target_clans:
            print(f"Clan {clan_tag}:")
            members = self.get_clan_members(clan_tag)
            
            found_targets = []
            for player in target_players:
                if player in members:
                    found_targets.append(f"{player} -> {members[player]}")
            
            if found_targets:
                print(f"   Encontrados: {', '.join(found_targets)}")
            else:
                print(f"   Ninguno de los jugadores objetivo encontrado")
            print()

        return found_attacks

    def resolve_tags_only(self, max_attacks=None, skip_existing=True):
        """
        Solo resuelve los tags de jugadores, sin calcular poderes
        """
        if not os.path.exists(self.input_file):
            print(f"El archivo {self.input_file} no existe")
            return

        # Crear nombre de archivo específico para tags
        tags_output_file = f"ataques_con_tags_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

        print(f"Iniciando resolución de tags únicamente")
        print(f"Archivo entrada: {self.input_file}")
        print(f"Archivo salida: {tags_output_file}")
        print("=" * 60)

        # Análisis previo más simple para tags
        missing_attacker_tags = 0
        missing_defender_tags = 0
        total_attacks = 0
        
        with open(self.input_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        attack = json.loads(line)
                        total_attacks += 1
                        if not attack.get('attacker_tag'):
                            missing_attacker_tags += 1
                        if not attack.get('defender_tag'):
                            missing_defender_tags += 1
                    except:
                        continue
        
        print(f"Estadísticas previas:")
        print(f"   - Total ataques: {total_attacks}")
        print(f"   - Ataques sin tag de atacante: {missing_attacker_tags}")
        print(f"   - Ataques sin tag de defensor: {missing_defender_tags}")
        print()

        # Procesamiento
        with open(self.input_file, 'r', encoding='utf-8') as f_in:
            with open(tags_output_file, 'w', encoding='utf-8') as f_out:
                
                for line_num, line in enumerate(f_in, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        attack = json.loads(line)
                        self.processed_attacks += 1
                        
                        # Verificar si ya tiene los tags (skip_existing)
                        has_attacker_tag = attack.get('attacker_tag') is not None
                        has_defender_tag = attack.get('defender_tag') is not None
                        
                        if skip_existing and has_attacker_tag and has_defender_tag:
                            # Ya tiene ambos tags, escribir tal como está
                            f_out.write(json.dumps(attack) + '\n')
                            continue
                        
                        # Mostrar progreso cada 10 ataques
                        if self.processed_attacks % 10 == 0:
                            print(f"Procesando ataque {self.processed_attacks}...")
                            print(f"   API calls: {self.api_calls}, Cache hits: {self.cache_hits}, Tags resueltos: {self.tags_resolved}")
                        
                        # Resolver tags de jugadores si faltan
                        attacker_tag = attack.get('attacker_tag')
                        defender_tag = attack.get('defender_tag')
                        
                        # Resolver tag del atacante si falta
                        if not attacker_tag and attack.get('attacker_name') and attack.get('clan_tag'):
                            attacker_tag = self.resolve_player_tag(
                                attack['attacker_name'], 
                                attack['clan_tag'], 
                                attack.get('opponent_tag')
                            )
                            if attacker_tag:
                                attack['attacker_tag'] = attacker_tag
                        
                        # Resolver tag del defensor si falta
                        if not defender_tag and attack.get('defender_name') and attack.get('opponent_tag'):
                            defender_tag = self.resolve_player_tag(
                                attack['defender_name'], 
                                attack['opponent_tag'], 
                                attack.get('clan_tag')
                            )
                            if defender_tag:
                                attack['defender_tag'] = defender_tag
                        
                        # Contar como enriquecido si se añadió algún tag
                        if attacker_tag or defender_tag:
                            self.enriched_attacks += 1
                        
                        # Escribir ataque (con tags resueltos o no)
                        f_out.write(json.dumps(attack) + '\n')
                        
                        # Límite opcional
                        if max_attacks and self.processed_attacks >= max_attacks:
                            print(f"Límite alcanzado: {max_attacks} ataques")
                            break
                            
                    except json.JSONDecodeError as e:
                        print(f"Error JSON en línea {line_num}: {e}")
                        continue
                    except Exception as e:
                        print(f"Error procesando línea {line_num}: {e}")
                        continue

        # Resumen final
        self.print_tags_summary(tags_output_file)

    def print_tags_summary(self, output_file):
        """
        Imprime resumen de la resolución de tags
        """
        print(f"\nRESOLUCIÓN DE TAGS COMPLETADA")
        print("=" * 60)
        print(f"Estadísticas finales:")
        print(f"   - Ataques procesados: {self.processed_attacks}")
        print(f"   - Ataques con tags añadidos: {self.enriched_attacks}")
        print(f"   - Llamadas a API: {self.api_calls}")
        print(f"   - Cache hits: {self.cache_hits}")
        print(f"   - Tags de jugadores resueltos: {self.tags_resolved}")
        print(f"   - Clanes en cache: {len(self.clan_members_cache)}")
        print(f"   - Archivo con tags guardado en: {output_file}")

        # Analizar el archivo resultante
        self.analyze_tags_in_file(output_file)

    def analyze_tags_in_file(self, file_path):
        """
        Analiza cuántos tags se resolvieron exitosamente
        """
        if not os.path.exists(file_path):
            return

        total = 0
        with_attacker_tag = 0
        with_defender_tag = 0
        with_both_tags = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        attack = json.loads(line)
                        total += 1
                        
                        has_attacker = attack.get('attacker_tag') is not None
                        has_defender = attack.get('defender_tag') is not None
                        
                        if has_attacker:
                            with_attacker_tag += 1
                        if has_defender:
                            with_defender_tag += 1
                        if has_attacker and has_defender:
                            with_both_tags += 1
                            
                    except:
                        continue

        print(f"\nANÁLISIS DEL ARCHIVO RESULTANTE:")
        print(f"   - Total ataques: {total}")
        print(f"   - Con tag de atacante: {with_attacker_tag} ({with_attacker_tag/total*100:.1f}%)")
        print(f"   - Con tag de defensor: {with_defender_tag} ({with_defender_tag/total*100:.1f}%)")
        print(f"   - Con ambos tags: {with_both_tags} ({with_both_tags/total*100:.1f}%)")


def main():
    # Configuración
    API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjQ1NjlkM2U4LTI5ZjctNDU0NS1hODBiLWE0OTdmMDk1YmI2ZiIsImlhdCI6MTc1NDMyNTkzNSwic3ViIjoiZGV2ZWxvcGVyL2EzMDM4ZTcwLTM3ZWMtNzExMi1jZDI1LTVlMGMzZmQwMDUyZiIsInNjb3BlcyI6WyJjbGFzaCJdLCJsaW1pdHMiOlt7InRpZXIiOiJkZXZlbG9wZXIvc2lsdmVyIiwidHlwZSI6InRocm90dGxpbmcifSx7ImNpZHJzIjpbIjgzLjU0LjE0MC4yMTAiXSwidHlwZSI6ImNsaWVudCJ9XX0.GyGNAv2fFdzho6KVRGcEvA9V-7jsZhQoHKvGMU9buo9LYNnCTl4a7AHBl1FWS6p_35MP1iVAPk0O7eXBh_RTgg"
    INPUT_FILE = "ataques_con_tags_20250808_182625.jsonl"
    
    print("Script de Enriquecimiento de Ataques con Poderes")
    print("=" * 60)
    
    # Crear enriquecedor
    enricher = AttackEnricher(API_TOKEN, INPUT_FILE)
    
    try:
        # Opciones del usuario
        print("Opciones disponibles:")
        print("1. Enriquecer todos los ataques (con resolución de tags)")
        print("2. Enriquecer solo los primeros 50 ataques (prueba)")
        print("3. Analizar distribución de poderes en archivo existente")
        print("4. Analizar tags faltantes en el archivo actual")
        print("5. Probar conexión con la API")
        print("6. Debug - Analizar ataques específicos")
        print("7. Solo resolver tags (sin poderes) - RÁPIDO")
        print("8. Solo resolver tags de primeros 50 ataques (prueba)")
        print("9. Salir")
        
        opcion = input("\nElige una opción (1-9): ").strip()
        
        if opcion == "1":
            print("\nEnriqueciendo todos los ataques...")
            enricher.enrich_attacks()
            enricher.analyze_power_distribution()
            
        elif opcion == "2":
            print("\nEnriqueciendo primeros 50 ataques (modo prueba)...")
            enricher.enrich_attacks(max_attacks=50)
            enricher.analyze_power_distribution()
            
        elif opcion == "3":
            print("\nAnalizando distribución de poderes...")
            enricher.analyze_power_distribution()
            
        elif opcion == "4":
            print("\nAnalizando tags faltantes...")
            enricher.analyze_missing_tags()
            
        elif opcion == "5":
            print("\nProbando conexión con la API...")
            if enricher.test_api_connection():
                print("La API está funcionando correctamente")
            else:
                print("Hay problemas con la API")
            
        elif opcion == "6":
            print("\n Debug - Analizando ataques específicos...")
            enricher.debug_specific_attacks()
            
        elif opcion == "7":
            print("\n Resolviendo todos los tags (sin poderes)...")
            enricher.resolve_tags_only()
            
        elif opcion == "8":
            print("\n Resolviendo tags de primeros 50 ataques (prueba)...")
            enricher.resolve_tags_only(max_attacks=50)
            
        elif opcion == "9":
            print(" Saliendo...")
            
        else:
            print(" Opción no válida")
            
    except KeyboardInterrupt:
        print("\n\n Proceso cancelado por el usuario")
        enricher.print_summary()
    except Exception as e:
        print(f"\n Error inesperado: {e}")
        enricher.print_summary()

if __name__ == "__main__":
    main()
