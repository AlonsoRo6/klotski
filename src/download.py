'''
Descarrega tots els puzzles del repositori sense duplicar els que ja existeixen.
Ús: python3 src/download.py
'''

import requests
import json
from pathlib import Path

URL = "https://klotski.pauek.dev/api/puzzles"
OUT_DIR = Path("puzzles/repository")

def download_puzzle(i: int | None, puzzle_id: str) -> None:
    '''
    Donat un puzzle_id, crea el fitxer JSON corresponent si no existeix.
    '''

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    filename = OUT_DIR / f"puzzle_{puzzle_id}.json"

    if filename.exists():
        print(f"[{i}] El puzzle {puzzle_id} ja existeix. Saltem la descàrrega")
        return

    url = f"{URL}/{puzzle_id}"
    
    try:
        response = requests.get(url)
        data_puzzle = response.json()

        with open(filename, 'w') as f:
            json.dump(data_puzzle["puzzle"], f, indent=4)
        print(f"[{i}] Puzzle {puzzle_id} descarregat correctament.")
        
    except Exception as e:
        print(f"[{i}] Error descarregant el puzzle {puzzle_id}: {e}")


def download_all_puzzles() -> None:
    all_url = requests.get(URL)
    for i,puzzle in enumerate(all_url.json()):
        download_puzzle(i+1,puzzle)        

if __name__ == '__main__':
    download_all_puzzles()