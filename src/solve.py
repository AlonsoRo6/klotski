'''
Crea la solució d'un puzzle donat el seu graf.

Ús: python3 src/solve.py <graf.graphml> <output.sol.json>
'''

from __future__ import annotations
import json
import sys
from pathlib import Path
import graph_tool.all as gt  # type: ignore
from puzzle import Puzzle, State
from graph import state_key, get_normalized_id
from logic import possible_moves, apply_move


def find_shortest_path(g: gt.Graph) -> list[int] | None:
    '''Donat un graf, retorna una llista amb l'índex dels estats
    del camí més curt de l'estat inicial a un goal'''
    vp_is_start = g.vp["is_start"]
    vp_is_goal  = g.vp["is_goal"]

    start_v = next((v for v in g.vertices() if vp_is_start[v]), None)
    if start_v is None:
        raise ValueError("No hi ha node inicial")

    goals = [v for v in g.vertices() if vp_is_goal[v]]
    if not goals:
        return None

    dist_map = gt.shortest_distance(g, start_v)
    best_goal = min(goals, key=lambda v: dist_map[v])  # type: ignore
    best_path = gt.shortest_path(g, start_v, best_goal)[0]

    return [int(v) for v in best_path]


def path_to_moves(
    g: gt.Graph, puzzle: Puzzle, path: list[int]
) -> list[tuple[int, str, int]]:
    """
    Reconstrueix la seqüència de moviments del camí donada una llista path amb l'índex
    dels estats que conformen la solució més curta.

    Per cada pas del camí, sabem l'estat normalitzat destí (guardat al graf).
    Busquem quin moviment vàlid des de l'estat real actual porta a un estat
    que tingui el mateix identificadot únic que el node destí.
    Així evitem qualsevol problema amb peces idèntiques reordenades.
    """
    vp_state = g.vp["state"]

    moves: list[tuple[int, str, int]] = []
    real_state: State = puzzle.start

    for i in range(len(path) - 1):
        # Identificador únic de l'estat destí al graf
        dest_key = get_normalized_id(
            puzzle, State(state_key(puzzle, vp_state[g.vertex(path[i + 1])]))
        )

        # Provem tots els moviments vàlids d'un pas des de l'estat real actual
        found = False
        for move in possible_moves(puzzle, real_state):
            candidate = apply_move(puzzle, real_state, move)
            if get_normalized_id(puzzle, candidate) == dest_key:
                piece_idx, direction, dist = move
                moves.append((piece_idx, direction, dist))
                real_state = candidate
                found = True
                break

        if not found:
            raise ValueError(
                f"No s'ha trobat cap moviment vàlid per al pas {i} → {i+1} "
                f"del camí. L'estat al graf pot estar corrupte."
            )

    return moves


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Ús: python src/solve.py <graf.graphml> <output.sol.json>")
        sys.exit(1)

    graphml_path = Path(sys.argv[1])
    output_path  = Path(sys.argv[2])

    g = gt.load_graph(str(graphml_path))

    puzzle = Puzzle.from_json(g.gp["puzzle"])
    path = find_shortest_path(g)

    if path is None:
        print("El puzzle no té solució")
        sys.exit(1)

    print(f"Solució trobada: {len(path) - 1} moviments")

    moves = path_to_moves(g, puzzle, path)
    output_path.write_text(json.dumps([[p, d, dist] for p, d, dist in moves]))
    print(f"Solució guardada a {output_path}")
    