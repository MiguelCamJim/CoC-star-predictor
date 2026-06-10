"""
Archivo principal para ejecutar el planificador de guerras de Clash of Clans
"""

from war import War
from attackcollector import AttackCollector
from star_predictor import StarPredictor

if __name__ == "__main__":
    TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjU4ODhlOWI2LTk2YTctNDQ3My04NmNjLWY2MjU4MzAxY2JiNCIsImlhdCI6MTc1NTcxNjQ3NSwic3ViIjoiZGV2ZWxvcGVyL2EzMDM4ZTcwLTM3ZWMtNzExMi1jZDI1LTVlMGMzZmQwMDUyZiIsInNjb3BlcyI6WyJjbGFzaCJdLCJsaW1pdHMiOlt7InRpZXIiOiJkZXZlbG9wZXIvc2lsdmVyIiwidHlwZSI6InRocm90dGxpbmcifSx7ImNpZHJzIjpbIjgzLjU1Ljk4LjEyNSJdLCJ0eXBlIjoiY2xpZW50In1dfQ.ZfA4ooT229Ior88o_tasg4MexJhQR-wYKD2P-r4R82pOZDAfLJdiuzkO9UMI0_eYm0zxTI5aAE8YwCpcR26XuA"
    CLAN_TAG = "%23J9R2VLGG"  # El %23 es por el #

    model = StarPredictor()
    model.train_from_file("ataques_recientes.jsonl")
    war = War(TOKEN, CLAN_TAG, model)
    war.plan_matchups()

