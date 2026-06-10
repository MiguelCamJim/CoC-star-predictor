"""
Flujo principal para planificar los ataques en una guerra de Clash of Clans usando un modelo de ML para predecir la esperanza de estrellas."""

import requests
import numpy as np
from scipy.optimize import linear_sum_assignment
import json

class War:
    def __init__(self, api_token, clan_tag, model):
        self.api_token = api_token
        self.clan_tag = clan_tag
        self.headers = {"Authorization": f"Bearer {api_token}"}
        self.war_data = None
        self.attackers = []
        self.defenders = []
        self.matrix = None
        self.matching = []
        self.model = model
        self.war_type = "normal"  # Por defecto, tipo de guerra normal

    # Obtenemos los datos de la guerra actual del clan usando la API de Clash of Clans
    def fetch_war_data(self):
        url = f"https://api.clashofclans.com/v1/clans/{self.clan_tag}/currentwar"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            self.war_data = response.json()
        else:
            raise Exception(f"Error en API: {response.status_code} - {response.text}")

    # Extraemos atacantes y defensores, filtrando por ataques realizados y ordenando por posición en el mapa
    def extract_attackers_and_defenders(self):
        clan_members = self.war_data["clan"]["members"]
        opponent_members = self.war_data["opponent"]["members"]

        # Filtramos atacantes que todavía no atacaron
        self.attackers = [
            {
                "name": m["name"],
                "th": m["townhallLevel"],
                "map_pos": m["mapPosition"],
                "team_size": len(clan_members),
                "war_type": self.war_data.get("warType", "normal"),
                "tag": m["tag"]
            }
            for m in clan_members
            if not m.get("attacks")
        ]
        # Ordenamos por posición en el mapa
        self.attackers.sort(key=lambda x: x["map_pos"])

        self.defenders = [
            {
                "name": m["name"],
                "th": m["townhallLevel"],
                "map_pos": m["mapPosition"],
                "team_size": len(opponent_members),
                "war_type": self.war_data.get("warType", "normal")
            }
            for m in opponent_members
        ]
        self.defenders.sort(key=lambda x: x["map_pos"])

    # Calcula la esperanza de estrellas en un ataque para un atacante y defensor dados usando el modelo
    def expected_stars(self, attacker, defender):
        # Usamos el modelo
        stars, exp, conf = self.model.predict(
            attacker_th=attacker["th"], 
            attacker_map_pos=attacker["map_pos"],
            defender_th=defender["th"], 
            defender_map_pos=defender["map_pos"],
            team_size=attacker["team_size"], 
            player_tag=attacker["tag"],
            war_type=attacker["war_type"]
        )
        self.war_type = attacker["war_type"]
        return exp

    # Construimos la matriz de expectativas
    def build_expectation_matrix(self):
        rows = len(self.attackers)
        cols = len(self.defenders)
        self.matrix = np.zeros((rows, cols))

        for i, atk in enumerate(self.attackers):
            for j, dfn in enumerate(self.defenders):
                self.matrix[i, j] = self.expected_stars(atk, dfn)

    # Emparejamiento óptimo usando el algoritmo de asignación importado de scipy
    def compute_optimal_matching_cwl(self):
        if self.matrix is None:
            raise Exception("Expectation matrix not built yet.")
        cost_matrix = -self.matrix
        
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        self.matching = list(zip(row_ind, col_ind))

    def compute_optimal_matching_normal(self):
        # Duplicamos filas para representar los dos ataques
        repeated_matrix = np.repeat(self.matrix, 2, axis=0)
        cost_matrix = -repeated_matrix

        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        # Guardar quién es el jugador original y si es su 1er o 2do ataque
        self.matching = []
        for row, col in zip(row_ind, col_ind):
            original_player = row // 2
            attack_number = (row % 2) + 1
            self.matching.append((original_player, attack_number, col))

    # Estrategia final
    def print_strategy(self):
        print("\n📋 Estrategia óptima de ataques:\n")
        total_expected_stars = 0.0
        for i, att, j in self.matching:
            atk_name = self.attackers[i]["name"]
            atk_pos = i + 1  # posición en el mapa
            dfn_name = self.defenders[j]["name"]
            dfn_pos = j + 1  # posición en el mapa
            exp = round(self.matrix[i, j], 2)
            total_expected_stars += exp
            if self.war_type == "cwl":
                print(f"{atk_pos}. {atk_name} → {dfn_pos}. {dfn_name} (esperanza: {exp}⭐)")
            else:
                print(f"{atk_pos}. {atk_name} (Ataque {att}) → {dfn_pos}. {dfn_name} (esperanza: {exp}⭐)")
        print(f"⭐ Estrellas esperadas en total: {total_expected_stars:.2f}")

    # Función principal para ejecutar todo el proceso
    def plan_matchups(self):
        self.fetch_war_data()
        # Imprimimos el nombre del clan y el oponente
        print(f"Clan: {self.war_data['clan']['name']}")
        print(f"Oponente: {self.war_data['opponent']['name']}")
        print(f"Estado de la guerra: {self.war_data['state']}\n")
        self.extract_attackers_and_defenders()
        self.build_expectation_matrix()
        if self.war_type == "cwl":
            self.compute_optimal_matching_cwl()
        else:
            self.compute_optimal_matching_normal()
        self.print_strategy()
