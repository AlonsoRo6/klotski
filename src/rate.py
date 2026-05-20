"""
Envia la valoració d'un puzzle al repositori klotski.pauek.dev.
Llegeix la puntuació del fitxer puzzles_metrics.csv generat per eval.py.
L'ID del puzzle s'extreu del nom del fitxer (format: puzzle_N_<id>.json).

Ús: python rate.py <puzzle_N_<id>.json> <token>
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
import pandas as pd  # Importat per llegir el CSV centralitzat

BASE_URL = "https://klotski.pauek.dev"
import os
CSV_PATH = Path(os.environ.get("KLOTSKI_CSV_PATH", "puzzles_metrics.csv"))


def puzzle_id_from_path(puzzle_path: Path) -> str:
    """Extreu l'ID del puzzle a partir del nom del fitxer (puzzle_<id>.json)."""
    return puzzle_path.stem.split("_")[-1]


def load_stars_from_csv(puzzle_id: str, csv_path: Path) -> float:
    """Cerca la puntuació del puzzle al fitxer CSV centralitzat."""
    if not csv_path.exists():
        print(f"Error: no s'ha trobat el fitxer '{csv_path}'.")
        print("Executa primer 'eval.py' per generar les mètriques al CSV.")
        sys.exit(1)

    try:
        df = pd.read_csv(csv_path)
        # Busquem la fila que coincideixi amb l'ID
        row = df[df['id'] == puzzle_id]

        if row.empty:
            print(f"Error: L'ID '{puzzle_id}' no existeix al CSV.")
            sys.exit(1)

        # Retornem el valor de la columna 'score'
        return float(row.iloc[0]['score'])
    
    except Exception as e:
        print(f"Error llegint el CSV: {e}")
        sys.exit(1)


def post_vote(puzzle_id: str, stars: float, token: str) -> bool:
    url = f"{BASE_URL}/api/puzzles/{puzzle_id}/votes"
    payload = json.dumps({"stars": round(stars)}).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            resp.read()
            return True
    
    except Exception as e:
        print(f"  [!] Error enviant {puzzle_id}: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Ús: python rate.py <puzzle_<id>.json> [<csv_path>]")
        sys.exit(1)

    puzzle_path = Path(sys.argv[1])
    if len(sys.argv) > 2:
        CSV_PATH = Path(sys.argv[2])
        
    import os
    user = os.environ.get("KLOTSKI_USER")
    if not user:
        user = input("Qui vol executar això? (x: Xavi, a: Angel): ").strip().lower()

    if user == 'a':
        token = '019d90b1-6a74-7000-bd6e-1ba9c9ca9973'
    elif user == 'x':
        token = '019d90b1-6a3c-7000-ad15-514895909854'
    else:
        print("Usuari desconegut. Cancel·lant...")
        sys.exit(1)
        
    puzzle_id = puzzle_id_from_path(puzzle_path)
    
    stars = load_stars_from_csv(puzzle_id, CSV_PATH)

    if post_vote(puzzle_id, stars, token):
        print(f"Valoració {stars:.2f} extreta del CSV i enviada per a '{puzzle_path.name}'.")
    else:
        print(f"No s'ha pogut enviar la valoració de '{puzzle_path.name}'.")