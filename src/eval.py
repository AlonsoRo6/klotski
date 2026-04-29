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


def calculate_metrics(g: gt.Graph, puzzle: Puzzle) -> dict: # type: ignore
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
    branching_factor = [v.out_degree() for v in g.vertices()]
    total_degrees = sum(branching_factor)
    avg_branching_factor = total_degrees / num_states
    variancia = sum((bf-avg_branching_factor)**2 for bf in branching_factor) / num_states
    std = math.sqrt(variancia)

    return {
        "min_moves": min_moves,
        "num_states": num_states,
        "articulation_points_optimal": num_articulation_points,
        "avg_branching_factor": avg_branching_factor,
        "variancia_branching_factor": std
    }



def calculate_stars(metrics: dict, puzzle:Puzzle) -> float: # type: ignore
    """
    Calcula una valoració d'1 a 5 estrelles normalitzant cada component de 0 a 1.
    """
    # 1. MOVIMENTS (min_moves) -> Rang [0, 1]
    s_diff = metrics["min_moves"] / (puzzle.W*puzzle.H)


    # 2. MIDA (num_states) -> Rang [0, 1]
    s_scale = math.log(metrics["num_states"])

    # 3. COLL D'AMPOLLA (Articulació) -> Rang [0, 1]
    
    s_strategy = metrics["articulation_points_optimal"] / metrics["min_moves"]


    # 4. DECISIÓ (avg_branching_factor) -> Rang [0, 1]
    # Si s'allunya més de 2 del 3 (b_ideal), la nota és 0

    s_branch = metrics["avg_branching_factor"] * (1 + metrics["variancia_branching_factor"] / metrics["avg_branching_factor"])



     
    def sigmoid(x:float, mu:float, k:float):
        return 1 / (1 + math.exp(-k * (x - mu)))

    def gaussian(x:float, mu:float, k:float):
        return math.exp(-k * (x - mu) ** 2)


    f1 = sigmoid(s_diff, mu=0.80, k=8.0)
    f2 = sigmoid(s_scale, mu=3.0, k=2.0)
    f4 = gaussian(s_strategy,  mu=0.45, k=6.0)
    f5 = sigmoid(s_branch, mu=4.00, k=0.5)
    
    # PONDERACIÓ FINAL
    puntuacio =  0.30 * f1 + 0.30 * f2 + 0.20 * f4 + 0.20 * f5

    return round(1 + (puntuacio * 4), 2)



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
    stars   = calculate_stars(metrics, puzzle)

    print(f"\n--- Resultats per a {puzzle_path.name} ---")
    print(f"  Moviments mínims:   {metrics['min_moves']}")
    print(f"  Estats totals:      {metrics['num_states']}")
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
