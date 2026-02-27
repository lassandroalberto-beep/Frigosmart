# =============================================================================
# schermata_pianificatore.py — Schermata pianificatore pasti per Kivy
# =============================================================================
# Mostra il menu settimanale con colazione/pranzo/cena per ogni giorno.
# Permette di generare un nuovo piano con l'AI e modificare i singoli pasti.

import json
import os
from datetime import date

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.network.urlrequest import UrlRequest
from kivy.metrics import dp

SERVER_URL = os.getenv('SERVER_URL', 'http://127.0.0.1:5000')

VERDE = (0.176, 0.478, 0.310, 1)
ARANCIO = (0.953, 0.612, 0.071, 1)
BLU = (0.2, 0.4, 0.8, 1)
ROSSO = (0.906, 0.298, 0.235, 1)
GRIGIO = (0.5, 0.5, 0.5, 1)

ICONE_PASTI = {
    'colazione': '☕',
    'pranzo': '🍝',
    'cena': '🍽️'
}


class SchermataPianificatore(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))

        # --- HEADER ---
        header = BoxLayout(size_hint=(1, None), height=dp(56), spacing=dp(8))

        titolo = Label(
            text='📅 Piano Settimanale',
            font_size=dp(18), bold=True,
            color=VERDE, size_hint=(0.5, 1)
        )
        btn_genera = Button(
            text='🤖 Genera con AI',
            size_hint=(0.35, 1),
            background_color=ARANCIO, font_size=dp(13),
            on_press=lambda x: self.genera_piano()
        )
        btn_torna = Button(
            text='🔙',
            size_hint=(0.15, 1),
            background_color=VERDE,
            on_press=lambda x: self.manager.vai_a_scanner()
        )
        header.add_widget(titolo)
        header.add_widget(btn_genera)
        header.add_widget(btn_torna)

        # --- STATO ---
        self.label_stato = Label(
            text='Caricamento...',
            size_hint=(1, None), height=dp(28),
            font_size=dp(12), color=GRIGIO
        )

        # --- SCROLL contenuto giorni ---
        self.scroll = ScrollView(size_hint=(1, 1))
        self.contenuto = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(10),
            padding=dp(4)
        )
        self.contenuto.bind(minimum_height=self.contenuto.setter('height'))
        self.scroll.add_widget(self.contenuto)

        layout.add_widget(header)
        layout.add_widget(self.label_stato)
        layout.add_widget(self.scroll)
        self.add_widget(layout)

    def on_enter(self):
        self.carica_piano()

    def carica_piano(self):
        self.label_stato.text = '⏳ Caricamento piano...'
        self.contenuto.clear_widgets()
        UrlRequest(
            f'{SERVER_URL}/piano',
            on_success=self.mostra_piano,
            on_failure=self.on_errore,
            on_error=self.on_errore
        )

    def genera_piano(self):
        self.label_stato.text = '🤖 L\'AI sta creando il tuo menu... (può richiedere qualche secondo)'
        self.contenuto.clear_widgets()
        UrlRequest(
            f'{SERVER_URL}/piano/genera',
            req_body='{}',
            req_headers={'Content-type': 'application/json'},
            on_success=self.mostra_piano,
            on_failure=self.on_errore,
            on_error=self.on_errore
        )

    def mostra_piano(self, req, data):
        self.contenuto.clear_widgets()

        # Nessun piano esistente
        if data.get('piano') is None and 'messaggio' in data:
            self.label_stato.text = data['messaggio']
            self.contenuto.add_widget(Label(
                text='Premi "🤖 Genera con AI" per creare il tuo menu settimanale!',
                size_hint=(1, None), height=dp(60),
                font_size=dp(14), color=GRIGIO,
                halign='center', text_size=(dp(320), None)
            ))
            return

        if 'errore' in data:
            self.label_stato.text = f'❌ {data["errore"]}'
            return

        giorni = data.get('giorni', [])
        settimana_dal = data.get('settimana_dal', '')
        self.label_stato.text = f'✅ Menu dal {settimana_dal} — {len(giorni)} giorni'

        for giorno in giorni:
            self.contenuto.add_widget(self._card_giorno(giorno))

    def _card_giorno(self, giorno):
        """Crea la card per un giorno con colazione/pranzo/cena."""
        card = BoxLayout(
            orientation='vertical',
            size_hint=(1, None),
            spacing=dp(4),
            padding=(dp(10), dp(8))
        )

        # Intestazione giorno
        oggi = date.today().strftime('%Y-%m-%d')
        colore_giorno = ARANCIO if giorno['data'] == oggi else VERDE
        card.add_widget(Label(
            text=f"{'📍 ' if giorno['data'] == oggi else ''}{giorno['giorno']} {giorno['data']}",
            size_hint=(1, None), height=dp(32),
            font_size=dp(15), bold=True, color=colore_giorno,
            halign='left', text_size=(dp(340), None)
        ))

        # Righe per ogni pasto
        for tipo in ('colazione', 'pranzo', 'cena'):
            valore = giorno.get(tipo, '') or '—'
            card.add_widget(self._riga_pasto(
                tipo=tipo,
                valore=valore,
                data=giorno['data']
            ))

        # Separatore
        card.add_widget(Label(
            text='─' * 50,
            size_hint=(1, None), height=dp(16),
            font_size=dp(10), color=(0.85, 0.85, 0.85, 1)
        ))

        card.height = dp(32) + dp(48) * 3 + dp(16) + dp(12)
        return card

    def _riga_pasto(self, tipo, valore, data):
        """Riga singola con icona, testo del pasto e bottone modifica."""
        riga = BoxLayout(size_hint=(1, None), height=dp(46), spacing=dp(6))

        icona = ICONE_PASTI.get(tipo, '🍴')
        testo = f"{icona} [b]{tipo.capitalize()}:[/b] {valore}"

        lbl = Label(
            text=testo, markup=True,
            size_hint=(0.78, 1), font_size=dp(12),
            color=(0.2, 0.2, 0.2, 1),
            halign='left', text_size=(dp(260), None)
        )

        btn_modifica = Button(
            text='✏️',
            size_hint=(0.22, 0.8),
            background_color=BLU, font_size=dp(14),
            on_press=lambda x, t=tipo, v=valore, d=data: self.apri_modifica(t, v, d)
        )

        riga.add_widget(lbl)
        riga.add_widget(btn_modifica)
        return riga

    def apri_modifica(self, tipo, valore_attuale, data):
        """Apre un popup per modificare un singolo pasto."""
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))

        content.add_widget(Label(
            text=f'Modifica {tipo} del {data}',
            size_hint=(1, None), height=dp(30),
            font_size=dp(14), color=VERDE
        ))

        input_pasto = TextInput(
            text=valore_attuale if valore_attuale != '—' else '',
            hint_text=f'Inserisci il nuovo {tipo}...',
            size_hint=(1, None), height=dp(80),
            multiline=True, font_size=dp(13)
        )
        content.add_widget(input_pasto)

        bottoni = BoxLayout(size_hint=(1, None), height=dp(44), spacing=dp(8))

        popup = Popup(
            title=f'✏️ Modifica {tipo.capitalize()}',
            content=content,
            size_hint=(0.9, None), height=dp(240)
        )

        def salva(instance):
            nuovo_valore = input_pasto.text.strip()
            if nuovo_valore:
                self._invia_modifica(data, tipo, nuovo_valore)
            popup.dismiss()

        btn_salva = Button(
            text='💾 Salva', background_color=VERDE,
            on_press=salva
        )
        btn_annulla = Button(
            text='Annulla', background_color=GRIGIO,
            on_press=lambda x: popup.dismiss()
        )
        bottoni.add_widget(btn_salva)
        bottoni.add_widget(btn_annulla)
        content.add_widget(bottoni)

        popup.open()

    def _invia_modifica(self, data, tipo, valore):
        """Invia la modifica al server e ricarica il piano."""
        payload = json.dumps({'data': data, 'tipo': tipo, 'valore': valore})
        headers = {'Content-type': 'application/json'}
        self.label_stato.text = '⏳ Salvataggio...'
        UrlRequest(
            f'{SERVER_URL}/piano/pasto',
            req_body=payload,
            req_headers=headers,
            on_success=lambda req, res: self.carica_piano(),
            on_failure=self.on_errore,
            on_error=self.on_errore
        )

    def on_errore(self, req, error):
        self.label_stato.text = f'❌ Errore: {error}'