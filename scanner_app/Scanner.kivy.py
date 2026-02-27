# =============================================================================
# scanner_kivy.py — App principale: scanner + spesa + storico + piano + famiglia
# =============================================================================

import cv2
import json
import os

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.network.urlrequest import UrlRequest
from kivy.metrics import dp
from pyzbar.pyzbar import decode

from schermata_spesa import SchermataSpesal
from schermata_storico import SchermataStorico
from schermata_pianificatore import SchermataPianificatore
from schermata_famiglia import SchermataFamiglia

SERVER_URL = os.getenv('SERVER_URL', 'http://127.0.0.1:5000')

VERDE   = (0.176, 0.478, 0.310, 1)
ARANCIO = (0.953, 0.612, 0.071, 1)
BLU     = (0.2,   0.4,   0.8,   1)
VIOLA   = (0.5,   0.2,   0.7,   1)
VERDE_S = (0.1,   0.55,  0.35,  1)  # verde scuro per famiglia


class SchermataScannerLayout(BoxLayout):
    def __init__(self, screen, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.screen = screen

        # Preview camera
        self.image_widget = Image(size_hint=(1, 0.68))
        self.add_widget(self.image_widget)

        # Stato scansione
        self.status_label = Label(
            text='📷 Punta la fotocamera su un codice a barre',
            size_hint=(1, None), height=dp(30),
            font_size=dp(13), color=(0.2, 0.2, 0.2, 1)
        )
        self.add_widget(self.status_label)

        # Griglia 2x2 + 1 bottoni navigazione
        nav = BoxLayout(orientation='vertical', size_hint=(1, None), height=dp(104), spacing=dp(6))
        riga1 = BoxLayout(spacing=dp(6), size_hint=(1, None), height=dp(46))
        riga2 = BoxLayout(spacing=dp(6), size_hint=(1, None), height=dp(46))

        riga1.add_widget(Button(
            text='🛒 Spesa', background_color=ARANCIO, font_size=dp(13),
            on_press=lambda x: self.screen.manager.vai_a('spesa')
        ))
        riga1.add_widget(Button(
            text='📊 Storico', background_color=BLU, font_size=dp(13),
            on_press=lambda x: self.screen.manager.vai_a('storico')
        ))
        riga2.add_widget(Button(
            text='📅 Piano Pasti', background_color=VIOLA, font_size=dp(13),
            on_press=lambda x: self.screen.manager.vai_a('pianificatore')
        ))
        riga2.add_widget(Button(
            text='👨‍👩‍👧 Famiglia', background_color=VERDE_S, font_size=dp(13),
            on_press=lambda x: self.screen.manager.vai_a('famiglia')
        ))

        nav.add_widget(riga1)
        nav.add_widget(riga2)
        self.add_widget(nav)


class SchermataScannerScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.capture = None
        self.is_sending = False
        self._clock_event = None
        self.layout = SchermataScannerLayout(screen=self)
        self.add_widget(self.layout)

    def on_enter(self):
        self.capture = cv2.VideoCapture(0)
        self._clock_event = Clock.schedule_interval(self.update, 1.0 / 30)

    def on_leave(self):
        if self._clock_event:
            self._clock_event.cancel()
        if self.capture:
            self.capture.release()
            self.capture = None

    def update(self, dt):
        if not self.capture:
            return
        ret, frame = self.capture.read()
        if not ret:
            return

        barcodes = decode(frame)
        for barcode in barcodes:
            barcode_data = barcode.data.decode('utf-8')
            if not self.is_sending:
                self.layout.status_label.text = f'⏳ Invio: {barcode_data}'
                self.send_barcode(barcode_data)

        buf = cv2.flip(frame, 0).tobytes()
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.layout.image_widget.texture = texture

    def send_barcode(self, code):
        self.is_sending = True
        payload = json.dumps({'barcode': code})
        headers = {'Content-type': 'application/json'}
        UrlRequest(
            f'{SERVER_URL}/scan',
            req_body=payload, req_headers=headers,
            on_success=self.on_success,
            on_failure=self.on_failure,
            on_error=self.on_error
        )

    def on_success(self, req, result):
        nome = result.get('nome', 'Prodotto sconosciuto')
        icona = '✅' if result.get('trovato_online') else '⚠️'
        self.layout.status_label.text = f'{icona} Salvato: {nome}'
        Clock.schedule_once(self.reset_scanner, 2)

    def on_failure(self, req, result):
        self.layout.status_label.text = '❌ Errore dal server. Riprova.'
        self.is_sending = False

    def on_error(self, req, error):
        self.layout.status_label.text = '🌐 Errore di rete.'
        self.is_sending = False

    def reset_scanner(self, dt):
        self.is_sending = False
        self.layout.status_label.text = '📷 Punta la fotocamera su un codice a barre'


# =============================================================================
# SCREEN MANAGER
# =============================================================================

class FrigoSmartScreenManager(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.transition = SlideTransition()

        self.add_widget(SchermataScannerScreen(name='scanner'))
        self.add_widget(SchermataSpesal(name='spesa'))
        self.add_widget(SchermataStorico(name='storico'))
        self.add_widget(SchermataPianificatore(name='pianificatore'))
        self.add_widget(SchermataFamiglia(name='famiglia'))

        self.current = 'scanner'

    def vai_a(self, schermata, direzione='left'):
        self.transition.direction = direzione
        self.current = schermata

    def vai_a_scanner(self):
        self.vai_a('scanner', 'right')


# =============================================================================
# APP PRINCIPALE
# =============================================================================

class FrigoSmartApp(App):
    def build(self):
        self.title = '🥦 FrigoSmart'
        return FrigoSmartScreenManager()


if __name__ == '__main__':
    FrigoSmartApp().run()