# =============================================================================
# notifiche.py — Sistema di notifiche per le scadenze
# =============================================================================
# Usiamo ntfy.sh: un servizio gratuito e open-source per notifiche push.
# Non richiede account — basta scegliere un "canale" con un nome unico.
#
# Come funziona:
# 1. Installa l'app "ntfy" sul tuo telefono (Android/iOS, gratuita)
# 2. Iscriviti al canale "frigosmart-TUONOME" (scegli un nome unico!)
# 3. Il backend manda notifiche a quel canale → arrivano sul telefono
#
# Alternativa email: vedi la funzione invia_email_scadenze() in fondo al file.

import requests
from datetime import datetime
from config import GIORNI_PREAVVISO
from scanner_app.database import get_prodotti_in_scadenza


# ⚠️  CAMBIA QUESTO con un nome unico per te (es. "frigosmart-mario-rossi")
# Chiunque conosca questo nome può ricevere le tue notifiche, quindi rendilo non ovvio.
NTFY_CANALE = 'frigosmart-cambia-questo-nome'
NTFY_URL = f'https://ntfy.sh/{NTFY_CANALE}'


def controlla_e_notifica():
    """
    Funzione principale: controlla i prodotti in scadenza e manda notifiche.
    Viene chiamata automaticamente ogni giorno dallo scheduler in app.py.
    """
    print(f"🔔 Controllo scadenze... ({datetime.now().strftime('%d/%m/%Y %H:%M')})")
    
    prodotti = get_prodotti_in_scadenza(giorni=GIORNI_PREAVVISO)
    
    if not prodotti:
        print("✅ Nessun prodotto in scadenza nei prossimi giorni.")
        return
    
    # Raggruppiamo per urgenza
    oggi = []
    presto = []
    
    for p in prodotti:
        scadenza = datetime.strptime(p['data_scadenza'], '%Y-%m-%d').date()
        giorni_rimasti = (scadenza - datetime.today().date()).days
        
        if giorni_rimasti == 0:
            oggi.append(p['nome_prodotto'])
        else:
            presto.append((p['nome_prodotto'], giorni_rimasti))
    
    # Costruiamo il messaggio
    messaggio = _costruisci_messaggio(oggi, presto)
    urgenza = 'urgent' if oggi else 'default'
    
    _invia_ntfy(messaggio, urgenza)


def _costruisci_messaggio(oggi, presto):
    """Costruisce il testo della notifica in modo leggibile."""
    parti = []
    
    if oggi:
        nomi = ', '.join(oggi)
        parti.append(f"⚠️ SCADE OGGI: {nomi}")
    
    if presto:
        righe = [f"• {nome} ({giorni}gg)" for nome, giorni in presto]
        parti.append("📅 In scadenza presto:\n" + '\n'.join(righe))
    
    return '\n\n'.join(parti)


def _invia_ntfy(messaggio, priorita='default'):
    """
    Invia la notifica tramite ntfy.sh usando una semplice richiesta HTTP POST.
    
    Gli 'headers' sono metadati che accompagnano la richiesta HTTP.
    In questo caso diciamo a ntfy il titolo della notifica e la sua priorità.
    """
    try:
        risposta = requests.post(
            NTFY_URL,
            data=messaggio.encode('utf-8'),  # encode() converte il testo in bytes
            headers={
                'Title': '🥦 FrigoSmart — Scadenze',
                'Priority': priorita,         # 'urgent' = notifica con suono forte
                'Tags': 'refrigerator,warning'
            },
            timeout=5
        )
        
        if risposta.status_code == 200:
            print(f"✅ Notifica inviata a ntfy canale '{NTFY_CANALE}'")
        else:
            print(f"⚠️  ntfy ha risposto con status {risposta.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("🌐 Impossibile inviare la notifica: nessuna connessione internet.")
    except Exception as e:
        print(f"❌ Errore nell'invio notifica: {e}")


# =============================================================================
# ALTERNATIVA: Notifiche via Email (opzionale)
# =============================================================================
# Se preferisci ricevere email invece di notifiche push, usa questa funzione.
# Richiede di abilitare "App password" su Gmail (non la tua password normale).
# Guida: https://support.google.com/accounts/answer/185833

import smtplib
from email.mime.text import MIMEText

def invia_email_scadenze(destinatario, prodotti_in_scadenza):
    """
    Invia un'email di riepilogo delle scadenze.
    
    Parametri da configurare (meglio in config.py o variabili d'ambiente):
    - EMAIL_MITTENTE: la tua email Gmail
    - EMAIL_PASSWORD: la App Password di Gmail (non la password normale!)
    - destinatario: a chi mandare l'email
    """
    EMAIL_MITTENTE = 'tua-email@gmail.com'    # ← cambia
    EMAIL_PASSWORD = 'xxxx xxxx xxxx xxxx'    # ← App Password Gmail

    if not prodotti_in_scadenza:
        return

    # Costruiamo il corpo dell'email in HTML per renderlo più leggibile
    righe_html = ''.join(
        f"<li><b>{p['nome_prodotto']}</b> — scade il {p['data_scadenza']}</li>"
        for p in prodotti_in_scadenza
    )
    corpo = f"""
    <h2>🥦 FrigoSmart — Scadenze imminenti</h2>
    <p>Questi prodotti stanno per scadere:</p>
    <ul>{righe_html}</ul>
    <p><i>Controlla il tuo frigorifero!</i></p>
    """
    
    msg = MIMEText(corpo, 'html')
    msg['Subject'] = '⚠️ FrigoSmart: prodotti in scadenza'
    msg['From'] = EMAIL_MITTENTE
    msg['To'] = destinatario

    try:
        # Connessione sicura al server SMTP di Gmail
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_MITTENTE, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"✅ Email inviata a {destinatario}")
    except Exception as e:
        print(f"❌ Errore invio email: {e}")
