"""
Envia TOTS els .eval.json de la carpeta 'evals' al repositori klotski.pauek.dev.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from rate import post_vote, puzzle_id_from_path

BASE_URL  = "https://klotski.pauek.dev"
EVALS_DIR = Path("evals")
PUZZLES_DIR = Path("puzzles")


if __name__ == "__main__":
    token = '019d90b1-6a3c-7000-ad15-514895909854'
    
    if not EVALS_DIR.exists():
        print(f"Error: La carpeta '{EVALS_DIR}' no existeix.")
        sys.exit(1)

    # Busquem tots els fitxers .eval.json dins la carpeta evals
    eval_files = list(EVALS_DIR.glob("*.eval.json"))
    
    if not eval_files:
        print("No s'han trobat fitxers .eval.json a la carpeta.")
        sys.exit(0)

    print(f"S'han trobat {len(eval_files)} valoracions. Començant l'enviament...")

    success_count = 0
    for eval_path in eval_files:
        try:
            # 1. Obtenir l'ID del puzzle
            puzzle_id = puzzle_id_from_path(eval_path)
            
            # 2. Llegir les estrelles
            data = json.loads(eval_path.read_text())
            stars = float(data["stars"])
            
            # 3. Enviar
            if post_vote(puzzle_id, stars, token):
                print(f"✓ {puzzle_id}: {stars:.2f}★ enviat correctament.")
                success_count += 1
            
        except Exception as e:
            print(f"✘ Error processant {eval_path.name}: {e}")

    print(f"\n--- Procés finalitzat ---")
    print(f"S'han enviat correctament {success_count} de {len(eval_files)} puzzles.")