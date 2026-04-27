"""
Avaluació d'un puzzle de peces lliscants mitjançant el graf d'estats.

Ús: python src/eval.py <puzzle.json> <graphs/puzzle.graphml>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import math

import graph_tool.all as gt  # type: ignore
from graph_tool.topology import shortest_distance, label_biconnected_components  # type: ignore

from puzzle import Puzzle


def calculate_metrics(g: gt.Graph, puzzle: Puzzle) -> dict:
    """Calcula les mètriques del graf.
    - Moviments mínims per arribar a la millor solució
    - Número total d'estats
    - Diàmetre del graf
    - Punts d'articulació de la solució òptima
    - Average branching factor del graf
    """

    vp_is_start = g.vp["is_start"]
    vp_is_goal  = g.vp["is_goal"]

    start_vertex = next(v for v in g.vertices() if vp_is_start[v])
    goal_vertices = [v for v in g.vertices() if vp_is_goal[v]]

    dist_from_start = shortest_distance(g, start_vertex)

    #------------------------------------------
    min_moves = min(int(dist_from_start[v]) for v in goal_vertices)
    
    #------------------------------------------
    num_states = g.num_vertices()

    #------------------------------------------
    diameter = max([int(dist_from_start[v]) for v in g.vertices() if int(dist_from_start[v]) < 2**30])

    #------------------------------------------
     # Busquem el goal que tingui la distància mínima
    best_goal = min(goal_vertices, key=lambda v: dist_from_start[v]) #type: ignore
    min_total_dist = int(dist_from_start[best_goal])

    dist_from_best_goal = shortest_distance(g, best_goal) #VertexPropertyMap

    edge_is_optimal = g.new_edge_property("bool") #EdgePropertyMap
    for e in g.edges():
        u, v = e.source(), e.target()
        dist_start_u, dist_start_v = dist_from_start[u], dist_from_start[v]
        dist_goal_u, dist_goal_v = dist_from_best_goal[u], dist_from_best_goal[v]

        # L'aresta és part del camí crític cap al millor goal
        if (dist_start_u + 1 + dist_goal_v == min_total_dist) or (dist_start_v + 1 + dist_goal_u == min_total_dist):
            edge_is_optimal[e] = True
    
    # Creem una vista del graf que només contingui els camins òptims
    g_optimal = gt.GraphView(g, efilt=edge_is_optimal)

    # Els punts d'articulació són "passos obligats" per mantenir l'optimitat
    _, art, _ = label_biconnected_components(g_optimal)  # type: ignore
    num_articulation_points = int(sum(art.a))

    #------------------------------------------
    # Això mesura la llibertat de moviment total del puzzle
    total_degrees = sum(v.out_degree() for v in g.vertices())
    avg_branching_factor = total_degrees / num_states

    return {
        "min_moves": min_moves,
        "num_states": num_states,
        "diameter": diameter,
        "articulation_points_optimal": num_articulation_points,
        "avg_branching_factor": avg_branching_factor
    }



def calculate_stars(metrics: dict) -> float:
    """
    Calcula una valoració d'1 a 5 estrelles normalitzant cada component de 0 a 1.
    """
    
    # 1. MOVIMENTS (min_moves) -> Rang [0, 1]
    s_diff = metrics["min_moves"] / (metrics["min_moves"] + 15)

    # 2. MIDA (num_states) -> Rang [0, 1]
    s_scale = math.log(metrics["num_states"] + 1) / (math.log(metrics["num_states"] + 1) + 2)

    # 3. COLL D'AMPOLLA (Articulació) -> Rang [0, 1]
    if metrics["min_moves"] > 0:
        ratio_art = metrics["articulation_points_optimal"] / metrics["min_moves"]
        s_strategy = max(0.0, 1.0 - (abs(ratio_art - 0.15) / 0.25))
    else:
        s_strategy = 0

    # 4. DECISIÓ (avg_branching_factor) -> Rang [0, 1]
    # Si s'allunya més de 2 del 3 (b_ideal), la nota és 0
    b_ideal = 3
    branching_factor = metrics["avg_branching_factor"]
    if branching_factor <= 2:
        s_branch = 0
    else:
        s_branch = max(0.0, 1.0 - (abs(branching_factor - b_ideal) / 2))

    # 5. EXPLORACIÓ (diametre) -> Rang [0, 1]
    if metrics["diameter"] > 0:
        s_exploration = 1 - (metrics["min_moves"] / (metrics["diameter"]))
    else:
        s_exploration = 0

    # PONDERACIÓ FINAL
    # Ara totes les s_ estan entre 0.0 i 1.0
    puntuacio_ponderada = (
        s_diff        * 0.25 +
        s_scale       * 0.15 +
        s_strategy    * 0.20 + # El 30% del pes és l'estratègia
        s_branch      * 0.25 +
        s_exploration * 0.15
    )

    # Transformació: 1 estrella base + (0 a 4 estrelles addicionals)
    # Si puntuacio_ponderada és 1.0, el resultat és 5.0
    # Si puntuacio_ponderada és 0.0, el resultat és 1.0
    return round(1 + (puntuacio_ponderada * 4), 1)



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

    g = gt.load_graph(str(graphml_path))
    puzzle = Puzzle.from_json(puzzle_path.read_text())

    metrics = calculate_metrics(g, puzzle)
    stars   = calculate_stars(metrics)

    print(f"\n--- Resultats per a {puzzle_path.name} ---")
    print(f"  Moviments mínims:   {metrics['min_moves']}")
    print(f"  Estats totals:      {metrics['num_states']}")
    print(f"  Diàmetre del graf:  {metrics['diameter']}")
    print(f"  Colls d'ampolla òptims:      {metrics['articulation_points_optimal']}")
    print(f"  Average branching factor:   {metrics['avg_branching_factor']:.4f}")

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
