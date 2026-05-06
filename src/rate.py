"""
Envia la valoració d'un puzzle al repositori klotski.pauek.dev.
Llegeix la puntuació del fitxer .eval.json generat per eval.py.
L'ID del puzzle s'extreu del nom del fitxer (format: puzzle_N_<id>.json).

Ús: python rate.py <puzzle_N_<id>.json> <token>
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL  = "https://klotski.pauek.dev"
EVALS_DIR = Path("evals")


def puzzle_id_from_path(puzzle_path: Path) -> str:
    """Extreu l'ID del puzzle a partir del nom del fitxer (puzzle_<id>.json)."""
    # puzzle_path.stem ens dona el nom sense l'extensió .json (ex: "puzzle_123")
    # .split("_") divideix la cadena per l'guionet baix
    # [-1] agafa l'última part de la llista resultant
    return puzzle_path.stem.split("_")[-1]


def load_stars(puzzle_path: Path) -> float:
    eval_path = EVALS_DIR / puzzle_path.with_suffix(".eval.json").name
    if not eval_path.exists():
        print(f"Error: no s'ha trobat '{eval_path}'.")
        print(f"  Executa primer: python eval.py {puzzle_path} <graf.graphml>")
        sys.exit(1)
    data = json.loads(eval_path.read_text())
    return float(data["stars"])


def post_vote(puzzle_id: str, stars: float, token: str) -> None:
    url     = f"{BASE_URL}/api/puzzles/{puzzle_id}/votes"
    payload = json.dumps({"stars": stars}).encode("utf-8")

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
    
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Error HTTP {e.code}: {body[:300]}")
    
    except urllib.error.URLError as e:
        raise RuntimeError(f"Error de connexió: {e.reason}")


if __name__ == "__main__":

    if len(sys.argv) < 3:
        print("Ús: python rate.py <puzzle_N_<id>.json> <token>")
        sys.exit(1)

    puzzle_path = Path(sys.argv[1])
    token = '019d90b1-6a3c-7000-ad15-514895909854'
    puzzle_id = puzzle_id_from_path(puzzle_path)
    stars = load_stars(puzzle_path)

    post_vote(puzzle_id, stars, token)
    print(f"✓ Valoració {stars:.2f}★ enviada per a '{puzzle_path.name}'.")