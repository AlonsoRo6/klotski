import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import joblib #type:ignore
import os
import argparse


MODEL_OUTPUT = 'model_difficulty.pkl'

def train_with_validation(csv_path:str):
    if not os.path.exists(csv_path):
        print(f"Error: No s'ha trobat {csv_path}")
        return

    df = pd.read_csv(csv_path)
    train_df = df.dropna(subset=['manual_score'])

    if len(train_df) < 10: # Necessitem una mica més de massa crítica per validar
        print(f"Tens pocs puzzles ({len(train_df)}). Entrenant amb tot el set sense validació.")
        X_train = train_df[['size', 'min_moves', 'total_states', 'articulation_points', 'avg_branching']]
        y_train = train_df['manual_score']
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
    
    else:
        # 1. Separem les dades: 80% per aprendre, 20% per a l'examen
        X = train_df[['size', 'min_moves', 'total_states', 'articulation_points', 'avg_branching']]
        y = train_df['manual_score']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42)

        # 2. Entrenem amb el 80%
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        

        # 3. EXAMEN: Predim la nota dels puzzles que el model NO ha vist mai (el 20%)
        predictions = model.predict(X_test)
        
        # 4. Calculem l'error mitjà (MAE)
        error = mean_absolute_error(y_test, predictions)

        train_preds = model.predict(X_train)
        train_error = mean_absolute_error(y_train, train_preds)
        print(f"Error en dades d'estudi: {train_error:.2f}")
        print(f"Error en dades d'examen: {error:.2f}") # L'error que ja calculaves
        
        print("\n--- Resultats de la validació ---")
        for real, pred in zip(y_test, predictions):
            print(f"Nota real: {real} | Predicció: {pred:.2f} | Diferència: {abs(real-pred):.2f}")
        
        print(f"\nError mitjà absolut: {error:.2f} estrelles.")
        
        # Finalment, tornem a entrenar amb EL 100% per a que el model sigui el més fort possible
        model.fit(X, y)

    joblib.dump(model, MODEL_OUTPUT)
    print(f"✓ Model final guardat a '{MODEL_OUTPUT}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entrenador del model de machine learning.")
    parser.add_argument("--csv-path", type=str, default="puzzles_metrics.csv", help="Fitxer CSV amb les dades d'entrenament")
    args = parser.parse_args()

    CSV_PATH = args.csv_path
    train_with_validation(CSV_PATH)