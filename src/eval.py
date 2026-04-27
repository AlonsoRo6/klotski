"""
Avaluació d'un puzzle de peces lliscants mitjançant el graf d'estats.

Ús: python src/eval.py <puzzle.json> <graphs/puzzle.graphml>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import graph_tool.all as gt  # type: ignore
from graph_tool.topology import shortest_distance  # type: ignore

from puzzle import Puzzle


def calculate_metrics(g: gt.Graph, puzzle: Puzzle) -> dict:
    """Calcula les mètriques del graf."""
    vp_is_start = g.vp["is_start"]
    vp_is_goal  = g.vp["is_goal"]

    start_v = next(v for v in g.vertices() if vp_is_start[v])
    goal_vs  = [v for v in g.vertices() if vp_is_goal[v]]


    dist_map = shortest_distance(g, start_v)

    min_moves = min(int(dist_map[v]) for v in goal_vs)

    num_states = g.num_vertices()

    # Diàmetre: distància màxima des de l'inici (excloent infinits)
    diameter = max(int(dist_map[v]) for v in g.vertices() if int(dist_map[v]) < 2**30)

    # Comptem quants nodes goal estan a distància min_moves
    num_optimal_goals = sum(1 for v in goal_vs if int(dist_map[v]) == min_moves)

    # Coeficient de clustering local mitjà (via graph-tool)
    clustering_map = gt.local_clustering(g)  # type: ignore
    avg_clustering = float(sum(clustering_map[v] for v in g.vertices()) / num_states)

    return {
        "min_moves":        min_moves,
        "num_states":       num_states,
        "diameter":         diameter,
        "num_optimal_goals": num_optimal_goals,
        "avg_clustering":   avg_clustering,
    }


def normalize(value: float, min_val: float, max_val: float) -> float:
    """Normalitza un valor entre 0 i 1."""
    if max_val == min_val:
        return 0.0
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))


def calculate_stars(metrics: dict) -> float:
    """
    Combina les mètriques en una valoració entre 1 i 5 estrelles.
    Criteris:
      - Més moviments mínims      → més interessant
      - Més estats totals         → més interessant
      - Diàmetre més gran         → més interessant
      - Menys camins òptims       → més interessant (solució més única)
      - Més clustering            → més interessant (més trampes)
    """
    # Valors de referència aproximats per normalitzar
    # (ajusta'ls segons els teus puzzles)
    score_moves = normalize(metrics["min_moves"], 0, 100)
    score_states = normalize(metrics["num_states"], 0, 50000)
    score_diameter = normalize(metrics["diameter"], 0, 200)
    score_uniqueness = normalize(1 / max(metrics["num_optimal_goals"], 1), 0, 1)
    score_clustering = normalize(metrics["avg_clustering"], 0, 1)

    # Pesos (sumen 1.0)
    w_moves      = 0.35
    w_states     = 0.25
    w_diameter   = 0.20
    w_uniqueness = 0.10
    w_clustering = 0.10

    score = (
        w_moves      * score_moves      +
        w_states     * score_states     +
        w_diameter   * score_diameter   +
        w_uniqueness * score_uniqueness +
        w_clustering * score_clustering
    )

    # Mapeja a 1-5 estrelles
    stars = 1.0 + score * 4.0
    return round(stars, 2)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Ús: python src/eval.py <puzzle.json> <graphs/puzzle.graphml>")
        sys.exit(1)

    puzzle_path  = Path(sys.argv[1])
    graphml_path = Path(sys.argv[2])

    if not puzzle_path.exists():
        print(f"No s'ha trobat el puzzle: {puzzle_path}")
        sys.exit(1)

    if not graphml_path.exists():
        print(f"No s'ha trobat el graf: {graphml_path}")
        sys.exit(1)

    print(f"Carregant graf {graphml_path}...")
    g = gt.load_graph(str(graphml_path))
    puzzle = Puzzle.from_json(puzzle_path.read_text())

    print("Calculant mètriques...")
    metrics = calculate_metrics(g, puzzle)
    stars   = calculate_stars(metrics)

    print(f"\n--- Resultats per a {puzzle_path.name} ---")
    print(f"  Moviments mínims:   {metrics['min_moves']}")
    print(f"  Estats totals:      {metrics['num_states']}")
    print(f"  Diàmetre del graf:  {metrics['diameter']}")
    print(f"  Camins òptims:      {metrics['num_optimal_goals']}")
    print(f"  Clustering mitjà:   {metrics['avg_clustering']:.4f}")
    print(f"\n  ⭐ Valoració: {stars} / 5.0")

    result = {
        "puzzle":   puzzle_path.name,
        "metrics":  metrics,
        "stars":    stars,
    }
    evals_dir = Path("evals")
    evals_dir.mkdir(parents=True, exist_ok=True)
    output = evals_dir / puzzle_path.with_suffix(".eval.json").name
    output.write_text(json.dumps(result, indent=2))
    print(f"\n  Resultat guardat a {output}")