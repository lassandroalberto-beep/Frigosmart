# =============================================================================
# utenti.py — Gestione profili utente e famiglie condivise
# =============================================================================
# Ogni utente ha un nome, un avatar emoji e appartiene a una "famiglia".
# La famiglia è identificata da un codice univoco che tutti i membri inseriscono
# per condividere la stessa dispensa.
#
# Struttura:
# - Utente: id, nome, avatar, codice_famiglia, data_creazione
# - Famiglia: codice univoco (es. "ROSSI-2026"), dispensa condivisa da tutti i membri

import secrets
import string
from database import (
    crea_utente, get_utente, get_utente_by_nome,
    crea_famiglia, get_famiglia, get_membri_famiglia,
    aggiorna_famiglia_utente
)


AVATAR_DEFAULT = ['👨', '👩', '👦', '👧', '👴', '👵', '🧑', '👨‍🍳', '👩‍🍳']


def registra_utente(nome, avatar=None, codice_famiglia=None):
    """
    Registra un nuovo utente.
    Se codice_famiglia è fornito, unisce l'utente a quella famiglia.
    Se non è fornito, crea una nuova famiglia e ne diventa admin.

    Restituisce:
    {
        'utente': {...},
        'famiglia': {'codice': 'ROSSI-2026', 'nome': 'Famiglia Rossi'},
        'nuovo': True/False
    }
    """
    # Controlla se l'utente esiste già
    esistente = get_utente_by_nome(nome)
    if esistente:
        return {
            'utente': esistente,
            'famiglia': get_famiglia(esistente['codice_famiglia']),
            'nuovo': False
        }

    avatar = avatar or AVATAR_DEFAULT[0]

    if codice_famiglia:
        # Unisciti a famiglia esistente
        famiglia = get_famiglia(codice_famiglia)
        if not famiglia:
            return {'errore': f'Codice famiglia "{codice_famiglia}" non trovato.'}
    else:
        # Crea nuova famiglia
        codice_famiglia = _genera_codice_famiglia(nome)
        crea_famiglia(codice_famiglia, f'Famiglia {nome}')
        famiglia = get_famiglia(codice_famiglia)

    utente_id = crea_utente(nome, avatar, codice_famiglia)
    utente = get_utente(utente_id)

    return {
        'utente': utente,
        'famiglia': famiglia,
        'nuovo': True
    }


def get_profilo_famiglia(codice_famiglia):
    """
    Restituisce il profilo completo della famiglia:
    codice, nome, lista membri con avatar.
    """
    famiglia = get_famiglia(codice_famiglia)
    if not famiglia:
        return None

    membri = get_membri_famiglia(codice_famiglia)
    return {
        'codice': famiglia['codice'],
        'nome': famiglia['nome'],
        'membri': membri
    }


def _genera_codice_famiglia(nome_admin):
    """
    Genera un codice famiglia leggibile e unico.
    Esempio: "MARIO-X7K2"
    """
    prefisso = nome_admin.upper()[:6].replace(' ', '')
    suffisso = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    return f'{prefisso}-{suffisso}'