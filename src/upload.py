"""
Envia un puzzle en format JSON al repositori.

Ús:
    python3 src/upload.py <puzzle_path>

"""

import json
import sys
import urllib.request
from pathlib import Path
import os


URL = "https://klotski.pauek.dev/api/puzzles"


def upload_puzzle(file_path: Path, token: str) -> bool:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            puzzle_data = json.load(f)
    
    except FileNotFoundError:
        print(f"Error: No s'ha trobat el fitxer '{file_path.name}'.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: El fitxer '{file_path.name}' no és un JSON vàlid.")
        sys.exit(1)

    data_bytes = json.dumps(puzzle_data).encode("utf-8")

    
    request = urllib.request.Request(
        URL,
        data = data_bytes,
        method = "POST",
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
    )
    try: 
        with urllib.request.urlopen(request) as response:
            response.read()
            return True
        
    except Exception as e:
        print(f"Error enviant {file_path}: {e}")
        return False
    

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Ús: python3 src/upload.py <puzzle_path>")
        sys.exit(1)
    
    puzzle_path = Path(sys.argv[1])
    
    user = os.environ.get("KLOTSKI_USER")
    if not user:
        user = input("Qui vol executar això? (x: Xavi, a: Angel): ").strip().lower()
    if user == 'a':
        token = '019d90b1-6a74-7000-bd6e-1ba9c9ca9973'
    elif user == 'x':
        token = '019d90b1-6a3c-7000-ad15-514895909854'
    else:
        print("Error: Usuari desconegut.")
        sys.exit(1)

    if upload_puzzle(puzzle_path, token):
        print(f"Puzzle {puzzle_path.name} enviat correctament.")
    else:
        print(f"No s'ha pogut pujar el puzzle {puzzle_path.name}.")
