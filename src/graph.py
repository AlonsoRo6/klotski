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


def build_graph(puzzle: Puzzle) -> gt.Graph:
    """
    Construeix el graf del puzzle fent un DFS des de l'estat inicial.
    Cada node és un estat, cada aresta és un moviment d'un pas.
    """
    g = gt.Graph(directed=False)

    # Propietats dels nodes
    vp_state = g.new_vertex_property("string")
    vp_is_start = g.new_vertex_property("bool")
    vp_is_goal = g.new_vertex_property("bool")

    # Propietat del graf: guardem el puzzle en JSON
    gp_puzzle = g.new_graph_property("string")
    gp_puzzle[g] = puzzle.to_json()
    g.graph_properties["puzzle"] = gp_puzzle

    state_to_vertex: dict[State, gt.Vertex] = {}

    def get_or_create(state: State) -> gt.Vertex:
        if state not in state_to_vertex:
            v = g.add_vertex()
            vp_state[v] = state_to_str(state)
            vp_is_start[v] = (state == puzzle.start)
            vp_is_goal[v] = is_goal(puzzle, state)
            state_to_vertex[state] = v
        return state_to_vertex[state]

    # DFS iteratiu
    stack = [puzzle.start]
    get_or_create(puzzle.start)

    while stack:
        state = stack.pop()
        v_cur = state_to_vertex[state] #el vertex ja ha estat creat

        for move in possible_moves(puzzle, state):
            new_state = apply_move(puzzle, state, move)

            if new_state not in state_to_vertex:
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

    g = build_graph(puzzle)

    n_goals = sum(1 for v in g.vertices() if g.vp["is_goal"][v])
    print(f"Nodes (estats): {g.num_vertices()}")
    print(f"Arestes (moviments): {g.num_edges()}")
    print(f"Estats finals: {n_goals}")
    print(f"Resoluble: {'Sí' if n_goals > 0 else 'No'}")

    g.save(str(output_path))
    print(f"Graf guardat a {output_path}")