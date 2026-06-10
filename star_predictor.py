"""
Modelo de red neuronal para predecir estrellas en ataques de Clash of Clans
"""
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import json
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import numpy as np
from stats import calculate_offensive_power

class StarPredictor(nn.Module):
    def __init__(self, input_dim=8, hidden_dim=64, output_dim=4):
        super(StarPredictor, self).__init__()
        
        # Detectar dispositivo (GPU si está disponible, sino CPU)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Usando dispositivo: {self.device}")
        if torch.cuda.is_available():
            print(f"GPU detectada: {torch.cuda.get_device_name(0)}")
        
        self.model = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, output_dim)  # SIN Softmax aquí
        )
        
        # Guardar el scaler para usar en predicciones
        self.scaler = None
        
        # Mover modelo a GPU si está disponible
        self.to(self.device)

    def forward(self, x):
        return self.model(x)

    def train_from_file(self, file_path, epochs=10000, batch_size=32, lr=0.001):
        # Cargar datos desde archivo JSONL (línea por línea)
        data = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if line_num % 100 == 0:  # Mostrar progreso cada 100 líneas
                    print(f"Cargando línea {line_num}...")
                line = line.strip()
                if line:
                    try:
                        attack = json.loads(line)
                        data.append(attack)
                    except json.JSONDecodeError as e:
                        print(f"Error en línea {line_num}: {e}")
                        continue
        
        print(f"Cargados {len(data)} ataques desde {file_path}")

        # Mapear war_type a número
        war_type_map = {}
        war_type_counter = 0

        rows = []
        for attack in data:
            try:
                war_type_str = attack.get("war_type", "normal")
                if war_type_str not in war_type_map:
                    war_type_map[war_type_str] = war_type_counter
                    war_type_counter += 1

                th_diff = attack["attacker_th"] - attack["defender_th"]

                rows.append([
                    attack["attacker_th"],
                    attack["attacker_map_pos"],
                    attack["defender_th"],
                    attack["defender_map_pos"],
                    attack["team_size"],
                    war_type_map[war_type_str],
                    np.sign(th_diff) * (np.abs(th_diff) ** 2),
                    attack["attacker_offensive_power"],
                    attack["stars"]
                ])
            except KeyError:
                continue  # Saltar entradas rotas

        df = pd.DataFrame(rows, columns=[
            "attacker_th", "attacker_map_pos",
            "defender_th", "defender_map_pos",
            "team_size", "war_type", "th_difference", "attacker_offensive_power", "stars"
        ])

        # Features y target
        X = df[["attacker_th", "attacker_map_pos", "defender_th", "defender_map_pos", "team_size", "war_type", "th_difference", "attacker_offensive_power"]].values
        y_raw = df["stars"].values

        # Normalizar Y GUARDAR EL SCALER
        self.scaler = StandardScaler()
        X = self.scaler.fit_transform(X)
        
        print(f"Distribución de estrellas:")
        unique, counts = np.unique(y_raw, return_counts=True)
        for star, count in zip(unique, counts):
            print(f"   {star} estrellas: {count} ataques ({count/len(y_raw)*100:.1f}%)")

        # One-hot de estrellas
        y = np.zeros((len(y_raw), 4))
        for i, s in enumerate(y_raw):
            if 0 <= s <= 3:
                y[i][s] = 1

        # Split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Tensores y mover a GPU
        X_train = torch.tensor(X_train, dtype=torch.float32).to(self.device)
        y_train = torch.tensor(y_train, dtype=torch.float32).to(self.device)
        X_test = torch.tensor(X_test, dtype=torch.float32).to(self.device)
        y_test = torch.tensor(y_test, dtype=torch.float32).to(self.device)
        
        print(f"Datos de entrenamiento: {X_train.shape} en {X_train.device}")
        print(f"Datos de validación: {X_test.shape} en {X_test.device}")

        # Entrenar
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.parameters(), lr=lr)

        print(f"Iniciando entrenamiento por {epochs} épocas...")
        
        for epoch in range(epochs):
            self.train()
            optimizer.zero_grad()
            output = self(X_train)
            loss = criterion(output, torch.argmax(y_train, dim=1))
            loss.backward()
            optimizer.step()

            if epoch % 5 == 0 or epoch == epochs - 1:
                self.eval()
                with torch.no_grad():
                    val_output = self(X_test)
                    val_loss = criterion(val_output, torch.argmax(y_test, dim=1))
                    acc = (torch.argmax(val_output, dim=1) == torch.argmax(y_test, dim=1)).float().mean()
                    print(f"Epoch {epoch:3d}: loss = {loss.item():.4f} - val_loss = {val_loss.item():.4f} - acc = {acc.item():.4f}")

        print("Entrenamiento completado")

    def save_model(self, file_path):
        # Guardar modelo, scaler y información del dispositivo
        torch.save({
            'model_state_dict': self.state_dict(),
            'device': str(self.device),
            'scaler_mean': self.scaler.mean_ if self.scaler else None,
            'scaler_scale': self.scaler.scale_ if self.scaler else None
        }, file_path)
        print(f"Modelo guardado en {file_path}")

    def load_model(self, file_path):
        checkpoint = torch.load(file_path, map_location=self.device)
        self.load_state_dict(checkpoint['model_state_dict'])
        
        # Restaurar scaler
        if checkpoint.get('scaler_mean') is not None:
            self.scaler = StandardScaler()
            self.scaler.mean_ = checkpoint['scaler_mean']
            self.scaler.scale_ = checkpoint['scaler_scale']
        
        self.eval()
        print(f"Modelo cargado desde {file_path} en {self.device}")
    
    def predict(self, attacker_th, attacker_map_pos, defender_th, defender_map_pos, team_size, player_tag, war_type="normal"):
        """
        Predecir estrellas para un ataque específico
        """
        if self.scaler is None:
            print("Modelo no entrenado o scaler no disponible")
            return 0, 0.0
            
        self.eval()
        
        # Mapear war_type a número (simplificado)
        war_type_num = 0 if war_type == "normal" else 1
        
        # Calcular diferencia de TH con amplificación que mantiene el signo
        th_diff_raw = attacker_th - defender_th
        th_difference = th_diff_raw * abs(th_diff_raw)  # x * |x|

        att_off_power = calculate_offensive_power(player_tag, "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjU4ODhlOWI2LTk2YTctNDQ3My04NmNjLWY2MjU4MzAxY2JiNCIsImlhdCI6MTc1NTcxNjQ3NSwic3ViIjoiZGV2ZWxvcGVyL2EzMDM4ZTcwLTM3ZWMtNzExMi1jZDI1LTVlMGMzZmQwMDUyZiIsInNjb3BlcyI6WyJjbGFzaCJdLCJsaW1pdHMiOlt7InRpZXIiOiJkZXZlbG9wZXIvc2lsdmVyIiwidHlwZSI6InRocm90dGxpbmcifSx7ImNpZHJzIjpbIjgzLjU1Ljk4LjEyNSJdLCJ0eXBlIjoiY2xpZW50In1dfQ.ZfA4ooT229Ior88o_tasg4MexJhQR-wYKD2P-r4R82pOZDAfLJdiuzkO9UMI0_eYm0zxTI5aAE8YwCpcR26XuA")
        
        # Crear datos de entrada y normalizar con el mismo scaler del entrenamiento
        x_raw = np.array([[attacker_th, attacker_map_pos, defender_th, defender_map_pos, team_size, war_type_num, th_difference, att_off_power]])
        x_normalized = self.scaler.transform(x_raw)
        
        # Crear tensor de entrada
        x = torch.tensor(x_normalized, dtype=torch.float32).to(self.device)
        
        with torch.no_grad():
            output = self(x)  # Sin softmax en el modelo
            probabilities = torch.softmax(output, dim=1)  # Aplicar softmax aquí
            predicted_stars = torch.argmax(probabilities, dim=1).item()
            confidence = torch.max(probabilities, dim=1).values.item()
            
            # Mostrar todas las probabilidades para debug
            probs = probabilities.cpu().numpy().flatten()
            print(f"Probabilidades: 0★:{probs[0]:.3f} 1★:{probs[1]:.3f} 2★:{probs[2]:.3f} 3★:{probs[3]:.3f}")
            
            expected_stars = np.sum(np.arange(4) * probs)
            
        return predicted_stars, expected_stars, confidence

if __name__ == "__main__":
    print("Iniciando predictor de estrellas de Clash of Clans")
    print("=" * 50)
    
    # Verificar disponibilidad de GPU
    if torch.cuda.is_available():
        print(f"CUDA disponible: {torch.cuda.get_device_name(0)}")
        print(f"Memoria GPU: {torch.cuda.get_device_properties(0).total_memory // 1024**3} GB")
    else:
        print("GPU no disponible, usando CPU")
    
    model = StarPredictor()
    model.train_from_file("ataques_recientes.jsonl")
    model.save_model("star_predictor.pth")
    
    # Ejemplos de predicción variados
    print("\nEjemplos de predicción:")
    
    test_cases = [
        {"attacker_th": 14, "attacker_map_pos": 1, "defender_th": 13, "defender_map_pos": 1, "team_size": 30, "war_type": "normal", "desc": "TH14 vs TH13 (similar)"},
        {"attacker_th": 13, "attacker_map_pos": 10, "defender_th": 14, "defender_map_pos": 5, "team_size": 30, "war_type": "normal", "desc": "TH13 vs TH14 (difícil)"},
        {"attacker_th": 12, "attacker_map_pos": 5, "defender_th": 10, "defender_map_pos": 8, "team_size": 15, "war_type": "cwl", "desc": "TH12 vs TH10 (fácil)"},
        {"attacker_th": 11, "attacker_map_pos": 8, "defender_th": 11, "defender_map_pos": 3, "team_size": 50, "war_type": "normal", "desc": "TH11 vs TH11 (mismo nivel)"},
        
        # Casos extremos fáciles (debería dar muchas estrellas)
        {"attacker_th": 16, "attacker_map_pos": 1, "defender_th": 12, "defender_map_pos": 15, "team_size": 30, "war_type": "normal", "desc": "🟢 TH16 vs TH12 (EXTREMO FÁCIL)"},
        {"attacker_th": 15, "attacker_map_pos": 2, "defender_th": 11, "defender_map_pos": 20, "team_size": 25, "war_type": "cwl", "desc": "🟢 TH15 vs TH11 (MUY FÁCIL)"},
        {"attacker_th": 14, "attacker_map_pos": 3, "defender_th": 10, "defender_map_pos": 25, "team_size": 40, "war_type": "normal", "desc": "🟢 TH14 vs TH10 (SÚPER FÁCIL)"},
        
        # Casos extremos difíciles (debería dar pocas estrellas)
        {"attacker_th": 10, "attacker_map_pos": 30, "defender_th": 16, "defender_map_pos": 1, "team_size": 30, "war_type": "normal", "desc": "🔴 TH10 vs TH16 (IMPOSIBLE)"},
        {"attacker_th": 11, "attacker_map_pos": 25, "defender_th": 15, "defender_map_pos": 2, "team_size": 15, "war_type": "cwl", "desc": "🔴 TH11 vs TH15 (EXTREMO DIFÍCIL)"},
        {"attacker_th": 12, "attacker_map_pos": 20, "defender_th": 14, "defender_map_pos": 3, "team_size": 50, "war_type": "normal", "desc": "🔴 TH12 vs TH14 (MUY DIFÍCIL)"},
        
        # Casos edge/raros
        {"attacker_th": 8, "attacker_map_pos": 15, "defender_th": 8, "defender_map_pos": 1, "team_size": 10, "war_type": "normal", "desc": "⚪ TH8 vs TH8 #1 (guerra pequeña)"},
        {"attacker_th": 16, "attacker_map_pos": 50, "defender_th": 16, "defender_map_pos": 1, "team_size": 50, "war_type": "cwl", "desc": "⚪ TH16 último vs TH16 #1 (CWL grande)"},
        {"attacker_th": 9, "attacker_map_pos": 1, "defender_th": 13, "defender_map_pos": 15, "team_size": 20, "war_type": "normal", "desc": "🟡 TH9 #1 vs TH13 medio (estrategia?)"},
        {"attacker_th": 13, "attacker_map_pos": 15, "defender_th": 9, "defender_map_pos": 1, "team_size": 20, "war_type": "normal", "desc": "🟡 TH13 medio vs TH9 #1 (cleanup)"}
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- Caso {i}: {case['desc']} ---")
        stars, exp, conf = model.predict(
            attacker_th=case["attacker_th"], 
            attacker_map_pos=case["attacker_map_pos"],
            defender_th=case["defender_th"], 
            defender_map_pos=case["defender_map_pos"],
            team_size=case["team_size"], 
            war_type=case["war_type"]
        )
        print(f"🎯 Resultado: {stars} estrellas | 📊 Esperadas: {exp:.2f} | 🎪 Confianza: {conf:.1%}")
    
    if torch.cuda.is_available():
        print(f"\n📊 Memoria GPU utilizada: {torch.cuda.memory_allocated() / 1024**2:.1f} MB")