# =============================================================================
# GUIDA: Come rendere FrigoSmart accessibile da internet con ngrok
# =============================================================================
# ngrok crea un "tunnel" sicuro che espone il tuo server Flask locale
# su un URL pubblico (es. https://abc123.ngrok.io) accessibile da qualsiasi
# dispositivo connesso a internet, anche fuori casa.

# =============================================================================
# 1. INSTALLA NGROK
# =============================================================================
# Vai su https://ngrok.com → registrati (gratuito) → scarica ngrok
# Oppure installa con:
#   Windows:  scoop install ngrok
#   Mac:      brew install ngrok
#   Linux:    snap install ngrok

# =============================================================================
# 2. CONFIGURA IL TOKEN (una sola volta)
# =============================================================================
# Dal sito ngrok copia il tuo authtoken e incollalo qui:
#   ngrok config add-authtoken IL-TUO-TOKEN

# =============================================================================
# 3. AVVIA IL TUNNEL
# =============================================================================
# Prima avvia il server Flask:
#   python app.py
#
# Poi in un altro terminale avvia ngrok:
#   ngrok http 5000
#
# Vedrai qualcosa come:
#   Forwarding  https://abc123.ngrok-free.app -> http://localhost:5000
#
# Quell'URL è il tuo SERVER_URL da condividere con la famiglia!

# =============================================================================
# 4. CONFIGURA L'APP KIVY CON L'URL NGROK
# =============================================================================
# Nel terminale prima di avviare scanner_kivy.py:
#
# Windows (PowerShell):
#   $env:SERVER_URL = "https://abc123.ngrok-free.app"
#   python scanner_kivy.py
#
# Mac/Linux:
#   export SERVER_URL="https://abc123.ngrok-free.app"
#   python scanner_kivy.py
#
# ⚠️  L'URL ngrok cambia ad ogni riavvio (piano gratuito).
#     Per un URL fisso puoi pagare il piano a pagamento di ngrok,
#     oppure usare un Raspberry Pi con IP statico in casa.

# =============================================================================
# 5. CONDIVIDI CON LA FAMIGLIA
# =============================================================================
# 1. Avvia app.py sul tuo PC
# 2. Avvia ngrok http 5000
# 3. Copia l'URL https://....ngrok-free.app
# 4. Ogni membro della famiglia imposta SERVER_URL con quell'indirizzo
# 5. Al primo avvio dell'app, ogni membro crea il proprio profilo
#    e inserisce il CODICE FAMIGLIA mostrato nella schermata 👨‍👩‍👧 Famiglia