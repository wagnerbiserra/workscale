from firebase_config import db

# Criar um teste no banco
db.collection("teste").document("teste1").set({
    "nome": "Wagner",
    "status": "ok"
})

print("🔥 Gravou no Firebase com sucesso!")