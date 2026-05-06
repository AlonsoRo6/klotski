"""
Genera el graf, la solució i el gif de la solució per a TOTS els puzzles a la carpeta 'puzzles/'.
Ús: python src/solve_all.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def run(cmd: list[str]) -> None:
    print(f"\n$ {' '.join(cmd)}") 
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        print(f"Error executant: {' '.join(cmd)}")
        # Aquí millor no fer sys.exit(1) perquè si un puzzle falla, 
        # volem que continuï amb el següent.
        return 


def main() -> None:
    # Definir carpetes
    puzzles_dir = Path("puzzles")
    graphs_dir = Path("graphs")
    solutions_dir = Path("solutions")
    gifs_dir = Path("solutions_gifs")


    # Buscar tots els fitxers .json a la carpeta puzzles/
    puzzle_files = list(puzzles_dir.glob("*.json"))

    if not puzzle_files:
        print(f"No s'han trobat fitxers .json a {puzzles_dir}")
        return

    print(f"S'han trobat {len(puzzle_files)} puzzles. Començant el processament...\n")

    for puzzle_path in puzzle_files:
        name = puzzle_path.stem  # Nom del fitxer sense extensió
        
        print(f"{'='*40}")
        print(f"PROCESSANT: {name}")
        print(f"{'='*40}")

        graphml_path = graphs_dir / f"{name}.graphml"
        solution_path = solutions_dir / f"{name}.sol.json"
        gif_path = gifs_dir / f"{name}.gif"

        # 1. Generar Graf
        if not graphml_path.exists():
            print(f'-> Generant graf per a {name}...')
            run(["python3", "src/graph.py", str(puzzle_path), str(graphml_path)])
        else:
            print(f"-> El graf ja existeix: {graphml_path}")

        # 2. Resoldre
        if not solution_path.exists():
            print(f'-> Resolent {name}...')
            run(["python3", "src/solve.py", str(graphml_path), str(solution_path)])
        else:
            print(f"-> La solució ja existeix: {solution_path}")

        # 3. Generar GIF
        if not gif_path.exists():
            print(f'-> Generant GIF per a {name}...')
            run(["python3", "src/movie.py", str(puzzle_path), str(solution_path), str(gif_path)])
        else:
            print(f"-> El GIF ja existeix: {gif_path}")

    print("\nProcés finalitzat per a tots els puzzles.")


if __name__ == "__main__":
    main()