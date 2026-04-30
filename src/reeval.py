"""
Reavalua tots els puzzles que ja tenien una valoració a la carpeta evals/.
Per cada .eval.json existent, busca el .json del puzzle i el .graphml del graf
i torna a calcular les mètriques i les estrelles amb el codi actual d'eval.py.

Ús: python reeval.py
     python reeval.py --puzzles puzzles/ --graphs graphs/ --evals evals/
"""

from __future__ import annotations

import subprocess
import json
import sys
from pathlib import Path

# Importem les funcions directament d'eval.py (sense el bloc __main__)
from eval import calculate_metrics, calculate_stars
from puzzle import Puzzle
import graph_tool.all as gt  # type: ignore


def run(cmd: list[str]) -> None:
    print(f"\n$ {' '.join(cmd)}") 
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        print(f"Error executant: {' '.join(cmd)}")
        sys.exit(1)

def reeval_all(
    puzzles_dir: Path,
    graphs_dir: Path,
    evals_dir: Path,
) -> None:
    
    # Busquem tots els fitxers .eval.json existents
    eval_files = list(puzzles_dir.glob("*.json"))

    if not eval_files:
        print(f"No s'ha trobat cap .json a {puzzles_dir}/")
        sys.exit(0)

    print(f"Trobats {len(eval_files)} puzzles per valorar. Avaluant...\n")

    ok = 0
    errors = []

    for eval_path in eval_files:
        # El nom del puzzle el traiem del propi .eval.json o del nom del fitxer.
        # El fitxer es diu, p.ex., "puzzle_0.eval.json" → puzzle és "puzzle_0.json"
        puzzle_name = eval_path.name
        puzzle_path = puzzles_dir / puzzle_name
        
        graph_name  = eval_path.name.replace(".json", ".graphml")
        graph_path  = graphs_dir / graph_name

        eval_name = puzzle_path.name.replace(".json", ".eval.json")
        eval_path = evals_dir / eval_name

        # Comprovacions
        missing = []
        if not puzzle_path.exists():
            missing.append(str(puzzle_path))
       
        if not graph_path.exists():
            run(["python3", "src/graph.py", str(puzzle_path), str(graph_path)])
            missing.append(str(graph_path))
        
        if missing:
            msg = f"  ✗ {puzzle_name}: falten fitxers: {', '.join(missing)}"
            print(msg)
            errors.append(msg)
            continue

        puzzle = Puzzle.from_json(puzzle_path.read_text())
        g = gt.load_graph(str(graph_path))

        metrics = calculate_metrics(g, puzzle)
        stars = calculate_stars(metrics, puzzle)

        result = {
            "puzzle":  puzzle_name,
            "metrics": metrics,
            "stars":   stars,
        }

        eval_path.write_text(json.dumps(result, indent=2))

        print(
            f"  ✓ {puzzle_name:15s}  "
            f"{metrics['min_moves']:3d} movs  "
            f"{metrics['num_states']:6d} estats  "
            f"{stars:.2f}/5.0"
        )
        ok += 1


    print(f"\nFet: {ok}/{len(eval_files)} reavalauts correctament.")
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    reeval_all(
        puzzles_dir = Path("puzzles"),
        graphs_dir  = Path("graphs"),
        evals_dir   = Path("evals"),
    )