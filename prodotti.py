# =============================================================================
# prodotti.py — Integrazione con Open Food Facts
# =============================================================================
# Open Food Facts è un database collaborativo di prodotti alimentari,
# completamente gratuito e senza bisogno di registrazione.
# Contiene milioni di prodotti con barcode, nomi, ingredienti, nutrizionali, ecc.
# Documentazione: https://world.openfoodfacts.org/data

import requests
from config import OPENFOODFACTS_URL, OPENFOODFACTS_TIMEOUT


def cerca_prodotto(barcode):
    """
    Cerca un prodotto su Open Food Facts tramite il suo barcode.
    
    Restituisce un dizionario con i dati del prodotto, oppure None se
    il prodotto non è stato trovato o si è verificato un errore di rete.
    
    Esempio di risposta:
    {
        'nome': 'Latte fresco intero',
        'marca': 'Parmalat',
        'categoria': 'Latticini',
        'trovato': True
    }
    """
    url = OPENFOODFACTS_URL.format(barcode=barcode)
    
    try:
        # timeout evita che l'app si blocchi se il server è lento
        risposta = requests.get(url, timeout=OPENFOODFACTS_TIMEOUT)
        
        # Se la richiesta HTTP non è andata a buon fine (es. 404, 500), lancia un'eccezione
        risposta.raise_for_status()
        
        dati = risposta.json()
        
        # status = 1 significa che il prodotto è stato trovato nel database
        if dati.get('status') == 1:
            prodotto = dati['product']
            return _estrai_campi(prodotto, barcode)
        else:
            print(f"⚠️  Barcode {barcode} non trovato su Open Food Facts.")
            return _prodotto_sconosciuto(barcode)

    except requests.exceptions.Timeout:
        print(f"⏱️  Timeout: Open Food Facts ha impiegato troppo. Barcode: {barcode}")
        return _prodotto_sconosciuto(barcode)

    except requests.exceptions.ConnectionError:
        print("🌐 Errore di connessione: controlla la rete.")
        return _prodotto_sconosciuto(barcode)

    except Exception as e:
        print(f"❌ Errore inaspettato nella ricerca prodotto: {e}")
        return _prodotto_sconosciuto(barcode)


def _estrai_campi(prodotto, barcode):
    """
    Estrae solo i campi che ci interessano dalla risposta grezza dell'API.
    
    Le funzioni che iniziano con _ (underscore) sono per convenzione "private":
    sono pensate per essere usate solo all'interno di questo file, non dall'esterno.
    
    .get('campo', 'Valore default') è un modo sicuro per leggere un dizionario:
    se il campo non esiste, restituisce il valore di default invece di crashare.
    """
    
    # Il nome del prodotto può trovarsi in campi diversi, proviamo in ordine
    nome = (
        prodotto.get('product_name_it')    # Prima proviamo il nome italiano
        or prodotto.get('product_name')    # Poi quello generico
        or prodotto.get('generic_name')    # Poi il nome generico
        or f"Prodotto {barcode}"           # Fallback: usiamo il barcode
    )
    
    # La marca (brand)
    marca = prodotto.get('brands', '').split(',')[0].strip()  # Prende solo il primo brand
    
    # La categoria — puliamo la stringa che spesso contiene prefissi come "en:"
    categoria_raw = prodotto.get('categories', '')
    categoria = _pulisci_categoria(categoria_raw)
    
    return {
        'nome': nome,
        'marca': marca if marca else None,
        'categoria': categoria if categoria else None,
        'trovato': True
    }


def _pulisci_categoria(categoria_raw):
    """
    Open Food Facts restituisce categorie nel formato:
    "en:beverages, it:bevande, fr:boissons"
    
    Vogliamo solo il termine italiano o, se non c'è, quello inglese.
    """
    if not categoria_raw:
        return None
    
    parti = [p.strip() for p in categoria_raw.split(',')]
    
    # Cerca prima un termine italiano
    for parte in parti:
        if parte.startswith('it:'):
            return parte.replace('it:', '').capitalize()
    
    # Altrimenti usa il primo termine, rimuovendo i prefissi lingua
    if parti:
        primo = parti[0]
        if ':' in primo:
            primo = primo.split(':', 1)[1]
        return primo.capitalize()
    
    return None


def _prodotto_sconosciuto(barcode):
    """
    Quando non troviamo il prodotto, restituiamo comunque qualcosa
    di sensato invece di None. L'utente potrà modificare il nome manualmente.
    """
    return {
        'nome': f'Prodotto sconosciuto ({barcode})',
        'marca': None,
        'categoria': None,
        'trovato': False
    }
