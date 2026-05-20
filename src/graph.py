"""
Construcció del graf d'un puzzle.

Ús: python src/graph.py <puzzle.json> <output.graphml>
"""

from __future__ import annotations

import sys
from pathlib import Path

import graph_tool.all as gt  # type: ignore

from puzzle import Puzzle, State
from logic import possible_moves, apply_move, is_goal, astar_path
from typing import cast
import pandas as pd
import os
from graph_tool.topology import shortest_distance, label_biconnected_components  # type: ignore

# StateKey és una tupla de posicions que identifica un estat
StateKey = tuple[tuple[int, int], ...]
import os

CSV_PATH = os.environ.get("KLOTSKI_CSV_PATH", "puzzles_metrics.csv")


def calculate_metrics_in_graph(g: gt.Graph, puzzle: Puzzle) -> dict:  # type: ignore
    """Càlcul de mètriques idèntic al de eval.py"""
    vp_is_start = g.vp["is_start"]
    vp_is_goal = g.vp["is_goal"]

    start_vertex = next(v for v in g.vertices() if vp_is_start[v])
    goal_vertices = [v for v in g.vertices() if vp_is_goal[v]]

    if not goal_vertices:
        return {}

    dist_from_start = shortest_distance(g, start_vertex)
    min_moves = min(int(dist_from_start[v]) for v in goal_vertices)
    num_states = g.num_vertices()

    best_goal = min(goal_vertices, key=lambda v: dist_from_start[v])  # type: ignore
    min_total_dist = int(dist_from_start[best_goal])
    dist_from_best_goal = shortest_distance(g, best_goal)

    edge_is_optimal = g.new_edge_property("bool")
    for e in g.edges():
        u, v = e.source(), e.target()
        if (dist_from_start[u] + 1 + dist_from_best_goal[v] == min_total_dist) or (
            dist_from_start[v] + 1 + dist_from_best_goal[u] == min_total_dist
        ):
            edge_is_optimal[e] = True

    g_optimal = gt.GraphView(g, efilt=edge_is_optimal)
    _, art, _ = label_biconnected_components(g_optimal)
    num_articulation_points = sum(art.a)

    avg_branching = sum(v.out_degree() for v in g.vertices()) / num_states

    return {
        "size": puzzle.W * puzzle.H,
        "min_moves": min_moves,
        "num_states": num_states,
        "articulation_points": num_articulation_points,
        "avg_branching": avg_branching,
    }


def save_metrics_to_csv(puzzle_id: str, metrics: dict, csv_path: str):  # type: ignore
    """Guarda les mètriques al CSV sense la nota (que es posarà a eval.py)"""
    if not metrics:
        return

    new_data = {
        "id": puzzle_id,
        "size": metrics["size"],
        "min_moves": metrics["min_moves"],
        "total_states": metrics["num_states"],
        "articulation_points": metrics["articulation_points"],
        "avg_branching": metrics["avg_branching"],
    }

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        if puzzle_id in df["id"].values:
            idx = df[df["id"] == puzzle_id].index[0]
            for key, value in new_data.items():
                df.at[idx, key] = value
        else:
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    else:
        df = pd.DataFrame([new_data])

    df.to_csv(CSV_PATH, index=False)
    print(f"Mètriques guardades al CSV per a {puzzle_id}")


def state_key(puzzle: Puzzle, state_str: str | State) -> StateKey:
    """
    Converteix un estat en una StateKey.
    Accepta tant un string guardat al graf com un objecte State.
    """
    if isinstance(state_str, State):
        return state_str.positions
    parts = state_str.split(";")
    return cast(StateKey, tuple(tuple(int(v) for v in p.split(",")) for p in parts))


def state_to_str(state: State) -> str:
    """Converteix un State a string per guardar-lo al graf."""
    return ";".join(f"{x},{y}" for x, y in state.positions)


def get_normalized_id(puzzle: Puzzle, state: State) -> tuple:  # type: ignore
    """
    Genera un identificador únic que ignora l'ordre de peces idèntiques,
    però mantenint fixes les peces que apareixen als objectius (goal pieces),
    per evitar que la normalització confongui estats on la peça objectiu
    és a la posició meta amb estats on és una altra peça idèntica la que hi és.
    """

    goal_piece_indices: set[int] = {i for i, _ in puzzle.goals}

    fixed: list[tuple] = []  # type: ignore | peces objectiu: es guarden amb el seu índex

    grouped: dict[tuple, list[tuple]] = {}  # type: ignore | peces lliures: agrupades per forma

    for i, pos in enumerate(state.positions):
        shape = tuple(tuple(p) for p in puzzle.pieces[i].coords)
        if i in goal_piece_indices:
            # La peça objectiu es tracta com a única: l'índex forma part de la clau
            fixed.append((i, shape, pos))
        else:
            # Les peces no-objectiu amb la mateixa forma són intercanviables
            if shape not in grouped:
                grouped[shape] = []
            grouped[shape].append(pos)

    free_part = tuple(
        sorted(
            (shape, tuple(sorted(positions))) for shape, positions in grouped.items()
        )
    )
    fixed_part = tuple(sorted(fixed))

    return (fixed_part, free_part)


NODE_LIMIT = 2_500_000


def build_graph(puzzle: Puzzle, node_limit: int = NODE_LIMIT) -> gt.Graph:
    """
    Construeix el graf del puzzle fent un DFS des de l'estat inicial.
    """
    g = gt.Graph(directed=False)

    # Propietats dels nodes
    vp_state = g.new_vertex_property("string")
    vp_is_start = g.new_vertex_property("bool")
    vp_is_goal = g.new_vertex_property("bool")

    # Propietat del graf
    gp_puzzle = g.new_graph_property("string")
    gp_puzzle[g] = puzzle.to_json()
    g.graph_properties["puzzle"] = gp_puzzle

    # La clau del diccionari és la versió normalitzada de l'estat
    state_to_vertex: dict[tuple, gt.Vertex] = {}  # type: ignore

    def get_or_create(state: State) -> gt.Vertex:
        key = get_normalized_id(puzzle, state)  # Normalitzem l'estat
        if key not in state_to_vertex:  # si encara no l'havíem visitat: creem
            v = g.add_vertex()
            vp_state[v] = state_to_str(state)
            vp_is_start[v] = state == puzzle.start
            vp_is_goal[v] = is_goal(puzzle, state)
            state_to_vertex[key] = v
        return state_to_vertex[key]

    stack = [puzzle.start]
    get_or_create(puzzle.start)
    
    i = 1
    while stack:
        if len(state_to_vertex) >= node_limit:
            print(f"Límit de nodes superat ({node_limit}). S'atura la cerca.")
            
            # Injectem el camí òptim mitjançant A* perquè el graf trobi la solució
            print("Executant A* per trobar el camí òptim des de l'inici...")
            opt_path = astar_path(puzzle, max_states=3_000_000)
            if opt_path:
                print(f"A* ha trobat una solució de {len(opt_path)-1} passos. Injectant-la al graf per validar...")
                for i in range(len(opt_path) - 1):
                    st_u = State(opt_path[i])
                    st_v = State(opt_path[i+1])
                    v_u = get_or_create(st_u)
                    v_v = get_or_create(st_v)
                    if not g.edge(v_u, v_v):
                        g.add_edge(v_u, v_v)
            else:
                print("L'A* tampoc ha trobat solució o ha excedit el límit.")
            break

        if i % 100000 == 0:
            print(f"{i}, queue:{len(stack)}, nodes:{len(state_to_vertex)}")
        i += 1

        state = stack.pop()
        v_cur = get_or_create(state)

        for move in possible_moves(puzzle, state):
            new_state = apply_move(puzzle, state, move)
            new_key = get_normalized_id(puzzle, new_state)

            if new_key not in state_to_vertex:
                stack.append(new_state)

            v_new = get_or_create(new_state)

            if not g.edge(v_cur, v_new):
                g.add_edge(v_cur, v_new)

    g.vertex_properties["state"] = vp_state
    g.vertex_properties["is_start"] = vp_is_start
    g.vertex_properties["is_goal"] = vp_is_goal

    return g


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Ús: python src/graph.py <puzzle.json> <output.graphml> [<csv_path>]")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if len(sys.argv) > 3:
        CSV_PATH = sys.argv[3]

    try:
        puzzle = Puzzle.from_json(json_path.read_text())

        print("Executant graph.py")
        g = build_graph(puzzle)

        puzzle_id = json_path.stem.split("_")[-1]
        metrics = calculate_metrics_in_graph(g, puzzle)
        save_metrics_to_csv(puzzle_id, metrics, CSV_PATH)

        n_goals = sum(1 for v in g.vertices() if g.vp["is_goal"][v])
        print(f"Nodes (estats): {g.num_vertices()}")
        print(f"Arestes (moviments): {g.num_edges()}")
        print(f"Estats finals: {n_goals}")
        print(f"Resoluble: {'Sí' if n_goals > 0 else 'No'}")

        g.save(str(output_path))
        print(f"Graf guardat a {output_path}")

    except Exception as e:
        print(f"Error: {e}")
