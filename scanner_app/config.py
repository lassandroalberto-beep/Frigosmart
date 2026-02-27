# =============================================================================
# config.py — Configurazione centrale dell'app
# =============================================================================
# Metti QUI tutte le impostazioni. Così non devi cercare valori sparsi
# per il codice ogni volta che vuoi cambiare qualcosa.

# --- SERVER ---
HOST = '0.0.0.0'   # Ascolta su tutte le interfacce di rete (necessario per il telefono)
PORT = 5000
DEBUG = True        # Metti False quando l'app è "in produzione"

# --- DATABASE ---
DB_NAME = 'frigo.db'

# --- NOTIFICHE SCADENZE ---
# Quanti giorni prima ti avvisiamo che un prodotto sta per scadere?
GIORNI_PREAVVISO = 3

# --- OPEN FOOD FACTS ---
# API gratuita e pubblica, nessuna chiave necessaria!
OPENFOODFACTS_URL = 'https://world.openfoodfacts.org/api/v0/product/{barcode}.json'
OPENFOODFACTS_TIMEOUT = 5  # secondi massimi di attesa

# --- ANTHROPIC (AI RICETTE) ---
# Legge la chiave API dalla variabile d'ambiente, non hardcodarla mai nel codice!
# Per impostarla: export ANTHROPIC_API_KEY="sk-ant-..."
import os
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
