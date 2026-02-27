# =============================================================================
# database.py — Tutto ciò che riguarda il database SQLite
# =============================================================================

import sqlite3
from datetime import datetime
from config import DB_NAME


def get_connection():
    """
    Crea e restituisce una connessione al database.
    row_factory = sqlite3.Row permette di accedere ai campi per nome (riga['nome']).
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Crea le tabelle se non esistono ancora.
    Chiamata una sola volta all'avvio dell'app.
    """
    with get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS inventario (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode           TEXT NOT NULL,
                nome_prodotto     TEXT NOT NULL,
                marca             TEXT,
                categoria         TEXT,
                data_inserimento  TEXT NOT NULL,
                data_scadenza     TEXT,
                quantita          INTEGER DEFAULT 1
            )
        ''')
        # Indice su data_scadenza per velocizzare le query di scadenza
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_scadenza 
            ON inventario(data_scadenza)
        ''')
        # Nuova tabella: prodotti che vuoi avere SEMPRE in casa
        conn.execute('''
            CREATE TABLE IF NOT EXISTS prodotti_fissi (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                nome      TEXT NOT NULL UNIQUE,
                categoria TEXT,
                priorita  TEXT DEFAULT 'normale'
            )
        ''')
        _init_storico(conn)
        _init_pianificatore(conn)
        _init_condivisione(conn)
        conn.commit()
    print("✅ Database inizializzato correttamente.")


def inserisci_prodotto(barcode, nome, marca, categoria, data_scadenza=None, quantita=1):
    """Inserisce un nuovo prodotto nel database. Restituisce l'ID creato."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with get_connection() as conn:
        cursor = conn.execute('''
            INSERT INTO inventario 
                (barcode, nome_prodotto, marca, categoria, data_inserimento, data_scadenza, quantita)
            VALUES 
                (?, ?, ?, ?, ?, ?, ?)
        ''', (barcode, nome, marca, categoria, now, data_scadenza, quantita))
        conn.commit()
        return cursor.lastrowid


def get_tutti_prodotti():
    """
    Restituisce tutti i prodotti ordinati per data di scadenza.
    FIX: Rimosso 'NULLS LAST' (non supportato da SQLite < 3.30).
         Usiamo CASE WHEN per mettere i NULL in fondo manualmente.
    """
    with get_connection() as conn:
        rows = conn.execute('''
            SELECT * FROM inventario
            ORDER BY 
                CASE WHEN data_scadenza IS NULL THEN 1 ELSE 0 END,
                data_scadenza ASC
        ''').fetchall()
        return [dict(row) for row in rows]


def get_prodotto_by_id(prodotto_id):
    """Restituisce un singolo prodotto dato il suo ID."""
    with get_connection() as conn:
        row = conn.execute(
            'SELECT * FROM inventario WHERE id = ?', (prodotto_id,)
        ).fetchone()
        return dict(row) if row else None


def aggiorna_scadenza(prodotto_id, data_scadenza):
    """Aggiorna la data di scadenza di un prodotto."""
    with get_connection() as conn:
        conn.execute(
            'UPDATE inventario SET data_scadenza = ? WHERE id = ?',
            (data_scadenza, prodotto_id)
        )
        conn.commit()


def elimina_prodotto(prodotto_id):
    """Rimuove un prodotto (es. perché consumato o scaduto)."""
    with get_connection() as conn:
        conn.execute('DELETE FROM inventario WHERE id = ?', (prodotto_id,))
        conn.commit()


def get_prodotti_in_scadenza(giorni=3):
    """
    Restituisce i prodotti che scadono entro X giorni da oggi.
    FIX: Rimosso 'NULLS LAST', compatibile con tutte le versioni SQLite.
    """
    with get_connection() as conn:
        rows = conn.execute('''
            SELECT * FROM inventario
            WHERE data_scadenza IS NOT NULL
              AND data_scadenza <= DATE('now', '+' || ? || ' days')
              AND data_scadenza >= DATE('now')
            ORDER BY data_scadenza ASC
        ''', (giorni,)).fetchall()
        return [dict(row) for row in rows]


def get_tutti_ingredienti():
    """
    Restituisce nome e scadenza dei prodotti non scaduti (per l'AI ricette).
    FIX: Rimosso 'NULLS LAST', compatibile con tutte le versioni SQLite.
    """
    with get_connection() as conn:
        rows = conn.execute('''
            SELECT nome_prodotto, data_scadenza FROM inventario
            WHERE data_scadenza IS NULL 
               OR data_scadenza >= DATE('now')
            ORDER BY 
                CASE WHEN data_scadenza IS NULL THEN 1 ELSE 0 END,
                data_scadenza ASC
        ''').fetchall()
        return [dict(row) for row in rows]


# =============================================================================
# PRODOTTI FISSI — Prodotti che vuoi avere sempre in casa
# =============================================================================

def get_prodotti_fissi():
    """Restituisce tutti i prodotti fissi definiti dall'utente."""
    with get_connection() as conn:
        rows = conn.execute('''
            SELECT * FROM prodotti_fissi
            ORDER BY priorita DESC, nome ASC
        ''').fetchall()
        return [dict(row) for row in rows]


def aggiungi_prodotto_fisso(nome, categoria=None, priorita='normale'):
    """
    Aggiunge un prodotto alla lista dei 'sempre in casa'.
    Se esiste già (UNIQUE su nome), ignora silenziosamente.
    """
    with get_connection() as conn:
        try:
            conn.execute(
                'INSERT INTO prodotti_fissi (nome, categoria, priorita) VALUES (?, ?, ?)',
                (nome, categoria, priorita)
            )
            conn.commit()
            return True
        except Exception:
            return False  # Già esistente


def elimina_prodotto_fisso(prodotto_id):
    """Rimuove un prodotto dalla lista dei fissi."""
    with get_connection() as conn:
        conn.execute('DELETE FROM prodotti_fissi WHERE id = ?', (prodotto_id,))
        conn.commit()


# =============================================================================
# STORICO CONSUMI — Tracciamento di cosa viene mangiato o sprecato
# =============================================================================

def _init_storico(conn):
    """Crea la tabella storico se non esiste (chiamata da init_db)."""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS storico_consumi (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            prodotto_id   INTEGER,
            nome_prodotto TEXT NOT NULL,
            categoria     TEXT,
            tipo          TEXT NOT NULL CHECK(tipo IN ('consumo', 'spreco')),
            data          TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_storico_data
        ON storico_consumi(data)
    ''')


def registra_consumo(prodotto_id, nome, categoria=None, tipo='consumo'):
    """
    Salva nello storico un consumo o uno spreco.
    tipo = 'consumo' → mangiato
    tipo = 'spreco'  → buttato perché scaduto
    """
    from datetime import datetime
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_connection() as conn:
        conn.execute('''
            INSERT INTO storico_consumi (prodotto_id, nome_prodotto, categoria, tipo, data)
            VALUES (?, ?, ?, ?, ?)
        ''', (prodotto_id, nome, categoria, tipo, now))
        conn.commit()


def get_storico_mensile(anno, mese):
    """Restituisce tutti i movimenti del mese, ordinati dal più recente."""
    mese_str = f'{anno}-{mese:02d}'
    with get_connection() as conn:
        rows = conn.execute('''
            SELECT * FROM storico_consumi
            WHERE strftime('%Y-%m', data) = ?
            ORDER BY data DESC
        ''', (mese_str,)).fetchall()
        return [dict(row) for row in rows]


def get_statistiche_mensili(anno, mese):
    """
    Calcola statistiche aggregate per il mese:
    - totale consumati e sprecati
    - suddivisione per categoria
    """
    mese_str = f'{anno}-{mese:02d}'
    with get_connection() as conn:
        # Totali
        rows_totali = conn.execute('''
            SELECT tipo, COUNT(*) as totale
            FROM storico_consumi
            WHERE strftime('%Y-%m', data) = ?
            GROUP BY tipo
        ''', (mese_str,)).fetchall()

        consumati = 0
        sprecati = 0
        for r in rows_totali:
            if r['tipo'] == 'consumo':
                consumati = r['totale']
            elif r['tipo'] == 'spreco':
                sprecati = r['totale']

        # Per categoria
        rows_cat = conn.execute('''
            SELECT categoria, tipo, COUNT(*) as totale
            FROM storico_consumi
            WHERE strftime('%Y-%m', data) = ?
              AND categoria IS NOT NULL
            GROUP BY categoria, tipo
        ''', (mese_str,)).fetchall()

        per_categoria = {}
        for r in rows_cat:
            cat = r['categoria']
            if cat not in per_categoria:
                per_categoria[cat] = {'consumati': 0, 'sprecati': 0}
            if r['tipo'] == 'consumo':
                per_categoria[cat]['consumati'] = r['totale']
            else:
                per_categoria[cat]['sprecati'] = r['totale']

        return {
            'consumati': consumati,
            'sprecati': sprecati,
            'per_categoria': per_categoria
        }


# =============================================================================
# PIANO PASTI — Pianificatore settimanale
# =============================================================================

def _init_pianificatore(conn):
    """Crea la tabella piano_pasti (chiamata da init_db)."""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS piano_pasti (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            settimana_dal TEXT NOT NULL,
            data          TEXT NOT NULL,
            giorno        TEXT NOT NULL,
            colazione     TEXT,
            pranzo        TEXT,
            cena          TEXT,
            UNIQUE(settimana_dal, data)
        )
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_piano_settimana
        ON piano_pasti(settimana_dal)
    ''')


def salva_piano_pasti(settimana_dal, data, giorno, colazione, pranzo, cena):
    """Inserisce un giorno del piano pasti nel DB."""
    with get_connection() as conn:
        conn.execute('''
            INSERT OR REPLACE INTO piano_pasti
                (settimana_dal, data, giorno, colazione, pranzo, cena)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (settimana_dal, data, giorno, colazione, pranzo, cena))
        conn.commit()


def get_piano_settimana(settimana_dal):
    """Restituisce tutti i giorni del piano per la settimana specificata."""
    with get_connection() as conn:
        rows = conn.execute('''
            SELECT * FROM piano_pasti
            WHERE settimana_dal = ?
            ORDER BY data ASC
        ''', (settimana_dal,)).fetchall()
        return [dict(row) for row in rows]


def aggiorna_pasto(data, tipo_pasto, valore):
    """
    Aggiorna un singolo pasto (colazione/pranzo/cena) per una data specifica.
    tipo_pasto deve essere 'colazione', 'pranzo' o 'cena'.
    """
    campi_validi = {'colazione', 'pranzo', 'cena'}
    if tipo_pasto not in campi_validi:
        return False
    with get_connection() as conn:
        conn.execute(
            f'UPDATE piano_pasti SET {tipo_pasto} = ? WHERE data = ?',
            (valore, data)
        )
        conn.commit()
    return True


def elimina_piano_settimana(settimana_dal):
    """Elimina il piano della settimana specificata (per rigenerarlo)."""
    with get_connection() as conn:
        conn.execute('DELETE FROM piano_pasti WHERE settimana_dal = ?', (settimana_dal,))
        conn.commit()


# =============================================================================
# UTENTI E FAMIGLIE — Condivisione dispensa
# =============================================================================

def _init_condivisione(conn):
    """Crea le tabelle per utenti, famiglie e commenti (chiamata da init_db)."""

    # Famiglie
    conn.execute('''
        CREATE TABLE IF NOT EXISTS famiglie (
            codice          TEXT PRIMARY KEY,
            nome            TEXT NOT NULL,
            data_creazione  TEXT NOT NULL
        )
    ''')

    # Utenti
    conn.execute('''
        CREATE TABLE IF NOT EXISTS utenti (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT NOT NULL UNIQUE,
            avatar          TEXT DEFAULT '👤',
            codice_famiglia TEXT,
            data_creazione  TEXT NOT NULL,
            FOREIGN KEY (codice_famiglia) REFERENCES famiglie(codice)
        )
    ''')

    # Aggiunge colonna "aggiunto_da" all'inventario (se non esiste già)
    try:
        conn.execute('ALTER TABLE inventario ADD COLUMN aggiunto_da TEXT')
    except Exception:
        pass  # Colonna già esistente

    # Commenti sui prodotti
    conn.execute('''
        CREATE TABLE IF NOT EXISTS commenti (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            prodotto_id     INTEGER NOT NULL,
            utente_nome     TEXT NOT NULL,
            utente_avatar   TEXT DEFAULT '👤',
            testo           TEXT NOT NULL,
            data            TEXT NOT NULL,
            FOREIGN KEY (prodotto_id) REFERENCES inventario(id)
        )
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_commenti_prodotto
        ON commenti(prodotto_id)
    ''')


# --- FAMIGLIE ---

def crea_famiglia(codice, nome):
    from datetime import datetime
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_connection() as conn:
        conn.execute(
            'INSERT OR IGNORE INTO famiglie (codice, nome, data_creazione) VALUES (?, ?, ?)',
            (codice, nome, now)
        )
        conn.commit()


def get_famiglia(codice):
    with get_connection() as conn:
        row = conn.execute(
            'SELECT * FROM famiglie WHERE codice = ?', (codice,)
        ).fetchone()
        return dict(row) if row else None


def get_membri_famiglia(codice_famiglia):
    with get_connection() as conn:
        rows = conn.execute(
            'SELECT id, nome, avatar, data_creazione FROM utenti WHERE codice_famiglia = ? ORDER BY data_creazione ASC',
            (codice_famiglia,)
        ).fetchall()
        return [dict(row) for row in rows]


# --- UTENTI ---

def crea_utente(nome, avatar, codice_famiglia):
    from datetime import datetime
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_connection() as conn:
        cursor = conn.execute(
            'INSERT INTO utenti (nome, avatar, codice_famiglia, data_creazione) VALUES (?, ?, ?, ?)',
            (nome, avatar, codice_famiglia, now)
        )
        conn.commit()
        return cursor.lastrowid


def get_utente(utente_id):
    with get_connection() as conn:
        row = conn.execute('SELECT * FROM utenti WHERE id = ?', (utente_id,)).fetchone()
        return dict(row) if row else None


def get_utente_by_nome(nome):
    with get_connection() as conn:
        row = conn.execute('SELECT * FROM utenti WHERE nome = ?', (nome,)).fetchone()
        return dict(row) if row else None


def aggiorna_famiglia_utente(utente_id, codice_famiglia):
    with get_connection() as conn:
        conn.execute(
            'UPDATE utenti SET codice_famiglia = ? WHERE id = ?',
            (codice_famiglia, utente_id)
        )
        conn.commit()


# --- COMMENTI ---

def aggiungi_commento(prodotto_id, utente_nome, utente_avatar, testo):
    from datetime import datetime
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_connection() as conn:
        cursor = conn.execute('''
            INSERT INTO commenti (prodotto_id, utente_nome, utente_avatar, testo, data)
            VALUES (?, ?, ?, ?, ?)
        ''', (prodotto_id, utente_nome, utente_avatar, testo, now))
        conn.commit()
        return cursor.lastrowid


def get_commenti_prodotto(prodotto_id):
    with get_connection() as conn:
        rows = conn.execute('''
            SELECT * FROM commenti
            WHERE prodotto_id = ?
            ORDER BY data ASC
        ''', (prodotto_id,)).fetchall()
        return [dict(row) for row in rows]


def elimina_commento(commento_id):
    with get_connection() as conn:
        conn.execute('DELETE FROM commenti WHERE id = ?', (commento_id,))
        conn.commit()