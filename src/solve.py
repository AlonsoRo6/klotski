"""
Resolució d'un puzzle de peces lliscants mitjançant el graf d'estats.

Ús: python src/solve.py graphs/<graf.graphml> solutions/<output.sol.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import graph_tool.all as gt #type:ignore

from puzzle import Puzzle
from graph import state_key

def find_shortest_path(g: gt.Graph) -> list[int] | None:
    vp_is_start = g.vp["is_start"]
    vp_is_goal  = g.vp["is_goal"]

    # Trobar el node inicial
    start_v = None
    for v in g.vertices():
        if vp_is_start[v]:
            start_v = v
            break

    if start_v is None:
        raise ValueError("No s'ha trobat el node inicial al graf")


    goals = [v for v in g.vertices() if vp_is_goal[v]]

    if not goals:
        return None
    
    #trobem el goal que està més a prop
    dist_map = gt.shortest_distance(g, start_v) 

    best_goal = min(goals, key=lambda v: dist_map[v]) # type: ignore
    best_path = gt.shortest_path(g, start_v, best_goal)[0]

    return [int(v) for v in best_path]


def path_to_moves(
    g: gt.Graph, puzzle: Puzzle, path: list[int]
) -> list[tuple[int, str, int]]:
    
    vp_state = g.vp["state"]

    moves = []
    for i in range(len(path) - 1):
        key_cur = state_key(puzzle, vp_state[g.vertex(path[i])])
        key_nxt = state_key(puzzle, vp_state[g.vertex(path[i + 1])])

        for piece_idx, (pos_cur, pos_nxt) in enumerate(zip(key_cur, key_nxt)):
            if pos_cur != pos_nxt:
                dx = pos_nxt[0] - pos_cur[0]
                dy = pos_nxt[1] - pos_cur[1]

                if dx > 0:
                    direction, dist = "E", dx
                elif dx < 0:
                    direction, dist = "W", -dx
                elif dy > 0:
                    direction, dist = "S", dy
                else:
                    direction, dist = "N", -dy

                moves.append((piece_idx, direction, dist))
                break

    return moves


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Ús: python src/solve.py <graf.graphml> <output.sol.json>")
        sys.exit(1)

    graphml_path = Path(sys.argv[1])
    output_path  = Path(sys.argv[2])

    g = gt.load_graph(str(graphml_path))
    print(f"Graf: {g.num_vertices()} vèrtexs, {g.num_edges()} arestes")

    puzzle = Puzzle.from_json(g.gp["puzzle"])

    path = find_shortest_path(g)

    if path is None:
        print("El puzzle no té solució")
        sys.exit(1)

    print(f"Solució trobada: {len(path) - 1} moviments")

    moves = path_to_moves(g, puzzle, path)
    output_path.write_text(json.dumps([[p, d, dist] for p, d, dist in moves]))
    print(f"Solució guardada a {output_path}")