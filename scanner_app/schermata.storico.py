# =============================================================================
# schermata_storico.py — Schermata storico consumi per l'app Kivy
# =============================================================================
# Mostra:
#   - Statistiche del mese corrente (consumati, sprecati, % spreco)
#   - Barra visiva spreco vs consumo
#   - Dettaglio per categoria
#   - Lista ultimi movimenti

import os
from datetime import date

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.network.urlrequest import UrlRequest
from kivy.metrics import dp

SERVER_URL = os.getenv('SERVER_URL', 'http://127.0.0.1:5000')

VERDE = (0.176, 0.478, 0.310, 1)
ROSSO = (0.906, 0.298, 0.235, 1)
ARANCIO = (0.953, 0.612, 0.071, 1)
GRIGIO = (0.5, 0.5, 0.5, 1)

NOMI_MESI = [
    '', 'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
    'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'
]


class SchermataStorico(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        oggi = date.today()
        self.anno_corrente = oggi.year
        self.mese_corrente = oggi.month
        self.build_ui()

    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))

        # --- HEADER ---
        header = BoxLayout(size_hint=(1, None), height=dp(56), spacing=dp(8))

        btn_indietro = Button(
            text='◀',
            size_hint=(None, 1),
            width=dp(40),
            background_color=GRIGIO,
            on_press=lambda x: self.cambia_mese(-1)
        )
        self.titolo_mese = Label(
            text=self._titolo(),
            font_size=dp(17),
            bold=True,
            color=VERDE,
            size_hint=(1, 1)
        )
        btn_avanti = Button(
            text='▶',
            size_hint=(None, 1),
            width=dp(40),
            background_color=GRIGIO,
            on_press=lambda x: self.cambia_mese(1)
        )
        btn_torna = Button(
            text='🔙',
            size_hint=(None, 1),
            width=dp(48),
            background_color=VERDE,
            on_press=lambda x: self.manager.vai_a_scanner()
        )
        header.add_widget(btn_indietro)
        header.add_widget(self.titolo_mese)
        header.add_widget(btn_avanti)
        header.add_widget(btn_torna)

        # --- STATO ---
        self.label_stato = Label(
            text='Caricamento...',
            size_hint=(1, None),
            height=dp(28),
            font_size=dp(12),
            color=GRIGIO
        )

        # --- STATISTICHE RIEPILOGO ---
        self.box_stats = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(80),
            spacing=dp(8)
        )

        # --- BARRA SPRECO ---
        self.box_barra = BoxLayout(
            orientation='vertical',
            size_hint=(1, None),
            height=dp(50),
            spacing=dp(4)
        )

        # --- SCROLL contenuto dettaglio ---
        self.scroll = ScrollView(size_hint=(1, 1))
        self.contenuto = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(4),
            padding=dp(4)
        )
        self.contenuto.bind(minimum_height=self.contenuto.setter('height'))
        self.scroll.add_widget(self.contenuto)

        layout.add_widget(header)
        layout.add_widget(self.label_stato)
        layout.add_widget(self.box_stats)
        layout.add_widget(self.box_barra)
        layout.add_widget(self.scroll)
        self.add_widget(layout)

    def on_enter(self):
        self.carica_storico()

    def _titolo(self):
        return f'📊 {NOMI_MESI[self.mese_corrente]} {self.anno_corrente}'

    def cambia_mese(self, delta):
        """Naviga al mese precedente o successivo."""
        self.mese_corrente += delta
        if self.mese_corrente > 12:
            self.mese_corrente = 1
            self.anno_corrente += 1
        elif self.mese_corrente < 1:
            self.mese_corrente = 12
            self.anno_corrente -= 1
        self.titolo_mese.text = self._titolo()
        self.carica_storico()

    def carica_storico(self):
        self.label_stato.text = '⏳ Caricamento storico...'
        self.box_stats.clear_widgets()
        self.box_barra.clear_widgets()
        self.contenuto.clear_widgets()

        url = f'{SERVER_URL}/storico?anno={self.anno_corrente}&mese={self.mese_corrente}'
        UrlRequest(
            url,
            on_success=self.mostra_storico,
            on_failure=self.on_errore,
            on_error=self.on_errore
        )

    def mostra_storico(self, req, data):
        consumati = data.get('totale_consumati', 0)
        sprecati = data.get('totale_sprecati', 0)
        perc = data.get('percentuale_spreco', 0.0)
        per_cat = data.get('per_categoria', {})
        movimenti = data.get('ultimi_movimenti', [])

        self.label_stato.text = f'✅ {consumati + sprecati} prodotti questo mese'

        # --- STATISTICHE ---
        self.box_stats.clear_widgets()
        self.box_stats.add_widget(self._stat_box('✅ Consumati', str(consumati), VERDE))
        self.box_stats.add_widget(self._stat_box('🗑️ Sprecati', str(sprecati), ROSSO))
        colore_perc = ROSSO if perc > 20 else ARANCIO if perc > 10 else VERDE
        self.box_stats.add_widget(self._stat_box('📉 Spreco', f'{perc}%', colore_perc))

        # --- BARRA SPRECO ---
        self.box_barra.clear_widgets()
        totale = consumati + sprecati
        if totale > 0:
            self.box_barra.add_widget(Label(
                text=f'Spreco del mese: {perc}%',
                size_hint=(1, None), height=dp(20),
                font_size=dp(12), color=GRIGIO
            ))
            pb = ProgressBar(
                max=100,
                value=perc,
                size_hint=(1, None),
                height=dp(20)
            )
            self.box_barra.add_widget(pb)

        # --- PER CATEGORIA ---
        if per_cat:
            self._aggiungi_sezione('📦 Per categoria')
            for cat, vals in per_cat.items():
                c = vals.get('consumati', 0)
                s = vals.get('sprecati', 0)
                testo = f'{cat}:  ✅ {c} consumati   🗑️ {s} sprecati'
                self.contenuto.add_widget(Label(
                    text=testo,
                    size_hint=(1, None), height=dp(32),
                    font_size=dp(13), color=(0.2, 0.2, 0.2, 1),
                    halign='left', text_size=(dp(340), None)
                ))

        # --- ULTIMI MOVIMENTI ---
        if movimenti:
            self._aggiungi_sezione('🕐 Ultimi movimenti')
            for m in movimenti:
                icona = '✅' if m['tipo'] == 'consumo' else '🗑️'
                data_fmt = m['data'][:10]
                testo = f"{icona} {m['nome_prodotto']}\n[size=11][color=888888]{data_fmt}[/color][/size]"
                self.contenuto.add_widget(Label(
                    text=testo,
                    markup=True,
                    size_hint=(1, None), height=dp(44),
                    font_size=dp(13), color=(0.2, 0.2, 0.2, 1),
                    halign='left', text_size=(dp(340), None)
                ))

        if not movimenti and not per_cat:
            self.contenuto.add_widget(Label(
                text='Nessun dato per questo mese.',
                size_hint=(1, None), height=dp(40),
                font_size=dp(14), color=GRIGIO
            ))

    def _stat_box(self, etichetta, valore, colore):
        box = BoxLayout(orientation='vertical', size_hint=(1, 1))
        box.add_widget(Label(text=valore, font_size=dp(26), bold=True, color=colore, size_hint=(1, 0.6)))
        box.add_widget(Label(text=etichetta, font_size=dp(11), color=GRIGIO, size_hint=(1, 0.4)))
        return box

    def _aggiungi_sezione(self, testo):
        self.contenuto.add_widget(Label(
            text=testo,
            size_hint=(1, None), height=dp(38),
            font_size=dp(14), bold=True, color=VERDE,
            halign='left', text_size=(dp(340), None)
        ))

    def on_errore(self, req, error):
        self.label_stato.text = f'❌ Errore: {error}'