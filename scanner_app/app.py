# =============================================================================
# app.py — Il cuore del backend: server Flask + scheduler notifiche
# =============================================================================
# Avvia con: python app.py

from flask import Flask, request, jsonify, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

from config import HOST, PORT, DEBUG
from spesa import genera_lista_spesa
from database import (
    init_db, inserisci_prodotto, get_tutti_prodotti,
    get_prodotto_by_id, aggiorna_scadenza, elimina_prodotto,
    get_prodotti_fissi, aggiungi_prodotto_fisso, elimina_prodotto_fisso
)
from prodotti import cerca_prodotto
from notifiche import controlla_e_notifica
from ricette import genera_ricette

app = Flask(__name__)

# Inizializziamo il DB subito, così funziona anche con gunicorn
# (non solo quando si avvia con "python app.py")
init_db()


# =============================================================================
# ROUTE: Ricezione scansione dallo scanner (usata dall'app Kivy)
# =============================================================================

@app.route('/scan', methods=['POST'])
def receive_scan():
    """
    Riceve il barcode dallo scanner, cerca il prodotto su Open Food Facts
    e lo salva nel database.
    """
    dati = request.json

    if not dati or not dati.get('barcode'):
        return jsonify({'status': 'error', 'message': 'Barcode mancante'}), 400

    barcode = dati['barcode'].strip()

    print(f"🔍 Ricerca barcode: {barcode}")

    try:
        prodotto = cerca_prodotto(barcode)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Errore ricerca prodotto: {str(e)}'}), 500

    prodotto_id = inserisci_prodotto(
        barcode=barcode,
        nome=prodotto['nome'],
        marca=prodotto['marca'],
        categoria=prodotto['categoria'],
        data_scadenza=None
    )

    print(f"✅ Salvato: {prodotto['nome']} (ID: {prodotto_id})")

    return jsonify({
        'status': 'success',
        'id': prodotto_id,
        'nome': prodotto['nome'],
        'marca': prodotto['marca'],
        'trovato_online': prodotto['trovato']
    }), 201


# =============================================================================
# ROUTE: API REST per gestire i prodotti
# =============================================================================

@app.route('/prodotti', methods=['GET'])
def lista_prodotti():
    """Restituisce tutti i prodotti in formato JSON."""
    prodotti = get_tutti_prodotti()
    return jsonify(prodotti)


@app.route('/prodotti/<int:prodotto_id>', methods=['GET'])
def dettaglio_prodotto(prodotto_id):
    """Restituisce i dettagli di un singolo prodotto."""
    prodotto = get_prodotto_by_id(prodotto_id)
    if not prodotto:
        return jsonify({'error': 'Prodotto non trovato'}), 404
    return jsonify(prodotto)


@app.route('/prodotti/<int:prodotto_id>/scadenza', methods=['PUT'])
def aggiorna_data_scadenza(prodotto_id):
    """
    Aggiorna la data di scadenza di un prodotto.
    Body: {"data_scadenza": "2025-12-31"}
    """
    dati = request.json
    if not dati:
        return jsonify({'error': 'Body JSON mancante'}), 400

    data_scadenza = dati.get('data_scadenza')
    if not data_scadenza:
        return jsonify({'error': 'data_scadenza mancante'}), 400

    aggiorna_scadenza(prodotto_id, data_scadenza)
    return jsonify({'status': 'success', 'message': 'Data aggiornata'})


@app.route('/prodotti/<int:prodotto_id>', methods=['DELETE'])
def cancella_prodotto(prodotto_id):
    """Elimina un prodotto dal database."""
    elimina_prodotto(prodotto_id)
    return jsonify({'status': 'success', 'message': 'Prodotto eliminato'})


# =============================================================================
# ROUTE: Ricette AI
# =============================================================================

@app.route('/ricette', methods=['GET'])
def suggerisci_ricette():
    """
    Chiede all'AI di suggerire ricette con gli ingredienti disponibili.
    FIX: Gestione errori esplicita con status code appropriato.
    """
    print("🤖 Generazione ricette in corso...")
    try:
        ricette = genera_ricette()
    except Exception as e:
        return jsonify({'errore': f'Errore interno: {str(e)}'}), 500

    if 'errore' in ricette:
        return jsonify(ricette), 400

    return jsonify(ricette)


# =============================================================================
# ROUTE: Notifiche manuali (per test)
# =============================================================================

@app.route('/notifiche/test', methods=['POST'])
def test_notifica():
    """Forza il controllo scadenze manualmente (per test)."""
    controlla_e_notifica()
    return jsonify({'status': 'success', 'message': 'Controllo scadenze eseguito'})


# =============================================================================
# ROUTE: Dashboard web
# =============================================================================

@app.route('/', methods=['GET'])
def dashboard():
    """Pagina HTML per visualizzare e gestire la dispensa."""
    prodotti = get_tutti_prodotti()

    html = """
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FrigoSmart</title>
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; }
            h1 { color: #2d7a4f; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #f5f5f5; }
            .scade-oggi { color: #e74c3c; font-weight: bold; }
            .scade-presto { color: #c45c1a; font-weight: bold; }
            .api-links { margin-top: 30px; padding: 15px; background: #f9f9f9; border-radius: 8px; }
            .api-links a { margin-right: 15px; color: #2d7a4f; }
        </style>
    </head>
    <body>
        <h1>🥦 FrigoSmart — Dashboard</h1>
        <p>Prodotti in dispensa: <strong>{{ prodotti|length }}</strong></p>

        <table>
            <tr><th>Nome</th><th>Marca</th><th>Categoria</th><th>Scadenza</th></tr>
            {% for p in prodotti %}
            <tr>
                <td>{{ p.nome_prodotto }}</td>
                <td>{{ p.marca or '—' }}</td>
                <td>{{ p.categoria or '—' }}</td>
                <td class="{{ p.css_scadenza }}">
                    {{ p.data_scadenza or 'Da inserire' }}
                </td>
            </tr>
            {% endfor %}
        </table>

        <div class="api-links">
            <strong>API disponibili:</strong><br><br>
            <a href="/prodotti">GET /prodotti</a>
            <a href="/ricette">GET /ricette</a>
        </div>
    </body>
    </html>
    """

    from datetime import date, datetime
    oggi = date.today()
    for p in prodotti:
        if p.get('data_scadenza'):
            giorni = (datetime.strptime(p['data_scadenza'], '%Y-%m-%d').date() - oggi).days
            if giorni == 0:
                p['css_scadenza'] = 'scade-oggi'
                p['css_badge']    = 'badge-alert'
            elif giorni <= 3:
                p['css_scadenza'] = 'scade-presto'
                p['css_badge']    = 'badge-warn'
            else:
                p['css_scadenza'] = ''
                p['css_badge']    = 'badge-ok'
        else:
            p['css_scadenza'] = ''
            p['css_badge']    = 'badge-grey'

    return render_template_string(open('templates/dashboard.html').read(), prodotti=prodotti)


# =============================================================================
# AVVIO: Scheduler e server
# =============================================================================

if __name__ == '__main__':
    # Avviamo lo scheduler per i controlli automatici delle scadenze
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=controlla_e_notifica,
        trigger='cron',
        hour=9,
        minute=0,
        id='controllo_scadenze'
    )
    scheduler.start()
    print("⏰ Scheduler avviato — controllo scadenze ogni mattina alle 9:00")

    atexit.register(lambda: scheduler.shutdown())

    print(f"🚀 Server avviato su http://{HOST}:{PORT}")
    print(f"📱 Gli scanner devono puntare a: http://<IP-DEL-PC>:{PORT}/scan")
    app.run(host=HOST, port=PORT, debug=DEBUG)


# =============================================================================
# ROUTE: Lista della spesa
# =============================================================================

@app.route('/spesa', methods=['GET'])
def lista_spesa():
    """
    Restituisce la lista della spesa completa:
    - prodotti fissi mancanti dalla dispensa
    - suggerimenti AI
    """
    spesa = genera_lista_spesa()
    return jsonify(spesa)


@app.route('/spesa/fissi', methods=['GET'])
def get_fissi():
    """Restituisce tutti i prodotti fissi configurati."""
    return jsonify(get_prodotti_fissi())


@app.route('/spesa/fissi', methods=['POST'])
def aggiungi_fisso():
    """
    Aggiunge un prodotto alla lista dei fissi.
    Body: {"nome": "Latte", "categoria": "Latticini", "priorita": "alta"}
    """
    dati = request.json
    if not dati or not dati.get('nome'):
        return jsonify({'error': 'nome mancante'}), 400

    ok = aggiungi_prodotto_fisso(
        nome=dati['nome'],
        categoria=dati.get('categoria'),
        priorita=dati.get('priorita', 'normale')
    )
    if ok:
        return jsonify({'status': 'success', 'message': 'Prodotto fisso aggiunto'}), 201
    else:
        return jsonify({'status': 'exists', 'message': 'Prodotto già presente'}), 200


@app.route('/spesa/fissi/<int:prodotto_id>', methods=['DELETE'])
def rimuovi_fisso(prodotto_id):
    """Rimuove un prodotto dalla lista dei fissi."""
    elimina_prodotto_fisso(prodotto_id)
    return jsonify({'status': 'success'})


# =============================================================================
# ROUTE: Storico consumi
# =============================================================================

from storico import segna_come_mangiato, segna_come_sprecato, get_riepilogo_mensile
from database import registra_consumo

@app.route('/storico', methods=['GET'])
def storico_mensile():
    """
    Restituisce il riepilogo del mese corrente (o anno/mese specificati).
    Query params opzionali: ?anno=2026&mese=2
    """
    from datetime import date
    oggi = date.today()
    anno = request.args.get('anno', oggi.year, type=int)
    mese = request.args.get('mese', oggi.month, type=int)
    riepilogo = get_riepilogo_mensile(anno, mese)
    return jsonify(riepilogo)


@app.route('/prodotti/<int:prodotto_id>/mangiato', methods=['POST'])
def segna_mangiato(prodotto_id):
    """
    Segna un prodotto come mangiato:
    - lo registra nello storico come 'consumo'
    - lo elimina dalla dispensa
    """
    prodotto = get_prodotto_by_id(prodotto_id)
    if not prodotto:
        return jsonify({'error': 'Prodotto non trovato'}), 404

    segna_come_mangiato(
        prodotto_id=prodotto_id,
        nome=prodotto['nome_prodotto'],
        categoria=prodotto.get('categoria')
    )
    elimina_prodotto(prodotto_id)
    return jsonify({'status': 'success', 'message': 'Registrato come consumato'})


@app.route('/prodotti/<int:prodotto_id>/sprecato', methods=['POST'])
def segna_sprecato(prodotto_id):
    """
    Segna un prodotto come sprecato (buttato perché scaduto):
    - lo registra nello storico come 'spreco'
    - lo elimina dalla dispensa
    """
    prodotto = get_prodotto_by_id(prodotto_id)
    if not prodotto:
        return jsonify({'error': 'Prodotto non trovato'}), 404

    segna_come_sprecato(
        prodotto_id=prodotto_id,
        nome=prodotto['nome_prodotto'],
        categoria=prodotto.get('categoria')
    )
    elimina_prodotto(prodotto_id)
    return jsonify({'status': 'success', 'message': 'Registrato come sprecato'})


# =============================================================================
# ROUTE: Pianificatore pasti settimanale
# =============================================================================

from pianificatore import genera_piano_settimanale, get_piano_corrente, modifica_pasto

@app.route('/piano', methods=['GET'])
def get_piano():
    """
    Restituisce il piano della settimana corrente.
    Se non esiste ancora, restituisce None.
    """
    piano = get_piano_corrente()
    if not piano:
        return jsonify({'piano': None, 'messaggio': 'Nessun piano per questa settimana. Generane uno!'})
    return jsonify(piano)


@app.route('/piano/genera', methods=['POST'])
def genera_piano():
    """
    Genera un nuovo piano settimanale con l'AI.
    Sovrascrive il piano esistente per questa settimana.
    """
    print("📅 Generazione piano settimanale in corso...")
    try:
        piano = genera_piano_settimanale()
    except Exception as e:
        return jsonify({'errore': f'Errore interno: {str(e)}'}), 500

    if 'errore' in piano:
        return jsonify(piano), 400

    return jsonify(piano)


@app.route('/piano/pasto', methods=['PUT'])
def modifica_singolo_pasto():
    """
    Modifica un singolo pasto nel piano.
    Body: {"data": "2026-02-25", "tipo": "pranzo", "valore": "Pasta al pesto"}
    """
    dati = request.json
    if not dati:
        return jsonify({'error': 'Body JSON mancante'}), 400

    data = dati.get('data')
    tipo = dati.get('tipo')
    valore = dati.get('valore', '')

    if not data or not tipo:
        return jsonify({'error': 'data e tipo sono obbligatori'}), 400

    if tipo not in ('colazione', 'pranzo', 'cena'):
        return jsonify({'error': 'tipo deve essere colazione, pranzo o cena'}), 400

    modifica_pasto(data, tipo, valore)
    return jsonify({'status': 'success', 'message': 'Pasto aggiornato'})


# =============================================================================
# ROUTE: Utenti, famiglie e commenti
# =============================================================================

from utenti import registra_utente, get_profilo_famiglia
from database import (
    aggiungi_commento, get_commenti_prodotto, elimina_commento,
    get_utente_by_nome
)


@app.route('/utenti/registra', methods=['POST'])
def registra():
    """
    Registra un nuovo utente o lo recupera se esiste già.
    Body: {"nome": "Mario", "avatar": "👨‍🍳", "codice_famiglia": "ROSSI-X7K2"}
    codice_famiglia è opzionale — se assente crea una nuova famiglia.
    """
    dati = request.json
    if not dati or not dati.get('nome'):
        return jsonify({'error': 'nome obbligatorio'}), 400

    risultato = registra_utente(
        nome=dati['nome'],
        avatar=dati.get('avatar', '👤'),
        codice_famiglia=dati.get('codice_famiglia')
    )

    if 'errore' in risultato:
        return jsonify(risultato), 404

    return jsonify(risultato), 201


@app.route('/famiglia/<codice>', methods=['GET'])
def profilo_famiglia(codice):
    """Restituisce il profilo della famiglia con la lista dei membri."""
    profilo = get_profilo_famiglia(codice)
    if not profilo:
        return jsonify({'error': 'Famiglia non trovata'}), 404
    return jsonify(profilo)


@app.route('/prodotti/<int:prodotto_id>/commenti', methods=['GET'])
def get_commenti(prodotto_id):
    """Restituisce tutti i commenti di un prodotto."""
    commenti = get_commenti_prodotto(prodotto_id)
    return jsonify(commenti)


@app.route('/prodotti/<int:prodotto_id>/commenti', methods=['POST'])
def aggiungi_commento_route(prodotto_id):
    """
    Aggiunge un commento a un prodotto.
    Body: {"utente_nome": "Mario", "testo": "Quasi finito!"}
    """
    dati = request.json
    if not dati or not dati.get('utente_nome') or not dati.get('testo'):
        return jsonify({'error': 'utente_nome e testo obbligatori'}), 400

    utente = get_utente_by_nome(dati['utente_nome'])
    avatar = utente['avatar'] if utente else '👤'

    commento_id = aggiungi_commento(
        prodotto_id=prodotto_id,
        utente_nome=dati['utente_nome'],
        utente_avatar=avatar,
        testo=dati['testo']
    )
    return jsonify({'status': 'success', 'id': commento_id}), 201


@app.route('/commenti/<int:commento_id>', methods=['DELETE'])
def elimina_commento_route(commento_id):
    """Elimina un commento."""
    elimina_commento(commento_id)
    return jsonify({'status': 'success'})