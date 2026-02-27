# =============================================================================
# app.py — Backend Flask con autenticazione e scanner web
# =============================================================================

from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import os

from config import HOST, PORT, DEBUG, APP_PASSWORD
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
app.secret_key = os.getenv('SECRET_KEY', 'frigosmart-secret-2025-cambia-questo')

# Inizializzazione DB
init_db()


# =============================================================================
# AUTENTICAZIONE — protezione con password semplice
# =============================================================================

def login_required(f):
    """Decoratore: reindirizza al login se non autenticato."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('autenticato'):
            # Per le chiamate API restituisce 401
            if request.path.startswith('/api') or request.is_json:
                return jsonify({'error': 'Non autenticato'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/login', methods=['GET', 'POST'])
def login():
    errore = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == APP_PASSWORD:
            session['autenticato'] = True
            return redirect(url_for('dashboard'))
        else:
            errore = 'Password errata'

    return render_template('login.html', errore=errore)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# =============================================================================
# SCANNER WEB — pagina per il cellulare
# =============================================================================

@app.route('/scanner')
@login_required
def scanner_page():
    """Pagina web con fotocamera per scansionare barcode dal cellulare."""
    return render_template('scanner.html')


# =============================================================================
# ROUTE: Ricezione scansione
# =============================================================================

@app.route('/scan', methods=['POST'])
@login_required
def receive_scan():
    dati = request.json
    if not dati or not dati.get('barcode'):
        return jsonify({'status': 'error', 'message': 'Barcode mancante'}), 400

    barcode = dati['barcode'].strip()
    print(f"🔍 Ricerca barcode: {barcode}")

    try:
        prodotto = cerca_prodotto(barcode)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Errore ricerca: {str(e)}'}), 500

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
# ROUTE: Dashboard
# =============================================================================

@app.route('/')
@login_required
def dashboard():
    prodotti = get_tutti_prodotti()

    from datetime import date, datetime
    oggi = date.today()
    for p in prodotti:
        if p.get('data_scadenza'):
            giorni = (datetime.strptime(p['data_scadenza'], '%Y-%m-%d').date() - oggi).days
            if giorni == 0:
                p['css_scadenza'] = 'scade-oggi'
                p['css_badge'] = 'badge-alert'
            elif giorni <= 3:
                p['css_scadenza'] = 'scade-presto'
                p['css_badge'] = 'badge-warn'
            else:
                p['css_scadenza'] = ''
                p['css_badge'] = 'badge-ok'
        else:
            p['css_scadenza'] = ''
            p['css_badge'] = 'badge-grey'

    return render_template('dashboard.html', prodotti=prodotti)


# =============================================================================
# ROUTE: API prodotti
# =============================================================================

@app.route('/prodotti', methods=['GET'])
@login_required
def lista_prodotti():
    return jsonify(get_tutti_prodotti())


@app.route('/prodotti/<int:prodotto_id>', methods=['GET'])
@login_required
def dettaglio_prodotto(prodotto_id):
    prodotto = get_prodotto_by_id(prodotto_id)
    if not prodotto:
        return jsonify({'error': 'Prodotto non trovato'}), 404
    return jsonify(prodotto)


@app.route('/prodotti/<int:prodotto_id>/scadenza', methods=['PUT'])
@login_required
def aggiorna_data_scadenza(prodotto_id):
    dati = request.json
    if not dati or not dati.get('data_scadenza'):
        return jsonify({'error': 'data_scadenza mancante'}), 400
    aggiorna_scadenza(prodotto_id, dati['data_scadenza'])
    return jsonify({'status': 'success'})


@app.route('/prodotti/<int:prodotto_id>', methods=['DELETE'])
@login_required
def cancella_prodotto(prodotto_id):
    elimina_prodotto(prodotto_id)
    return jsonify({'status': 'success'})


# =============================================================================
# ROUTE: Ricette AI
# =============================================================================

@app.route('/ricette', methods=['GET'])
@login_required
def suggerisci_ricette():
    print("🤖 Generazione ricette in corso...")
    try:
        ricette = genera_ricette()
    except Exception as e:
        return jsonify({'errore': f'Errore interno: {str(e)}'}), 500
    if 'errore' in ricette:
        return jsonify(ricette), 400
    return jsonify(ricette)


# =============================================================================
# ROUTE: Lista spesa
# =============================================================================

@app.route('/spesa', methods=['GET'])
@login_required
def lista_spesa():
    return jsonify(genera_lista_spesa())


@app.route('/spesa/fissi', methods=['GET'])
@login_required
def get_fissi():
    return jsonify(get_prodotti_fissi())


@app.route('/spesa/fissi', methods=['POST'])
@login_required
def aggiungi_fisso():
    dati = request.json
    if not dati or not dati.get('nome'):
        return jsonify({'error': 'nome mancante'}), 400
    ok = aggiungi_prodotto_fisso(
        nome=dati['nome'],
        categoria=dati.get('categoria'),
        priorita=dati.get('priorita', 'normale')
    )
    return jsonify({'status': 'success' if ok else 'exists'}), 201 if ok else 200


@app.route('/spesa/fissi/<int:prodotto_id>', methods=['DELETE'])
@login_required
def rimuovi_fisso(prodotto_id):
    elimina_prodotto_fisso(prodotto_id)
    return jsonify({'status': 'success'})


# =============================================================================
# ROUTE: Storico
# =============================================================================

from storico import segna_come_mangiato, segna_come_sprecato, get_riepilogo_mensile
from database import registra_consumo


@app.route('/storico', methods=['GET'])
@login_required
def storico_mensile():
    from datetime import date
    oggi = date.today()
    anno = request.args.get('anno', oggi.year, type=int)
    mese = request.args.get('mese', oggi.month, type=int)
    return jsonify(get_riepilogo_mensile(anno, mese))


@app.route('/prodotti/<int:prodotto_id>/mangiato', methods=['POST'])
@login_required
def segna_mangiato(prodotto_id):
    prodotto = get_prodotto_by_id(prodotto_id)
    if not prodotto:
        return jsonify({'error': 'Prodotto non trovato'}), 404
    segna_come_mangiato(prodotto_id=prodotto_id, nome=prodotto['nome_prodotto'], categoria=prodotto.get('categoria'))
    elimina_prodotto(prodotto_id)
    return jsonify({'status': 'success'})


@app.route('/prodotti/<int:prodotto_id>/sprecato', methods=['POST'])
@login_required
def segna_sprecato(prodotto_id):
    prodotto = get_prodotto_by_id(prodotto_id)
    if not prodotto:
        return jsonify({'error': 'Prodotto non trovato'}), 404
    segna_come_sprecato(prodotto_id=prodotto_id, nome=prodotto['nome_prodotto'], categoria=prodotto.get('categoria'))
    elimina_prodotto(prodotto_id)
    return jsonify({'status': 'success'})


# =============================================================================
# ROUTE: Piano pasti
# =============================================================================

from pianificatore import genera_piano_settimanale, get_piano_corrente, modifica_pasto


@app.route('/piano', methods=['GET'])
@login_required
def get_piano():
    piano = get_piano_corrente()
    if not piano:
        return jsonify({'piano': None, 'messaggio': 'Nessun piano. Generane uno!'})
    return jsonify(piano)


@app.route('/piano/genera', methods=['POST'])
@login_required
def genera_piano():
    print("📅 Generazione piano settimanale...")
    try:
        piano = genera_piano_settimanale()
    except Exception as e:
        return jsonify({'errore': f'Errore: {str(e)}'}), 500
    if 'errore' in piano:
        return jsonify(piano), 400
    return jsonify(piano)


@app.route('/piano/pasto', methods=['PUT'])
@login_required
def modifica_singolo_pasto():
    dati = request.json
    if not dati:
        return jsonify({'error': 'Body JSON mancante'}), 400
    data = dati.get('data')
    tipo = dati.get('tipo')
    valore = dati.get('valore', '')
    if not data or not tipo:
        return jsonify({'error': 'data e tipo obbligatori'}), 400
    if tipo not in ('colazione', 'pranzo', 'cena'):
        return jsonify({'error': 'tipo deve essere colazione, pranzo o cena'}), 400
    modifica_pasto(data, tipo, valore)
    return jsonify({'status': 'success'})


# =============================================================================
# ROUTE: Utenti e famiglie
# =============================================================================

from utenti import registra_utente, get_profilo_famiglia
from database import aggiungi_commento, get_commenti_prodotto, elimina_commento, get_utente_by_nome


@app.route('/utenti/registra', methods=['POST'])
@login_required
def registra():
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
@login_required
def profilo_famiglia(codice):
    profilo = get_profilo_famiglia(codice)
    if not profilo:
        return jsonify({'error': 'Famiglia non trovata'}), 404
    return jsonify(profilo)


@app.route('/prodotti/<int:prodotto_id>/commenti', methods=['GET'])
@login_required
def get_commenti(prodotto_id):
    return jsonify(get_commenti_prodotto(prodotto_id))


@app.route('/prodotti/<int:prodotto_id>/commenti', methods=['POST'])
@login_required
def aggiungi_commento_route(prodotto_id):
    dati = request.json
    if not dati or not dati.get('utente_nome') or not dati.get('testo'):
        return jsonify({'error': 'utente_nome e testo obbligatori'}), 400
    utente = get_utente_by_nome(dati['utente_nome'])
    avatar = utente['avatar'] if utente else '👤'
    commento_id = aggiungi_commento(prodotto_id, dati['utente_nome'], avatar, dati['testo'])
    return jsonify({'status': 'success', 'id': commento_id}), 201


@app.route('/commenti/<int:commento_id>', methods=['DELETE'])
@login_required
def elimina_commento_route(commento_id):
    elimina_commento(commento_id)
    return jsonify({'status': 'success'})


# =============================================================================
# ROUTE: Notifiche test
# =============================================================================

@app.route('/notifiche/test', methods=['POST'])
@login_required
def test_notifica():
    controlla_e_notifica()
    return jsonify({'status': 'success'})


# =============================================================================
# AVVIO
# =============================================================================

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=controlla_e_notifica, trigger='cron', hour=9, minute=0)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    print(f"🚀 Server su http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=DEBUG)
