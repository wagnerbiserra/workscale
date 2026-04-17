import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    try:
        # ☁️ Streamlit Cloud (usa secrets)
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
    except Exception:
        # 💻 Local (usa arquivo)
        cred = credentials.Certificate("firebase_key.json")

    firebase_admin.initialize_app(cred)

db = firestore.client()