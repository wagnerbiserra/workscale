from firebase_config import db

print("Testando conexão...")

usuarios = list(db.collection("usuarios").stream())
print(f"Total usuários: {len(usuarios)}")