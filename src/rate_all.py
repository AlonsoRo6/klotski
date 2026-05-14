"""
Envia TOTES les valoracions guardades al fitxer 'puzzles_metrics.csv' al repositori klotski.pauek.dev.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
from rate import post_vote

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Envia les valoracions dels puzzles al servidor.")
    parser.add_argument("--puzzles-dir", type=str, default="puzzles/repository", help="Carpeta on hi ha els puzzles a valorar")
    parser.add_argument("--csv-path", type=str, default="puzzles_metrics.csv", help="Fitxer CSV amb les mètriques")
    args = parser.parse_args()

    CSV_PATH = Path(args.csv_path)
    puzzles_dir = Path(args.puzzles_dir)
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

    # Només volem pujar els puzzles que existeixin a la carpeta indicada
    valid_ids = set()
    if puzzles_dir.exists():
        for p in puzzles_dir.rglob("*.json"):
            # Suposant que el nom és puzzle_{id}.json o {id}.json
            puzzle_id = p.stem.split("_")[-1]
            valid_ids.add(puzzle_id)
            
    df_filtered = df[df['id'].astype(str).isin(valid_ids)]

    total_puzzles = len(df_filtered)
    print(f"S'han trobat {len(df)} valoracions al CSV. {total_puzzles} pertanyen a '{puzzles_dir}'.")

    success_count = 0
    
    # Iterem per cada fila filtrada
    for _, row in df_filtered.iterrows():
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