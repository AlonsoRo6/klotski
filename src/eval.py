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
import os
import pandas as pd # Utilitzem pandas per facilitar la gestió del CSV
from typing import Any


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

    return {
        "size": puzzle.W * puzzle.H,
        "min_moves": min_moves,
        "num_states": num_states,
        "articulation_points_optimal": num_articulation_points,
        "avg_branching_factor": avg_branching_factor,
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




CSV_PATH = 'puzzles_metrics.csv'

def save_metrics_to_csv(puzzle_id: str, metrics: dict[str, Any], score: float) -> None:
    """
    Guarda o actualitza les mètriques d'un puzzle al fitxer CSV, mantenint les notes manuals.
    """
    # Estructura de la nova fila
    new_data: dict[str, Any] = {
        'id': puzzle_id,
        'size': metrics["size"],
        'min_moves': metrics['min_moves'],
        'total_states': metrics['num_states'],
        'articulation_points': metrics['articulation_points_optimal'],
        'avg_branching': metrics['avg_branching_factor'],
        'score': score,
        'manual_score': None  # Es mantindrà si ja existia
    }

    df: pd.DataFrame
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH)
        
        # Comprovar si el puzzle ja és al CSV per no duplicar i mantenir la nota manual
        if puzzle_id in df['id'].values:
            idx = df[df['id'] == puzzle_id].index[0]
            
            # Preservem la manual_score actual si no és nul·la
            current_manual = df.at[idx, 'manual_score']
            new_data['manual_score'] = current_manual
            
            # Actualitzem els valors de la fila existent
            for key, value in new_data.items():
                df.at[idx, key] = value
        else:
            # Si el puzzle és nou, l'afegim com a nova fila
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    else:
        # Si el fitxer no existeix, el creem de zero amb la primera fila
        df = pd.DataFrame([new_data])

    # Guardem el fitxer (sobrescrivint l'anterior amb les dades actualitzades)
    df.to_csv(CSV_PATH, index=False)
    print(f"Mètriques de '{puzzle_id}' actualitzades al CSV.")
    



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


    puzzle_id = puzzle_path.stem.split("_")[-1]
    metrics = calculate_metrics(g, puzzle)
    score = calculate_stars_2(metrics, puzzle)
    save_metrics_to_csv(puzzle_id, metrics, score)


    print(f"\n--- Resultat per a {puzzle_path.name} ---")
    print(f"\n  ⭐ Valoració: {score} / 5.0")