"""
Script per solucionar un puzzle de peces lliscants de forma interactiva.
Ús: python src/auto_solve.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        print(f"Error executant: {' '.join(cmd)}")
        sys.exit(1)


def main() -> None:
    name = input("Nom del puzzle (sense extensió): ").strip()

    puzzle_path = Path(f"puzzles/{name}.json")
    graphml_path = Path(f"graphs/{name}.graphml")
    solution_path = Path(f"solutions/{name}.sol.json")
    gif_path = Path(f"solutions_gifs/{name}.gif")

    if not puzzle_path.exists():
        print(f"No s'ha trobat el puzzle: {puzzle_path}")
        sys.exit(1)

    '''# Crear directoris si no existeixen
    graphml_path.parent.mkdir(parents=True, exist_ok=True)
    solution_path.parent.mkdir(parents=True, exist_ok=True)'''


    
    run(["python3", "src/graph.py", str(puzzle_path), str(graphml_path)])

    run(["python3", "src/solve.py", str(graphml_path), str(solution_path)])

    run(["python3", "src/movie.py", str(puzzle_path), str(solution_path), str(gif_path)])


if __name__ == "__main__":
    main()