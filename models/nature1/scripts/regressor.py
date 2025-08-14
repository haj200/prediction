import json
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split, cross_val_score
from sentence_transformers import SentenceTransformer
import matplotlib.pyplot as plt
import os

# === 1. Charger les données JSON ===
json_path = "../nature1.json"
if not os.path.exists(json_path):
    raise FileNotFoundError(f"Fichier '{json_path}' introuvable.")

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Gérer le cas d'un seul enregistrement JSON
if not isinstance(data, list):
    data = [data]

# === 2. Charger dans un DataFrame ===
df = pd.DataFrame(data)

# === 3. Nettoyer les données ===
df = df[df["montant"].notna() & df["objet"].notna() & df["acheteur"].notna()]

# === 4. Créer le texte combiné (objet + acheteur + référence) ===
def fusion_texte(row):
    ref = row.get("reference", "")
    return f"{row['objet']} {row['acheteur']} {ref}"

df["texte_complet"] = df.apply(fusion_texte, axis=1)

# === 5. Encoder le texte avec SentenceTransformer ===
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
X = model.encode(df["texte_complet"].tolist())

# === 6. Log-transformer la cible ===
y = np.log1p(df["montant"].values)  # log(1 + montant)

# === 7. Split des données ===
if len(df) > 10:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
else:
    X_train, X_test, y_train, y_test = X, X, y, y

# === 8. Entraîner un modèle moins complexe ===
reg = GradientBoostingRegressor(
    n_estimators=150,
    learning_rate=0.05,
    max_depth=2,
    subsample=0.8,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=42
)
reg.fit(X_train, y_train)

# === 9. Cross-validation (optionnel mais utile)
cv_scores = cross_val_score(reg, X, y, cv=5, scoring="r2")
print(f"✅ Moyenne R² en cross-validation (5 folds) : {np.mean(cv_scores):.3f}")

# === 10. Évaluer le modèle ===
y_pred_log = reg.predict(X_test)
y_pred = np.expm1(y_pred_log)  # Revenir à l’échelle normale
y_test_true = np.expm1(y_test)

mse = mean_squared_error(y_test_true, y_pred)
mae = mean_absolute_error(y_test_true, y_pred)
r2 = r2_score(y_test_true, y_pred)

print("\n📊 Résultats sur jeu de test")
print(f"Train R² : {reg.score(X_train, y_train):.3f}")
print(f"Test  R² : {r2:.3f}")
print(f"MAE : {mae:.2f} MAD")
print(f"MSE : {mse:.2f}")

# === 11. Visualisation ===
if len(y_test) > 1:
    plt.figure(figsize=(8, 6))
    plt.scatter(y_test_true, y_pred, alpha=0.5, color='green')
    plt.plot([min(y_test_true), max(y_test_true)], [min(y_test_true), max(y_test_true)], 'r--')
    plt.title("Montant réel vs Montant prédit")
    plt.xlabel("Montant réel")
    plt.ylabel("Montant prédit")
    plt.grid(True)
    plt.tight_layout()
    plt.show()
else:
    print(f"✅ Montant réel : {y_test_true[0]} MAD — Montant prédit : {y_pred[0]:.2f} MAD")

# === 12. Fonction pour prédire un nouvel enregistrement ===
def predict_new_record(reg, model, nouvel_enregistrement):
    ref = nouvel_enregistrement.get("reference", "")
    texte = f"{nouvel_enregistrement['objet']} {nouvel_enregistrement['acheteur']} {ref}"
    vecteur = model.encode([texte])
    log_montant = reg.predict(vecteur)[0]
    return np.expm1(log_montant)

# === 13. Boucle interactive ===
print("\n=== Testez des nouveaux enregistrements (tapez 'quit' pour sortir) ===")

while True:
    objet = input("Objet : ").strip()
    if objet.lower() == "quit":
        print("Fin du programme.")
        break

    acheteur = input("Acheteur : ").strip()
    if acheteur.lower() == "quit":
        print("Fin du programme.")
        break

    reference = input("Reference (optionnelle) : ").strip()
    if reference.lower() == "quit":
        print("Fin du programme.")
        break

    nouveau = {
        "objet": objet,
        "acheteur": acheteur,
        "reference": reference
    }

    montant_pred = predict_new_record(reg, model, nouveau)
    print(f"➡️ Montant prédit : {montant_pred:.2f} MAD\n")
