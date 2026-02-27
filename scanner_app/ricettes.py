import anthropic
from config import ANTHROPIC_API_KEY
from scanner_app.database import get_tutti_prodotti

def genera_ricette():
    if not ANTHROPIC_API_KEY:
        return {"errore": "API Key mancante in config.py"}

    # 1. Recuperiamo gli ingredienti dal DB
    prodotti = get_tutti_prodotti()
    nomi_prodotti = [p['nome_prodotto'] for p in prodotti]
    
    if not nomi_prodotti:
        return {"messaggio": "Il frigo è vuoto! Scansiona qualcosa prima."}

    # 2. Prepariamo il messaggio per l'AI
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""Ho i seguenti ingredienti in frigo: {', '.join(nomi_prodotti)}. 
    Suggeriscimi 3 ricette veloci che posso cucinare. 
    Rispondi in formato JSON con questa struttura:
    {{
      "ricette": [
        {{"titolo": "...", "ingredienti": "...", "procedimento": "..."}}
      ]
    }}
    Rispondi solo con il JSON, niente chiacchiere."""

    try:
        messaggio = client.messages.create(
            model="claude-3-haiku-20240307", # Modello veloce ed economico
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        # Estraiamo il testo e lo convertiamo in dizionario Python
        import json
        return json.loads(messaggio.content[0].text)
    except Exception as e:
        return {"errore": f"L'AI ha avuto un problema: {str(e)}"}