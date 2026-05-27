"""
Avalua un puzzle fent servir unes mètriques específiques, i guarda la valoració al csv corresponent.

Ús: python3 src/eval.py <puzzles/puzzle.json> <graphs/puzzle.graphml> [<csv_path>]
"""
from __future__ import annotations

import sys
from pathlib import Path
from puzzle import Puzzle
import os
import pandas as pd 
from typing import Any
import joblib

MODEL_PATH = 'model_difficulty.pkl'

def predict_score_ml(metrics: dict[str, Any]) -> float | None:
    """Intenta predir la nota usant el model de machine learning del fitxer model_difficulty.pkl."""
    if not os.path.exists(MODEL_PATH):
        return None
    
    try:
        model = joblib.load(MODEL_PATH)
        features = pd.DataFrame([{
            'size': metrics['size'],
            'min_moves': metrics['min_moves'],
            'total_states': metrics['num_states'],
            'articulation_points': metrics['articulation_points'],
            'avg_branching': metrics['avg_branching']
        }])
        prediction = model.predict(features)[0]
        return round(float(prediction), 2)
    except Exception as e:
        print(f"Error en la predicció: {e}")
        return None


def set_score(puzzle_id: str, puzzle: Puzzle, csv_path: str | Path) -> float | None:
    '''Assigna una puntuació al puzzle donades unes mètriques guardades al csv_path'''
    df = pd.read_csv(csv_path)
    
    row_mask = df['id'] == puzzle_id
    if not row_mask.any():
        print(f"Error: L'ID {puzzle_id} no està al CSV {csv_path}.")
        return None
        
    row = df[row_mask].iloc[0]
    
    metrics = {
        'size': row['size'],
        'min_moves': row['min_moves'],
        'num_states': row['total_states'],
        'articulation_points': row['articulation_points'],
        'avg_branching': row['avg_branching']
    }
    
    score = predict_score_ml(metrics)
    print(f"Valoració: {score} / 5.0")
    
    df.loc[row_mask, 'score'] = score
    df.to_csv(csv_path, index=False)
    
    return score


CSV_PATH = os.environ.get("KLOTSKI_CSV_PATH", 'puzzles_metrics.csv')

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Ús: python src/eval.py <puzzle.json> <graphs/puzzle.graphml> [<csv_path>]")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    graphml_path = Path(sys.argv[2])
    
    if len(sys.argv) > 3:
        CSV_PATH = sys.argv[3]
        
    puzzle_path = json_path

    if not puzzle_path.exists():
        print(f"No s'ha trobat el puzzle: {puzzle_path}")
        sys.exit(1)

    if not graphml_path.exists():
        print(f"No s'ha trobat el graf: {graphml_path}")
        sys.exit(1)

    puzzle = Puzzle.from_json(puzzle_path.read_text())
    puzzle_id = puzzle_path.stem.split("_")[-1]
    score = set_score(puzzle_id, puzzle, CSV_PATH)
    
    if score is not None:
        print(f"\nResultat per a {puzzle_path.name}")
        print(f"Valoració: {score} / 5.0", int(score)*'⭐')