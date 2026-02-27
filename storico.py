Copia

# =============================================================================
# storico.py — Storico consumi, sprechi e statistiche mensili
# =============================================================================

from database import (
    registra_consumo,
    get_storico_mensile, get_statistiche_mensili
)


def segna_come_mangiato(prodotto_id, nome, categoria=None):
    """
    Registra che un prodotto è stato consumato.
    Chiamata quando l'utente preme 'Mangiato' nella dashboard o nell'app.
    """
    registra_consumo(prodotto_id, nome, categoria, tipo='consumo')


def segna_come_sprecato(prodotto_id, nome, categoria=None):
    """
    Registra che un prodotto è stato buttato perché scaduto.
    Chiamata dallo scheduler quando trova prodotti scaduti non ancora rimossi.
    """
    registra_consumo(prodotto_id, nome, categoria, tipo='spreco')


def get_riepilogo_mensile(anno=None, mese=None):
    """
    Restituisce il riepilogo completo del mese specificato.
    Se anno/mese non specificati, usa il mese corrente.

    Restituisce:
    {
        'anno': 2026, 'mese': 2,
        'totale_consumati': 24,
        'totale_sprecati': 3,
        'percentuale_spreco': 11.1,
        'per_categoria': {
            'Latticini': {'consumati': 5, 'sprecati': 1},
            ...
        },
        'ultimi_movimenti': [...]
    }
    """
    from datetime import date
    oggi = date.today()
    anno = anno or oggi.year
    mese = mese or oggi.month

    movimenti = get_storico_mensile(anno, mese)
    stats = get_statistiche_mensili(anno, mese)

    consumati = stats.get('consumati', 0)
    sprecati = stats.get('sprecati', 0)
    totale = consumati + sprecati
    perc_spreco = round((sprecati / totale * 100), 1) if totale > 0 else 0.0

    return {
        'anno': anno,
        'mese': mese,
        'totale_consumati': consumati,
        'totale_sprecati': sprecati,
        'percentuale_spreco': perc_spreco,
        'per_categoria': stats.get('per_categoria', {}),
        'ultimi_movimenti': movimenti[:20] } #
