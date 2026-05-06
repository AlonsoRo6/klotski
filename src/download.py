'''
Descarrega tots els puzzles del repositori.
Ús: python3 src/download.py
'''

import requests
import json

URL = "https://klotski.pauek.dev/api/puzzles"

def download_puzzle(i: int|None ,puzzle_id:str) -> None:
    '''Given a puzzle_id (str), it creates the corresponding json file with the puzzle information'''

    url = URL + "/" + puzzle_id

    response = requests.get(url)

    data_puzzle = response.json()

    filename = f"puzzles/puzzle_{puzzle_id}.json"
    with open(filename, 'w') as f:
        json.dump(data_puzzle["puzzle"], f, indent=4)

def download_all_puzzles() -> None:
    all_url = requests.get(URL)
    for i,puzzle in enumerate(all_url.json()):
        download_puzzle(i+1,puzzle)

if __name__ == '__main__':
    download_all_puzzles()
