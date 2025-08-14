import json
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sentence_transformers import SentenceTransformer
import matplotlib.pyplot as plt

# === 1. Charger les données JSON ===
json_path = "../nature3.json"
if not os.path.exists(json_path):
    raise FileNotFoundError(f"Fichier '{json_path}' introuvable.")

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Gérer le cas d'un seul enregistrement
if not isinstance(data, list):
    data = [data]

# === 2. Nettoyer les données ===
df = pd.DataFrame(data)
df = df[df["montant"].notna() & df["objet"].notna() & df["acheteur"].notna()]

# === 3. Créer le texte complet ===
def fusion_texte(row):
    ref = row.get("reference", "")
    return f"{row['objet']} {row['acheteur']} {ref}"

df["texte_complet"] = df.apply(fusion_texte, axis=1)

# === 4. Transformer le texte en vecteurs ===
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
X = model.encode(df["texte_complet"].tolist())  # shape (n_samples, 384)
y = df["montant"].values

# === 5. Split train/test ===
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

# === 6. Entraîner un modèle de régression ===
reg = GradientBoostingRegressor(
    n_estimators=100,
    learning_rate=0.05,
    max_depth=3,
    subsample=0.8,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=42
)
reg.fit(X_train, y_train)

# === 7. Prédictions et évaluation ===
y_pred = reg.predict(X_test)

mse = mean_squared_error(y_test, y_pred)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("📊 Résultats de la régression (Embedding + Regressor)")
print(f"MAE : {mae:.2f} MAD")
print(f"MSE : {mse:.2f}")
print(f"R²  : {r2:.3f}")

# === 8. Visualisation ===
if len(y_test) > 1:
    plt.figure(figsize=(10, 5))
    plt.scatter(y_test, y_pred, alpha=0.6, color="green")
    plt.plot([min(y_test), max(y_test)], [min(y_test), max(y_test)], "r--")
    plt.xlabel("Montant réel")
    plt.ylabel("Montant prédit")
    plt.title("Montant réel vs Montant prédit (Embedding + Regressor)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()
else:
    print(f"✅ Montant réel : {y_test[0]} MAD — Montant prédit : {y_pred[0]:.2f} MAD")

# === 9. Fonction pour prédire un nouvel enregistrement ===
def predict_new_record(reg, model, nouvel_enregistrement):
    ref = nouvel_enregistrement.get("reference", "")
    texte = f"{nouvel_enregistrement['objet']} {nouvel_enregistrement['acheteur']} {ref}"
    vecteur = model.encode([texte])
    montant = reg.predict(vecteur)[0]
    return montant

# === 10. Boucle interactive ===
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
