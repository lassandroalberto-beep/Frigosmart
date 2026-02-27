# =============================================================================
# pianificatore.py — Pianificatore pasti settimanale con AI
# =============================================================================
# L'AI genera un menu completo per 7 giorni (colazione, pranzo, cena)
# basandosi sugli ingredienti in dispensa, privilegiando quelli in scadenza.
# L'utente può poi modificare i singoli pasti manualmente.

import json
import re
import anthropic
from datetime import date, timedelta
from config import ANTHROPIC_API_KEY
from database import (
    get_tutti_ingredienti, salva_piano_pasti,
    get_piano_settimana, aggiorna_pasto, elimina_piano_settimana
)

GIORNI_SETTIMANA = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']


def genera_piano_settimanale():
    """
    Chiede all'AI di generare un menu per 7 giorni.
    Salva il piano nel DB e lo restituisce.

    Struttura restituita:
    {
        'settimana_dal': '2026-02-25',
        'giorni': [
            {
                'giorno': 'Lunedì',
                'data': '2026-02-25',
                'colazione': 'Yogurt con frutta e cereali',
                'pranzo': 'Pasta al pomodoro',
                'cena': 'Pollo arrosto con patate'
            },
            ...
        ]
    }
    """
    if not ANTHROPIC_API_KEY:
        return {'errore': "Chiave API Anthropic non configurata."}

    ingredienti = get_tutti_ingredienti()
    if not ingredienti:
        return {'errore': 'Nessun prodotto in dispensa. Scansiona qualcosa prima!'}

    lista = _formatta_ingredienti(ingredienti)
    piano_ai = _chiedi_piano_a_claude(lista)

    if 'errore' in piano_ai:
        return piano_ai

    # Calcoliamo le date della settimana a partire da oggi
    oggi = date.today()
    # Troviamo il lunedì di questa settimana
    lunedi = oggi - timedelta(days=oggi.weekday())

    giorni_con_date = []
    for i, giorno_data in enumerate(piano_ai.get('giorni', [])):
        data_giorno = lunedi + timedelta(days=i)
        giorni_con_date.append({
            'giorno': GIORNI_SETTIMANA[i],
            'data': data_giorno.strftime('%Y-%m-%d'),
            'colazione': giorno_data.get('colazione', ''),
            'pranzo': giorno_data.get('pranzo', ''),
            'cena': giorno_data.get('cena', '')
        })

    piano_completo = {
        'settimana_dal': lunedi.strftime('%Y-%m-%d'),
        'giorni': giorni_con_date
    }

    # Salviamo nel DB (sostituisce eventuale piano esistente per questa settimana)
    elimina_piano_settimana(lunedi.strftime('%Y-%m-%d'))
    for g in giorni_con_date:
        salva_piano_pasti(
            settimana_dal=lunedi.strftime('%Y-%m-%d'),
            data=g['data'],
            giorno=g['giorno'],
            colazione=g['colazione'],
            pranzo=g['pranzo'],
            cena=g['cena']
        )

    return piano_completo


def get_piano_corrente():
    """
    Recupera il piano della settimana corrente dal DB.
    Se non esiste, restituisce None.
    """
    oggi = date.today()
    lunedi = oggi - timedelta(days=oggi.weekday())
    settimana_dal = lunedi.strftime('%Y-%m-%d')
    giorni = get_piano_settimana(settimana_dal)

    if not giorni:
        return None

    return {
        'settimana_dal': settimana_dal,
        'giorni': giorni
    }


def modifica_pasto(data, tipo_pasto, nuovo_valore):
    """
    Aggiorna un singolo pasto nel piano.
    tipo_pasto: 'colazione', 'pranzo' o 'cena'
    """
    aggiorna_pasto(data, tipo_pasto, nuovo_valore)


def _formatta_ingredienti(ingredienti):
    """Formatta la lista ingredienti per il prompt AI."""
    from datetime import datetime
    oggi = date.today()
    righe = []

    for p in ingredienti:
        nome = p['nome_prodotto']
        scadenza = p.get('data_scadenza')
        if scadenza:
            giorni = (datetime.strptime(scadenza, '%Y-%m-%d').date() - oggi).days
            if giorni <= 3:
                righe.append(f"- {nome} (⚠️ scade tra {giorni}gg)")
            else:
                righe.append(f"- {nome}")
        else:
            righe.append(f"- {nome}")

    return '\n'.join(righe)


def _chiedi_piano_a_claude(lista_ingredienti):
    """Invia la richiesta all'API di Claude e restituisce il piano strutturato."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    system_prompt = """Sei un nutrizionista e chef italiano esperto.
Genera un piano pasti settimanale completo (7 giorni) bilanciato e vario,
basandoti sugli ingredienti disponibili in dispensa.

Regole:
- Usa gli ingredienti disponibili, specialmente quelli in scadenza (⚠️)
- Varia i pasti ogni giorno, evita ripetizioni
- Bilancia i nutrienti (carboidrati, proteine, verdure)
- Pasti realistici e tipicamente italiani
- Puoi assumere ingredienti base sempre presenti: sale, olio, aglio, cipolla, uova, pane

Rispondi SOLO con JSON valido, niente testo o ```json:
{
  "giorni": [
    {
      "colazione": "Descrizione colazione lunedì",
      "pranzo": "Descrizione pranzo lunedì",
      "cena": "Descrizione cena lunedì"
    },
    ... (7 elementi, uno per ogni giorno da lunedì a domenica)
  ]
}"""

    user_message = f"""Ho in dispensa:
{lista_ingrediendi}

Crea il piano pasti per questa settimana (7 giorni, da lunedì a domenica)."""

    # Fix typo in variable name
    user_message = user_message.replace('lista_ingrediendi', 'lista_ingredienti')
    user_message = f"""Ho in dispensa:
{lista_ingredienti}

Crea il piano pasti per questa settimana (7 giorni, da lunedì a domenica)."""

    try:
        messaggio = client.messages.create(
            model='claude-opus-4-5',
            max_tokens=2000,
            system=system_prompt,
            messages=[{'role': 'user', 'content': user_message}]
        )

        testo = messaggio.content[0].text
        testo_pulito = re.sub(r'```(?:json)?\s*', '', testo).strip()
        return json.loads(testo_pulito)

    except json.JSONDecodeError:
        return {'errore': 'Risposta AI non valida. Riprova.'}
    except anthropic.AuthenticationError:
        return {'errore': 'Chiave API non valida.'}
    except anthropic.APIConnectionError:
        return {'errore': 'Impossibile connettersi ad Anthropic.'}
    except Exception as e:
        return {'errore': f'Errore: {str(e)}'}