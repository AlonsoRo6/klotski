'''
1r download
2n solve_all
3r eval_all
4t rate_all

'''
from __future__ import annotations

import subprocess

def run(cmd: list[str]) -> None:
    print(f"\n$ {' '.join(cmd)}") 
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        print(f"Error executant: {' '.join(cmd)}")

        return 
    
def main() -> None:
    run(['python3', 'src/download.py'])
    run(['python3', 'src/solve_all.py'])
    run(['python3', 'src/eval_all.py'])
    run(['python3', 'src/rate_all.py'])


if __name__ == '__main__':
    main()