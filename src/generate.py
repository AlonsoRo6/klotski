"""
Generador de puzzles de Klotski canònics.

Implementa tres estratègies de generació:
  - 'classic'  : taulell 4x5 amb peça 2x2 principal (Klotski clàssic)
  - 'freeform' : taulell i peces aleatòries dins uns paràmetres
  - 'walls'    : taulell amb parets que creen laberints

Ús:
  python src/generate.py [--strategy classic|freeform|walls]
                         [--count N]
                         [--min-stars X]
                         [--out-dir DIR]
                         [--seed S]

Exemples:
  python src/generate.py --strategy classic --count 5 --min-stars 2.5
  python src/generate.py --strategy freeform --count 10 --min-stars 2.0
  python src/generate.py --strategy walls --count 5 --min-stars 2.0
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path
from typing import Optional

# ─── Imports del projecte ───────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from puzzle import Coord, Piece, Puzzle, State
from logic  import valid_placement, possible_moves, apply_move, is_goal


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _cells(piece: Piece, pos: Coord) -> set[Coord]:
    px, py = pos
    return {(px + dx, py + dy) for dx, dy in piece.coords}


def _all_occupied(puzzle: Puzzle, state: State) -> set[Coord]:
    occ: set[Coord] = set(puzzle.walls)
    for i, piece in enumerate(puzzle.pieces):
        occ |= _cells(piece, state.positions[i])
    return occ


def _build_puzzle(W: int, H: int,
                  walls: list[Coord],
                  pieces_and_positions: list[tuple[Piece, Coord]],
                  goal_piece_idx: int,
                  goal_pos: Coord) -> Optional[Puzzle]:
    """
    Construeix un Puzzle canònic a partir de les dades en brut.
    Retorna None si la construcció falla per qualsevol motiu.
    """
    try:
        walls_t = tuple(sorted(set(walls)))
        # Ordenació canònica: (forma, posició_inicial)
        sorted_pp = sorted(pieces_and_positions, key=lambda pp: (pp[0], pp[1]))
        # El goal_piece_idx és sobre la llista original; cal trobar on ha anat
        orig_piece  = pieces_and_positions[goal_piece_idx][0]
        orig_pos    = pieces_and_positions[goal_piece_idx][1]
        new_idx = next(
            i for i, (p, pos) in enumerate(sorted_pp)
            if p == orig_piece and pos == orig_pos
        )
        pieces = tuple(p for p, _ in sorted_pp)
        start  = State(tuple(pos for _, pos in sorted_pp))
        goals  = ((new_idx, goal_pos),)
        return Puzzle(W=W, H=H, walls=walls_t, pieces=pieces, start=start, goals=goals)
    except Exception:
        return None


# ════════════════════════════════════════════════════════════════════════════
#  BFS COMPLET per avaluació (sense graph-tool)
# ════════════════════════════════════════════════════════════════════════════

def _full_bfs(puzzle: Puzzle, max_states: int = 100_000) -> dict:
    """
    BFS complet des de l'estat inicial.

    A més de les mètriques bàsiques, estima els 'articulation_points' del
    camí òptim sense necessitar graph-tool:

      - Construeix el graf d'estats complet (adjacència bidireccional).
      - Troba el camí òptim (profunditat mínima fins al goal).
      - Compta els nodes del camí òptim on el grau dins del subgraf òptim
        és exactament 2 (un predecessor + un successor), és a dir, nodes
        per on TOTES les solucions òptimes han de passar forçosament.
        Aquests equivalen als punts d'articulació del subgraf òptim.

    Retorna:
        min_moves, num_states, avg_branching_factor,
        articulation_points (estimació), reachable, truncated
    """
    from collections import deque

    start = puzzle.start.positions

    # dist[estat] = profunditat mínima des de l'inici
    dist: dict[tuple, int] = {start: 0}
    # adjacència: estat -> conjunt de veïns (bidireccional, tots els estats)
    adj: dict[tuple, set[tuple]] = {start: set()}

    queue: deque[tuple] = deque([start])
    min_moves = None
    best_goal_state: tuple | None = None
    total_out = 0
    num_states = 0

    while queue and num_states < max_states:
        pos_tuple = queue.popleft()
        state     = State(pos_tuple)
        depth     = dist[pos_tuple]
        num_states += 1

        if is_goal(puzzle, state):
            if min_moves is None or depth < min_moves:
                min_moves = depth
                best_goal_state = pos_tuple

        moves = possible_moves(puzzle, state)
        total_out += len(moves)
        for move in moves:
            nstate = apply_move(puzzle, state, move)
            nb = nstate.positions
            # Afegim l'aresta en ambdues direccions
            adj[pos_tuple].add(nb)
            if nb not in dist:
                dist[nb] = depth + 1
                adj[nb] = {pos_tuple}
                queue.append(nb)
            else:
                adj.setdefault(nb, set()).add(pos_tuple)

    avg_bf    = total_out / max(num_states, 1)
    reachable = min_moves is not None
    truncated = num_states >= max_states

    # ── Estimació dels punts d'articulació del subgraf òptim ────────────────
    articulation_points = 0
    if reachable and best_goal_state is not None:
        min_d = min_moves  # type: ignore[assignment]
        goal_dist: dict[tuple, int] = {}

        # BFS invers des del millor goal per obtenir dist_goal[estat]
        gqueue: deque[tuple] = deque([best_goal_state])
        goal_dist[best_goal_state] = 0
        while gqueue:
            cur = gqueue.popleft()
            for nb in adj.get(cur, set()):
                if nb not in goal_dist:
                    goal_dist[nb] = goal_dist[cur] + 1
                    gqueue.append(nb)

        # Subgraf òptim: arestes (u,v) on dist[u]+1+goal_dist[v] == min_d
        # (o dist[v]+1+goal_dist[u] == min_d, ja que el graf és no dirigit)
        opt_adj: dict[tuple, set[tuple]] = {}
        for u, neighbours in adj.items():
            du = dist.get(u)
            if du is None or du > min_d:
                continue
            for v in neighbours:
                dv = dist.get(v)
                gv = goal_dist.get(v)
                gu = goal_dist.get(u)
                if dv is not None and gv is not None and gu is not None:
                    if du + 1 + gv == min_d or dv + 1 + gu == min_d:
                        opt_adj.setdefault(u, set()).add(v)
                        opt_adj.setdefault(v, set()).add(u)

        # Punt d'articulació del subgraf òptim: node (ni start ni goal) amb
        # grau == 2 dins del subgraf òptim on el predecessor i successor
        # estan a profunditats dist-1 i dist+1 respectivament.
        # Equivalentment: un sol camí passa per ell → és un coll d'ampolla.
        for node, neighbours in opt_adj.items():
            if node == start or node == best_goal_state:
                continue
            d = dist.get(node, -1)
            preds = [n for n in neighbours if dist.get(n, -1) == d - 1]
            succs = [n for n in neighbours if dist.get(n, -1) == d + 1]
            # Si té exactament 1 predecessor i 1 successor en el subgraf
            # òptim, és un punt d'articulació (coll d'ampolla obligatori)
            if len(preds) == 1 and len(succs) == 1:
                articulation_points += 1

    return {
        "size":                    puzzle.W * puzzle.H,
        "min_moves":               min_moves,
        "num_states":              num_states,
        "avg_branching_factor":    avg_bf,
        "articulation_points":     articulation_points,
        "reachable":               reachable,
        "truncated":               truncated,
    }


# ════════════════════════════════════════════════════════════════════════════
#  PREDICCIÓ D'ESTRELLES AMB EL MODEL ENTRENAT
# ════════════════════════════════════════════════════════════════════════════

def _load_model(model_path: Path = Path("model_difficulty.pkl")):
    """Carrega el model de ML. Retorna None si no existeix."""
    if not model_path.exists():
        # Buscar també un nivell amunt (si s'executa des de src/)
        alt = model_path.parent.parent / model_path.name
        if alt.exists():
            model_path = alt
        else:
            return None
    try:
        import joblib  # type: ignore
        return joblib.load(model_path)
    except Exception:
        return None


_MODEL_CACHE = None  # singleton per no recarregar en cada crida


def _predict_stars(metrics: dict) -> float | None:
    """
    Intenta predir les estrelles amb el model de ML.
    Retorna None si el model no està disponible.
    Les features han de coincidir exactament amb les de train_model.py:
        size, min_moves, total_states, articulation_points, avg_branching
    """
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        _MODEL_CACHE = _load_model()
    if _MODEL_CACHE is None:
        return None

    try:
        import pandas as pd  # type: ignore
        features = pd.DataFrame([{
            "size":                 metrics["size"],
            "min_moves":            metrics["min_moves"],
            "total_states":         metrics["num_states"],
            "articulation_points":  metrics["articulation_points"],
            "avg_branching":        metrics["avg_branching_factor"],
        }])
        pred = _MODEL_CACHE.predict(features)[0]
        return round(float(pred), 2)
    except Exception:
        return None


def _fallback_stars(metrics: dict) -> float:
    """
    Fórmula heurística (la mateixa base que calculate_stars_2 d'eval.py)
    com a pla B quan el model no és disponible.
    """
    if not metrics["reachable"] or metrics["min_moves"] is None:
        return 0.0

    size     = metrics["size"]
    log_max  = sum(math.log(i) for i in range(1, size + 1))

    s_diff   = min(metrics["min_moves"] / size, 1.0)
    s_scale  = min(math.log(max(metrics["num_states"], 1)) / log_max, 1.0)

    def ramp_up(x: float, cap: float = 1.0) -> float:
        return min(x / cap, 1.0) if x > 0 else 0.0

    score = 0.5 * ramp_up(s_diff, 0.8) + 0.5 * ramp_up(s_scale, 0.35)
    return round(1 + score * 4, 2)


def _stars(metrics: dict) -> tuple[float, str]:
    """
    Retorna (estrelles, font) on font és 'ML' o 'heurística'.
    """
    pred = _predict_stars(metrics)
    if pred is not None:
        return pred, "ML"
    return _fallback_stars(metrics), "heurística"


# ════════════════════════════════════════════════════════════════════════════
#  FORMES DE PECES
# ════════════════════════════════════════════════════════════════════════════

# Formes predefinides (forma canònica, coordenades relatives ordenades)
SHAPES: dict[str, Piece] = {
    "1x1":  Piece((0,0)),
    "1x2":  Piece((0,0),(0,1)),
    "2x1":  Piece((0,0),(1,0)),
    "1x3":  Piece((0,0),(0,1),(0,2)),
    "3x1":  Piece((0,0),(1,0),(2,0)),
    "2x2":  Piece((0,0),(0,1),(1,0),(1,1)),
    "L":    Piece((0,0),(0,1),(1,1)),
    "Lrev": Piece((0,1),(1,0),(1,1)),
    "J":    Piece((0,0),(1,0),(1,1)),
    "Jrev": Piece((0,0),(0,1),(1,0)),
    "S":    Piece((0,1),(1,0),(1,1)),
    "Z":    Piece((0,0),(0,1),(1,1)),
    "T":    Piece((0,0),(1,0),(1,1),(2,0)),
}

CLASSIC_PIECES = ["1x1", "1x2", "2x1", "2x2"]
FREEFORM_PIECES = list(SHAPES.keys())


def _random_piece(rng: random.Random, choices: list[str]) -> Piece:
    return SHAPES[rng.choice(choices)]


# ════════════════════════════════════════════════════════════════════════════
#  PLACEMENT: col·loca peces al taulell sense solapament
# ════════════════════════════════════════════════════════════════════════════

def _place_pieces(rng: random.Random,
                  W: int, H: int,
                  walls: list[Coord],
                  pieces: list[Piece],
                  max_tries: int = 2000) -> Optional[list[Coord]]:
    """
    Intenta col·locar totes les peces sense solapar-se ni solapar les parets.
    Retorna la llista de posicions o None si falla.
    """
    wall_set = set(walls)

    def fits(piece: Piece, pos: Coord, occupied: set[Coord]) -> bool:
        px, py = pos
        for dx, dy in piece.coords:
            x, y = px + dx, py + dy
            if x < 0 or x >= W or y < 0 or y >= H:
                return False
            if (x, y) in occupied or (x, y) in wall_set:
                return False
        return True

    for _ in range(max_tries):
        occupied: set[Coord] = set(walls)
        positions: list[Coord] = []
        ok = True
        for piece in pieces:
            # Posicions vàlides per a aquesta peça
            valid: list[Coord] = [
                (x, y)
                for x in range(W)
                for y in range(H)
                if fits(piece, (x, y), occupied)
            ]
            if not valid:
                ok = False
                break
            pos = rng.choice(valid)
            occupied |= _cells(piece, pos)
            positions.append(pos)
        if ok:
            return positions
    return None


# ════════════════════════════════════════════════════════════════════════════
#  ESTRATÈGIA 1: CLASSIC
#  Taulell 4x5, peça 2x2 principal, peces clàssiques de Klotski.
# ════════════════════════════════════════════════════════════════════════════

def _goal_positions_for(piece: Piece, W: int, H: int) -> list[Coord]:
    """Retorna totes les posicions vàlides de l'objectiu per a una peça."""
    positions = []
    for x in range(W):
        for y in range(H):
            # La peça ha de cabre dins del taulell en la posició objectiu
            if all(0 <= x+dx < W and 0 <= y+dy < H for dx, dy in piece.coords):
                positions.append((x, y))
    return positions


def generate_classic(rng: random.Random,
                     W: int = 4, H: int = 5,
                     num_small: int = 4,
                     num_medium: int = 3) -> Optional[Puzzle]:
    """
    Genera un puzzle estil Klotski clàssic:
    - Peça 2x2 és l'objectiu principal
    - Peces addicionals: 1x2/2x1 (medium) i 1x1 (small)
    - L'objectiu és moure el 2x2 a la fila inferior centre
    """
    main_piece = SHAPES["2x2"]

    medium_shapes = [SHAPES["1x2"], SHAPES["2x1"]]
    small_shape   = SHAPES["1x1"]

    medium_pieces = [rng.choice(medium_shapes) for _ in range(num_medium)]
    small_pieces  = [small_shape] * num_small

    all_pieces = [main_piece] + medium_pieces + small_pieces

    positions = _place_pieces(rng, W, H, [], all_pieces)
    if positions is None:
        return None

    # Objectiu: 2x2 al centre baix (o a qualsevol posició del marge inferior)
    goal_candidates = [(x, H - 2) for x in range(W - 1)]
    goal_pos = rng.choice(goal_candidates)

    # L'índex de la peça principal (0) canviarà amb l'ordenació canònica
    pp = list(zip(all_pieces, positions))
    return _build_puzzle(W, H, [], pp, 0, goal_pos)


# ════════════════════════════════════════════════════════════════════════════
#  ESTRATÈGIA 2: FREEFORM
#  Taulell i peces aleatòries, objectiu aleatori.
# ════════════════════════════════════════════════════════════════════════════

def generate_freeform(rng: random.Random,
                      W_range: tuple[int,int] = (4, 6),
                      H_range: tuple[int,int] = (4, 6),
                      num_pieces_range: tuple[int,int] = (4, 8),
                      piece_pool: list[str] = CLASSIC_PIECES) -> Optional[Puzzle]:
    """
    Genera un puzzle amb taulell i peces totalment aleatoris.
    """
    W = rng.randint(*W_range)
    H = rng.randint(*H_range)
    num_pieces = rng.randint(*num_pieces_range)

    # Generem les peces (bias cap a peces petites/mitjanes per no omplir el taulell)
    weights = [3, 2, 2, 1]  # 1x1 és més probable
    pool_w  = piece_pool[:len(weights)]
    pieces: list[Piece] = []
    for _ in range(num_pieces):
        name = rng.choices(pool_w, weights=weights[:len(pool_w)], k=1)[0]
        pieces.append(SHAPES[name])

    # Assegurem que hi ha almenys una peça que no sigui 1x1 com a objectiu
    big_pieces = [i for i, p in enumerate(pieces) if len(p.coords) > 1]
    if not big_pieces:
        pieces[0] = SHAPES["2x1"]
        big_pieces = [0]

    positions = _place_pieces(rng, W, H, [], pieces)
    if positions is None:
        return None

    # Tria una peça gran com a objectiu
    goal_idx = rng.choice(big_pieces)
    goal_piece = pieces[goal_idx]

    # Posició objectiu: vora del taulell (dreta o baix), diferent de l'inicial
    edge_goals = []
    for x in range(W):
        for y in range(H):
            if (x, y) != positions[goal_idx]:
                if all(0 <= x+dx < W and 0 <= y+dy < H for dx, dy in goal_piece.coords):
                    if x + max(dx for dx, _ in goal_piece.coords) == W - 1 \
                    or y + max(dy for _, dy in goal_piece.coords) == H - 1:
                        edge_goals.append((x, y))

    if not edge_goals:
        return None

    goal_pos = rng.choice(edge_goals)
    pp = list(zip(pieces, positions))
    return _build_puzzle(W, H, [], pp, goal_idx, goal_pos)


# ════════════════════════════════════════════════════════════════════════════
#  ESTRATÈGIA 3: WALLS
#  Taulell amb parets que comporten laberints interiors.
# ════════════════════════════════════════════════════════════════════════════

def _gen_walls(rng: random.Random, W: int, H: int,
               num_walls: int) -> list[Coord]:
    """Genera parets aleatòries (caselles buides bloquejades)."""
    all_cells = [(x, y) for x in range(W) for y in range(H)]
    rng.shuffle(all_cells)
    return all_cells[:num_walls]


def generate_walls(rng: random.Random,
                   W: int = 5, H: int = 5,
                   num_walls_range: tuple[int,int] = (2, 6),
                   num_pieces_range: tuple[int,int] = (3, 6)) -> Optional[Puzzle]:
    """
    Genera un puzzle amb parets que creen laberints interiors.
    Les peces han de navegar al voltant de les parets.
    """
    num_walls  = rng.randint(*num_walls_range)
    num_pieces = rng.randint(*num_pieces_range)
    walls = _gen_walls(rng, W, H, num_walls)

    pieces: list[Piece] = []
    for _ in range(num_pieces):
        # En taulells amb parets, peces petites/mitjanes funcionen millor
        name = rng.choice(["1x1", "1x1", "2x1", "1x2", "2x2"])
        pieces.append(SHAPES[name])

    big_pieces = [i for i, p in enumerate(pieces) if len(p.coords) > 1]
    if not big_pieces:
        pieces[0] = SHAPES["2x1"]
        big_pieces = [0]

    positions = _place_pieces(rng, W, H, walls, pieces)
    if positions is None:
        return None

    goal_idx   = rng.choice(big_pieces)
    goal_piece = pieces[goal_idx]

    # Objectiu: algun cantó del taulell accessible (sense parets)
    wall_set = set(walls)
    corner_candidates = []
    for x in range(W):
        for y in range(H):
            if (x, y) == positions[goal_idx]:
                continue
            if all(0 <= x+dx < W and 0 <= y+dy < H
                   and (x+dx, y+dy) not in wall_set
                   for dx, dy in goal_piece.coords):
                if x == 0 or x + max(dx for dx,_ in goal_piece.coords) == W - 1 \
                or y == 0 or y + max(dy for _,dy in goal_piece.coords) == H - 1:
                    corner_candidates.append((x, y))

    if not corner_candidates:
        return None

    goal_pos = rng.choice(corner_candidates)
    pp = list(zip(pieces, positions))
    return _build_puzzle(W, H, walls, pp, goal_idx, goal_pos)


# ════════════════════════════════════════════════════════════════════════════
#  PIPELINE PRINCIPAL
# ════════════════════════════════════════════════════════════════════════════

STRATEGIES = {
    "classic":  generate_classic,
    "freeform": generate_freeform,
    "walls":    generate_walls,
}


def generate_batch(strategy: str = "classic",
                   count: int = 5,
                   min_stars: float = 2.0,
                   out_dir: Path = Path("puzzles/generated"),
                   seed: Optional[int] = None,
                   verbose: bool = True) -> list[Path]:
    """
    Genera `count` puzzles vàlids (que superin `min_stars`) i els guarda.
    Usa el model ML entrenat (model_difficulty.pkl) per puntuar; si no
    existeix, usa la fórmula heurística de fallback.
    Retorna la llista de fitxers generats.
    """
    rng = random.Random(seed)
    gen_fn = STRATEGIES[strategy]
    out_dir.mkdir(parents=True, exist_ok=True)

    # Informar si el model ML és disponible
    model_available = _load_model() is not None
    source_label = "ML" if model_available else "heurística"
    print(f"Generant puzzles (estratègia='{strategy}', mínim={min_stars}⭐, puntuació={source_label})...")
    print(f"{'#':>4}  {'Intent':>6}  {'Movs':>5}  {'Arts':>5}  {'Estats':>8}  {'⭐':>5}  Fitxer")
    print("─" * 72)

    generated: list[Path] = []
    attempts  = 0
    max_attempts = count * 300  # evita bucle infinit

    while len(generated) < count and attempts < max_attempts:
        attempts += 1

        puzzle = gen_fn(rng)
        if puzzle is None:
            continue

        # BFS complet: obté totes les mètriques que necessita el model
        metrics = _full_bfs(puzzle, max_states=100_000)

        if not metrics["reachable"]:
            continue
        if metrics["min_moves"] is None or metrics["min_moves"] < 5:
            continue  # massa fàcil
        if metrics["num_states"] < 20:
            continue  # massa petit

        stars, source = _stars(metrics)
        if stars < min_stars:
            continue

        # Desa el puzzle
        idx  = len(generated) + 1
        name = f"gen_{strategy}_{idx:03d}.json"
        path = out_dir / name
        path.write_text(puzzle.to_json(indent=4))
        generated.append(path)

        moves_str  = str(metrics["min_moves"])
        arts_str   = str(metrics["articulation_points"])
        states_str = str(metrics["num_states"]) + ("+" if metrics["truncated"] else "")

        print(f"{idx:>4}  {attempts:>6}  {moves_str:>5}  {arts_str:>5}  {states_str:>8}  {stars:>5.2f}  {name}")

    if len(generated) < count:
        print(f"\n⚠ Només s'han generat {len(generated)}/{count} puzzles en {attempts} intents.")
        print("  Prova de reduir --min-stars o canviar d'estratègia.")
    else:
        print(f"\n✓ {len(generated)} puzzles generats a '{out_dir}' (puntuació via {source_label})")

    return generated


# ════════════════════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generador de puzzles Klotski canònics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--strategy", choices=list(STRATEGIES), default="classic",
                        help="Estratègia de generació (default: classic)")
    parser.add_argument("--count", type=int, default=5,
                        help="Nombre de puzzles a generar (default: 5)")
    parser.add_argument("--min-stars", type=float, default=2.0,
                        help="Valoració mínima per acceptar un puzzle (default: 2.0)")
    parser.add_argument("--out-dir", type=Path, default=Path("puzzles/generated"),
                        help="Carpeta de sortida (default: puzzles/generated)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Llavor aleatòria per a reproduïbilitat")
    parser.add_argument("--quiet", action="store_true",
                        help="Suprimeix la sortida detallada")

    args = parser.parse_args()

    generate_batch(
        strategy=args.strategy,
        count=args.count,
        min_stars=args.min_stars,
        out_dir=args.out_dir,
        seed=args.seed,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()