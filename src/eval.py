"""
Avalua un puzzle fent servir unes mètriques específiques, i guarda la valoració a la carpeta evals.

Ús: python src/eval.py <puzzle.json> <graphs/puzzle.graphml>
"""

from __future__ import annotations

import sys
from pathlib import Path
import math
from puzzle import Puzzle
import os
import pandas as pd 
from typing import Any
import joblib #type:ignore

MODEL_PATH = 'model_difficulty.pkl'

def predict_score_ml(metrics: dict[str, Any]) -> float | None:
    """Intenta predir la nota usant el model de ML."""
    if not os.path.exists(MODEL_PATH):
        return None
    
    try:
        model = joblib.load(MODEL_PATH)
        # Preparar les dades en el mateix ordre que l'entrenament
        features = pd.DataFrame([{
            'size': metrics['size'],
            'min_moves': metrics['min_moves'],
            'total_states': metrics['num_states'],
            'articulation_points': metrics['articulation_points_optimal'],
            'avg_branching': metrics['avg_branching_factor']
        }])
        prediction = model.predict(features)[0]
        return round(float(prediction), 2)
    except Exception as e:
        print(f"Error en la predicció: {e}")
        return None



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

    puzzle = Puzzle.from_json(puzzle_path.read_text())
    puzzle_id = puzzle_path.stem.split("_")[-1]
    
    df = pd.read_csv(CSV_PATH)
    row = df[df['id']==puzzle_id].iloc[0]
    
    metrics = {
        'size': row['size'],
        'min_moves': row['min_moves'],
        'num_states': row['total_states'],
        'articulation_points_optimal': row['articulation_points'],
        'avg_branching_factor': row['avg_branching']
    }
    
    # Calculem la nota
    ml_score = predict_score_ml(metrics)
    score = ml_score if ml_score is not None else calculate_stars_2(metrics, puzzle)
    
    # Actualitzem només la nota al CSV
    df.loc[df['id'] == puzzle_id, 'score'] = score
    df.to_csv(CSV_PATH, index=False)
    

    print(f"\n--- Resultat per a {puzzle_path.name} ---")
    print(f"\n  ⭐ Valoració: {score} / 5.0")