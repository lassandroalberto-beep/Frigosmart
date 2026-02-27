# =============================================================================
# config.py — Configurazione per deploy su Render.com
# =============================================================================

import os

# --- SERVER ---
HOST = '0.0.0.0'
PORT = int(os.getenv('PORT', 5000))
DEBUG = False

# --- DATABASE ---
# Su Render il disco persistente è montato in /data
# In locale usa frigo.db nella cartella corrente
DB_NAME = os.getenv('DB_PATH', 'frigo.db')

# --- AUTENTICAZIONE (password semplice per uso personale) ---
APP_PASSWORD = os.getenv('APP_PASSWORD', 'cucina2025')  # cambia su Render!

# --- NOTIFICHE SCADENZE ---
GIORNI_PREAVVISO = 3

# --- OPEN FOOD FACTS ---
OPENFOODFACTS_URL = 'https://world.openfoodfacts.org/api/v0/product/{barcode}.json'
OPENFOODFACTS_TIMEOUT = 5

# --- ANTHROPIC (AI RICETTE) ---
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
