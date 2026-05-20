"""
Generador de puzzles de Klotski canònics.

  - 'classic'  : taulell 4x5 amb peça 2x2 principal (Klotski clàssic)
  - 'freeform' : taulell i peces aleatòries dins uns paràmetres
  - 'walls'    : taulell amb parets que creen laberints

Ús:
  python src/generate.py [--strategy classic|freeform|walls]
                         [--count N]
                         [--min-stars X]
                         [-min-steps Y]
                         [-max-states Z]
                         [--num-goals M]
                         [--prefix P]
                         [--seed S]
                         [--quiet]

Exemples:
  python src/generate.py --strategy classic --count 5 --min-stars 2.5
  python src/generate.py --strategy freeform --count 10 --min-stars 2.0
  python src/generate.py --strategy walls --count 5 --min-stars 2.0
"""

from __future__ import annotations

import argparse
import heapq
import math
import random
import sys
from pathlib import Path
from typing import Optional, Callable

sys.path.insert(0, str(Path(__file__).parent))

from puzzle import Coord, Piece, Puzzle, State
from logic import valid_placement, possible_moves, apply_move, is_goal
from eval import predict_score_ml, calculate_stars_2

def _cells(piece: Piece, pos: Coord) -> set[Coord]:
    px, py = pos
    return {(px + dx, py + dy) for dx, dy in piece.coords}


def _all_occupied(puzzle: Puzzle, state: State) -> set[Coord]:
    occ: set[Coord] = set(puzzle.walls)
    for i, piece in enumerate(puzzle.pieces):
        occ |= _cells(piece, state.positions[i])
    return occ


def _find_non_overlapping_goals(
    rng: random.Random,
    walls: list[Coord],
    pieces: tuple[Piece, ...],
    goal_indices: list[int],
    candidate_funcs: list[Callable[[], list[Coord]]],
    max_tries: int = 100
) -> Optional[tuple[tuple[int, Coord], ...]]:
    wall_set = set(walls)
    for _ in range(max_tries):
        goals_chosen = []
        occupied = set(walls)
        ok = True
        for i, idx in enumerate(goal_indices):
            candidates = candidate_funcs[i]()
            valid = []
            for px, py in candidates:
                if all((px + dx, py + dy) not in occupied for dx, dy in pieces[idx].coords):
                    valid.append((px, py))
            if not valid:
                ok = False
                break
            chosen_pos = rng.choice(valid)
            goals_chosen.append((idx, chosen_pos))
            occupied |= _cells(pieces[idx], chosen_pos)
        if ok:
            return tuple(goals_chosen)
    return None

def _build_puzzle(
    W: int,
    H: int,
    walls: list[Coord],
    pieces_and_positions: list[tuple[Piece, Coord]],
    goals: tuple[tuple[int, Coord], ...]
) -> Optional[Puzzle]:
    """
    Construeix un Puzzle canònic a partir de les dades.
    Retorna None si la construcció falla per qualsevol motiu.
    """
    try:
        walls_t = tuple(sorted(set(walls)))
        # Ordenació canònica: (forma, posició_inicial)
        sorted_pp = sorted(pieces_and_positions, key=lambda pp: (pp[0], pp[1]))
        
        # Mapejar els índexs originals cap als nous índexs
        new_goals = []
        for g_idx, g_pos in goals:
            orig_piece = pieces_and_positions[g_idx][0]
            orig_pos = pieces_and_positions[g_idx][1]
            new_idx = next(i for i, (p, pos) in enumerate(sorted_pp) if p == orig_piece and pos == orig_pos)
            new_goals.append((new_idx, g_pos))
            
        pieces = tuple(p for p, _ in sorted_pp)
        start = State(tuple(pos for _, pos in sorted_pp))
        return Puzzle(W, H, walls_t, pieces, start, tuple(new_goals))
    except Exception:
        return None



def _heuristic(puzzle: Puzzle, state: State) -> int:
    """
    Heurística admissible: Distància de Manhattan entre la peça objectiu i la seva
    posició final.
    """
    h = 0
    for goal_idx, (gx, gy) in puzzle.goals:
        sx, sy = state.positions[goal_idx]
        h += abs(sx - gx) + abs(sy - gy)
    return h


def _quick_astar(puzzle: Puzzle, max_states: int = 15_000) -> int | None:
    """
    A* per trobar el nombre mínim de moviments ràpidament.
    Retorna el nombre de moviments de la solució òptima, o None si no en té
    (o si supera el límit d'estats explorats).
    """
    print("Fent A* per trobar el nombre mínim de moviments ràpidament...")
    start_pos = puzzle.start.positions

    # Cua de prioritats: (f, g, counter, state_positions)
    # El counter desempatarà quan la f i la g siguin iguals
    counter = 0

    h_start = _heuristic(puzzle, puzzle.start)
    queue: list[tuple[int, int, int, tuple]] = [(h_start, 0, counter, start_pos)] #type:ignore
    counter += 1
    
    # Millor cost (g) trobat fins ara per a cada estat
    best_g: dict[tuple, int] = {start_pos: 0} #type:ignore

    num_states = 0

    while queue and num_states < max_states:
        f, g, _, pos_tuple = heapq.heappop(queue)
        state = State(pos_tuple)

        # Si ja havíem trobat un camí millor prèviament cap a aquest estat, l'ignorem
        if g > best_g.get(pos_tuple, float("inf")):
            continue

        if is_goal(puzzle, state):
            return g

        num_states += 1

        for move in possible_moves(puzzle, state):
            nstate = apply_move(puzzle, state, move)
            nb = nstate.positions
            new_g = g + 1

            # Només afegim a la cua si hem trobat un camí millor
            if new_g < best_g.get(nb, float("inf")):
                best_g[nb] = new_g
                h = _heuristic(puzzle, nstate)
                heapq.heappush(queue, (new_g + h, new_g, counter, nb))
                counter += 1

    return None



def _full_explore(puzzle: Puzzle, max_states: int = 500_000) -> dict | None: #type:ignore
    """
    Exploració completa des de l'estat inicial limitat a `max_states`.

    Utilitza `build_graph` i `calculate_metrics_in_graph` de `graph.py`
    si graph-tool està disponible, assegurant que la normalització d'estats
    és idèntica a l'oficial per unificar els estats amb peces repetides.
    """
    try:
        from graph import build_graph, calculate_metrics_in_graph

        print("Calculant graf complet amb graph-tool (DFS)...")
        g = build_graph(puzzle, max_states)
        metrics = calculate_metrics_in_graph(g, puzzle)

        truncated = g.num_vertices() >= max_states

        if not metrics:
            return {
                "size": puzzle.W * puzzle.H,
                "min_moves": None,
                "num_states": g.num_vertices(),
                "avg_branching": 0,
                "articulation_points": 0,
                "reachable": False,
                "truncated": truncated,
            }

        metrics["reachable"] = True
        metrics["truncated"] = truncated
        return metrics
    except ImportError:
        print("No s'ha pogut generar el graf complet. No s'han pogut calcular les mètriques.")
        return None



# Formes predefinides (forma canònica, coordenades relatives ordenades)
SHAPES: dict[str, Piece] = {
    "1x1": Piece((0, 0)),
    "1x2": Piece((0, 0), (0, 1)),
    "2x1": Piece((0, 0), (1, 0)),
    "1x3": Piece((0, 0), (0, 1), (0, 2)),
    "3x1": Piece((0, 0), (1, 0), (2, 0)),
    "2x2": Piece((0, 0), (0, 1), (1, 0), (1, 1)),
    "L": Piece((0, 0), (0, 1), (1, 1)),
    "Lrev": Piece((0, 1), (1, 0), (1, 1)),
    "J": Piece((0, 0), (1, 0), (1, 1)),
    "Jrev": Piece((0, 0), (0, 1), (1, 0)),
    "S": Piece((0, 1), (1, 0), (1, 1)),
    "Z": Piece((0, 0), (0, 1), (1, 1)),
    "T": Piece((0, 0), (1, 0), (1, 1), (2, 0)),
}

CLASSIC_PIECES = ["1x1", "1x2", "2x1", "2x2"]
FREEFORM_PIECES = list(SHAPES.keys())


def _random_piece(rng: random.Random, choices: list[str]) -> Piece:
    return SHAPES[rng.choice(choices)]


# ════════════════════════════════════════════════════════════════════════════
#  PLACEMENT: col·loca peces al taulell sense solapament
# ════════════════════════════════════════════════════════════════════════════


def _place_pieces(
    rng: random.Random,
    W: int,
    H: int,
    walls: list[Coord],
    pieces: list[Piece],
    max_tries: int = 2000,
) -> Optional[list[Coord]]:
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

    # Ordenem les peces de més grans a més petites per facilitar el bin packing
    ordered_pieces = sorted(
        enumerate(pieces), key=lambda p: len(p[1].coords), reverse=True
    )

    for _ in range(max_tries):
        occupied: set[Coord] = set(walls)
        temp_positions: dict[int, Coord] = {}
        ok = True
        for orig_idx, piece in ordered_pieces:
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
            temp_positions[orig_idx] = pos
        if ok:
            return [temp_positions[i] for i in range(len(pieces))]
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
            if all(0 <= x + dx < W and 0 <= y + dy < H for dx, dy in piece.coords):
                positions.append((x, y))
    return positions


def generate_classic(
    rng: random.Random, W: int = 4, H: int = 5, num_small_range: tuple[int, int] = (4, 6), num_medium_range: tuple[int, int] = (3, 4), num_goals: int = 1
) -> Optional[Puzzle]:
    """
    Genera un puzzle estil Klotski clàssic:
    - Peça 2x2 és l'objectiu principal
    - Peces addicionals: 1x2/2x1 (medium) i 1x1 (small)
    - S'intenta posar la 2x2 a dalt de tot i l'objectiu a baix
    """
    main_piece = SHAPES["2x2"]

    medium_shapes = [SHAPES["1x2"], SHAPES["2x1"]]
    small_shape = SHAPES["1x1"]
    
    num_medium = rng.randint(*num_medium_range)
    num_small = rng.randint(*num_small_range)

    medium_pieces = [rng.choice(medium_shapes) for _ in range(num_medium)]
    small_pieces = [small_shape] * num_small

    all_pieces = [main_piece] + medium_pieces + small_pieces

    # Busquem una disposició on el 2x2 comenci a la part superior
    positions = None
    for _ in range(15):
        pos_candidates = _place_pieces(rng, W, H, [], all_pieces)
        if pos_candidates is not None:
            if pos_candidates[0][1] <= 1:  # La peça 2x2 està a la meitat superior (y=0 o y=1)
                positions = pos_candidates
                break
            # Si no, ens ho guardem per si no trobem res millor
            positions = pos_candidates

    if positions is None:
        return None

    # Volem que els num_goals objectius vagin a posicions no solapades al fons
    # El principal serà el 2x2 (index 0). Els altres seran peces aleatòries
    big_pieces = [i for i, p in enumerate(all_pieces) if len(p.coords) > 1]
    rng.shuffle(big_pieces)
    
    goal_indices = []
    if 0 in big_pieces:
        goal_indices.append(0)
        big_pieces.remove(0)
        
    while len(goal_indices) < num_goals and big_pieces:
        goal_indices.append(big_pieces.pop())
        
    while len(goal_indices) < num_goals:
        goal_indices.append(rng.randint(0, len(all_pieces) - 1))
        
    candidate_funcs = []
    for idx in goal_indices:
        candidate_funcs.append(lambda i=idx: [
            (x, y) for x in range(W) for y in range(H)
            if all(0 <= x + dx < W and 0 <= y + dy < H for dx, dy in all_pieces[i].coords)
            and abs(x - positions[i][0]) + abs(y - positions[i][1]) >= 2
            and (y + max(dy for _, dy in all_pieces[i].coords) == H - 1 or y == 0)
        ])

    goals = _find_non_overlapping_goals(rng, [], tuple(all_pieces), goal_indices, candidate_funcs)
    if goals is None:
        return None

    pp = list(zip(all_pieces, positions))
    return _build_puzzle(W, H, [], pp, goals)


# ════════════════════════════════════════════════════════════════════════════
#  ESTRATÈGIA 2: FREEFORM
# ════════════════════════════════════════════════════════════════════════════


def generate_freeform(
    rng: random.Random,
    W_range: tuple[int, int] = (5, 7),
    H_range: tuple[int, int] = (5, 6),
    num_pieces_range: tuple[int, int] = (6, 12),
    piece_pool: list[str] = FREEFORM_PIECES,
    num_goals: int = 1
) -> Optional[Puzzle]:
    """
    Genera un puzzle amb taulell i peces totalment aleatoris.
    """
    W = rng.randint(*W_range)
    H = rng.randint(*H_range)
    num_pieces = max(2, rng.randint(*num_pieces_range))

    pieces: list[Piece] = []
    
    # 1. Garantir almenys una peça gran (L, J, 2x2, 3x1...)
    grans = [p for p in piece_pool if len(SHAPES[p].coords) >= 3 or p == "2x2"]
    if not grans: grans = piece_pool
    pieces.append(SHAPES[rng.choice(grans)])
    
    # 2. Garantir almenys una peça petita però de mida 2 (1x2 o 2x1)
    petites = [p for p in piece_pool if len(SHAPES[p].coords) == 2]
    if not petites: petites = piece_pool
    pieces.append(SHAPES[rng.choice(petites)])
    
    # 3. La resta de peces de manera aleatòria
    for _ in range(num_pieces - 2):
        # Donem una mica més de probabilitat a les peces petites per no saturar el taulell
        weights = [1 if len(SHAPES[p].coords) >= 3 else 3 for p in piece_pool]
        name = rng.choices(piece_pool, weights=weights, k=1)[0]
        pieces.append(SHAPES[name])

    big_pieces = [i for i, p in enumerate(pieces) if len(p.coords) > 1]
    if not big_pieces:
        pieces[0] = SHAPES["2x1"]
        big_pieces = [0]

    positions = _place_pieces(rng, W, H, [], pieces)
    if positions is None:
        return None

    big_pieces = [i for i, p in enumerate(pieces) if len(p.coords) > 1]
    rng.shuffle(big_pieces)
    
    goal_indices = []
    while len(goal_indices) < num_goals and big_pieces:
        goal_indices.append(big_pieces.pop())
        
    while len(goal_indices) < num_goals:
        goal_indices.append(rng.randint(0, len(pieces) - 1))
        
    candidate_funcs = []
    for idx in goal_indices:
        candidate_funcs.append(lambda i=idx: [
            (x, y) for x in range(W) for y in range(H)
            if all(0 <= x + dx < W and 0 <= y + dy < H for dx, dy in pieces[i].coords)
            and abs(x - positions[i][0]) + abs(y - positions[i][1]) >= 2
            and (x + max(dx for dx, _ in pieces[i].coords) == W - 1 or y + max(dy for _, dy in pieces[i].coords) == H - 1 or x == 0 or y == 0)
        ])

    goals = _find_non_overlapping_goals(rng, [], tuple(pieces), goal_indices, candidate_funcs)
    if goals is None:
        return None

    pp = list(zip(pieces, positions))
    return _build_puzzle(W, H, [], pp, goals)


# ════════════════════════════════════════════════════════════════════════════
#  ESTRATÈGIA 3: WALLS
#  Taulell amb parets que comporten laberints interiors.
# ════════════════════════════════════════════════════════════════════════════


def _gen_walls(rng: random.Random, W: int, H: int, num_walls: int) -> list[Coord]:
    """Genera parets aleatòries (caselles buides bloquejades)."""
    all_cells = [(x, y) for x in range(W) for y in range(H)]
    rng.shuffle(all_cells)
    return all_cells[:num_walls]


def generate_walls(
    rng: random.Random,
    W_range: tuple[int, int] = (5, 7),
    H_range: tuple[int, int] = (5, 6),
    num_walls_range: tuple[int, int] = (3, 6),
    num_pieces_range: tuple[int, int] = (5, 11),
    piece_pool: list[str] = FREEFORM_PIECES,
    num_goals: int = 1
) -> Optional[Puzzle]:
    """
    Genera un puzzle amb parets que creen laberints interiors.
    Les peces han de navegar al voltant de les parets.
    """
    W = rng.randint(*W_range)
    H = rng.randint(*H_range)    
    num_walls = rng.randint(*num_walls_range)
    num_pieces = max(2, rng.randint(*num_pieces_range))
    walls = _gen_walls(rng, W, H, num_walls)

    pieces: list[Piece] = []
    
    # 1. Garantir almenys una peça gran (L, J, 2x2, 3x1...)
    grans = [p for p in piece_pool if len(SHAPES[p].coords) >= 3 or p == "2x2"]
    if not grans: grans = piece_pool
    pieces.append(SHAPES[rng.choice(grans)])
    
    # 2. Garantir almenys una peça petita però de mida 2 (1x2 o 2x1)
    petites = [p for p in piece_pool if len(SHAPES[p].coords) == 2]
    if not petites: petites = piece_pool
    pieces.append(SHAPES[rng.choice(petites)])
    
    # 3. La resta de peces de manera aleatòria
    for _ in range(num_pieces - 2):
        # Donem una mica més de probabilitat a les peces petites perquè en parets l'espai és escàs
        weights = [1 if len(SHAPES[p].coords) >= 3 else 4 for p in piece_pool]
        name = rng.choices(piece_pool, weights=weights, k=1)[0]
        pieces.append(SHAPES[name])

    big_pieces = [i for i, p in enumerate(pieces) if len(p.coords) > 1]
    if not big_pieces:
        pieces[0] = SHAPES["2x1"]
        big_pieces = [0]

    positions = _place_pieces(rng, W, H, walls, pieces)
    if positions is None:
        return None

    big_pieces = [i for i, p in enumerate(pieces) if len(p.coords) > 1]
    rng.shuffle(big_pieces)
    
    goal_indices = []
    while len(goal_indices) < num_goals and big_pieces:
        goal_indices.append(big_pieces.pop())
        
    while len(goal_indices) < num_goals:
        goal_indices.append(rng.randint(0, len(pieces) - 1))
        
    wall_set = set(walls)
    candidate_funcs = []
    for idx in goal_indices:
        candidate_funcs.append(lambda i=idx: [
            (x, y) for x in range(W) for y in range(H)
            if all(0 <= x + dx < W and 0 <= y + dy < H and (x + dx, y + dy) not in wall_set for dx, dy in pieces[i].coords)
            and abs(x - positions[i][0]) + abs(y - positions[i][1]) >= 2
            and (x == 0 or x + max(dx for dx, _ in pieces[i].coords) == W - 1 or y == 0 or y + max(dy for _, dy in pieces[i].coords) == H - 1)
        ])

    goals = _find_non_overlapping_goals(rng, walls, tuple(pieces), goal_indices, candidate_funcs)
    if goals is None:
        return None

    pp = list(zip(pieces, positions))
    return _build_puzzle(W, H, walls, pp, goals)

STRATEGIES = {
    "classic": generate_classic,
    "freeform": generate_freeform,
    "walls": generate_walls,
}

OUT_DIR = Path("puzzles/custom")

def generate_batch(strategy: str = "classic",count: int = 5, min_stars: float = 2.0, min_steps:int=15, max_states:int=750_000, rng_seed: int = random.randint(1, 1_000_000), verbose: bool = True, num_goals: int = 1, prefix: str = None) -> list[Path]:
    """
    Genera "count" puzzles vàlids (que superin "min_stars") i els guarda.
    Retorna la llista de fitxers generats.
    """
    print(f'max_states: {max_states}')
    rng = random.Random(rng_seed)
    funcio_generacio = STRATEGIES[strategy]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(
        f"Generant puzzles (estratègia='{strategy}', mínim={min_stars}⭐)...")
    

    generated: list[Path] = []
    attempts = 0
    max_attempts = count * 1500  # evita bucle infinit
    comptador = 0
    while len(generated) < count and attempts < max_attempts:
        attempts += 1

        puzzle = funcio_generacio(rng, num_goals=num_goals)
        if puzzle is None:
            continue

        # 1. Si el taulell està massa buit o massa ple, no serà gaire complex ni eficient de buscar
        total_cells = sum(len(p.coords) for p in puzzle.pieces)
        free_cells = (puzzle.W * puzzle.H) - total_cells - len(puzzle.walls)
        
        # Si busquem puntuacions altes, exigim taulells més atapeïts (més difícils)
        max_free = 4 if min_stars >= 4.0 else 10
        
        if free_cells < 2 or free_cells > max_free:
            continue

        # 2. Descartem ràpidament els puzzles que no tenen solució o són evidents amb A*
        min_moves_astar = _quick_astar(puzzle)
        print(attempts)
        if min_moves_astar is None or min_moves_astar < min_steps:
            continue

        # 3. Només s'executa si el filtre de l'A* indica que el puzle promet
        comptador += 1
        metrics = _full_explore(puzzle, max_states)
        
        if metrics is None:
            continue

        if not metrics["reachable"]:
            continue
        if metrics["min_moves"] is None or metrics["min_moves"] < min_steps:
            continue  #per si un cas s'ha saltat el filtre d'abans
        if metrics["num_states"] < 20:
            continue  # massa petit
        if metrics["min_moves"] > min_moves_astar + 5: #el graf és tan gran que la solució trobada s'allunya masssa de la òptima
            continue
        
        eval_metrics = metrics.copy()
            
        pred = predict_score_ml(eval_metrics)
        if pred is not None:
            stars, source = pred, "ML"
        else:
            stars, source = calculate_stars_2(eval_metrics, puzzle), "heurística"
            
        print(stars)
        if stars < min_stars:
            continue

        # Desa el puzzle
        idx = len(generated) + 1
        if prefix:
            name = f"{prefix}{idx:02d}.json"
        else:
            name = f"gen_{strategy}_{idx:03d}.json"
        path = OUT_DIR / name
        path.write_text(puzzle.to_json())
        generated.append(path)

        moves_str = str(metrics["min_moves"])
        arts_str = str(metrics["articulation_points"])
        states_str = str(metrics["num_states"]) + ("+" if metrics["truncated"] else "")

        if verbose:
            print(
                f"{'#':>4}  {'Intent':>6}  {'Movs':>5}  {'Arts':>5}  {'Estats':>8}  {'⭐':>5}  Fitxer"
            )
            print("─" * 72)
            print(
                f"{idx:>4}  {attempts:>6}  {moves_str:>5}  {arts_str:>5}  {states_str:>8}  {stars:>5.2f}  {name}"
            )
            if metrics["truncated"]:
                print("Puzzle truncat, pot ser que la puntuació no es correspongui amb la realitat")

    if len(generated) < count:
        print(
            f"\n⚠ Només s'han generat {len(generated)}/{count} puzzles en {attempts} intents."
        )
        print("  Prova de reduir --min-stars, --min-steps, --max-states, o canviar d'estratègia.")
    else:
        print(
            f"\n✓ {len(generated)} puzzles generats a '{OUT_DIR}')"
        )
    
    print(f"S'han explorat {comptador} puzzles amb dfs (graph_tool)")

    return generated



def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generador de puzzles Klotski canònics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--strategy", choices=list(STRATEGIES), default="classic", help="Estratègia de generació (default: classic)",)

    parser.add_argument("--count", type=int, default=5, help="Nombre de puzzles a generar (default: 5)")

    parser.add_argument("--min-stars", type=float,default=2.5,help="Valoració mínima per acceptar un puzzle (default: 2.5)",)

    parser.add_argument("--min-steps", type=int,default=15, help="Mínim número de passos de la solució d'A* (default: 15)",)

    parser.add_argument("--max-states", type=int,default=750_000, help="Màxim número d'estats a explorar amb BFS (default: 750_000)",)

    parser.add_argument("--seed", type=int,default=random.randint(1, 1_000_000), help="Seed per al generador de números aleatoris (default: 42)")

    parser.add_argument("--num-goals", type=int, default=1, help="Nombre de peces que han d'arribar a una destinació (default: 1)")

    parser.add_argument("--prefix", type=str, default=None, help="Prefix pel nom dels fitxers generats sense '_' (ex: intent -> intent01.json)")

    parser.add_argument("--quiet", action="store_true", help="Suprimeix la sortida detallada")
    

    args = parser.parse_args()

    generate_batch(
        strategy=args.strategy,
        count=args.count,
        min_stars=args.min_stars,
        min_steps=args.min_steps,
        max_states=args.max_states,
        rng_seed=args.seed,
        verbose=not args.quiet,
        num_goals=args.num_goals,
        prefix=args.prefix,
    )


if __name__ == "__main__":
    main()