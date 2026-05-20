# Segona Pràctica d'AP2 - Klotski

## Índex

- [Instal·lació i Prerequisits](#installació-i-prerequisits)
- [Instruccions d'Ús](#instruccions-dús)
- [Arquitectura del Projecte](#arquitectura-del-projecte)
  - [Programes Base](#programes-base)
  - [Programes "All"](#programes-all)
- [Decisions de Disseny](#decisions-de-disseny)
- [Referències i Eines de Suport](#referències-i-eines-de-suport)

---

## Instal·lació i Prerequisits

Per a una guia detallada sobre la preparació de l'entorn de treball i la instal·lació dels requisits (com WSL, Pixi o `graph-tool`), consulteu la secció corresponent al [repositori original del treball a GitHub](https://github.com/pauek/klotski#prep). 

De la mateixa manera, per a consultar les diferents maneres en què es pot executar el codi, referiu-vos al mateix repositori.

---

## Instruccions d'ús

A continuació es detalla com es fan servir els diferents programes del projecte, incloent-hi els paràmetres i les flags més habituals per a cadascun.

### 1. Eines de Visualització i Joc
* **Jugar a un puzzle interactivament**:
  ```bash
  python src/play.py <puzzle.json>
  # Exemple:
  python src/play.py puzzles/sample1.json
  ```
* **Generar una imatge de l'estat inicial**:
  ```bash
  python src/image.py <puzzle.json> [imatge_de_sortida.png]
  # Exemple:
  python src/image.py puzzles/klotski.json puzzles/klotski.png
  ```
* **Visualitzador 3D del graf d'estats**:
  Obre una web interactiva per veure el graf en 3D. De manera opcional, es pot fer que mostri els camins de les solucions.
  ```bash
  python src/3D_view.py <graf.graphml> [<solució.sol.json>] [--port PORT]
  # Exemple:
  python src/3D_view.py graphs/sample1.graphml solutions/sample1.sol.json --port 8080
  ```
* **Generar un GIF animat de la solució**:
  ```bash
  python src/movie.py <puzzle.json> <solució.sol.json> [gif_de_sortida.gif]
  # Exemple:
  python src/movie.py puzzles/sample1.json solutions/sample1.sol.json solutions_gifs/sample1.gif
  ```

### 2. Generació i Càrrega de Puzzles
* **Generar nous puzzles a l'atzar sota certs paràmetres**:
  ```bash
  python src/generate.py [--strategy classic|freeform|walls] [--count N] [--min-stars STARS] [--min-steps STEPS] [--max-states STATES] [--seed SEED] [--num-goals GOALS] [--prefix PREFIX] [--quiet]
  # Exemple (genera 10 puzzles freeform amb dificultat i els desa a puzzles/custom):
  python src/generate.py --strategy freeform --count 10 --min-stars 3.0 --min-steps 20 --prefix meupuzzle
  ```
* **Pujar un puzzle al repositori del projecte**:
  ```bash
  python src/upload.py <puzzle.json>
  # Exemple:
  python src/upload.py puzzles/custom/meupuzzle01.json
  ```

### 3. Processament i Resolució dels puzzles
* **Generar el graf d'estats d'un puzzle**:
  ```bash
  python src/graph.py <puzzle.json> <sortida.graphml> [camí_al_csv]
  # Exemple (crea el graf i guarda les mètriques estructurals a custom_metrics.csv):
  python src/graph.py puzzles/sample1.json graphs/sample1.graphml custom_metrics.csv
  ```
* **Resoldre un puzzle a partir del seu graf**:
  ```bash
  python src/solve.py <graf.graphml> <sortida.sol.json>
  # Exemple:
  python src/solve.py graphs/sample1.graphml solutions/sample1.sol.json
  ```
* **Avaluar un puzzle individualment**:
  ```bash
  python src/eval.py <puzzle.json> <graf.graphml> [camí_al_csv]
  # Exemple (calcula la nota basant-se en les mètriques que ja estan al CSV i la desa al mateix CSV):
  python src/eval.py puzzles/sample1.json graphs/sample1.graphml custom_metrics.csv
  ```
* **Valorar un puzzle (pujar el vot de 1-5 estrelles al servidor)**:
  ```bash
  python src/rate.py <puzzle.json> [camí_al_csv]
  # Exemple:
  python src/rate.py puzzles/sample1.json custom_metrics.csv
  ```

### 4. Programes "All"
Aquests programes serveixen per processar carpetes de puzzles senceres i guardar els resultats. Les flags són:
* `--puzzles-dir`: Carpeta on hi ha els fitxers dels puzzles.
* `--csv-path`: Fitxer CSV on es llegeixen o s'escriuen les mètriques i notes.

Exemples:
* **Executar tota la cadena per lots** (Descarrega, resol, avalua i puja els vots):
  ```bash
  python src/all.py [--puzzles-dir DIR] [--csv-path CSV] [--skip-download]
  ```
* **Solucionar tots els puzzles d'un directori** (Generant graf, solució i gif):
  ```bash
  python src/solve_all.py [--puzzles-dir DIR] [--csv-path CSV]
  # Exemple:
  python src/solve_all.py --puzzles-dir puzzles/custom --csv-path custom_metrics.csv
  ```
* **Avaluar tots els puzzles de cop**:
  ```bash
  python src/eval_all.py [--puzzles-dir DIR] [--csv-path CSV]
  # Exemple:
  python src/eval_all.py --puzzles-dir puzzles/custom --csv-path custom_metrics.csv
  ```
* **Enviar en bloc totes les valoracions guardades al CSV cap al servidor**:
  ```bash
  python src/rate_all.py [--puzzles-dir DIR] [--csv-path CSV]
  # Exemple:
  python src/rate_all.py --puzzles-dir puzzles/repository --csv-path puzzles_metrics.csv
  ```

---


## Arquitectura del Projecte

El projecte està dividit en diferents programes petits, dissenyats en la mesura del possible per fer una funció concreta i que es "comuniquen" entre ells mitjançant l'escriptura i lectura de fitxers JSON que descriuen els trencaclosques i fitxers CSV amb les mètriques i valoracions dels mateixos.

### Programes Base
- **`src/download.py`**: Es connecta al repositori remot per descarregar els puzzles.
- **`src/graph.py`**: Llegeix el puzzle i genera el graf d'estats fent servir la llibreria graph-tool. També extreu les mètriques del graf i les guarda al fitxer CSV.
- **`src/solve.py`**: Resol un puzzle concret fent servir el graf d'estats per trobar el camí òptim i ho guarda en un JSON.
- **`src/eval.py`**: Calcula una nota de l'1 al 5 (decimal) d'un puzzle segons les mètriques obtingudes del seu graf. Actualitza el CSV amb la nota calculada.
- **`src/rate.py`**: Envia les puntuacions obtingudes localment al repositori del projecte.
- **`src/generate.py`**: Genera puzzles sota diverses estratègies i amb uns certs paràmetres.
- **`src/upload.py`**: Puja els puzzles generats al repositori del projecte.
- **`src/play.py`, `src/image.py`, `src/movie.py`, `src/3D_view.py`**: Serveixen respectivament per jugar al puzzle manualment, generar una imatge fixa de l'estat inicial, fer una gravació de la solució o veure el graf generat en 3D.
- **`src/train_model.py`**: Programa per entrenar un model de Machine Learning (RandomForest) encarregat de valorar i avaluar els puzzles generats. El model resultant es guarda a `model_difficulty.pkl`.
- **`src/puzzle.py`, `src/logic.py`**: Programes auxiliars de classes i funcions lògiques per gestionar regles, coordenades, peces i la lògica del joc.
- **`src/auto_solve.py`**: Demana a l'usuari que introdueixi la ruta d'un puzzle i el nom d'un CSV i genera el graf, la solcuió i les mètriques d'aquell puzzl

### Programes "All"
Aquests scripts automatitzen processos executant seqüencialment les eines base sobre el directori `puzzles/`:
- **`src/all.py`**: Orquestrador principal. Executa, per aquest ordre: `download`, `solve_all`, `eval_all` i finalment `rate_all`. Per tant, es descarrega tots els puzzles del repositori, en genera el graf, la solució i les mètriques, en calcula la nota i finalment envia les puntuacions al repositori del projecte.
- **`src/solve_all.py`**: Itera per tota la carpeta de puzzles i per cadascun en genera el `graph`, en troba la solució òptima amb `solve` i genera el gif amb `movie`.
- **`src/eval_all.py`**: Llegeix tots els puzzles locals, crea els seus grafs (si no existien) i executa l'avaluació amb `eval`, guardant la valoració al mateix CSv en què hi havia les mètriques.
- **`src/rate_all.py`**: Llegeix un CSV en què s'han guardat les valoracions dels puzzles i les puja totes al repositori del projecte.

---

## Decisions de Disseny

### Avaluació de Puzzles i Mètriques
L'avaluació de la qualitat d'un puzzle es realitza mitjançant l'aplicació combinada de **mètriques de grafs** i **Machine Learning**. 

Les mètriques que s'analitzen i extreuen a `graph.py` per establir el nivell d'interès són:
1. **La mida del puzzle (`size`)**: Càlcul de `W * H`.
2. **Passos fins a la millor solució (`min_moves`)**: Llargada de la ruta òptima.
3. **Total d'estats del graf (`num_states`)**: El nombre total de disposicions assequibles des de l'inici.
4. **Articulation points de la millor solució**: Punts clau i colls d'ampolla estructurals de les solucions.
5. **Average branching factor**: La mitjana de branques per cada estat del graf.

En comptes de crear una fórmula totalment ad-hoc, s'utilitza un **model predictiu (entrenat amb `train_model.py`)** alimentat per aquestes mètriques. Aquest model de *Machine Learning* va ser entrenat usant els puzzles que hi havia originalment al repositori més un conjunt reduït de puzzles propis que van ser puntuats de manera completament manual aplicant criteris subjectius de "bellesa", "diversió" i "dificultat". D'aquesta manera s'obté la puntuació d'1 a 5 estrelles de cada puzzle avaluat.

### Generació de Puzzles
La generació automàtica de puzzles (`generate.py`) fa servir tres estratègies principals (`classic`, `freeform` i `walls`). Per evitar un oceà de puzzles aleatoris il·lògics, tediosos o injugables, s'han implementat severes **heurístiques de filtratge i poda**:
1. **Densitat de peces**: Es restringeix l'espai buit del taulell (ex: un taulell per tenir estrelles màximes només pot tenir fins a 4 caselles lliures).
2. **Poda Ràpida (Quick A*)**: S'intenta fer una resolució immediata utilitzant l'algorisme A*. Si es resol massa ràpidament (< min_steps), o directament no té cap solució assequible, es descarta abans de gastar processador en una anàlisi DFS exhaustiva.
3. **Complexitat mínima**: Es descarten grafs extremadament simples de menys de 20 estats totals.
4. **Acotament subòptim**: Es descarten els puzzles el qual el seu millor camí DFS té masses passeres afegides innecessàries respecte el Quick A*. 
5. Finalment, només es retenen aquells puzzles que obtenen una puntuació predita alta per part del model de ML.

---

## Referències i Eines de Suport

- **Projecte Base**: El projecte es basa en les instruccions i estructura del repositori de GitHub d'en **Pau Fernández** ([pauek/klotski](https://github.com/pauek/klotski)), desenvolupat i estructurat amb la col·laboració i ajuda de **Roberto Nsoni** i **Jordi Cortadella**.
- **Intel·ligència Artificial Generativa**: Durant l'execució d'aquest projecte s'han fet servir **Claude**, **Gemini** i l'**IDE Antigravity** per a comprendre millor la base de codi inicial proporcionada i l'arquitectura general del projecte, aprendre a utilitzar llibreries i eines noves per a nosaltres, com ara graph-tool, les llibreries request, json, argparse, sys, etc., superar el bloqueig inicial a l'hora d'implementar certs algorismes amb eines amb les quals no erem familiars, accelerar la localització d'errors desconeguts o comportaments inesperats...
Malgrat això, tot el codi final ha estat revisat, adaptat i integrat de manera crítica per a assegurar-ne la correcció, l'eficiència i el compliment dels requisits acadèmics de la pràctica.
