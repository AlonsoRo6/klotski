"""
Envia TOTES les valoracions guardades al fitxer 'puzzles_metrics.csv' al repositori klotski.pauek.dev.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
from rate import post_vote

CSV_PATH = Path("puzzles_metrics.csv")

if __name__ == "__main__":
    token = '019d90b1-6a3c-7000-ad15-514895909854'
    
    if not CSV_PATH.exists():
        print(f"Error: El fitxer '{CSV_PATH}' no existeix.")
        print("Executa primer 'eval_all.py' (o eval.py per a cada puzzle) per generar el CSV.")
        sys.exit(1)

    try:
        df = pd.read_csv(CSV_PATH)
    except Exception as e:
        print(f"Error llegint el CSV: {e}")
        sys.exit(1)
    
    if df.empty:
        print("El fitxer CSV està buit.")
        sys.exit(0)

    total_puzzles = len(df)
    print(f"S'han trobat {total_puzzles} valoracions al CSV.")

    success_count = 0
    
    # Iterem per cada fila del DataFrame
    for _, row in df.iterrows():
        try:
            puzzle_id = str(row['id'])
            stars = float(row['score'])
            
            if post_vote(puzzle_id, stars, token):
                print(f"{puzzle_id}: {stars:.2f} enviat correctament.")
                success_count += 1
            else:
                print(f"Error enviant el puzzle {puzzle_id}.")
            
        except KeyError as e:
            print(f"Error: Falta la columna {e} al CSV.")
            break
        except Exception as e:
            print(f"Error inesperat processant la fila: {e}")

    print(f"\n--- Procés finalitzat ---")
    print(f"S'han enviat correctament {success_count} de {total_puzzles} puzzles.")