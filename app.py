"""
MRA 4 Dashboard - Dash Web Application
Dunkles minimales Design mit Echtzeit-Monitoring
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc
import dash_daq as daq
import plotly.graph_objs as go
from collections import deque
import time
from datetime import datetime
from modbus_client import MRA4Simulator, MRA4Client
from config_manager import get_config_manager, save_config
from pymodbus.client import ModbusTcpClient
import sys
import socket
import logging
import os

# Logging-Konfiguration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app_logger = logging.getLogger('mra4_dashboard')
app_logger.setLevel(logging.INFO)

# Log-Buffer für UI-Anzeige
LOG_BUFFER = deque(maxlen=100)
LOG_BUFFER_DEBUG = deque(maxlen=500)

class LogHandler(logging.Handler):
    """Custom Log Handler der Logs in den Buffer schreibt"""
    def emit(self, record):
        log_entry = self.format(record)
        LOG_BUFFER.append(log_entry)
        LOG_BUFFER_DEBUG.append(log_entry)

log_handler = LogHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'))
app_logger.addHandler(log_handler)

# Log-Handler auch für andere Logger hinzufügen
logging.getLogger('modbus_client').addHandler(log_handler)
logging.getLogger('modbus_client').setLevel(logging.INFO)

# Root-Logger für alle anderen Nachrichten
logging.getLogger().addHandler(log_handler)

# Werkzeug/Flask Logging für saubere Konsole deaktivieren
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('dash').setLevel(logging.ERROR)

# COT Code Mapping (Cause of Trip)
COT_CODES = {
    1: "NORM (Kein Fehler)",
    1001: "AnaP[1] - Analoger Schutz 1", 1002: "AnaP[2]", 1003: "AnaP[3]", 1004: "AnaP[4]",
    1201: "IE[1] - Erdstrom 1", 1202: "IE[2]", 1203: "IE[3]", 1204: "IE[4]",
    1306: "ExS[1] - Externer Schutz 1", 1307: "ExS[2]", 1308: "ExS[3]", 1309: "ExS[4]",
    1310: "LS-Mitnahme",
    1401: "f[1] - Überfrequenz 1", 1402: "f[2] - Überfrequenz 2", 1403: "f[3] - Überfrequenz 3",
    1404: "f[4] - Unterfrequenz 4", 1405: "f[5] - Unterfrequenz 5", 1406: "f[6] - Unterfrequenz 6",
    1407: "df/dt - Frequenzänderung", 1408: "delta phi - Phasenwinkel",
    2501: "LVRT[1] - Unterspannung", 2502: "LVRT[2]",
    2901: "I2>[1] - Gegensystem", 2902: "I2>[2]",
    3001: "U012[1] - Spannungssymmetrie", 3002: "U012[2]", 3003: "U012[3]", 3004: "U012[4]", 3005: "U012[5]", 3006: "U012[6]",
    3201: "I[1] - Überstrom 1", 3202: "I[2]", 3203: "I[3]", 3204: "I[4]", 3205: "I[5]", 3206: "I[6]",
    3401: "PQS[1] - Leistung 1", 3402: "PQS[2]", 3403: "PQS[3]", 3404: "PQS[4]", 3405: "PQS[5]", 3406: "PQS[6]",
    3407: "P - Wirkleistung", 3408: "Q - Blindleistung",
    3501: "LF[1] - Leitungsschutz", 3502: "LF[2]",
    3601: "Q->&U< - Blindleistung/Unterspannung", 3801: "ThA - Thermischer Alarm",
    4001: "UE[1] - Erdspannung", 4002: "UE[2]",
    4101: "U[1] - Überspannung 1", 4102: "U[2] - Überspannung 2", 4103: "U[3] - Überspannung 3",
    4104: "U[4] - Unterspannung 4", 4105: "U[5] - Unterspannung 5", 4106: "U[6] - Unterspannung 6",
    4107: "HVRT[1] - Überspannung", 4108: "HVRT[2]"
}

# Startup-Zeit für Uptime
STARTUP_TIME = time.time()  # Unix timestamp für Uptime-Berechnung

# Config Manager initialisieren
config = get_config_manager()

# Konfiguration - Max. Leistung
MAX_POWER_KW = config.get('max_power_kw', 12.0)

# Simulator Modus - IMMER beim Start AUS (nicht persistent)
SIMULATOR_MODE = False

# Schalter-Timeout aus Config (persistent, änderbar über Supervisor)
COUPLING_UNLOCK_TIMEOUT = config.get('coupling_unlock_timeout', 30)

def get_local_ip():
    """Ermittelt die lokale IP-Adresse des Rechners"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_hostname():
    """Ermittelt den Hostnamen"""
    try:
        return socket.gethostname()
    except Exception:
        return "localhost"

# Startup-Verbindungstest mit interaktiver IP-Eingabe
def check_modbus_connection_on_startup():
    """Prüft die Modbus-Verbindung beim Start"""
    global SIMULATOR_MODE

    ip = config.get('modbus.ip', '192.168.1.100')
    port = config.get('modbus.port', 502)

    while True:  # Schleife für Wiederholung mit neuer IP
        print(f"\nVerbindungsaufbau zu MRA4 ({ip}:{port})...")
        print("Timeout: 30 Sekunden\n")

        start_time = time.time()
        timeout = 30  # 30 Sekunden Timeout

        connected = False
        while time.time() - start_time < timeout:
            try:
                test_client = ModbusTcpClient(host=ip, port=port, timeout=3)
                if test_client.connect():
                    test_client.close()
                    print("Verbindung erfolgreich hergestellt!\n")
                    connected = True
                    break
                test_client.close()
            except Exception:
                pass
            time.sleep(1)
            remaining = int(timeout - (time.time() - start_time))
            if remaining > 0 and remaining % 5 == 0:
                print(f"Versuche Verbindung... ({remaining}s verbleibend)")

        if connected:
            SIMULATOR_MODE = False
            return True

        # Timeout erreicht - Fehlermeldung und Optionen anbieten
        print("\n" + "="*60)
        print("FEHLER: Keine MODBUS TCP Verbindung zu Schutzgerät möglich!")
        print("="*60)
        print("\nBitte prüfen Sie:")
        print("  - Netzwerkverbindung zum MRA4")
        print("  - Stromversorgung des Geräts")
        print(f"  - Aktuelle IP-Adresse: {ip}")
        print(f"  - Port: {port}")
        print("\n" + "="*60)
        print("\nOptionen:")
        print("  [1] Neue IP-Adresse eingeben")
        print("  [2] Neuen Port eingeben")
        print("  [3] Erneut versuchen (gleiche Einstellungen)")
        print("  [4] Im Simulator Modus starten (Simulierte Werte)")
        print("  [5] Programm beenden")
        print("\nIhre Wahl (1-5): ", end="", flush=True)

        try:
            choice = input().strip()

            if choice == "1":
                print("Neue IP-Adresse eingeben: ", end="", flush=True)
                new_ip = input().strip()
                if new_ip:
                    ip = new_ip
                    config.set('modbus.ip', ip)
                    print(f"IP-Adresse geändert zu: {ip}")

            elif choice == "2":
                print("Neuen Port eingeben: ", end="", flush=True)
                new_port = input().strip()
                if new_port.isdigit():
                    port = int(new_port)
                    config.set('modbus.port', port)
                    print(f"Port geändert zu: {port}")

            elif choice == "3":
                print("Versuche erneut...")
                continue

            elif choice == "4":
                print("Starte im Simulator Modus (Simulierte Werte)...")
                SIMULATOR_MODE = True
                return True

            elif choice == "5":
                print("Programm wird beendet.")
                sys.exit(0)

            else:
                print("Ungültige Eingabe. Bitte 1-5 wählen.")

        except Exception as e:
            print(f"Eingabefehler: {e}")
            print("Programm wird beendet.")
            sys.exit(1)

# Verbindungscheck beim Start
check_modbus_connection_on_startup()

# App initialisieren mit dunklem Theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG], suppress_callback_exceptions=True)
app.title = "MRA 4 Dashboard"

# Globale Variablen für Einstellungen
current_max_power = MAX_POWER_KW
current_update_interval = 1000

# Modbus Client aus Config initialisieren
def init_modbus_client():
    """Initialisiere Modbus Client basierend auf Simulator Modus"""
    global SIMULATOR_MODE
    if SIMULATOR_MODE:
        client = MRA4Simulator()
    else:
        ip = config.get('modbus.ip', '192.168.1.100')
        port = config.get('modbus.port', 502)
        unit_id = config.get('modbus.unit_id', 1)
        client = MRA4Client(host=ip, port=port, unit_id=unit_id)
    client.connect()
    return client

mra4 = init_modbus_client()

# Daten-Buffer für Graphen (letzte 60 Sekunden)
MAX_DATA_POINTS = 60
time_data = deque(maxlen=MAX_DATA_POINTS)
voltage_data = {'L1': deque(maxlen=MAX_DATA_POINTS), 'L2': deque(maxlen=MAX_DATA_POINTS), 'L3': deque(maxlen=MAX_DATA_POINTS)}
current_data = {'L1': deque(maxlen=MAX_DATA_POINTS), 'L2': deque(maxlen=MAX_DATA_POINTS), 'L3': deque(maxlen=MAX_DATA_POINTS)}
power_data = {'L1': deque(maxlen=MAX_DATA_POINTS), 'L2': deque(maxlen=MAX_DATA_POINTS), 'L3': deque(maxlen=MAX_DATA_POINTS), 'total': deque(maxlen=MAX_DATA_POINTS)}

# Custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                background: #0d0d0d url('/assets/background.jpg') center center fixed;
                background-size: cover;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                position: relative;
            }
            body::before {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: url('assets/background.jpg') center center;
                background-size: cover;
                background-repeat: no-repeat;
                opacity: 0.25;
                z-index: -2;
            }
            body::after {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(13, 13, 13, 0.7);
                z-index: -1;
            }
            .neon-text {
                color: #4CAF50;
                text-shadow: 0 0 5px rgba(76, 175, 80, 0.4);
            }
            .neon-cyan {
                color: #2196F3;
                text-shadow: 0 0 5px rgba(33, 150, 243, 0.4);
            }
            .neon-pink {
                color: #FF9800;
                text-shadow: 0 0 5px rgba(255, 152, 0, 0.4);
            }
            .header-logo {
                height: 240px;
                width: auto;
                object-fit: contain;
            }
            /* Custom Gauge Styling */
            ._dash-daq-gauge text {
                fill: #ffffff !important;
            }
            ._dash-daq-gauge text[font-size="20"] {
                font-size: 240px !important;
                fill: #ffffff !important;
                font-weight: 700 !important;
            }
            ._dash-daq-gauge .unit {
                fill: #ffffff !important;
                font-size: 240px !important;
            }
            ._dash-daq-gauge svg text:last-of-type {
                fill: #ffffff !important;
                font-size: 60px !important;
            }
            .power-warning {
                background: rgba(255, 152, 0, 0.2);
                border: 2px solid #FF9800;
                border-radius: 8px;
                padding: 15px;
                margin-top: 20px;
                animation: blink 1s ease-in-out infinite;
            }
            @keyframes blink {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.6; }
            }
            .card-dark {
                background: linear-gradient(145deg, #161616, #1c1c1c);
                border: 1px solid #252525;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255,255,255,0.03);
            }
            .data-table {
                width: 100%;
                border-collapse: collapse;
            }
            .data-table th {
                text-align: left;
                padding: 10px 12px;
                border-bottom: 1px solid #2a2a2a;
                color: #666;
                font-weight: 500;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .data-table td {
                padding: 10px 12px;
                border-bottom: 1px solid #1f1f1f;
                font-size: 14px;
                font-weight: 500;
            }
            .data-table tr:last-child td {
                border-bottom: none;
            }
            .startup-screen {
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                height: 100vh;
                background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
            }
            .logo-placeholder {
                width: 400px;
                height: 400px;
                border: 3px solid #4CAF50;
                border-radius: 50%;
                display: flex;
                justify-content: center;
                align-items: center;
                margin-bottom: 40px;
                box-shadow: 0 0 40px rgba(76, 175, 80, 0.4);
                animation: pulse 2s ease-in-out infinite;
            }
            @keyframes pulse {
                0%, 100% { box-shadow: 0 0 40px rgba(76, 175, 80, 0.4); }
                50% { box-shadow: 0 0 60px rgba(76, 175, 80, 0.6); }
            }
            @keyframes glow {
                0%, 100% {
                    text-shadow: 0 0 20px rgba(76, 175, 80, 0.8), 0 0 40px rgba(76, 175, 80, 0.4);
                    transform: scale(1);
                }
                50% {
                    text-shadow: 0 0 30px rgba(76, 175, 80, 1), 0 0 60px rgba(76, 175, 80, 0.6);
                    transform: scale(1.05);
                }
            }
            @keyframes pulse-ring {
                0% {
                    transform: translate(-50%, -50%) scale(0.5);
                    opacity: 1;
                }
                100% {
                    transform: translate(-50%, -50%) scale(2);
                    opacity: 0;
                }
            }
            .energy-pulse {
                position: relative;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .password-modal-body {
                background: #1a1a1a;
            }
            .password-input {
                background: #0f0f0f !important;
                border: 1px solid #2a2a2a !important;
                color: #00ff88 !important;
                border-radius: 8px !important;
                padding: 12px !important;
                font-size: 18px !important;
                text-align: center !important;
                letter-spacing: 4px !important;
            }
            .tab-admin {
                background: linear-gradient(135deg, #ff4444, #cc0000) !important;
                border-color: #ff4444 !important;
            }
            .unlocked-indicator {
                background: rgba(0, 255, 136, 0.2);
                border: 2px solid #00ff88;
                border-radius: 8px;
                padding: 10px 20px;
                text-align: center;
                margin-bottom: 15px;
            }
            .awd-em-indicator {
                background: rgba(255, 193, 7, 0.2);
                border: 2px solid #FFC107;
                border-radius: 8px;
                padding: 8px 15px;
                text-align: center;
                color: #FFC107;
                font-weight: 600;
                font-size: 12px;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Startbildschirm
startup_screen = html.Div([
    html.Div([
        html.Div([
            html.Img(src='assets/logo.png', style={'maxHeight': '360px', 'maxWidth': '360px', 'objectFit': 'contain'})
        ], className="logo-placeholder"),
        html.H1("ENERGIEMONITORING", className="neon-text", style={'fontSize': '126px', 'margin': 0, 'letterSpacing': '2px', 'fontWeight': '600'}),
        html.P("MRA 4 Dashboard", style={'color': '#666', 'fontSize': '48px', 'marginTop': '10px', 'letterSpacing': '1px'}),

        # Fortschrittsbalken
        # Animierte Energie-Wellen
        html.Div([
            html.Div(className="energy-pulse", style={
                'width': '300px',
                'height': '300px',
                'margin': '0 auto 40px auto',
                'position': 'relative',
                'display': 'flex',
                'justifyContent': 'center',
                'alignItems': 'center'
            }, children=[
                html.Div(id='startup-logo', style={
                    'fontSize': '120px',
                    'color': '#4CAF50',
                    'animation': 'glow 2s ease-in-out infinite',
                    'position': 'relative',
                    'zIndex': '10'
                }, children="⚡"),
                html.Div(className="pulse-ring", style={
                    'position': 'absolute',
                    'top': '50%',
                    'left': '50%',
                    'transform': 'translate(-50%, -50%)',
                    'width': '150px',
                    'height': '150px',
                    'border': '4px solid #4CAF50',
                    'borderRadius': '50%',
                    'animation': 'pulse-ring 2s ease-out infinite'
                }),
                html.Div(className="pulse-ring", style={
                    'position': 'absolute',
                    'top': '50%',
                    'left': '50%',
                    'transform': 'translate(-50%, -50%)',
                    'width': '150px',
                    'height': '150px',
                    'border': '4px solid #2196F3',
                    'borderRadius': '50%',
                    'animation': 'pulse-ring 2s ease-out infinite 1s'
                })
            ]),

            html.Div(id='startup-status', style={
                'color': '#00ddff',
                'fontSize': '18px',
                'textAlign': 'center',
                'marginTop': '30px',
                'fontWeight': '600',
                'letterSpacing': '2px'
            }, children="MRA 4 ENERGIEMONITORING")
        ])
    ], className="startup-screen")
], id="startup-page")

# Hauptnavigation mit COT-Anzeige
navbar = dbc.Navbar(
    dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.NavbarBrand(
                    html.Span("Energiemonitoring", style={'color': '#4CAF50', 'fontWeight': 'bold', 'fontSize': '20px'}),
                    href="/"
                )
            ], width="auto"),
            dbc.Col([
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink("Dashboard", href="/", style={'color': '#888'})),
                    dbc.NavItem(dbc.NavLink("Einstellungen", href="/settings", style={'color': '#888'})),
                ], navbar=True)
            ], width="auto"),
            dbc.Col([
                # COT-Anzeige in TopBar (große Anzeige)
                html.Div(id='topbar-cot-display', children=[], style={'textAlign': 'right'})
            ], width=True)
        ], align="center", className="g-0", style={'width': '100%'})
    ], fluid=True),
    color="#0a0a0a",
    dark=True,
    style={'borderBottom': '1px solid #222', 'padding': '10px 20px'}
)

# Passwort-Modal für Koppelschalter
password_modal_coupling = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Passwort erforderlich", style={'color': '#fff'}), close_button=True, style={'background': '#1a1a1a', 'borderBottom': '1px solid #333'}),
    dbc.ModalBody([
        html.P("Bitte geben Sie das Passwort ein, um den Koppelschalter freizuschalten:", style={'color': '#888', 'marginBottom': '20px'}),
        html.P(id="coupling-timeout-info", style={'color': '#666', 'marginBottom': '20px', 'fontSize': '12px'}),
        dbc.Input(id="coupling-password-input", type="password", placeholder="Passwort eingeben", className="password-input"),
        html.Div(id="coupling-password-error", style={'color': '#ff4444', 'marginTop': '10px', 'textAlign': 'center'})
    ], style={'background': '#1a1a1a'}),
    dbc.ModalFooter([
        dbc.Button("Abbrechen", id="coupling-password-cancel", color="secondary", style={'marginRight': '10px'}),
        dbc.Button("Freischalten", id="coupling-password-confirm", color="success")
    ], style={'background': '#1a1a1a', 'borderTop': '1px solid #333'})
], id="coupling-password-modal", is_open=False, centered=True)

# Dashboard-Seite
def create_dashboard_page():
    simulator_indicator = []
    if SIMULATOR_MODE:
        simulator_indicator = html.Div("SIMULATOR MODUS AKTIV", className="awd-em-indicator", style={'marginBottom': '10px'})

    return html.Div([
        navbar,
        password_modal_coupling,
        dbc.Container([
            # Simulator Modus Anzeige
            simulator_indicator,

            # Header mit Titel und Logo
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Row([
                            dbc.Col([
                                html.H2("ENERGIEVERBRAUCH MONITORING",
                                       style={'color': '#fff', 'fontWeight': '600', 'fontSize': '84px', 'margin': 0, 'letterSpacing': '1px'})
                            ], width=8, className="d-flex align-items-center"),
                            dbc.Col([
                                html.Img(src='assets/logo.png', className='header-logo')
                            ], width=4, className="d-flex align-items-center justify-content-end")
                        ])
                    ], style={'padding': '25px 20px', 'background': 'rgba(22, 22, 22, 0.85)', 'borderRadius': '8px', 'margin': '20px 0', 'border': '1px solid #2a2a2a'})
                ], width=12)
            ]),

            # Linke Spalte in Container
            dbc.Row([
                dbc.Col([
                    html.Div([
                        # Statuszeile
                        html.Div([
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        html.Span("Status: ", style={'color': '#666', 'fontSize': '13px'}),
                                        html.Span(id="connection-status", className="neon-text", style={'fontWeight': '600', 'fontSize': '14px'})
                                    ], style={'padding': '12px'})
                                ], width=6),
                                dbc.Col([
                                    html.Div([
                                        html.Span("Frequenz: ", style={'color': '#666', 'fontSize': '13px'}),
                                        html.Span(id="frequency-display", className="neon-cyan", style={'fontWeight': '600', 'fontSize': '14px'})
                                    ], style={'padding': '12px'})
                                ], width=6)
                            ])
                        ], className="card-dark", style={'marginBottom': '20px'}),

                        # Messwerte-Tabelle
                        html.Div([
                            html.H5("Messwerte", style={'color': '#666', 'marginBottom': '12px', 'fontSize': '13px', 'fontWeight': '600'}),
                            html.Table([
                                html.Thead([
                                    html.Tr([
                                        html.Th("Phase"),
                                        html.Th("Spannung"),
                                        html.Th("Strom"),
                                        html.Th("Leistung")
                                    ])
                                ]),
                                html.Tbody([
                                    html.Tr([
                                        html.Td("L1", className="neon-text"),
                                        html.Td(id="voltage-l1", className="neon-text"),
                                        html.Td(id="current-l1", className="neon-text"),
                                        html.Td(id="power-l1", className="neon-text")
                                    ]),
                                    html.Tr([
                                        html.Td("L2", className="neon-cyan"),
                                        html.Td(id="voltage-l2", className="neon-cyan"),
                                        html.Td(id="current-l2", className="neon-cyan"),
                                        html.Td(id="power-l2", className="neon-cyan")
                                    ]),
                                    html.Tr([
                                        html.Td("L3", className="neon-pink"),
                                        html.Td(id="voltage-l3", className="neon-pink"),
                                        html.Td(id="current-l3", className="neon-pink"),
                                        html.Td(id="power-l3", className="neon-pink")
                                    ]),
                                    html.Tr([
                                        html.Td("S", style={'fontWeight': '600', 'color': '#aaa', 'fontSize': '15px'}),
                                        html.Td("-", style={'color': '#444'}),
                                        html.Td("-", style={'color': '#444'}),
                                        html.Td(id="power-total", style={'fontWeight': '600', 'color': '#fff'})
                                    ])
                                ])
                            ], className="data-table")
                        ], className="card-dark", style={'padding': '18px', 'marginBottom': '15px'}),

                        # Koppelschalter
                        html.Div([
                            html.H5("Koppelschalter", style={'color': '#666', 'marginBottom': '12px', 'fontSize': '13px', 'fontWeight': '600'}),
                            # Unlock-Status Anzeige
                            html.Div(id='coupling-unlock-status', children=[]),
                            dbc.Row([
                                dbc.Col([
                                    # Button zum Öffnen des Passwort-Dialogs
                                    dbc.Button("Freischalten", id="coupling-unlock-btn", color="warning", size="sm",
                                              style={'marginBottom': '10px', 'width': '100%'}),
                                    daq.PowerButton(
                                        id='coupling-switch',
                                        on=False,
                                        label='',
                                        color='#4CAF50',
                                        size=60,
                                        disabled=True  # Standardmäßig deaktiviert
                                    )
                                ], width=3, style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center', 'justifyContent': 'center'}),
                                dbc.Col([
                                    html.Div([
                                        html.Span("Status: ", style={'color': '#666', 'fontSize': '12px'}),
                                        html.Span(id='coupling-di-status', className="neon-cyan", style={'fontSize': '16px', 'fontWeight': '700'})
                                    ], style={'textAlign': 'center', 'marginTop': '10px'})
                                ], width=5),
                                dbc.Col([
                                    # Quittier-Button (nur sichtbar bei Auslösung)
                                    html.Div(id='acknowledge-section', children=[])
                                ], width=4)
                            ])
                        ], style={'marginBottom': '30px'}),

                        # Störschrieb-Trigger (Leittechnik-Befehl 3)
                        html.Div([
                            html.H5("Störschrieb", style={'color': '#666', 'marginBottom': '12px', 'fontSize': '13px', 'fontWeight': '600'}),
                            dbc.Row([
                                dbc.Col([
                                    daq.PowerButton(
                                        id='fault-recording-switch',
                                        on=False,
                                        label='',
                                        color='#FF9800',
                                        size=60,
                                        disabled=False
                                    )
                                ], width=3, style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center', 'justifyContent': 'center'}),
                                dbc.Col([
                                    html.Div([
                                        html.Span("Leittechnik-Befehl 3", style={'color': '#666', 'fontSize': '12px'}),
                                        html.Br(),
                                        html.Span("Störschrieb-Aufzeichnung starten", style={'color': '#888', 'fontSize': '11px'})
                                    ], style={'textAlign': 'left', 'marginTop': '10px'})
                                ], width=9)
                            ])
                        ], className="card-dark", style={'padding': '18px'}),

                        # Schutz-Status und COT
                        html.Div([
                            html.H5("Schutz-Status", style={'color': '#666', 'marginBottom': '12px', 'fontSize': '13px', 'fontWeight': '600'}),
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        html.Span("Status: ", style={'color': '#666', 'fontSize': '12px'}),
                                        html.Span(id='protection-status-text', style={'fontSize': '14px', 'fontWeight': '600'})
                                    ], style={'marginBottom': '8px'}),
                                    html.Div([
                                        html.Span("Störfall-Nr.: ", style={'color': '#666', 'fontSize': '12px'}),
                                        html.Span(id='fault-number-display', style={'fontSize': '14px', 'fontWeight': '600', 'color': '#888'})
                                    ])
                                ], width=6),
                                dbc.Col([
                                    html.Div([
                                        html.Span("Auslöseursache (COT): ", style={'color': '#666', 'fontSize': '12px'}),
                                        html.Div(id='cot-display', style={'fontSize': '13px', 'fontWeight': '600', 'marginTop': '4px'})
                                    ])
                                ], width=6)
                            ])
                        ], className="card-dark", style={'padding': '18px', 'marginTop': '15px'})
                    ], className="card-dark", style={'padding': '20px'})
                ], width=9),

                # Rechte Spalte: Leistungs-Gauge (schmaler)
                dbc.Col([
                    html.Div([
                        html.H5("GESAMT", style={'color': '#fff', 'marginBottom': '10px', 'fontSize': '14px', 'textAlign': 'center', 'fontWeight': '600', 'letterSpacing': '1px'}),
                        daq.Gauge(
                            id='power-gauge-total',
                            min=0,
                            max=MAX_POWER_KW,
                            value=0,
                            showCurrentValue=True,
                            units="kW",
                            color="#4CAF50",
                            size=320
                        ),
                        html.Div([
                            html.Span("kW", style={'color': '#ffffff', 'fontSize': '18px', 'fontWeight': '600'})
                        ], style={'textAlign': 'center', 'marginTop': '10px', 'marginBottom': '8px'}),
                        html.Div([
                            html.Span(id='max-power-label', children=f"Maximum: {MAX_POWER_KW} kW", style={'color': '#888', 'fontSize': '11px', 'fontWeight': '500'})
                        ], style={'textAlign': 'center'}),
                        html.Div(id='power-warning', children='')
                    ], className="card-dark", style={'padding': '15px', 'textAlign': 'center'})
                ], width=3)
            ], style={'marginTop': '20px', 'marginBottom': '30px'}),

            # Leistung über volle Breite
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.H5("LEISTUNG", style={'color': '#fff', 'fontSize': '16px', 'fontWeight': '600', 'margin': 0, 'letterSpacing': '1px'}),
                            dbc.Button("", id="expand-power", size="sm",
                                      style={'background': 'transparent', 'border': 'none', 'color': '#888', 'fontSize': '18px', 'padding': '0 8px'})
                        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '20px'}),
                        dcc.Graph(id='power-graph', config={'displayModeBar': False}, style={'height': '300px'})
                    ], className="card-dark", style={'padding': '25px'})
                ], width=12)
            ], style={'marginBottom': '20px'}),

            # Spannung und Strom in 2 Spalten
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.H5("SPANNUNG", style={'color': '#fff', 'fontSize': '16px', 'fontWeight': '600', 'margin': 0, 'letterSpacing': '1px'}),
                            dbc.Button("", id="expand-voltage", size="sm",
                                      style={'background': 'transparent', 'border': 'none', 'color': '#888', 'fontSize': '18px', 'padding': '0 8px'})
                        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '20px'}),
                        dcc.Graph(id='voltage-graph', config={'displayModeBar': False}, style={'height': '300px'})
                    ], className="card-dark", style={'padding': '25px'})
                ], width=6),
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.H5("STROM", style={'color': '#fff', 'fontSize': '16px', 'fontWeight': '600', 'margin': 0, 'letterSpacing': '1px'}),
                            dbc.Button("", id="expand-current", size="sm",
                                      style={'background': 'transparent', 'border': 'none', 'color': '#888', 'fontSize': '18px', 'padding': '0 8px'})
                        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '20px'}),
                        dcc.Graph(id='current-graph', config={'displayModeBar': False}, style={'height': '300px'})
                    ], className="card-dark", style={'padding': '25px'})
                ], width=6)
            ]),

            # Update-Intervall
            dcc.Interval(id='interval-component', interval=1000, n_intervals=0),

            # Interval für Unlock-Timer (jede Sekunde)
            dcc.Interval(id='unlock-timer-interval', interval=1000, n_intervals=0),

            # Bottom Statusbar
            html.Div([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Span("Verbindung: ", style={'color': '#666', 'marginRight': '8px'}),
                            html.Span(id='statusbar-connection', children="---", style={'color': '#00ddff', 'fontWeight': '600'})
                        ])
                    ], width=4),
                    dbc.Col([
                        html.Div([
                            html.Span("Health: ", style={'color': '#666', 'marginRight': '8px'}),
                            html.Span(id='statusbar-health', children="---", style={'color': '#00ff88', 'fontWeight': '600'})
                        ], style={'textAlign': 'center'})
                    ], width=4),
                    dbc.Col([
                        html.Div([
                            html.Span("Uptime: ", style={'color': '#666', 'marginRight': '8px'}),
                            html.Span(id='statusbar-uptime', children="---", style={'color': '#ff9800', 'fontWeight': '600'})
                        ], style={'textAlign': 'right'})
                    ], width=4)
                ])
            ], style={
                'position': 'fixed',
                'bottom': '0',
                'left': '0',
                'right': '0',
                'background': '#0f0f0f',
                'borderTop': '2px solid #2a2a2a',
                'padding': '12px 30px',
                'fontSize': '13px',
                'zIndex': '1000'
            })

        ], fluid=True, style={'padding': '20px', 'paddingBottom': '70px'})
    ])

dashboard_page = create_dashboard_page()

# Settings-Seite mit Tabs (Allgemein + Simulator + Administrator)
def create_settings_page():
    cfg = get_config_manager()
    return html.Div([
        navbar,
        dbc.Container([
            html.H2("EINSTELLUNGEN", className="neon-text", style={'marginTop': '30px', 'marginBottom': '30px'}),

            # Tabs für Einstellungen
            dbc.Tabs([
                # Tab 1: Allgemeine Einstellungen
                dbc.Tab([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.H4("Modbus Verbindung", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '20px', 'fontWeight': '600'}),

                                html.Div([
                                    html.Label("IP-Adresse", style={'color': '#666', 'fontSize': '13px', 'marginBottom': '8px', 'display': 'block'}),
                                    dbc.Input(id="modbus-ip", placeholder="192.168.1.100", value=cfg.get('modbus.ip', '192.168.1.100'),
                                             style={'background': '#0f0f0f', 'border': '1px solid #2a2a2a', 'color': '#00ddff', 'borderRadius': '8px', 'padding': '10px'})
                                ], style={'marginBottom': '20px'}),

                                html.Div([
                                    html.Label("Port", style={'color': '#666', 'fontSize': '13px', 'marginBottom': '8px', 'display': 'block'}),
                                    dbc.Input(id="modbus-port", placeholder="502", value=cfg.get('modbus.port', 502), type="number",
                                             style={'background': '#0f0f0f', 'border': '1px solid #2a2a2a', 'color': '#00ddff', 'borderRadius': '8px', 'padding': '10px'})
                                ], style={'marginBottom': '20px'}),

                                html.Div([
                                    html.Label("Unit ID", style={'color': '#666', 'fontSize': '13px', 'marginBottom': '8px', 'display': 'block'}),
                                    dbc.Input(id="modbus-unit", placeholder="1", value=cfg.get('modbus.unit_id', 1), type="number",
                                             style={'background': '#0f0f0f', 'border': '1px solid #2a2a2a', 'color': '#00ddff', 'borderRadius': '8px', 'padding': '10px'})
                                ], style={'marginBottom': '24px'}),

                                dbc.Button("Verbindung testen", id="test-connection-btn",
                                          style={'width': '100%', 'background': 'linear-gradient(135deg, #00ff88, #00ddff)', 'color': '#0a0a0a', 'border': 'none', 'fontWeight': '600', 'borderRadius': '8px', 'padding': '12px'}),

                                html.Div(id="connection-test-result", style={'marginTop': '15px'})

                            ], className="card-dark", style={'padding': '30px'})
                        ], width=6),

                        dbc.Col([
                            html.Div([
                                html.H4("Anzeigeoptionen", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '20px', 'fontWeight': '600'}),

                                html.Div([
                                    html.Label("Update-Intervall", style={'color': '#666', 'fontSize': '13px', 'marginBottom': '8px', 'display': 'block'}),
                                    dbc.Input(id="update-interval", placeholder="1000", value=cfg.get('update_interval_ms', 1000), type="number",
                                             style={'background': '#0f0f0f', 'border': '1px solid #2a2a2a', 'color': '#00ff88', 'borderRadius': '8px', 'padding': '10px'}),
                                    html.Small("Millisekunden", style={'color': '#555', 'fontSize': '11px'})
                                ], style={'marginBottom': '24px'}),

                                html.Div([
                                    html.Label("Graph-Historie", style={'color': '#666', 'fontSize': '13px', 'marginBottom': '8px', 'display': 'block'}),
                                    dbc.Input(id="graph-history", placeholder="60", value=cfg.get('graph_history_seconds', 60), type="number",
                                             style={'background': '#0f0f0f', 'border': '1px solid #2a2a2a', 'color': '#00ff88', 'borderRadius': '8px', 'padding': '10px'}),
                                    html.Small("Sekunden", style={'color': '#555', 'fontSize': '11px'})
                                ], style={'marginBottom': '24px'}),

                                html.Div([
                                    html.Label("Maximale Leistung", style={'color': '#666', 'fontSize': '13px', 'marginBottom': '8px', 'display': 'block'}),
                                    dbc.Input(id="max-power-input", placeholder="12.0", value=str(cfg.get('max_power_kw', MAX_POWER_KW)), type="number", step="0.1",
                                             style={'background': '#0f0f0f', 'border': '1px solid #2a2a2a', 'color': '#00ff88', 'borderRadius': '8px', 'padding': '10px'}),
                                    html.Small("Kilowatt (kW)", style={'color': '#555', 'fontSize': '11px'})
                                ], style={'marginBottom': '24px'}),

                                dbc.Button("Einstellungen übernehmen", id="apply-settings-btn",
                                          style={'width': '100%', 'background': 'linear-gradient(135deg, #00ff88, #00ddff)', 'color': '#0a0a0a', 'border': 'none', 'fontWeight': '600', 'borderRadius': '8px', 'padding': '12px', 'marginTop': '10px'}),

                                html.Div(id="settings-saved-msg", style={'marginTop': '15px'})

                            ], className="card-dark", style={'padding': '30px'})
                        ], width=6),
                    ], style={'marginTop': '20px'}),

                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.H4("System-Information", className="neon-cyan"),
                                html.Hr(style={'borderColor': '#333'}),
                                html.P(f"Simulator Modus: {'Aktiv' if SIMULATOR_MODE else 'Inaktiv'}", className="neon-text", id="system-info-simulator"),
                                html.P(f"Modbus IP: {cfg.get('modbus.ip', '192.168.1.100')}:{cfg.get('modbus.port', 502)}", className="neon-text"),
                                html.P(f"Gestartet: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", className="neon-text"),
                                html.P("Version: 1.0.0", className="neon-text"),
                            ], className="card-dark", style={'padding': '30px', 'marginTop': '30px'})
                        ], width=12)
                    ]),

                    # Log-Fenster (Normal-Level)
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.H4("System-Log", className="neon-cyan"),
                                html.Hr(style={'borderColor': '#333'}),
                                html.Div(id='normal-log-display', children=[], style={
                                    'background': '#000',
                                    'border': '1px solid #333',
                                    'borderRadius': '8px',
                                    'padding': '15px',
                                    'height': '300px',
                                    'overflowY': 'scroll',
                                    'fontFamily': 'Courier New, monospace',
                                    'fontSize': '12px',
                                    'color': '#00ddff'
                                })
                            ], className="card-dark", style={'padding': '30px', 'marginTop': '30px'})
                        ], width=12)
                    ])
                ], label="Allgemein", tab_id="tab-general"),

                # Tab 2: Simulator Modus
                dbc.Tab([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.H4("Simulator Modus", style={'color': '#FFC107', 'fontSize': '16px', 'marginBottom': '20px', 'fontWeight': '600'}),
                                html.P("Der Simulator Modus simuliert Messwerte wenn keine echte Modbus-Verbindung besteht.", style={'color': '#888', 'marginBottom': '20px'}),
                                html.P("Hinweis: Dieser Modus wird beim Neustart automatisch deaktiviert.", style={'color': '#666', 'marginBottom': '20px', 'fontSize': '12px'}),

                                html.Div([
                                    html.Label("Simulator Modus aktivieren", style={'color': '#666', 'fontSize': '13px', 'marginBottom': '12px', 'display': 'block'}),
                                    daq.ToggleSwitch(
                                        id='simulator-toggle',
                                        value=SIMULATOR_MODE,
                                        color='#FFC107'
                                    ),
                                    html.Div(id='simulator-status', style={'marginTop': '10px', 'color': '#FFC107' if SIMULATOR_MODE else '#888'})
                                ], style={'marginBottom': '24px'}),

                                html.Div(id="simulator-save-result", style={'marginTop': '15px'})

                            ], className="card-dark", style={'padding': '30px', 'border': '1px solid #FFC107'})
                        ], width=6),

                        dbc.Col([
                            html.Div([
                                html.H4("Simulator Status", style={'color': '#FFC107', 'fontSize': '16px', 'marginBottom': '20px', 'fontWeight': '600'}),

                                html.Div([
                                    html.P("Aktueller Status:", style={'color': '#666', 'marginBottom': '10px'}),
                                    html.H3("AKTIV" if SIMULATOR_MODE else "INAKTIV",
                                           style={'color': '#FFC107' if SIMULATOR_MODE else '#888', 'fontWeight': '600'}),
                                ], style={'marginBottom': '24px', 'textAlign': 'center'}),

                                html.Div([
                                    html.P("Beschreibung:", style={'color': '#666', 'marginBottom': '10px'}),
                                    html.Ul([
                                        html.Li("Simulierte Spannungswerte: 210-240V", style={'color': '#888', 'fontSize': '13px'}),
                                        html.Li("Simulierte Stromwerte: 0-20A", style={'color': '#888', 'fontSize': '13px'}),
                                        html.Li("Simulierte Frequenz: 49.8-50.2Hz", style={'color': '#888', 'fontSize': '13px'}),
                                        html.Li("Werte ändern sich mit max. 10% pro Update", style={'color': '#888', 'fontSize': '13px'}),
                                    ])
                                ])

                            ], className="card-dark", style={'padding': '30px', 'border': '1px solid #FFC107'})
                        ], width=6),
                    ], style={'marginTop': '20px'}),
                ], label="Simulator", tab_id="tab-simulator", label_style={'color': '#FFC107'}),

                # Tab 3: Administrator-Einstellungen (Hypervisor)
                dbc.Tab([
                    html.Div([
                        # Passwort-Eingabe für Admin-Tab
                        html.Div(id="admin-tab-locked", children=[
                            html.Div([
                                html.H4("Administrator-Bereich", style={'color': '#ff4444', 'marginBottom': '20px'}),
                                html.P("Dieser Bereich erfordert das Hypervisor-Passwort.", style={'color': '#888', 'marginBottom': '20px'}),
                                dbc.Input(id="admin-password-input", type="password", placeholder="Hypervisor-Passwort eingeben", className="password-input", style={'maxWidth': '300px', 'margin': '0 auto'}),
                                html.Div(id="admin-password-error", style={'color': '#ff4444', 'marginTop': '10px', 'textAlign': 'center'}),
                                dbc.Button("Entsperren", id="admin-unlock-btn", color="danger", style={'marginTop': '20px'})
                            ], style={'textAlign': 'center', 'padding': '50px'})
                        ], className="card-dark", style={'padding': '30px', 'marginTop': '20px'}),

                        # Admin-Inhalt (versteckt bis Passwort korrekt)
                        html.Div(id="admin-tab-content", children=[
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        html.H4("Passwort-Verwaltung", style={'color': '#ff4444', 'fontSize': '16px', 'marginBottom': '20px', 'fontWeight': '600'}),

                                        html.Div([
                                            html.Label("Allgemeines Passwort", style={'color': '#666', 'fontSize': '13px', 'marginBottom': '8px', 'display': 'block'}),
                                            dbc.Input(id="general-password-new", type="password", placeholder="Neues allgemeines Passwort",
                                                     style={'background': '#0f0f0f', 'border': '1px solid #2a2a2a', 'color': '#ff8888', 'borderRadius': '8px', 'padding': '10px'}),
                                            html.Small("Für Einstellungen und Koppelschalter", style={'color': '#555', 'fontSize': '11px'})
                                        ], style={'marginBottom': '24px'}),

                                        html.Div([
                                            html.Label("Hypervisor-Passwort", style={'color': '#666', 'fontSize': '13px', 'marginBottom': '8px', 'display': 'block'}),
                                            dbc.Input(id="hypervisor-password-new", type="password", placeholder="Neues Hypervisor-Passwort",
                                                     style={'background': '#0f0f0f', 'border': '1px solid #2a2a2a', 'color': '#ff8888', 'borderRadius': '8px', 'padding': '10px'}),
                                            html.Small("Für Administrator-Bereich", style={'color': '#555', 'fontSize': '11px'})
                                        ], style={'marginBottom': '24px'}),

                                        dbc.Button("Passwörter speichern", id="save-passwords-btn",
                                                  style={'width': '100%', 'background': 'linear-gradient(135deg, #ff4444, #cc0000)', 'color': '#fff', 'border': 'none', 'fontWeight': '600', 'borderRadius': '8px', 'padding': '12px'}),
                                        html.Div(id="password-save-result", style={'marginTop': '15px'})
                                    ], className="card-dark", style={'padding': '30px', 'border': '1px solid #ff4444'})
                                ], width=6),

                                dbc.Col([
                                    html.Div([
                                        html.H4("Schalter-Einstellungen", style={'color': '#ff4444', 'fontSize': '16px', 'marginBottom': '20px', 'fontWeight': '600'}),

                                        html.Div([
                                            html.Label("Koppelschalter-Freischaltdauer", style={'color': '#666', 'fontSize': '13px', 'marginBottom': '8px', 'display': 'block'}),
                                            dbc.Input(id="coupling-timeout-input", type="number", value=cfg.get('coupling_unlock_timeout', 30), min=5, max=300,
                                                     style={'background': '#0f0f0f', 'border': '1px solid #2a2a2a', 'color': '#ff8888', 'borderRadius': '8px', 'padding': '10px'}),
                                            html.Small("Sekunden (5-300)", style={'color': '#555', 'fontSize': '11px'})
                                        ], style={'marginBottom': '24px'}),

                                        html.Div([
                                            html.Label("Modbus Verbindungs-Timeout", style={'color': '#666', 'fontSize': '13px', 'marginBottom': '8px', 'display': 'block'}),
                                            dbc.Input(id="modbus-timeout", type="number", value=cfg.get('modbus_timeout', 30), min=5, max=120,
                                                     style={'background': '#0f0f0f', 'border': '1px solid #2a2a2a', 'color': '#ff8888', 'borderRadius': '8px', 'padding': '10px'}),
                                            html.Small("Sekunden (5-120)", style={'color': '#555', 'fontSize': '11px'})
                                        ], style={'marginBottom': '24px'}),

                                        dbc.Button("Admin-Einstellungen speichern", id="save-admin-settings-btn",
                                                  style={'width': '100%', 'background': 'linear-gradient(135deg, #ff4444, #cc0000)', 'color': '#fff', 'border': 'none', 'fontWeight': '600', 'borderRadius': '8px', 'padding': '12px'}),
                                        html.Div(id="admin-settings-save-result", style={'marginTop': '15px'})
                                    ], className="card-dark", style={'padding': '30px', 'border': '1px solid #ff4444'})
                                ], width=6),
                            ], style={'marginTop': '20px'}),

                            # Koppelschalter BA/DI Status
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        html.H4("Koppelschalter Status (BA/DI)", style={'color': '#ff4444', 'fontSize': '16px', 'marginBottom': '20px', 'fontWeight': '600'}),
                                        html.Div([
                                            html.Div([
                                                html.Span("Befehl (BA1): ", style={'color': '#666', 'fontSize': '14px', 'marginRight': '10px'}),
                                                html.Span(id='admin-coupling-ba-status', children="---", style={'color': '#00ddff', 'fontSize': '16px', 'fontWeight': '700'})
                                            ], style={'marginBottom': '15px'}),
                                            html.Div([
                                                html.Span("Rückmeldung (DI1): ", style={'color': '#666', 'fontSize': '14px', 'marginRight': '10px'}),
                                                html.Span(id='admin-coupling-di-status', children="---", style={'color': '#00ff88', 'fontSize': '16px', 'fontWeight': '700'})
                                            ])
                                        ])
                                    ], className="card-dark", style={'padding': '30px', 'border': '1px solid #ff4444'})
                                ], width=12)
                            ], style={'marginTop': '20px'}),

                            # Log-Fenster (Debug-Level)
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        html.H4("System-Log (Debug-Level)", style={'color': '#ff4444', 'fontSize': '16px', 'marginBottom': '20px', 'fontWeight': '600'}),
                                        html.Div(id='admin-log-display', children=[], style={
                                            'background': '#000',
                                            'border': '1px solid #333',
                                            'borderRadius': '8px',
                                            'padding': '15px',
                                            'height': '400px',
                                            'overflowY': 'scroll',
                                            'fontFamily': 'Courier New, monospace',
                                            'fontSize': '12px',
                                            'color': '#00ff88'
                                        })
                                    ], className="card-dark", style={'padding': '30px', 'border': '1px solid #ff4444'})
                                ], width=12)
                            ], style={'marginTop': '20px'})
                        ], style={'display': 'none'})
                    ])
                ], label="Administrator", tab_id="tab-admin", label_style={'color': '#ff4444'})
            ], id="settings-tabs", active_tab="tab-general"),

        ], fluid=True, style={'padding': '20px'})
    ])

# Settings-Seite mit Passwort-Schutz
def create_settings_login_page():
    return html.Div([
        navbar,
        dbc.Container([
            html.Div([
                html.H2("EINSTELLUNGEN", className="neon-text", style={'marginTop': '30px', 'marginBottom': '30px'}),
                html.Div([
                    html.H4("Zugriff geschützt", style={'color': '#ff4444', 'marginBottom': '20px'}),
                    html.P("Bitte geben Sie das Passwort ein, um die Einstellungen zu öffnen.", style={'color': '#888', 'marginBottom': '20px'}),
                    dbc.Input(id="settings-password-input", type="password", placeholder="Passwort eingeben", className="password-input", style={'maxWidth': '300px', 'margin': '0 auto 20px auto'}),
                    html.Div(id="settings-password-error", style={'color': '#ff4444', 'marginTop': '10px', 'textAlign': 'center', 'marginBottom': '20px'}),
                    dbc.Button("Entsperren", id="settings-unlock-btn", color="success", style={'marginTop': '10px'})
                ], className="card-dark", style={'padding': '50px', 'textAlign': 'center'})
            ])
        ], fluid=True, style={'padding': '20px'})
    ])

# Layout mit URL-Routing
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content'),
    dcc.Interval(id='startup-interval', interval=500, n_intervals=0, max_intervals=12),
    dcc.Store(id='max-power-store', data=config.get('max_power_kw', MAX_POWER_KW)),
    dcc.Store(id='update-interval-store', data=config.get('update_interval_ms', 1000)),
    dcc.Store(id='startup-step', data=0),
    dcc.Store(id='settings-authenticated', data=False),
    dcc.Store(id='simulator-mode-store', data=SIMULATOR_MODE),
    # Stores für Koppelschalter (global, damit Callbacks funktionieren)
    dcc.Store(id='coupling-unlock-timestamp', data=0),
    dcc.Store(id='coupling-timeout-store', data=config.get('coupling_unlock_timeout', 30)),
    dcc.Store(id='admin-unlocked', data=False),
    # Modals für Graph-Expansion
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id="modal-title")),
        dbc.ModalBody(
            dcc.Graph(
                id='modal-graph',
                figure=go.Figure(),
                config={'displayModeBar': True},
                style={'height': '70vh'}
            )
        ),
    ], id="graph-modal", size="xl", is_open=False, centered=True)
])

# Routing Callback
@app.callback(Output('page-content', 'children'),
              Input('url', 'pathname'),
              Input('startup-interval', 'n_intervals'),
              Input('settings-authenticated', 'data'))
def display_page(pathname, n_intervals, settings_auth):
    if n_intervals < 12 and pathname == '/':
        return startup_screen
    elif pathname == '/settings':
        if settings_auth:
            return create_settings_page()
        else:
            return create_settings_login_page()
    else:
        return create_dashboard_page()

# Settings Authentication Callback
@app.callback(
    [Output('settings-authenticated', 'data'),
     Output('settings-password-error', 'children')],
    [Input('settings-unlock-btn', 'n_clicks')],
    [State('settings-password-input', 'value')],
    prevent_initial_call=True
)
def authenticate_settings(n_clicks, password):
    if n_clicks:
        cfg = get_config_manager()
        general_password = cfg.get('passwords.general', '2023')
        hypervisor_password = cfg.get('passwords.hypervisor', '202320')

        # Beide Passwörter akzeptieren
        if password == general_password or password == hypervisor_password:
            return True, ""
        else:
            return False, "Falsches Passwort!"
    return False, ""

# Admin Tab Unlock Callback
@app.callback(
    [Output('admin-unlocked', 'data'),
     Output('admin-tab-locked', 'style'),
     Output('admin-tab-content', 'style'),
     Output('admin-password-error', 'children')],
    [Input('admin-unlock-btn', 'n_clicks')],
    [State('admin-password-input', 'value'),
     State('admin-unlocked', 'data')],
    prevent_initial_call=True
)
def unlock_admin_tab(n_clicks, password, already_unlocked):
    if already_unlocked:
        return True, {'display': 'none'}, {'display': 'block'}, ""

    if n_clicks:
        cfg = get_config_manager()
        correct_password = cfg.get('passwords.hypervisor', '202320')
        if password == correct_password:
            return True, {'display': 'none'}, {'display': 'block'}, ""
        else:
            return False, {'display': 'block'}, {'display': 'none'}, "Falsches Hypervisor-Passwort!"
    return False, {'display': 'block'}, {'display': 'none'}, ""

# Save Passwords Callback
@app.callback(
    Output('password-save-result', 'children'),
    [Input('save-passwords-btn', 'n_clicks')],
    [State('general-password-new', 'value'),
     State('hypervisor-password-new', 'value')],
    prevent_initial_call=True
)
def save_passwords(n_clicks, general_pw, hypervisor_pw):
    if n_clicks:
        cfg = get_config_manager()
        saved = False

        if general_pw and len(general_pw) >= 4:
            cfg.set('passwords.general', general_pw)
            saved = True

        if hypervisor_pw and len(hypervisor_pw) >= 4:
            cfg.set('passwords.hypervisor', hypervisor_pw)
            saved = True

        if saved:
            return html.Div("Passwörter erfolgreich gespeichert!",
                          style={'color': '#00ff88', 'padding': '10px', 'background': 'rgba(0,255,136,0.1)', 'borderRadius': '6px'})
        else:
            return html.Div("Passwörter müssen mindestens 4 Zeichen haben!",
                          style={'color': '#ff4444', 'padding': '10px', 'background': 'rgba(255,68,68,0.1)', 'borderRadius': '6px'})
    return ""

# Save Admin Settings (inkl. Schalter-Timeout)
@app.callback(
    Output('admin-settings-save-result', 'children'),
    [Input('save-admin-settings-btn', 'n_clicks')],
    [State('coupling-timeout-input', 'value'),
     State('modbus-timeout', 'value')],
    prevent_initial_call=True
)
def save_admin_settings(n_clicks, coupling_timeout, modbus_timeout):
    if n_clicks:
        cfg = get_config_manager()

        if coupling_timeout and 5 <= int(coupling_timeout) <= 300:
            cfg.set('coupling_unlock_timeout', int(coupling_timeout))

        if modbus_timeout and 5 <= int(modbus_timeout) <= 120:
            cfg.set('modbus_timeout', int(modbus_timeout))

        return html.Div("Admin-Einstellungen gespeichert!",
                      style={'color': '#00ff88', 'padding': '10px', 'background': 'rgba(0,255,136,0.1)', 'borderRadius': '6px'})
    return ""

# Simulator Toggle Callback
@app.callback(
    [Output('simulator-mode-store', 'data'),
     Output('simulator-status', 'children')],
    [Input('simulator-toggle', 'value')],
    prevent_initial_call=True
)
def toggle_simulator_mode(value):
    global SIMULATOR_MODE, mra4

    SIMULATOR_MODE = value

    # Modbus Client neu initialisieren
    try:
        mra4.disconnect()
    except:
        pass

    mra4 = init_modbus_client()

    status_text = "Simulator Modus aktiviert - Simulierte Werte werden angezeigt" if value else "Simulator Modus deaktiviert - Echte Modbus-Verbindung"
    return value, status_text

# Coupling Switch - Passwort-Modal öffnen
@app.callback(
    Output('coupling-password-modal', 'is_open'),
    [Input('coupling-unlock-btn', 'n_clicks'),
     Input('coupling-password-confirm', 'n_clicks'),
     Input('coupling-password-cancel', 'n_clicks')],
    [State('coupling-password-modal', 'is_open')],
    prevent_initial_call=True
)
def toggle_coupling_modal(unlock_clicks, confirm_clicks, cancel_clicks, is_open):
    ctx = callback_context
    if not ctx.triggered:
        return False

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'coupling-unlock-btn':
        return True
    elif trigger_id in ['coupling-password-confirm', 'coupling-password-cancel']:
        return False

    return is_open

# Coupling Timeout Info aktualisieren
@app.callback(
    Output('coupling-timeout-info', 'children'),
    [Input('coupling-password-modal', 'is_open')]
)
def update_coupling_timeout_info(is_open):
    cfg = get_config_manager()
    timeout = cfg.get('coupling_unlock_timeout', 30)
    return f"Nach erfolgreicher Eingabe ist der Schalter für {timeout} Sekunden bedienbar."

# Coupling Switch - Passwort prüfen und freischalten
@app.callback(
    [Output('coupling-unlock-timestamp', 'data'),
     Output('coupling-password-error', 'children'),
     Output('coupling-password-input', 'value'),
     Output('coupling-timeout-store', 'data')],
    [Input('coupling-password-confirm', 'n_clicks')],
    [State('coupling-password-input', 'value')],
    prevent_initial_call=True
)
def verify_coupling_password(n_clicks, password):
    if n_clicks:
        cfg = get_config_manager()
        correct_password = cfg.get('passwords.general', '2023')
        timeout = cfg.get('coupling_unlock_timeout', 30)

        if password == correct_password:
            # Passwort korrekt - Zeitstempel setzen
            unlock_time = time.time()
            return unlock_time, "", "", timeout
        else:
            return 0, "Falsches Passwort!", "", timeout

    return 0, "", "", 30

# Coupling Switch - Status und Aktivierung basierend auf Timer
@app.callback(
    [Output('coupling-switch', 'disabled'),
     Output('coupling-unlock-status', 'children'),
     Output('coupling-unlock-btn', 'children'),
     Output('coupling-unlock-btn', 'color')],
    [Input('unlock-timer-interval', 'n_intervals')],
    [State('coupling-unlock-timestamp', 'data'),
     State('coupling-timeout-store', 'data')]
)
def update_coupling_unlock_status(n_intervals, unlock_timestamp, timeout):
    if timeout is None:
        timeout = config.get('coupling_unlock_timeout', 30)

    if unlock_timestamp and unlock_timestamp > 0:
        elapsed = time.time() - unlock_timestamp
        remaining = timeout - elapsed

        if remaining > 0:
            # Noch freigeschaltet
            status = html.Div([
                html.Span(f"Freigeschaltet ({int(remaining)}s)", style={'color': '#00ff88', 'fontWeight': '600'})
            ], className="unlocked-indicator")
            return False, status, f"Aktiv ({int(remaining)}s)", "success"
        else:
            # Abgelaufen
            return True, [], "Freischalten", "warning"

    return True, [], "Freischalten", "warning"

# Coupling Switch - Schalten und Status aktualisieren
@app.callback(
    Output('coupling-switch', 'on'),
    [Input('coupling-switch', 'on'),
     Input('interval-component', 'n_intervals')],
    [State('coupling-unlock-timestamp', 'data'),
     State('coupling-timeout-store', 'data')],
    prevent_initial_call=False
)
def update_coupling_switch(button_pressed, n, unlock_timestamp, timeout):
    ctx = callback_context
    if timeout is None:
        timeout = config.get('coupling_unlock_timeout', 30)

    # Daten vom MRA4 lesen
    data = mra4.read_all_data()
    di_status = data.get('di_status', False)

    # Prüfen welcher Input den Callback ausgelöst hat
    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if trigger_id == 'coupling-switch':
            # Button wurde gedrückt - nur bei Zustandsänderung zu EIN
            if button_pressed:
                # Prüfen ob freigeschaltet
                if unlock_timestamp and unlock_timestamp > 0:
                    elapsed = time.time() - unlock_timestamp
                    if elapsed < timeout:
                        # 2-Sekunden-Impuls in separatem Thread senden
                        import threading
                        def send_pulse():
                            success = mra4.send_coupling_pulse(duration=2.0)
                            if success:
                                app_logger.info("Koppelschalter 2s-Impuls gesendet")
                            else:
                                app_logger.error("Fehler beim Senden des Koppelschalter-Impulses")

                        thread = threading.Thread(target=send_pulse, daemon=True)
                        thread.start()

    # Schalter-Status folgt immer DI 1 (Rückmeldung)
    return di_status


# Störschrieb-Schalter (Leittechnik-Befehl 3)
@app.callback(
    Output('fault-recording-switch', 'on'),
    [Input('fault-recording-switch', 'on'),
     Input('interval-component', 'n_intervals')],
    prevent_initial_call=False
)
def update_fault_recording_switch(button_pressed, n):
    ctx = callback_context

    # Prüfen welcher Input den Callback ausgelöst hat
    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if trigger_id == 'fault-recording-switch':
            # Button wurde gedrückt - Leittechnik-Befehl 3 schalten
            success = mra4.write_fault_recording_trigger(button_pressed)
            if success:
                app_logger.info(f"Störschrieb-Trigger auf {'EIN' if button_pressed else 'AUS'} gesetzt")
            else:
                app_logger.error("Fehler beim Setzen des Störschrieb-Triggers")
            return button_pressed

    # Interval-Update: Status vom Gerät lesen
    try:
        status = mra4.read_fault_recording_status()
        return status if status is not None else False
    except:
        return False


# Daten-Update Callback
@app.callback(
    [Output('voltage-l1', 'children'),
     Output('voltage-l2', 'children'),
     Output('voltage-l3', 'children'),
     Output('current-l1', 'children'),
     Output('current-l2', 'children'),
     Output('current-l3', 'children'),
     Output('power-l1', 'children'),
     Output('power-l2', 'children'),
     Output('power-l3', 'children'),
     Output('power-total', 'children'),
     Output('power-gauge-total', 'value'),
     Output('power-gauge-total', 'color'),
     Output('frequency-display', 'children'),
     Output('connection-status', 'children'),
     Output('voltage-graph', 'figure'),
     Output('current-graph', 'figure'),
     Output('power-graph', 'figure'),
     Output('power-warning', 'children')],
    [Input('interval-component', 'n_intervals')],
    [State('max-power-store', 'data')]
)
def update_metrics(n, max_power_from_store):
    # Daten vom MRA4 lesen
    data = mra4.read_all_data()

    # Zeitstempel hinzufügen
    current_time = datetime.now().strftime('%H:%M:%S')
    time_data.append(current_time)

    # Daten zu Buffer hinzufügen
    for phase in ['L1', 'L2', 'L3']:
        voltage_data[phase].append(data['voltage'][phase] or 0)
        current_data[phase].append(data['current'][phase] or 0)
        power_data[phase].append((data['power'][phase] or 0) / 1000)  # Convert W to kW
    power_data['total'].append((data['power']['total'] or 0) / 1000)  # Convert W to kW

    # Spannungs-Graph
    voltage_fig = go.Figure()
    voltage_fig.add_trace(go.Scatter(x=list(time_data), y=list(voltage_data['L1']),
                                     name='L1', line=dict(color='#4CAF50', width=2, shape='spline'), mode='lines'))
    voltage_fig.add_trace(go.Scatter(x=list(time_data), y=list(voltage_data['L2']),
                                     name='L2', line=dict(color='#2196F3', width=2, shape='spline'), mode='lines'))
    voltage_fig.add_trace(go.Scatter(x=list(time_data), y=list(voltage_data['L3']),
                                     name='L3', line=dict(color='#FF9800', width=2, shape='spline'), mode='lines'))
    voltage_fig.update_layout(
        paper_bgcolor='#1a1a1a',
        plot_bgcolor='#0f0f0f',
        font=dict(color='#888', size=11),
        xaxis=dict(showgrid=True, gridcolor='#222', title=''),
        yaxis=dict(showgrid=True, gridcolor='#222', title='V'),
        margin=dict(l=40, r=10, t=10, b=30),
        legend=dict(x=0.02, y=0.98, bgcolor='rgba(0,0,0,0.7)', font=dict(size=10)),
        showlegend=True
    )

    # Strom-Graph
    current_fig = go.Figure()
    current_fig.add_trace(go.Scatter(x=list(time_data), y=list(current_data['L1']),
                                     name='L1', line=dict(color='#4CAF50', width=2, shape='spline'), mode='lines'))
    current_fig.add_trace(go.Scatter(x=list(time_data), y=list(current_data['L2']),
                                     name='L2', line=dict(color='#2196F3', width=2, shape='spline'), mode='lines'))
    current_fig.add_trace(go.Scatter(x=list(time_data), y=list(current_data['L3']),
                                     name='L3', line=dict(color='#FF9800', width=2, shape='spline'), mode='lines'))
    current_fig.update_layout(
        paper_bgcolor='#1a1a1a',
        plot_bgcolor='#0f0f0f',
        font=dict(color='#888', size=11),
        xaxis=dict(showgrid=True, gridcolor='#222', title=''),
        yaxis=dict(showgrid=True, gridcolor='#222', title='A'),
        margin=dict(l=40, r=10, t=10, b=30),
        legend=dict(x=0.02, y=0.98, bgcolor='rgba(0,0,0,0.7)', font=dict(size=10)),
        showlegend=True
    )

    # Leistungs-Graph
    power_fig = go.Figure()
    power_fig.add_trace(go.Scatter(x=list(time_data), y=list(power_data['L1']),
                                   name='L1', line=dict(color='#4CAF50', width=2, shape='spline'), mode='lines'))
    power_fig.add_trace(go.Scatter(x=list(time_data), y=list(power_data['L2']),
                                   name='L2', line=dict(color='#2196F3', width=2, shape='spline'), mode='lines'))
    power_fig.add_trace(go.Scatter(x=list(time_data), y=list(power_data['L3']),
                                   name='L3', line=dict(color='#FF9800', width=2, shape='spline'), mode='lines'))
    power_fig.add_trace(go.Scatter(x=list(time_data), y=list(power_data['total']),
                                   name='S', line=dict(color='#FFC107', width=2.5, shape='spline'), mode='lines'))
    power_fig.update_layout(
        paper_bgcolor='#1a1a1a',
        plot_bgcolor='#0f0f0f',
        font=dict(color='#888', size=11),
        xaxis=dict(showgrid=True, gridcolor='#222', title=''),
        yaxis=dict(showgrid=True, gridcolor='#222', title='kW'),
        margin=dict(l=40, r=10, t=10, b=30),
        legend=dict(x=0.02, y=0.98, bgcolor='rgba(0,0,0,0.7)', font=dict(size=10)),
        showlegend=True
    )

    # Status-Texte
    freq_text = f"{data['frequency']:.1f} Hz" if data['frequency'] else "-- Hz"
    status_text = "SIMULATOR" if SIMULATOR_MODE else ("ONLINE" if mra4.connected else "OFFLINE")

    # Warnung bei 90% Leistung und Gauge-Farbe
    total_power_kw = (data['power']['total'] or 0) / 1000
    max_power = max_power_from_store if max_power_from_store else MAX_POWER_KW
    power_percentage = (total_power_kw / max_power) * 100 if max_power > 0 else 0

    # Dynamische Gauge-Farbe basierend auf Prozentsatz
    if power_percentage < 50:
        gauge_color = "#4CAF50"  # Grün (0-50%)
    elif power_percentage < 80:
        gauge_color = "#FF9800"  # Orange (50-80%)
    else:
        gauge_color = "#F44336"  # Rot (80-100%)

    warning_msg = ''
    if power_percentage >= 90:
        warning_msg = html.Div([
            html.Span("! ", style={'fontSize': '20px', 'marginRight': '8px'}),
            html.Span(f"WARNUNG: Leistung bei {power_percentage:.0f}%!",
                     style={'fontSize': '14px', 'fontWeight': '600', 'color': '#FF9800'})
        ], style={
            'padding': '12px 20px',
            'background': 'rgba(255, 152, 0, 0.2)',
            'border': '2px solid #FF9800',
            'borderRadius': '6px',
            'marginTop': '15px',
            'textAlign': 'center',
            'animation': 'blink 1s ease-in-out infinite'
        })

    return (
        f"{data['voltage']['L1'] or 0:.1f} V",
        f"{data['voltage']['L2'] or 0:.1f} V",
        f"{data['voltage']['L3'] or 0:.1f} V",
        f"{data['current']['L1'] or 0:.2f} A",
        f"{data['current']['L2'] or 0:.2f} A",
        f"{data['current']['L3'] or 0:.2f} A",
        f"{(data['power']['L1'] or 0) / 1000:.2f} kW",
        f"{(data['power']['L2'] or 0) / 1000:.2f} kW",
        f"{(data['power']['L3'] or 0) / 1000:.2f} kW",
        f"{(data['power']['total'] or 0) / 1000:.2f} kW",
        total_power_kw,
        gauge_color,
        freq_text,
        status_text,
        voltage_fig,
        current_fig,
        power_fig,
        warning_msg
    )

# Schutz-Status, DI Status und Quittier-Button Update
@app.callback(
    [Output('coupling-di-status', 'children'),
     Output('protection-status-text', 'children'),
     Output('protection-status-text', 'style'),
     Output('cot-display', 'children'),
     Output('fault-number-display', 'children'),
     Output('acknowledge-section', 'children')],
    [Input('interval-component', 'n_intervals')],
    prevent_initial_call=False
)
def update_protection_and_di_status(n):
    # Daten vom MRA4 lesen
    data = mra4.read_all_data()

    # DI Status (Digitaler Eingang für Koppelschalter-Rückmeldung)
    di_status = data.get('di_status', False)
    di_status_text = "EIN" if di_status else "AUS"
    di_status_color = '#00ff88' if di_status else '#ff4444'

    # Schutz-Status
    prot_status = data.get('protection_status', {})
    aktiv = prot_status.get('aktiv', False)
    alarm = prot_status.get('alarm', False)
    ausl = prot_status.get('ausl', False)

    # Status Text und Farbe
    if ausl:
        status_text = "AUSGELÖST"
        status_color = '#ff4444'
        status_bg = 'rgba(255, 68, 68, 0.2)'
    elif alarm:
        status_text = "ALARM"
        status_color = '#ff9800'
        status_bg = 'rgba(255, 152, 0, 0.2)'
    elif aktiv:
        status_text = "AKTIV"
        status_color = '#00ff88'
        status_bg = 'rgba(0, 255, 136, 0.1)'
    else:
        status_text = "INAKTIV"
        status_color = '#888'
        status_bg = 'transparent'

    status_style = {
        'color': status_color,
        'fontWeight': '700',
        'fontSize': '16px',
        'padding': '8px 16px',
        'background': status_bg,
        'borderRadius': '4px',
        'display': 'inline-block'
    }

    # COT Code und Beschreibung
    cot_code = data.get('cause_of_trip', 0)
    cot_description = COT_CODES.get(cot_code, f"Unbekannt ({cot_code})")

    if cot_code == 0 or cot_code == 1:
        # COT 0 oder 1 = NORM (kein Fehler) - GRÜN anzeigen
        cot_display = html.Div([
            html.Span("✓ FEHLERFREI", style={'color': '#00ff88', 'fontWeight': '700', 'fontSize': '16px'})
        ], style={
            'padding': '12px',
            'background': 'rgba(0, 255, 136, 0.15)',
            'border': '2px solid #00ff88',
            'borderRadius': '6px',
            'textAlign': 'center'
        })
    else:
        cot_display = html.Div([
            html.Div([
                html.Span("Code: ", style={'color': '#888'}),
                html.Span(f"{cot_code}", style={'color': '#ff9800', 'fontWeight': '700', 'fontSize': '18px'})
            ], style={'marginBottom': '8px'}),
            html.Div([
                html.Span("Ursache: ", style={'color': '#888'}),
                html.Span(cot_description, style={'color': '#fff', 'fontWeight': '600'})
            ])
        ], style={
            'padding': '12px',
            'background': 'rgba(255, 152, 0, 0.15)',
            'border': '2px solid #ff9800',
            'borderRadius': '6px'
        })

    # Störfall-Nummer
    fault_number = data.get('fault_number', 0)
    if fault_number > 0:
        fault_display = html.Span(f"Störfall-Nr: {fault_number}",
                                  style={'color': '#ff9800', 'fontWeight': '600', 'marginLeft': '12px'})
    else:
        fault_display = ""

    # Quittier-Button (nur anzeigen wenn ausgelöst)
    if ausl:
        acknowledge_section = html.Div([
            dbc.Button(
                "QUITTIEREN",
                id='acknowledge-btn',
                color='danger',
                size='lg',
                style={
                    'width': '100%',
                    'fontWeight': '700',
                    'fontSize': '16px',
                    'padding': '12px',
                    'marginTop': '12px',
                    'animation': 'pulse 2s ease-in-out infinite'
                }
            )
        ])
    else:
        acknowledge_section = html.Div()

    return (
        html.Span(di_status_text, style={'color': di_status_color, 'fontWeight': '700'}),
        status_text,
        status_style,
        cot_display,
        fault_display,
        acknowledge_section
    )

# Quittier-Button Callback
@app.callback(
    Output('acknowledge-btn', 'children'),
    [Input('acknowledge-btn', 'n_clicks')],
    prevent_initial_call=True
)
def acknowledge_trip(n_clicks):
    if n_clicks:
        # ALLE Quittierungen durchführen (Register 22000-22005)
        success = mra4.acknowledge_all()
        if success:
            app_logger.info("Alle Quittierungen erfolgreich durchgeführt")
            return "QUITTIERT ✓"
        else:
            app_logger.error("Fehler bei Quittierung")
            return "FEHLER!"
    return "QUITTIEREN"

# Bottom Statusbar Update
@app.callback(
    [Output('statusbar-connection', 'children'),
     Output('statusbar-connection', 'style'),
     Output('statusbar-health', 'children'),
     Output('statusbar-health', 'style'),
     Output('statusbar-uptime', 'children')],
    [Input('interval-component', 'n_intervals')],
    prevent_initial_call=False
)
def update_statusbar(n):
    try:
        cfg = get_config_manager()

        # Verbindungsstatus - zeige sowohl Webserver als auch Modbus
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except:
            local_ip = "localhost"

        web_port = 8050
        modbus_ip = cfg.get('modbus.ip', '192.168.1.100')
        modbus_port = cfg.get('modbus.port', 502)

        if SIMULATOR_MODE:
            conn_text = f"Web: {local_ip}:{web_port} | Modbus: SIMULATOR"
            conn_color = '#ff9800'
            health_text = "SIMULATOR OK"
            health_color = '#ff9800'
        elif mra4.connected:
            conn_text = f"Web: {local_ip}:{web_port} | Modbus: {modbus_ip}:{modbus_port}"
            conn_color = '#00ddff'
            health_text = "ONLINE"
            health_color = '#00ff88'
        else:
            conn_text = f"Web: {local_ip}:{web_port} | Modbus: OFFLINE"
            conn_color = '#ff4444'
            health_text = "FEHLER"
            health_color = '#ff4444'

        conn_style = {'color': conn_color, 'fontWeight': '600', 'fontSize': '12px'}
        health_style = {'color': health_color, 'fontWeight': '600'}

        # Uptime berechnen
        uptime_seconds = int(time.time() - STARTUP_TIME)
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        uptime_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Debug-Log (nur alle 60 Sekunden)
        if n % 60 == 0:
            app_logger.info(f"Statusbar Update: {conn_text} | {health_text} | Uptime: {uptime_text}")

        return conn_text, conn_style, health_text, health_style, uptime_text
    except Exception as e:
        app_logger.error(f"Fehler in update_statusbar: {e}")
        return "---", {'color': '#666'}, "---", {'color': '#666'}, "00:00:00"

# TopBar COT-Anzeige (große Anzeige wie Simulator)
@app.callback(
    Output('topbar-cot-display', 'children'),
    [Input('interval-component', 'n_intervals')],
    prevent_initial_call=True
)
def update_topbar_cot(n):
    # Daten vom MRA4 lesen
    data = mra4.read_all_data()
    cot_code = data.get('cause_of_trip', 1)
    cot_description = COT_CODES.get(cot_code, f"Unbekannt ({cot_code})")

    prot_status = data.get('protection_status', {})
    ausl = prot_status.get('ausl', False)

    if cot_code == 0 or cot_code == 1:
        # NORM - Fehlerfrei (grün, klein)
        return html.Div([
            html.Span("✓ System OK", style={
                'color': '#00ff88',
                'fontSize': '14px',
                'fontWeight': '600',
                'padding': '6px 12px',
                'background': 'rgba(0, 255, 136, 0.1)',
                'borderRadius': '4px',
                'border': '1px solid #00ff88'
            })
        ])
    else:
        # Auslösung - GROSS anzeigen
        return html.Div([
            html.Div([
                html.Span("⚠ AUSLÖSUNG", style={
                    'color': '#ff4444',
                    'fontSize': '18px',
                    'fontWeight': '700',
                    'marginRight': '12px'
                }),
                html.Span(f"COT {cot_code}: {cot_description}", style={
                    'color': '#ff9800',
                    'fontSize': '16px',
                    'fontWeight': '600'
                })
            ], style={
                'padding': '8px 16px',
                'background': 'rgba(255, 68, 68, 0.2)',
                'borderRadius': '6px',
                'border': '2px solid #ff4444',
                'animation': 'pulse 2s ease-in-out infinite'
            })
        ])

# Log-Fenster Update (Normal-Level)
@app.callback(
    Output('normal-log-display', 'children'),
    [Input('interval-component', 'n_intervals')],
    prevent_initial_call=False
)
def update_normal_log(n):
    # Letzte 100 Log-Einträge aus LOG_BUFFER
    log_lines = []
    for entry in LOG_BUFFER:
        log_lines.append(html.Div(entry, style={'marginBottom': '4px'}))
    return log_lines

# Log-Fenster Update (Debug-Level im Admin-Tab)
@app.callback(
    Output('admin-log-display', 'children'),
    [Input('interval-component', 'n_intervals')],
    prevent_initial_call=False
)
def update_admin_log(n):
    # Letzte 500 Log-Einträge aus LOG_BUFFER_DEBUG
    log_lines = []
    for entry in LOG_BUFFER_DEBUG:
        log_lines.append(html.Div(entry, style={'marginBottom': '4px'}))
    return log_lines

# Admin BA/DI Status Update
@app.callback(
    [Output('admin-coupling-ba-status', 'children'),
     Output('admin-coupling-di-status', 'children')],
    [Input('interval-component', 'n_intervals')],
    prevent_initial_call=False
)
def update_admin_ba_di_status(n):
    try:
        data = mra4.read_all_data()
        ba_status = data.get('coupling_switch', False)
        di_status = data.get('di_status', False)
        return ("EIN" if ba_status else "AUS"), ("EIN" if di_status else "AUS")
    except:
        return "---", "---"

# Einstellungen übernehmen
@app.callback(
    [Output('max-power-store', 'data'),
     Output('update-interval-store', 'data')],
    [Input('apply-settings-btn', 'n_clicks')],
    [State('max-power-input', 'value'),
     State('update-interval', 'value'),
     State('graph-history', 'value')]
)
def apply_settings(n_clicks, max_power_kw, interval_ms, graph_history):
    if n_clicks:
        cfg = get_config_manager()

        if max_power_kw and float(max_power_kw) > 0:
            cfg.set('max_power_kw', float(max_power_kw))

        if interval_ms and int(interval_ms) > 0:
            cfg.set('update_interval_ms', int(interval_ms))

        if graph_history and int(graph_history) > 0:
            cfg.set('graph_history_seconds', int(graph_history))

        new_max_power = cfg.get('max_power_kw', MAX_POWER_KW)
        new_interval = cfg.get('update_interval_ms', 1000)

        return new_max_power, new_interval

    cfg = get_config_manager()
    return cfg.get('max_power_kw', MAX_POWER_KW), cfg.get('update_interval_ms', 1000)

# Update Intervall aktualisieren
@app.callback(
    Output('interval-component', 'interval'),
    [Input('update-interval-store', 'data')]
)
def update_interval_component(interval_ms):
    return interval_ms if interval_ms else 1000

# Gauge aktualisieren wenn Max Power geändert wird
@app.callback(
    [Output('power-gauge-total', 'max'),
     Output('max-power-label', 'children')],
    [Input('max-power-store', 'data')]
)
def update_gauge_max(max_power_kw):
    return max_power_kw, f"Maximum: {max_power_kw} kW"

# Graph Modal Callback
@app.callback(
    [Output('graph-modal', 'is_open'),
     Output('modal-graph', 'figure'),
     Output('modal-title', 'children')],
    [Input('expand-power', 'n_clicks'),
     Input('expand-voltage', 'n_clicks'),
     Input('expand-current', 'n_clicks')],
    [State('power-graph', 'figure'),
     State('voltage-graph', 'figure'),
     State('current-graph', 'figure')],
    prevent_initial_call=True
)
def toggle_modal(n_power, n_voltage, n_current, fig_power, fig_voltage, fig_current):
    ctx = callback_context
    if not ctx.triggered:
        return False, go.Figure(), ""

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'expand-power' and n_power:
        return True, fig_power, "Leistung - Detailansicht"
    elif button_id == 'expand-voltage' and n_voltage:
        return True, fig_voltage, "Spannung - Detailansicht"
    elif button_id == 'expand-current' and n_current:
        return True, fig_current, "Strom - Detailansicht"

    return False, go.Figure(), ""

# Settings Callbacks
@app.callback(
    Output('connection-test-result', 'children'),
    [Input('test-connection-btn', 'n_clicks')],
    [State('modbus-ip', 'value'),
     State('modbus-port', 'value'),
     State('modbus-unit', 'value')]
)
def test_connection(n_clicks, ip, port, unit):
    if not n_clicks:
        return ""

    try:
        # Teste echte Verbindung
        test_client = ModbusTcpClient(host=ip, port=int(port))
        connected = test_client.connect()
        test_client.close()

        if connected:
            return html.Div(f"Verbindung erfolgreich zu {ip}:{port}",
                          style={'color': '#00ff88', 'padding': '10px', 'background': 'rgba(0,255,136,0.1)', 'borderRadius': '6px'})
        else:
            return html.Div(f"Verbindung fehlgeschlagen zu {ip}:{port}",
                          style={'color': '#ff4444', 'padding': '10px', 'background': 'rgba(255,68,68,0.1)', 'borderRadius': '6px'})
    except Exception as e:
        return html.Div(f"Fehler: {str(e)}",
                      style={'color': '#ff4444', 'padding': '10px', 'background': 'rgba(255,68,68,0.1)', 'borderRadius': '6px'})

@app.callback(
    Output('settings-saved-msg', 'children'),
    [Input('apply-settings-btn', 'n_clicks')],
    [State('modbus-ip', 'value'),
     State('modbus-port', 'value'),
     State('modbus-unit', 'value'),
     State('update-interval', 'value'),
     State('graph-history', 'value'),
     State('max-power-input', 'value')]
)
def save_settings(n_clicks, ip, port, unit, interval, history, max_power):
    if not n_clicks:
        return ""

    try:
        # Konfiguration aktualisieren
        cfg_manager = get_config_manager()
        cfg_manager.set('modbus.ip', ip)
        cfg_manager.set('modbus.port', int(port))
        cfg_manager.set('modbus.unit_id', int(unit))
        cfg_manager.set('update_interval_ms', int(interval))
        cfg_manager.set('graph_history_seconds', int(history))
        cfg_manager.set('max_power_kw', float(max_power))

        return html.Div("Einstellungen gespeichert!",
                      style={'color': '#00ff88', 'padding': '10px', 'background': 'rgba(0,255,136,0.1)', 'borderRadius': '6px', 'marginTop': '15px'})
    except Exception as e:
        return html.Div(f"Fehler beim Speichern: {str(e)}",
                      style={'color': '#ff4444', 'padding': '10px', 'background': 'rgba(255,68,68,0.1)', 'borderRadius': '6px', 'marginTop': '15px'})

if __name__ == '__main__':
    # Setze Windows-Icon für Taskleiste und Fenster
    try:
        if sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes

            # Pfad zum Icon (relativ zum Script-Verzeichnis)
            if getattr(sys, 'frozen', False):
                # Läuft als .exe (PyInstaller)
                base_path = sys._MEIPASS
            else:
                # Läuft als Python-Script
                base_path = os.path.dirname(os.path.abspath(__file__))

            icon_path = os.path.join(base_path, 'assets', 'icon.ico')

            if os.path.exists(icon_path):
                # Windows App-ID setzen für Taskleiste-Gruppierung
                myappid = 'MRA4.Dashboard.WebApp.1.0'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

                # Konsolen-Fenster Icon setzen (falls Console-Modus)
                try:
                    # GetConsoleWindow gibt Handle des Konsolen-Fensters zurück
                    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
                    user32 = ctypes.WinDLL('user32', use_last_error=True)

                    hwnd = kernel32.GetConsoleWindow()
                    if hwnd:
                        # Icon laden
                        hicon = user32.LoadImageW(
                            None,
                            icon_path,
                            1,  # IMAGE_ICON
                            0, 0,
                            0x00000010 | 0x00008000  # LR_LOADFROMFILE | LR_DEFAULTSIZE
                        )
                        if hicon:
                            # Setze Icon für Fenster (WM_SETICON)
                            user32.SendMessageW(hwnd, 0x0080, 1, hicon)  # ICON_BIG
                            user32.SendMessageW(hwnd, 0x0080, 0, hicon)  # ICON_SMALL
                            app_logger.info(f"Icon erfolgreich gesetzt: {icon_path}")
                except Exception as e:
                    app_logger.debug(f"Konsolen-Icon konnte nicht gesetzt werden: {e}")
            else:
                app_logger.warning(f"Icon nicht gefunden: {icon_path}")
    except Exception as e:
        app_logger.warning(f"Icon konnte nicht gesetzt werden: {e}")

    # Dashboard-URL anzeigen
    local_ip = get_local_ip()
    hostname = get_hostname()
    port = 8050

    print("\n" + "="*60)
    print("  MRA 4 ENERGIEMONITORING DASHBOARD")
    print("="*60)
    print(f"\n  Dashboard erreichbar unter:")
    print(f"  -----------------------------------------")
    print(f"  Lokal:      http://localhost:{port}")
    print(f"  Netzwerk:   http://{local_ip}:{port}")
    print(f"  Hostname:   http://{hostname}:{port}")
    print(f"  -----------------------------------------")
    print(f"\n  Modbus-Konfiguration:")
    print(f"  IP: {config.get('modbus.ip', '192.168.1.100')}")
    print(f"  Port: {config.get('modbus.port', 502)}")
    print(f"  Simulator Modus: {'Ja' if SIMULATOR_MODE else 'Nein'}")
    print("\n" + "="*60 + "\n")

    app.run(debug=False, host='0.0.0.0', port=port)
