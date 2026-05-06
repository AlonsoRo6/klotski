"""
Avalua tots els puzzles que estan a la carpeta puzzles/. Si algun puzzle no tenia 
el graf generat, crea el graf i després fa la valoració. 

Ús: python3 src/eval_all.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from eval import calculate_metrics, calculate_stars_2, save_metrics_to_csv, predict_score_ml
from auto_solve import run
from puzzle import Puzzle
import graph_tool.all as gt  # type: ignore


def reeval_all(
    puzzles_dir: Path,
    graphs_dir: Path,
    evals_dir: Path,
) -> None:
    
    # Busquem tots els fitxers .json existents
    eval_files = list(puzzles_dir.glob("*.json"))

    if not eval_files:
        print(f"No s'ha trobat cap .json a {puzzles_dir}/")
        sys.exit(0)

    print(f"Trobats {len(eval_files)} puzzles per valorar. Avaluant...\n")


    for eval_path in eval_files:
        # El fitxer es diu, p.ex., "puzzle_0.json" → puzzle és "puzzle_0"
        puzzle_name = eval_path.name #nom del puzzle
        puzzle_path = puzzles_dir / puzzle_name #puzzle.json
        
        graph_name  = eval_path.name.replace(".json", ".graphml")
        graph_path  = graphs_dir / graph_name #graphs/puzzle.graphml

       
        if not graph_path.exists():
            run(["python3", "src/graph.py", str(puzzle_path), str(graph_path)])


        puzzle = Puzzle.from_json(puzzle_path.read_text())
        g = gt.load_graph(str(graph_path))
        
        puzzle_id = puzzle_path.stem.split("_")[-1]
        metrics = calculate_metrics(g, puzzle)
        ml_score = predict_score_ml(metrics)

        if ml_score is not None:
            score = int(round(ml_score))
            print(f"  🤖 Valoració (Machine Learning): {score} / 5.0")
        else:
            score = calculate_stars_2(metrics, puzzle) # formula per defecte
            print(f"  ⭐ Valoració (Fórmula): {score} / 5.0")

        save_metrics_to_csv(puzzle_id, metrics, score)

        print(f"--- Resultat per a {puzzle_path.name} ---")
        print(f" ⭐ Valoració: {score} / 5.0")
        print()


if __name__ == "__main__":
    reeval_all(
        puzzles_dir = Path("puzzles"),
        graphs_dir  = Path("graphs"),
        evals_dir   = Path("evals"),
    )