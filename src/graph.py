"""
Construcció del graf d'un puzzle de peces lliscants.

Ús: python src/graph.py <puzzle.json> <output.graphml>
"""

from __future__ import annotations

import sys
from pathlib import Path

import graph_tool.all as gt #type:ignore

from puzzle import Puzzle, State
from logic import possible_moves, apply_move, is_goal
from typing import cast

# StateKey és una tupla de posicions que identifica un estat
StateKey = tuple[tuple[int, int], ...]


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


def get_normalized_id(puzzle: Puzzle, state: State) -> tuple: #type:ignore
    """Genera una signatura única que ignora l'ordre de peces idèntiques."""
    grouped: dict[tuple,list[tuple]] = {} #type: ignore
    for i, pos in enumerate(state.positions):
        # Fem servir les coordenades de la peça (forma) com a clau
        shape = tuple(tuple(p) for p in puzzle.pieces[i].coords)
        if shape not in grouped:
            grouped[shape] = []
        grouped[shape].append(pos)
    
    # Ordenem posicions de peces iguals i després les formes
    return tuple(sorted((shape, tuple(sorted(positions))) for shape, positions in grouped.items()))

def build_graph(puzzle: Puzzle) -> gt.Graph:
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

    # OPTIMITZACIÓ: La clau del dict és la versió normalitzada de l'estat
    state_to_vertex: dict[tuple, gt.Vertex] = {} #type: ignore

    def get_or_create(state: State) -> gt.Vertex:
        key = get_normalized_id(puzzle, state) # Normalitzem aquí
        if key not in state_to_vertex:
            v = g.add_vertex()
            vp_state[v] = state_to_str(state)
            vp_is_start[v] = (state == puzzle.start)
            vp_is_goal[v] = is_goal(puzzle, state)
            state_to_vertex[key] = v
        return state_to_vertex[key]



    stack = [puzzle.start]
    get_or_create(puzzle.start)
    
    i = 0
    while stack:
        if i%1000 == 0:
            print(i)
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
        print(f"Ús: python src/graph.py <puzzle.json> <output.graphml>")
        sys.exit(1)

    json_path   = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    puzzle = Puzzle.from_json(json_path.read_text())

    print('Executant graph.py')
    g = build_graph(puzzle)

    n_goals = sum(1 for v in g.vertices() if g.vp["is_goal"][v])
    print(f"Nodes (estats): {g.num_vertices()}")
    print(f"Arestes (moviments): {g.num_edges()}")
    print(f"Estats finals: {n_goals}")
    print(f"Resoluble: {'Sí' if n_goals > 0 else 'No'}")

    g.save(str(output_path))
    print(f"Graf guardat a {output_path}")