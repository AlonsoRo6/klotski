"""
Resolució d'un puzzle de peces lliscants mitjançant el graf d'estats.

Ús: python src/solve.py graphs/<graf.graphml> solutions/<output.sol.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import deque

import graph_tool.all as gt #type:ignore

from puzzle import Puzzle, State
from graph import state_key, StateKey


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

    # Usem shortest_path de graph-tool cap a cada node goal
    # i ens quedem amb el camí més curt

    visited: dict[int, int|None] = {int(start_v): None}
    queue = deque([start_v])

    while queue:
        v = queue.popleft()

        if vp_is_goal[v]: #reconstruir el camí
            path = []
            current = int(v)
            while current is not None:
                path.append(current)
                current = visited[current]
            return list(reversed(path))

        for neighbor in v.out_neighbors():
            n_idx = int(neighbor)
            if n_idx not in visited:
                visited[n_idx] = int(v)  # guardem el pare
                queue.append(neighbor)


    '''best_path = None

    for v in g.vertices():
        if not vp_is_goal[v]:
            continue
        vlist, _ = gt.shortest_path(g, g.vertex(start_idx), v)  # type: ignore
        if len(vlist) == 0:
            continue
        if best_path is None or len(vlist) < len(best_path):
            best_path = [int(u) for u in vlist]

    return best_path'''


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

    print(f"Carregant graf {graphml_path}...")
    g = gt.load_graph(str(graphml_path))
    print(f"Graf: {g.num_vertices()} vèrtexs, {g.num_edges()} arestes")

    puzzle = Puzzle.from_json(g.gp["puzzle"])

    print("Cercant camí mínim...")
    path = find_shortest_path(g)

    if path is None:
        print("El puzzle no té solució!")
        sys.exit(1)

    print(f"Solució trobada: {len(path) - 1} moviments")

    moves = path_to_moves(g, puzzle, path)
    output_path.write_text(json.dumps([[p, d, dist] for p, d, dist in moves]))
    print(f"Solució guardada a {output_path}")