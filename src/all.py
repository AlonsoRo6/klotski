'''
1r download
2n solve_all
3r eval_all
4t rate_all

Ús: python3 src/all.py [--puzzles-dir puzzles/... --csv-path ..._metrics.csv --skip-download]
'''
from __future__ import annotations

import subprocess
import os
import sys

def run(cmd: list[str]) -> None:
    print(f"\n$ {' '.join(cmd)}") 
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        print(f"Error executant: {' '.join(cmd)}")
        return 
    
import argparse

def main() -> None:
    parser = argparse.ArgumentParser(description="Executa tots els scripts en cadena.")

    parser.add_argument("--puzzles-dir", type=str, default="puzzles", help="Carpeta base dels puzzles")

    parser.add_argument("--csv-path", type=str, default="puzzles_metrics.csv", help="Fitxer CSV per guardar/llegir mètriques")
    
    parser.add_argument("--skip-download", action="store_true", help="Omet la descàrrega de nous puzzles")
    args = parser.parse_args()

    user = input("Qui vol executar això? (x: Xavi, a: Angel): ").strip().lower()
    if user not in ('a', 'x'):
        print("Error: Usuari desconegut.")
        sys.exit(1)
    os.environ['KLOTSKI_USER'] = user

    if not args.skip_download:
        run(['python3', 'src/download.py'])
        
    common_args = [
        '--puzzles-dir', args.puzzles_dir,
        '--csv-path', args.csv_path
    ]
    
    run(['python3', 'src/solve_all.py'] + common_args)
    run(['python3', 'src/eval_all.py'] + common_args)
    run(['python3', 'src/rate_all.py'] + common_args)


if __name__ == '__main__':
    main()