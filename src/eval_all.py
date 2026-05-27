"""
Avalua tots els puzzles que estan a la carpeta puzzles/... . Si algun puzzle no tenia
el graf generat, crea el graf i després fa la valoració.

Ús: python3 src/eval_all.py [--puzzles-dir puzzles/... --csv-path ..._metrics.csv]
"""

from __future__ import annotations
import sys
from pathlib import Path
import os
import argparse

from eval import set_score
from auto_solve import run
from puzzle import Puzzle



def reeval_all(
    puzzles_dir: Path,
    graphs_dir: Path,
    csv_path: Path,
) -> None:


    eval_files = list(puzzles_dir.rglob("*.json"))

    if not eval_files:
        print(f"No s'ha trobat cap .json a {puzzles_dir}/")
        sys.exit(0)

    print(f"Trobats {len(eval_files)} puzzles. Avaluant...\n")

    for puzzle_path in eval_files:
        try:
            puzzle_name = puzzle_path.name 

            rel_path = puzzle_path.parent.relative_to(Path("puzzles"))
            graph_name = puzzle_path.name.replace(".json", ".graphml")
            graph_path = graphs_dir / rel_path / graph_name  # graphs/.../puzzle.graphml


            graph_path.parent.mkdir(parents=True, exist_ok=True)
            if not graph_path.exists():
                run(["python3", "src/graph.py", str(puzzle_path), str(graph_path), str(csv_path)])

            puzzle = Puzzle.from_json(puzzle_path.read_text())
            puzzle_id = puzzle_path.stem.split("_")[-1]

            if not csv_path.exists():
                print(f"Error: {csv_path} no existeix.")
                continue
                
            score = set_score(puzzle_id, puzzle, csv_path)

            if score is not None:
                print(f"Resultat per a {puzzle_path.name}")
                print(f"Valoració: {score} / 5.0", int(score)*'⭐')
                print()
                
        except Exception as e:
            print(f"Error avaluant {puzzle_path.name}: {e}")



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


    os.environ["KLOTSKI_CSV_PATH"] = args.csv_path
    
    reeval_all(
        puzzles_dir=Path(args.puzzles_dir),
        graphs_dir=Path("graphs"),
        csv_path=Path(args.csv_path),
    )
