"""
Avalua tots els puzzles que estan a la carpeta puzzles/. Si algun puzzle no tenia
el graf generat, crea el graf i després fa la valoració.

Ús: python3 src/eval_all.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from eval import set_score
from auto_solve import run
from puzzle import Puzzle
import os
import argparse



def reeval_all(
    puzzles_dir: Path,
    graphs_dir: Path,
    evals_dir: Path,
    csv_path: Path,
) -> None:

    # Busquem tots els fitxers .json existents, de manera recursiva
    eval_files = list(puzzles_dir.rglob("*.json"))

    if not eval_files:
        print(f"No s'ha trobat cap .json a {puzzles_dir}/")
        sys.exit(0)

    print(f"Trobats {len(eval_files)} puzzles per valorar. Avaluant...\n")

    for eval_path in eval_files:
        # El fitxer es diu, p.ex., "puzzle_0.json" → puzzle és "puzzle_0"
        try:
            puzzle_name = eval_path.name  # nom del puzzle
            puzzle_path = eval_path  # puzzle.json

            rel_path = puzzle_path.parent.relative_to(Path("puzzles"))
            graph_name = eval_path.name.replace(".json", ".graphml")
            graph_path = graphs_dir / rel_path / graph_name  # graphs/.../puzzle.graphml


            graph_path.parent.mkdir(parents=True, exist_ok=True)
            if not graph_path.exists():
                run(["python3", "src/graph.py", str(puzzle_path), str(graph_path), str(csv_path)])

            puzzle = Puzzle.from_json(puzzle_path.read_text())
            puzzle_id = puzzle_path.stem.split("_")[-1]

            if not csv_path.exists():
                print(f"Error: {csv_path} no existeix. Esborra el graf de {puzzle_name} i reintenta-ho.")
                continue
                
            score = set_score(puzzle_id, puzzle, csv_path)

            if score is not None:
                print(f"--- Resultat per a {puzzle_path.name} ---")
                print(f" ⭐ Valoració: {score} / 5.0")
                print()
        except Exception as e:
            print(f"Error evaluant {eval_path.name}: {e}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Avaluador de tots els puzzles.")

    parser.add_argument(
        "--puzzles-dir", type=str, default="puzzles", help="Carpeta base dels puzzles"
    )

    parser.add_argument(
        "--csv-path",
        type=str,
        default="puzzles_metrics.csv",
        help="Fitxer CSV de sortida/entrada",
    )
    args = parser.parse_args()

    # Cridarem l'eval individual amb el CSV argument

    os.environ["KLOTSKI_CSV_PATH"] = args.csv_path
    
    reeval_all(
        puzzles_dir=Path(args.puzzles_dir),
        graphs_dir=Path("graphs"),
        evals_dir=Path("evals"),
        csv_path=Path(args.csv_path),
    )
