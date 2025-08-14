import json
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel
from torch.optim import AdamW
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np

# === Paramètres ===
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EPOCHS = 10
BATCH_SIZE = 8
LEARNING_RATE = 2e-5
MAX_LENGTH = 128
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# === Chargement des données JSON ===
with open("../nature1.json", "r", encoding="utf-8") as f:
    data = json.load(f)

if not isinstance(data, list):
    data = [data]

# Création du texte combiné
for d in data:
    ref = d.get("reference", "")
    d["texte_complet"] = f"{d['objet']} {d['acheteur']} {ref}"

# Filtrage
data = [d for d in data if "montant" in d and d["montant"] is not None]

# === Dataset PyTorch personnalisé ===
class MarcheDataset(Dataset):
    def __init__(self, texts, targets, tokenizer):
        self.texts = texts
        self.targets = targets
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            self.texts[idx],
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
            return_tensors="pt"
        )
        item = {key: val.squeeze(0) for key, val in encoding.items()}
        item["labels"] = torch.tensor(self.targets[idx], dtype=torch.float)
        return item

# === Tokenizer & préparation des données ===
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

texts = [d["texte_complet"] for d in data]
targets = [d["montant"] for d in data]

X_train, X_test, y_train, y_test = train_test_split(texts, targets, test_size=0.2, random_state=42)

train_dataset = MarcheDataset(X_train, y_train, tokenizer)
test_dataset = MarcheDataset(X_test, y_test, tokenizer)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=1)

# === Modèle pour régression ===
class TransformerRegressor(nn.Module):
    def __init__(self, model_name):
        super().__init__()
        self.base_model = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(0.2)
        self.regressor = nn.Linear(self.base_model.config.hidden_size, 1)

    def forward(self, input_ids, attention_mask):
        output = self.base_model(input_ids=input_ids, attention_mask=attention_mask)
        pooled = output.last_hidden_state[:, 0, :]  # [CLS] token
        pooled = self.dropout(pooled)
        return self.regressor(pooled).squeeze(1)

# === Entraînement ===
model = TransformerRegressor(MODEL_NAME).to(DEVICE)
optimizer = AdamW(model.parameters(), lr=LEARNING_RATE)
criterion = nn.MSELoss()

print("📦 Début de l'entraînement...")
for epoch in range(EPOCHS):
    model.train()
    total_loss = 0
    for batch in train_loader:
        input_ids = batch["input_ids"].to(DEVICE)
        attention_mask = batch["attention_mask"].to(DEVICE)
        labels = batch["labels"].to(DEVICE)

        optimizer.zero_grad()
        outputs = model(input_ids, attention_mask)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    print(f"📘 Epoch {epoch+1}/{EPOCHS} — Loss: {total_loss/len(train_loader):.4f}")

# === Évaluation ===
model.eval()
y_true = []
y_pred = []

with torch.no_grad():
    for batch in test_loader:
        input_ids = batch["input_ids"].to(DEVICE)
        attention_mask = batch["attention_mask"].to(DEVICE)
        labels = batch["labels"].cpu().numpy()
        outputs = model(input_ids, attention_mask).cpu().numpy()
        y_true.extend(labels)
        y_pred.extend(outputs)

mse = mean_squared_error(y_true, y_pred)
r2 = r2_score(y_true, y_pred)

print("\n📊 Évaluation du modèle fine-tuné")
print(f"MSE  : {mse:.2f}")
print(f"R²   : {r2:.3f}")

# === 10. Fonction pour prédire un nouvel enregistrement ===
def predict_new_record(reg, model, nouvel_enregistrement):
    ref = nouvel_enregistrement.get("reference", "")
    texte = f"{nouvel_enregistrement['objet']} {nouvel_enregistrement['acheteur']} {ref}"
    vecteur = model.encode([texte])
    montant_pred = reg.predict(vecteur)[0]
    return montant_pred

# === 11. Boucle interactive pour tester de nouveaux enregistrements ===
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
