# =============================================================================
# spesa.py — Lista della spesa automatica
# =============================================================================
# Combina due fonti:
# 1. Prodotti FISSI: quelli che vuoi avere sempre in casa (es. latte, uova)
#    → il sistema avvisa quando non ne hai più in dispensa
# 2. Suggerimenti AI: Claude analizza la dispensa e suggerisce cosa comprare
#    in base alle ricette più comuni e a cosa sta per finire

import json
import re
import anthropic
from config import ANTHROPIC_API_KEY
from database import get_tutti_prodotti, get_prodotti_fissi


def genera_lista_spesa():
    """
    Funzione principale: genera la lista della spesa completa.

    Restituisce:
    {
        'mancanti': [                        # Prodotti fissi non presenti in dispensa
            {'nome': 'Latte', 'priorita': 'alta'},
            ...
        ],
        'suggeriti_ai': [                    # Suggerimenti dell'AI
            {'nome': 'Passata di pomodoro', 'motivo': 'Utile per molte ricette'},
            ...
        ]
    }
    """
    dispensa = get_tutti_prodotti()
    nomi_in_dispensa = {p['nome_prodotto'].lower() for p in dispensa}

    # 1. Prodotti fissi mancanti
    fissi = get_prodotti_fissi()
    mancanti = []
    for f in fissi:
        nome = f['nome'].lower()
        # Controllo semplice: se il nome del prodotto fisso non è in dispensa
        if not any(nome in d for d in nomi_in_dispensa):
            mancanti.append({
                'nome': f['nome'],
                'categoria': f.get('categoria', ''),
                'priorita': f.get('priorita', 'normale')
            })

    # 2. Suggerimenti AI (solo se abbiamo la chiave API)
    suggeriti_ai = []
    if ANTHROPIC_API_KEY and dispensa:
        suggeriti_ai = _chiedi_suggerimenti_ai(dispensa)

    return {
        'mancanti': mancanti,
        'suggeriti_ai': suggeriti_ai
    }


def _chiedi_suggerimenti_ai(dispensa):
    """
    Chiede a Claude cosa sarebbe utile comprare in base a cosa c'è in dispensa.
    Suggerisce ingredienti che completerebbero bene quello che già hai.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    lista = '\n'.join(f"- {p['nome_prodotto']}" for p in dispensa)

    system_prompt = """Sei un assistente per la spesa di una famiglia italiana.
Analizza cosa è presente in dispensa e suggerisci massimo 6 prodotti da acquistare
che completerebbero bene gli ingredienti già presenti, permettendo di cucinare
pasti completi ed equilibrati.

Rispondi SOLO con JSON valido, niente testo prima o dopo, niente ```json:
{
  "suggerimenti": [
    {"nome": "Nome prodotto", "motivo": "Breve motivo (max 8 parole)"},
    ...
  ]
}"""

    user_message = f"""Ho in dispensa:
{lista}

Cosa mi consigli di comprare per completare la dispensa?"""

    try:
        messaggio = client.messages.create(
            model='claude-opus-4-5',
            max_tokens=600,
            system=system_prompt,
            messages=[{'role': 'user', 'content': user_message}]
        )
        testo = messaggio.content[0].text
        testo_pulito = re.sub(r'```(?:json)?\s*', '', testo).strip()
        dati = json.loads(testo_pulito)
        return dati.get('suggerimenti', [])

    except Exception as e:
        print(f"❌ Errore AI lista spesa: {e}")
        return []