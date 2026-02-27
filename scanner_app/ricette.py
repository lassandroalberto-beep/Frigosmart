# =============================================================================
# ricette.py — Suggerimenti di ricette con l'AI (Claude di Anthropic)
# =============================================================================
# Questo modulo prende gli ingredienti che hai in casa dal database
# e chiede a Claude di suggerire ricette organizzate per categoria.
#
# Per usarlo hai bisogno di una chiave API Anthropic:
# 1. Registrati su https://console.anthropic.com
# 2. Crea una API key
# 3. Esegui nel terminale: export ANTHROPIC_API_KEY="sk-ant-..."

import anthropic
from config import ANTHROPIC_API_KEY
from scanner_app.database import get_tutti_ingredienti


def genera_ricette():
    """
    Funzione principale: legge gli ingredienti dal DB e chiede ricette all'AI.
    
    Restituisce un dizionario organizzato per categoria:
    {
        'primi': [...],
        'secondi': [...],
        'contorni': [...],
        'dessert': [...]
    }
    Oppure None in caso di errore.
    """
    
    if not ANTHROPIC_API_KEY:
        return {
            'errore': 'Chiave API Anthropic non configurata. '
                      'Imposta la variabile d\'ambiente ANTHROPIC_API_KEY.'
        }
    
    # Recuperiamo gli ingredienti dal database
    ingredienti = get_tutti_ingredienti()
    
    if not ingredienti:
        return {'errore': 'Nessun prodotto in dispensa. Scansiona qualcosa prima!'}
    
    # Prepariamo la lista per il prompt
    lista_ingredienti = _formatta_ingredienti(ingredienti)
    
    # Chiediamo le ricette all'AI
    risposta_ai = _chiedi_a_claude(lista_ingredienti)
    
    return risposta_ai


def _formatta_ingredienti(ingredienti):
    """
    Trasforma la lista di prodotti dal DB in una stringa leggibile per l'AI.
    Mette in evidenza quelli in scadenza, così l'AI li prioritizza nelle ricette.
    
    Esempio output:
    "- Pasta (scade tra 2 giorni ⚠️)
     - Pomodori
     - Mozzarella (scade oggi ⚠️)"
    """
    from datetime import datetime, date
    
    oggi = date.today()
    righe = []
    
    for prodotto in ingredienti:
        nome = prodotto['nome_prodotto']
        scadenza = prodotto.get('data_scadenza')
        
        if scadenza:
            data_sc = datetime.strptime(scadenza, '%Y-%m-%d').date()
            giorni = (data_sc - oggi).days
            
            if giorni == 0:
                righe.append(f"- {nome} (scade OGGI ⚠️)")
            elif giorni <= 3:
                righe.append(f"- {nome} (scade tra {giorni} giorni ⚠️)")
            else:
                righe.append(f"- {nome}")
        else:
            righe.append(f"- {nome}")
    
    return '\n'.join(righe)


def _chiedi_a_claude(lista_ingredienti):
    """
    Invia la richiesta all'API di Claude e processa la risposta.
    
    Il "system prompt" definisce il comportamento dell'AI.
    Il "user message" è la nostra domanda specifica.
    """
    
    # Inizializziamo il client Anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    system_prompt = """Sei un cuoco italiano esperto e creativo. 
Il tuo compito è suggerire ricette pratiche e gustose basandoti sugli ingredienti disponibili.

Regole:
- Suggerisci SOLO ricette realizzabili con gli ingredienti forniti (puoi assumere che ci siano condimenti base come sale, olio, aglio)
- Dai priorità agli ingredienti segnati con ⚠️ (in scadenza) 
- Sii specifico: dai nomi di ricette reali, non generici
- Per ogni ricetta indica (brevemente) gli ingredienti principali necessari

Rispondi SEMPRE in questo formato JSON valido e nient'altro:
{
  "primi": [
    {"nome": "Nome ricetta", "ingredienti_necessari": ["ing1", "ing2"], "difficolta": "facile/media/difficile"}
  ],
  "secondi": [...],
  "contorni": [...],
  "dessert": [...]
}
Se per una categoria non hai ingredienti sufficienti, metti un array vuoto [].
"""
    
    user_message = f"""Ho questi ingredienti in casa:

{lista_ingredienti}

Suggeriscimi delle ricette per oggi."""
    
    try:
        messaggio = client.messages.create(
            model='claude-opus-4-6',
            max_tokens=1500,
            system=system_prompt,
            messages=[
                {'role': 'user', 'content': user_message}
            ]
        )
        
        # Estraiamo il testo dalla risposta
        testo_risposta = messaggio.content[0].text
        
        # Convertiamo il JSON in un dizionario Python
        import json
        ricette = json.loads(testo_risposta)
        return ricette
        
    except json.JSONDecodeError:
        # Se l'AI non restituisce JSON valido (capita raramente)
        return {'errore': 'Risposta AI non valida. Riprova.'}
    
    except anthropic.AuthenticationError:
        return {'errore': 'Chiave API Anthropic non valida. Controlla config.py.'}
    
    except anthropic.APIConnectionError:
        return {'errore': 'Impossibile connettersi ad Anthropic. Controlla la connessione.'}
    
    except Exception as e:
        return {'errore': f'Errore imprevisto: {str(e)}'}
