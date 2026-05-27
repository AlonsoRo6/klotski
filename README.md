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
* **Executar tots els programes** (Descarrega, resol, avalua i puja els vots):
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
- **`src/eval.py`**: Calcula una nota del 0 al 5 (decimal) d'un puzzle segons les mètriques obtingudes del seu graf. Actualitza el CSV amb la nota calculada.
- **`src/rate.py`**: Envia les puntuacions obtingudes localment al repositori del projecte.
- **`src/generate.py`**: Genera puzzles sota diverses estratègies i amb uns certs paràmetres.
- **`src/upload.py`**: Puja els puzzles generats al repositori del projecte.
- **`src/play.py`, `src/image.py`, `src/movie.py`, `src/3D_view.py`**: Serveixen respectivament per jugar al puzzle manualment, generar una imatge fixa de l'estat inicial, fer una gravació de la solució o veure el graf generat en 3D.
- **`src/train_model.py`**: Programa per entrenar un model de Machine Learning (RandomForest) encarregat de valorar i avaluar els puzzles generats. El model resultant es guarda a `model_difficulty.pkl`.
- **`src/puzzle.py`, `src/logic.py`**: Programes auxiliars de classes i funcions lògiques per gestionar regles, coordenades, peces i la lògica del joc.
- **`src/auto_solve.py`**: Demana a l'usuari que introdueixi la ruta d'un puzzle i el nom d'un CSV i genera el graf, la solució i les mètriques d'aquell puzzle.

### Programes "All"
Aquests scripts automatitzen processos executant seqüencialment les eines base sobre el directori `puzzles/`:
- **`src/all.py`**: Orquestrador principal. Executa, per aquest ordre: `download`, `solve_all`, `eval_all` i finalment `rate_all`. Per tant, es descarrega tots els puzzles del repositori, en genera el graf, la solució i les mètriques, en calcula la nota i finalment envia les puntuacions al repositori del projecte.
- **`src/solve_all.py`**: Itera per tota la carpeta de puzzles i per cadascun en genera el `graph`, en troba la solució òptima amb `solve` i genera el gif amb `movie`.
- **`src/eval_all.py`**: Llegeix tots els puzzles locals, crea els seus grafs (si no existien) i executa l'avaluació amb `eval`, guardant la valoració al mateix CSv en què hi havia les mètriques.
- **`src/rate_all.py`**: Llegeix un CSV en què s'han guardat les valoracions dels puzzles i les puja totes al repositori del projecte.

---

## Decisions de Disseny

### Estructura dels directoris
Per a mantenir un cert ordre entre els puzzles que generàvem nosaltres i els que ens descarregàvem del repositori, vam decidir guardar-los cadascun en una carpeta pròpia: els puzzles generats a la carpeta `custom/` i els descarregats del repositori a la carpeta `repository/`. D'aquesta manera tenim més control sobre quins puzzles volem solucionar, enviar al repositori, etc., i mantenim molt més ordre. A més, vam fer que de manera automàtica quan generem un graf, la solució ..., aquests nous fitxers es generin a la mateixa carpeta que el puzzle original (custom/repository) , però en un directori diferent (graphs, solutions...). L'únic defecte que té tot això és que els puzzles generats per nosaltres els tenim duplicats: un cop amb el nostre nom i un altre cop amb el nom corresponent al seu ID del repositori.

### Mètriques del puzzle
Les mètriques que s'analitzen i extreuen a `graph.py` per establir més tarda la qualitat d'un puzzle són:
1. **La mida del puzzle (`size`)**: Càlcul de `W * H`. 
2. **Passos fins a la millor solució (`min_moves`)**: Llargada de la ruta òptima.
3. **Total d'estats del graf (`num_states`)**: El nombre total d'estats assolibles des de l'estat inicial.
4. **Articulation points de la millor solució**: Estats els quals s'hi ha de pasar sí o sí per arribar a la solució òptima.
5. **Average branching factor**: Mitjana de moviments diferents possibles per cada estat del graf.

### Normalització d'estats
Un problema considerable que vam trobar a les primeres etapes de generació del graf va ser el següent: quan un puzzle té més d'una peça de la mateixa forma, l'ideal seria que un estat en què la peça idèntica 1 està al (0,1) i la peça idèntica 2 està al (1,0), i un estat en què la peça idèntica 1 està al (1,0) i la peça idèntica 2 està al (0,1) fos el mateix estat. Per a poder fer-ho vam haver de fer el següent:  ordenar les peces de manera canònica, és a dir, vam haver de ordenar les peces segons la seva forma i la seva posició de manera que l'ID fos el mateix independentment de quina peça idèntica està a cada lloc.

L'únic cas en què no volem que sigui així és quan una de les peces idèntiques és la peça "goal", ja que aquesta peça no es pot "intercanviar" per cap altra.

### Truncament dels grafs i A*
Per tal de no generar un graf massa gran, vam decidir truncar-lo quan arribava a un cert nombre de nodes NODE_LIMIT. Quan s'arriba a aquest límit es para el dfs i es fa un A* per trobar la millor solució possible, afegint les arestes noves al graf en el cas en què fos necessari. Tot i que no tenim la garantia de que sigui la millor solució possible, és una bona aproximació per a la majoria dels casos. D'aquesta manera, tot i no tenir el graf complet podem calcular les mètriques i posar una nota, malgrat que aquesta podria ser diferent si generessim el graf complet. 

### Mètode de valoració
Un cop ja teníem les mètriques de cada graf, ens vam trobar amb una gran qüestió: com sabíem què era bó i què era dolent, què feia que una mètrica fos bona o fos dolenta? Per exemple, un nombre alt de passos és millor o pitjor? I un nombre alt d'estats? 

Després de provar diferents fòrmules i maneres de valorar els grafs, no ens acabava de convencer cap, i vam decidir seguir un camí poc convencional: utilitzar un model de *Machine Learning* per avaluar els puzzles. Ja teníem una mica d'experiència amb models d'aquest tipus, ja que havíem fet servir l'algorisme RandomForest a la Datathon d'aquest any, però malgrat això no teníem els coneixements necessaris per dur a terme aquest projecte. Per tant, vam haver de recórrer a l'ús de la IA per a què ens ajudés a fer el codi per entrenar el model. 

La manera en què el vam entrenar va ser la següent: vam agafar tots els puzzles originals del repositori i alguns puzzles que ja havíem generat anteriorment, i els hi vam posar una nota manualment. Aquesta nota està basada al 100% en el nostre criteri subjectiu, i tenint en compte el que feia que un puzzle fos "bo" segons nosaltres: si era suficientment complicat (però no massa com per que fos impossible), si ens agradava la manera en què es resolia (potser no era el klotski més llarg, però si que era un solució prou original) i en general, si ens semblava que era un puzzle que ens agradaria jugar.

Un cop fet això, i com que les mètriques ja les tenim calculades quan generem el graf, a eval.py simplement hem de fer servir el model per a posar una vloració basant-se en les mètriques.

### Generació de puzzles
Per generar nous puzzles també vam intentar seguir diverses estratègies. Per exemple, la primera estratègia que vam seguir va ser començar des de l'estat final, i moure enrere x moviments. El problema és que d'aquesta manera no ens assegurem que la millor solució estigui a x moviments, ja que pot existir un altre camí que estigui només a 3 moviments del goal malgrat haver fet 40 moviments.

La següent manera que vam provar, i que és la que en un principi anàvem a fer servir, era, a partir de l'estat inicial i d'un goal prefixat, fer un A* per a veure si la solució estava al menys a x moviments de l'inici, i si no ho estava descartar el puzzle ràpidament. Si la solució de l'estrella complia amb els requisits, passàvem a fer un DFS normal per generar tot el graf i trobar la millor solució i veure si realment el puzzle era suficientment bo o no. D'aquesta manera tractàvem cada puzzle molt ràpidament però teníem el problema que es necessitaven massa intents per generar un sol puzzle.

Finalment, la manera amb què ens hem quedat és la següent: partim d'un estat qualsevol, i aquest estat serà el nostre estat final.


### Seleccionar usuari
Per tal que els dos poguéssim pujar els puzzles i les valoracions amb el nostre token i usuari de manera còmoda i àgil, hem fet que a tots els programes en què es necessita un token, a la terminal, al principi et demani qui ets: "x" per a Xavi i "a" per a Àngel. D'aquesta manera només necessitem tenir els tokens guardats en una variable i no haver d'introduir-lo cada cop que volem interactuar amb el repositori.




## Referències i Eines de Suport

- **Projecte Base**: El projecte es basa en les instruccions i estructura del repositori de GitHub d'en **Pau Fernández** ([pauek/klotski](https://github.com/pauek/klotski)), desenvolupat i estructurat amb la col·laboració i ajuda de **Roberto Nsoni** i **Jordi Cortadella**.
- **Intel·ligència Artificial Generativa**: Durant l'execució d'aquest projecte s'han fet servir **Claude**, **Gemini** i l'**IDE Antigravity** per a comprendre millor la base de codi inicial proporcionada i l'arquitectura general del projecte, aprendre a utilitzar llibreries i eines noves per a nosaltres, com ara graph-tool, les llibreries request, json, argparse, sys, etc., superar el bloqueig inicial a l'hora d'implementar certs algorismes amb eines amb les quals no erem familiars, accelerar la localització d'errors desconeguts o comportaments inesperats...
Malgrat això, tot el codi final ha estat revisat, adaptat i integrat de manera crítica per a assegurar-ne la correcció, l'eficiència i que compleixi tots els requisits del projecte.
