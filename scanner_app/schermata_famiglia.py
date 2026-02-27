# =============================================================================
# schermata_famiglia.py — Schermata profilo, famiglia e commenti prodotti
# =============================================================================
# Permette di:
# - Registrarsi con nome e avatar emoji
# - Creare una famiglia o unirsi a una esistente con il codice
# - Vedere i membri della famiglia
# - Commentare i prodotti in dispensa

import json
import os

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.network.urlrequest import UrlRequest
from kivy.metrics import dp
from kivy.storage.jsonstore import JsonStore

SERVER_URL = os.getenv('SERVER_URL', 'http://127.0.0.1:5000')

VERDE  = (0.176, 0.478, 0.310, 1)
ARANCIO = (0.953, 0.612, 0.071, 1)
BLU    = (0.2, 0.4, 0.8, 1)
VIOLA  = (0.5, 0.2, 0.7, 1)
GRIGIO = (0.5, 0.5, 0.5, 1)
ROSSO  = (0.906, 0.298, 0.235, 1)

AVATAR_SCELTA = ['👨', '👩', '👦', '👧', '👴', '👵', '🧑', '👨‍🍳', '👩‍🍳', '🧑‍💻']

# Salviamo il profilo utente localmente sul dispositivo
store = JsonStore('frigosmart_profilo.json')


class SchermataFamiglia(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.utente_corrente = None
        self.famiglia_corrente = None
        self.avatar_selezionato = '👤'
        self.build_ui()

    def build_ui(self):
        self.layout_principale = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
        self.add_widget(self.layout_principale)

    def on_enter(self):
        """Controlla se l'utente ha già un profilo salvato."""
        self.layout_principale.clear_widgets()
        if store.exists('utente'):
            dati = store.get('utente')
            self.utente_corrente = dati
            self.mostra_profilo()
        else:
            self.mostra_registrazione()

    # =========================================================================
    # REGISTRAZIONE
    # =========================================================================

    def mostra_registrazione(self):
        """Schermata di registrazione primo accesso."""
        layout = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(10))

        # Header
        header = BoxLayout(size_hint=(1, None), height=dp(50))
        header.add_widget(Label(
            text='👋 Benvenuto in FrigoSmart!',
            font_size=dp(18), bold=True, color=VERDE
        ))
        btn_torna = Button(
            text='🔙', size_hint=(None, 1), width=dp(44),
            background_color=GRIGIO,
            on_press=lambda x: self.manager.vai_a_scanner()
        )
        header.add_widget(btn_torna)
        layout.add_widget(header)

        layout.add_widget(Label(
            text='Crea il tuo profilo per condividere\nla dispensa con la tua famiglia',
            font_size=dp(13), color=GRIGIO,
            size_hint=(1, None), height=dp(44),
            halign='center', text_size=(dp(300), None)
        ))

        # Scelta avatar
        layout.add_widget(Label(
            text='Scegli il tuo avatar:',
            size_hint=(1, None), height=dp(28),
            font_size=dp(13), color=(0.3, 0.3, 0.3, 1)
        ))
        self.lbl_avatar = Label(
            text=self.avatar_selezionato,
            font_size=dp(40), size_hint=(1, None), height=dp(56)
        )
        layout.add_widget(self.lbl_avatar)

        griglia_avatar = GridLayout(
            cols=5, size_hint=(1, None), height=dp(60), spacing=dp(6)
        )
        for av in AVATAR_SCELTA:
            griglia_avatar.add_widget(Button(
                text=av, font_size=dp(22),
                background_color=VERDE,
                on_press=lambda x, a=av: self.seleziona_avatar(a)
            ))
        layout.add_widget(griglia_avatar)

        # Nome
        layout.add_widget(Label(
            text='Il tuo nome:', size_hint=(1, None), height=dp(26),
            font_size=dp(13), color=(0.3, 0.3, 0.3, 1)
        ))
        self.input_nome = TextInput(
            hint_text='Es. Mario', size_hint=(1, None), height=dp(44),
            multiline=False, font_size=dp(15)
        )
        layout.add_widget(self.input_nome)

        # Codice famiglia (opzionale)
        layout.add_widget(Label(
            text='Codice famiglia (lascia vuoto per crearne una nuova):',
            size_hint=(1, None), height=dp(36),
            font_size=dp(12), color=GRIGIO,
            halign='left', text_size=(dp(320), None)
        ))
        self.input_codice = TextInput(
            hint_text='Es. MARIO-X7K2',
            size_hint=(1, None), height=dp(44),
            multiline=False, font_size=dp(15)
        )
        layout.add_widget(self.input_codice)

        # Bottone registra
        layout.add_widget(Button(
            text='✅ Crea profilo',
            size_hint=(1, None), height=dp(50),
            background_color=VERDE, font_size=dp(16),
            on_press=lambda x: self.esegui_registrazione()
        ))

        self.lbl_stato_reg = Label(
            text='', size_hint=(1, None), height=dp(30),
            font_size=dp(12), color=ROSSO
        )
        layout.add_widget(self.lbl_stato_reg)

        self.layout_principale.add_widget(layout)

    def seleziona_avatar(self, avatar):
        self.avatar_selezionato = avatar
        self.lbl_avatar.text = avatar

    def esegui_registrazione(self):
        nome = self.input_nome.text.strip()
        if not nome:
            self.lbl_stato_reg.text = '⚠️ Inserisci il tuo nome!'
            return

        codice = self.input_codice.text.strip().upper() or None
        payload = json.dumps({
            'nome': nome,
            'avatar': self.avatar_selezionato,
            'codice_famiglia': codice
        })
        self.lbl_stato_reg.text = '⏳ Creazione profilo...'

        UrlRequest(
            f'{SERVER_URL}/utenti/registra',
            req_body=payload,
            req_headers={'Content-type': 'application/json'},
            on_success=self.on_registrazione_ok,
            on_failure=self.on_errore,
            on_error=self.on_errore
        )

    def on_registrazione_ok(self, req, data):
        if 'errore' in data:
            self.lbl_stato_reg.text = f'❌ {data["errore"]}'
            return

        utente = data.get('utente', {})
        famiglia = data.get('famiglia', {})

        # Salviamo localmente
        store.put('utente',
            nome=utente.get('nome'),
            avatar=utente.get('avatar'),
            codice_famiglia=utente.get('codice_famiglia')
        )

        self.utente_corrente = store.get('utente')
        self.famiglia_corrente = famiglia
        self.layout_principale.clear_widgets()
        self.mostra_profilo()

    # =========================================================================
    # PROFILO E FAMIGLIA
    # =========================================================================

    def mostra_profilo(self):
        """Schermata principale del profilo dopo il login."""
        nome = self.utente_corrente.get('nome', '?')
        avatar = self.utente_corrente.get('avatar', '👤')
        codice = self.utente_corrente.get('codice_famiglia', '')

        layout = BoxLayout(orientation='vertical', spacing=dp(10))

        # Header
        header = BoxLayout(size_hint=(1, None), height=dp(50))
        header.add_widget(Label(
            text=f'{avatar} {nome}',
            font_size=dp(20), bold=True, color=VERDE, size_hint=(0.7, 1)
        ))
        btn_torna = Button(
            text='🔙', size_hint=(0.15, 1),
            background_color=GRIGIO,
            on_press=lambda x: self.manager.vai_a_scanner()
        )
        btn_esci = Button(
            text='🚪', size_hint=(0.15, 1),
            background_color=ROSSO,
            on_press=lambda x: self.esci_dal_profilo()
        )
        header.add_widget(btn_torna)
        header.add_widget(btn_esci)
        layout.add_widget(header)

        # Codice famiglia (da condividere)
        box_codice = BoxLayout(
            orientation='vertical', size_hint=(1, None), height=dp(72),
            padding=dp(8)
        )
        box_codice.add_widget(Label(
            text='📋 Codice famiglia da condividere:',
            font_size=dp(12), color=GRIGIO,
            size_hint=(1, None), height=dp(22)
        ))
        box_codice.add_widget(Label(
            text=codice,
            font_size=dp(22), bold=True, color=VERDE,
            size_hint=(1, None), height=dp(36)
        ))
        layout.add_widget(box_codice)

        # Membri famiglia
        self.box_membri = BoxLayout(
            orientation='vertical', size_hint=(1, None), height=dp(120)
        )
        layout.add_widget(self.box_membri)

        # Sezione commenti
        layout.add_widget(Label(
            text='💬 Commenta un prodotto',
            font_size=dp(15), bold=True, color=VERDE,
            size_hint=(1, None), height=dp(34)
        ))

        btn_commenta = Button(
            text='📝 Apri chat prodotto',
            size_hint=(1, None), height=dp(48),
            background_color=BLU, font_size=dp(14),
            on_press=lambda x: self.apri_selezione_prodotto()
        )
        layout.add_widget(btn_commenta)

        self.lbl_stato = Label(
            text='', size_hint=(1, None), height=dp(28),
            font_size=dp(12), color=GRIGIO
        )
        layout.add_widget(self.lbl_stato)

        self.layout_principale.add_widget(layout)
        self.carica_membri(codice)

    def carica_membri(self, codice):
        UrlRequest(
            f'{SERVER_URL}/famiglia/{codice}',
            on_success=self.mostra_membri,
            on_failure=lambda r, e: None,
            on_error=lambda r, e: None
        )

    def mostra_membri(self, req, data):
        self.box_membri.clear_widgets()
        self.box_membri.add_widget(Label(
            text='👨‍👩‍👧‍👦 Membri della famiglia:',
            font_size=dp(13), color=GRIGIO,
            size_hint=(1, None), height=dp(26)
        ))
        membri = data.get('membri', [])
        riga = BoxLayout(size_hint=(1, None), height=dp(56), spacing=dp(8))
        for m in membri:
            riga.add_widget(Label(
                text=f"{m['avatar']}\n{m['nome']}",
                font_size=dp(13), halign='center',
                text_size=(dp(60), None)
            ))
        self.box_membri.add_widget(riga)

    def esci_dal_profilo(self):
        """Cancella il profilo locale e torna alla registrazione."""
        store.delete('utente')
        self.utente_corrente = None
        self.layout_principale.clear_widgets()
        self.mostra_registrazione()

    # =========================================================================
    # COMMENTI SUI PRODOTTI
    # =========================================================================

    def apri_selezione_prodotto(self):
        """Carica la lista prodotti per scegliere quale commentare."""
        self.lbl_stato.text = '⏳ Caricamento prodotti...'
        UrlRequest(
            f'{SERVER_URL}/prodotti',
            on_success=self.mostra_selezione_prodotto,
            on_failure=self.on_errore,
            on_error=self.on_errore
        )

    def mostra_selezione_prodotto(self, req, prodotti):
        self.lbl_stato.text = ''
        if not prodotti:
            self.lbl_stato.text = '⚠️ Nessun prodotto in dispensa.'
            return

        content = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(8))
        scroll = ScrollView(size_hint=(1, 0.85))
        lista = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(4))
        lista.bind(minimum_height=lista.setter('height'))

        popup = Popup(
            title='💬 Scegli un prodotto da commentare',
            content=content,
            size_hint=(0.95, 0.85)
        )

        for p in prodotti[:20]:  # Max 20 prodotti
            lista.add_widget(Button(
                text=f"{p['nome_prodotto']}",
                size_hint=(1, None), height=dp(44),
                background_color=VERDE, font_size=dp(13),
                on_press=lambda x, prod=p: (popup.dismiss(), self.apri_chat_prodotto(prod))
            ))

        scroll.add_widget(lista)
        content.add_widget(scroll)
        content.add_widget(Button(
            text='Annulla', size_hint=(1, None), height=dp(44),
            background_color=GRIGIO,
            on_press=lambda x: popup.dismiss()
        ))
        popup.open()

    def apri_chat_prodotto(self, prodotto):
        """Apre il popup di chat per un prodotto specifico."""
        content = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(8))

        content.add_widget(Label(
            text=f"💬 {prodotto['nome_prodotto']}",
            font_size=dp(15), bold=True, color=VERDE,
            size_hint=(1, None), height=dp(36)
        ))

        # Area commenti
        scroll = ScrollView(size_hint=(1, 0.55))
        self.box_commenti = BoxLayout(
            orientation='vertical', size_hint_y=None, spacing=dp(4)
        )
        self.box_commenti.bind(minimum_height=self.box_commenti.setter('height'))
        scroll.add_widget(self.box_commenti)
        content.add_widget(scroll)

        # Input nuovo commento
        input_box = BoxLayout(size_hint=(1, None), height=dp(44), spacing=dp(6))
        self.input_commento = TextInput(
            hint_text='Scrivi un commento...',
            size_hint=(0.75, 1), multiline=False, font_size=dp(13)
        )
        btn_invia = Button(
            text='📤 Invia', size_hint=(0.25, 1),
            background_color=VERDE, font_size=dp(12),
            on_press=lambda x: self.invia_commento(prodotto['id'])
        )
        input_box.add_widget(self.input_commento)
        input_box.add_widget(btn_invia)
        content.add_widget(input_box)

        self.popup_chat = Popup(
            title=f"Chat — {prodotto['nome_prodotto']}",
            content=content, size_hint=(0.95, 0.85)
        )
        self.prodotto_chat_id = prodotto['id']
        self.popup_chat.open()
        self.carica_commenti(prodotto['id'])

    def carica_commenti(self, prodotto_id):
        UrlRequest(
            f'{SERVER_URL}/prodotti/{prodotto_id}/commenti',
            on_success=self.mostra_commenti,
            on_failure=lambda r, e: None,
            on_error=lambda r, e: None
        )

    def mostra_commenti(self, req, commenti):
        self.box_commenti.clear_widgets()
        if not commenti:
            self.box_commenti.add_widget(Label(
                text='Nessun commento ancora. Scrivi il primo!',
                size_hint=(1, None), height=dp(36),
                font_size=dp(12), color=GRIGIO
            ))
            return

        for c in commenti:
            testo = f"{c['utente_avatar']} [b]{c['utente_nome']}[/b]: {c['testo']}\n[size=10][color=888888]{c['data'][:16]}[/color][/size]"
            self.box_commenti.add_widget(Label(
                text=testo, markup=True,
                size_hint=(1, None), height=dp(52),
                font_size=dp(13), color=(0.15, 0.15, 0.15, 1),
                halign='left', text_size=(dp(300), None)
            ))

    def invia_commento(self, prodotto_id):
        testo = self.input_commento.text.strip()
        if not testo or not self.utente_corrente:
            return

        payload = json.dumps({
            'utente_nome': self.utente_corrente.get('nome'),
            'testo': testo
        })
        UrlRequest(
            f'{SERVER_URL}/prodotti/{prodotto_id}/commenti',
            req_body=payload,
            req_headers={'Content-type': 'application/json'},
            on_success=lambda r, d: (
                setattr(self.input_commento, 'text', ''),
                self.carica_commenti(prodotto_id)
            ),
            on_failure=lambda r, e: None,
            on_error=lambda r, e: None
        )

    def on_errore(self, req, error):
        if hasattr(self, 'lbl_stato'):
            self.lbl_stato.text = f'❌ Errore: {error}'