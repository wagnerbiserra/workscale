import firebase_admin
from firebase_admin import credentials, firestore

# Evita inicializar mais de uma vez
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred)

# Conexão com Firestore
db = firestore.client()