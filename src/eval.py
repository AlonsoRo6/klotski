"""
Avalua un puzzle fent servir unes mètriques específiques, i guarda la valoració a la carpeta evals.

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


def ramp_up(x:float, good:float=0.5, cap:float=1.0):
    """Millor com més alt, però cap a partir de 'cap'. Bo a partir de 'good'."""
    if x >= cap: return 1.0
    if x <= 0:   return 0.0
    return x / cap

def tent(x:float, peak:float=0.4, width:float=0.3):
    """Punt òptim a 'peak', cau linealment a banda i banda dins 'width'."""
    dist = abs(x - peak)
    if dist >= width: return 0.0
    return 1.0 - dist / width

def calculate_stars_2(metrics: dict, puzzle: Puzzle) -> float: #type: ignore
    W, H = puzzle.W, puzzle.H
    max_cells = W * H

    s_difficulty  = min(metrics["min_moves"] / max_cells, 1.0)
    
    
    log_max       = sum(math.log(i) for i in range(1, max_cells + 1))
    s_scale       = min(math.log(max(metrics["num_states"], 1)) / log_max, 1.0)


    s_bottleneck  = min(metrics["articulation_points_optimal"] / max(metrics["min_moves"], 1), 1.0)


    total_cells = sum(len(piece.coords) for piece in puzzle.pieces)
    occupancy = total_cells / (puzzle.W * puzzle.H) 
    # Com més ocupat està el taulell, menys moviments són possibles
    # Un taulell al 90% d'ocupació gairebé no té moviments lliures
    max_branching = 4 * len(puzzle.pieces) * (1 - occupancy)
    s_freedom = min(metrics["avg_branching_factor"] / max(max_branching, 1.0), 1.0)
    

    moviments = ramp_up(s_difficulty, cap=0.8)
    mida = ramp_up(s_scale,      cap=0.35)
    ampolla = tent(s_bottleneck, peak=0.4, width=0.35)
    llibertat = tent(s_freedom,    peak=0.4, width=0.35)
    
    print(f'Moviments: {moviments}')
    print(f'Mida: {mida}')
    print(f"Colls d'ampolla: {ampolla}")
    print(f'Graus llibertat: {llibertat}')

    score = (
        0.35 * moviments +  # bo si supera ~40% del taulell
        0.30 * mida +  # bo si hi ha molts estats
        0.20 * ampolla +  # òptim: uns pocs embuts
        0.15 * llibertat    # òptim: branching moderat
    )

    return round(1 + score * 4)


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
    stars   = calculate_stars_2(metrics, puzzle)

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
