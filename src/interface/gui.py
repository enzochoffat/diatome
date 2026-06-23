import sys
import json
import random
from pathlib import Path

# Add the project root to Python path so we can import from src
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSpinBox, QProgressBar, QTextEdit, QGroupBox,
    QGridLayout, QTabWidget, QDoubleSpinBox, QFileDialog, QMessageBox,
    QFrame,
)
from PyQt6.QtCore import QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from src.model import FisheryModel
import src.config as config


# ---------------------------------------------------------------------------
# SimulationCanvas — graphiques stocks & économie
# ---------------------------------------------------------------------------

class SimulationCanvas(FigureCanvas):
    """Widget de visualisation des indicateurs de simulation.

    OPTIMISATION [P1] : au lieu de fig.clear() + ax.plot() à chaque
    rafraîchissement (O(S) par appel → O(T²) total), on initialise la figure
    une seule fois puis on met à jour les objets Line2D existants via
    set_data() en O(1) par ligne, draw() ne redessine que ce qui a changé.
    """

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(10, 6))
        super().__init__(self.fig)
        self.setParent(parent)

        # État interne des lignes — None tant que non initialisé
        self._stock_lines: dict | None = None   # {key: (ax, Line2D)}
        self._econ_lines: dict | None = None    # {name: (ax, Line2D)}

    # ------------------------------------------------------------------
    # Stocks
    # ------------------------------------------------------------------

    def _init_stock_plot(self) -> None:
        """Crée les 4 subplots et les Line2D vides (appelé une seule fois)."""
        self.fig.clear()
        self._stock_lines = {}

        regions = [
            ("stock_A", "Region A (Archipelago)", "#d9eef9", "#246eb9", config.CARRYING_CAPACITY_A_INITIAL),
            ("stock_B", "Region B (Coastal 1)",   "#e3f5df", "#2a7f62", config.CARRYING_CAPACITY_B_INITIAL),
            ("stock_C", "Region C (Coastal 2)",   "#fff3d6", "#d99000", config.CARRYING_CAPACITY_C_INITIAL),
            ("stock_D", "Region D (Open Sea)",    "#ffe7dd", "#cb4b16", config.CARRYING_CAPACITY_D_INITIAL),
        ]

        for i, (key, title, bg_color, line_color, carrying_capacity) in enumerate(regions):
            ax = self.fig.add_subplot(2, 2, i + 1)
            ax.set_facecolor(bg_color)
            # Line2D initialisée vide — sera remplie par set_data()
            (line,) = ax.plot([], [], color=line_color, linewidth=1.5)
            msy = carrying_capacity / 2
            ax.axhline(y=msy, color="#b30000", linestyle="--", linewidth=1,
                       label=f"MSY = {msy:,.0f}")
            ax.set_title(title, fontsize=9)
            ax.set_xlabel("Jours", fontsize=8)
            ax.set_ylabel("Stock", fontsize=8)
            ax.grid(True, alpha=0.4)
            ax.tick_params(labelsize=7)
            self._stock_lines[key] = (ax, line)

        self.fig.tight_layout(pad=2.0)
        self.draw()

    def plot_stocks(self, model_data: dict) -> None:
        """Mise à jour O(1) des lignes — aucune recréation d'objets Axes."""
        required_keys = ["stock_A", "stock_B", "stock_C", "stock_D"]
        if not (
            model_data
            and all(k in model_data for k in required_keys)
            and any(len(model_data[k]) > 0 for k in required_keys)
        ):
            return

        # Initialisation paresseuse : une seule fois par session
        if self._stock_lines is None:
            self._init_stock_plot()

        steps = list(range(len(model_data["stock_A"])))
        for key, (ax, line) in self._stock_lines.items():
            line.set_data(steps, model_data[key])
            ax.relim()
            ax.autoscale_view()

        self.draw()

    # ------------------------------------------------------------------
    # Économie
    # ------------------------------------------------------------------

    def _init_economics_plot(self) -> None:
        """Crée les 2 subplots économiques et les Line2D vides."""
        self.fig.clear()
        self._econ_lines = {}

        ax1 = self.fig.add_subplot(211)
        (line_daily,) = ax1.plot([], [], color="#2a7f62", linewidth=1.2,
                                  label="Capture journalière")
        (line_cum,) = ax1.plot([], [], color="#245c36", linewidth=1.0,
                                alpha=0.6, label="Capture cumulative")
        ax1.set_ylabel("Captures")
        ax1.legend()
        ax1.grid(True)

        ax2 = self.fig.add_subplot(212)
        (line_cap,) = ax2.plot([], [], color="#246eb9", linewidth=1.5,
                                label="Capital moyen")
        ax2.set_xlabel("Jours")
        ax2.set_ylabel("Capital")
        ax2.legend()
        ax2.grid(True)

        self.fig.tight_layout(pad=2.0)
        self._econ_lines = {
            "daily": (ax1, line_daily),
            "cum":   (ax1, line_cum),
            "cap":   (ax2, line_cap),
        }
        self.draw()

    def plot_economics(self, model_data: dict) -> None:
        """Mise à jour O(1) — daily_catch pré-calculé dans model_data [P5]."""
        if not (model_data and model_data.get("total_catch") and model_data.get("avg_capital")):
            return

        if self._econ_lines is None:
            self._init_economics_plot()

        steps = list(range(len(model_data["total_catch"])))

        # OPTIMISATION [P5] : daily_catch calculé incrémentalement dans
        # step_simulation — on ne le recalcule plus ici.
        self._econ_lines["daily"][1].set_data(steps, model_data["daily_catch"])
        self._econ_lines["cum"][1].set_data(steps, model_data["total_catch"])
        self._econ_lines["cap"][1].set_data(steps, model_data["avg_capital"])

        for ax, _ in self._econ_lines.values():
            ax.relim()
            ax.autoscale_view()

        self.draw()

    def reset_canvas(self) -> None:
        """Réinitialise l'état interne lors d'un reset de simulation."""
        self._stock_lines = None
        self._econ_lines = None
        self.fig.clear()
        self.draw()


# ---------------------------------------------------------------------------
# GridCanvas — grille spatiale
# ---------------------------------------------------------------------------

class GridCanvas(FigureCanvas):
    """Widget pour afficher la grille spatiale avec les pêcheurs."""

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(8, 8))
        super().__init__(self.fig)
        self.setParent(parent)
        # OPTIMISATION [P3] : cache des positions "home" calculées une seule
        # fois par agent — évite O(A × T/15) instanciations de random.Random.
        self._home_cache: dict[int, tuple[int, int]] = {}

    def _home_position(self, agent) -> tuple[int, int]:
        """Position stable en zone LAND, mémoïsée par unique_id."""
        uid = agent.unique_id
        if uid not in self._home_cache:
            rng = random.Random(uid)
            self._home_cache[uid] = rng.choice(config.LAND) if config.LAND else (0, 0)
        return self._home_cache[uid]

    def reset_canvas(self) -> None:
        """Vide le cache et efface la figure lors d'un reset."""
        self._home_cache.clear()
        self.fig.clear()
        self.draw()

    def plot_grid(self, model) -> None:
        """Afficher la grille avec les positions des pêcheurs."""
        self.fig.clear()
        ax = self.fig.add_subplot(111)

        if not model:
            self.draw()
            return

        # Mapping densité → alpha
        density_alpha = {
            model.LOW:         0.25,
            model.LOW_MEDIUM:  0.375,
            model.MEDIUM:      0.5,
            model.MEDIUM_HIGH: 0.65,
            model.HIGH:        0.8,
        }

        # Mapping région → couleur
        region_color = {
            "A":    "#b7dff6",
            "B":    "#c6ebbf",
            "C":    "#ffe6a7",
            "D":    "#ffc9a8",
            "LAND": "#FFFFFF",
            "NULL": "#ff0000",
        }

        # Dessiner les patches selon densité
        for (x, y), patch in model.patches.items():
            region  = patch.get("region")
            density = patch.get("density")

            if region in ("LAND", "NULL"):
                color = region_color.get(region, "grey")
                ax.add_patch(plt.Rectangle((x, y), 1, 1, alpha=1.0, color=color, linewidth=0))
            elif region in region_color and density is not None:
                alpha = density_alpha.get(density, 0.1)
                color = region_color.get(region, "grey")
                ax.add_patch(plt.Rectangle((x, y), 1, 1, alpha=alpha, color=color, linewidth=0))

        # Collecter positions des agents
        archipelago_pos: list[tuple] = []
        coastal_pos:     list[tuple] = []
        trawler_pos:     list[tuple] = []

        for agent in model.agents:
            if agent.current_location and (agent.gone_fishing or getattr(agent, "fished_today", False)):
                pos = agent.current_location
            elif agent.display_location and getattr(agent, "fished_today", False):
                pos = agent.display_location
            else:
                pos = self._home_position(agent)

            if agent.fisher_type == "archipelago":
                archipelago_pos.append(pos)
            elif agent.fisher_type == "coastal":
                coastal_pos.append(pos)
            elif agent.fisher_type == "trawler":
                trawler_pos.append(pos)

        # Dessiner les agents
        if archipelago_pos:
            ax.scatter(*zip(*archipelago_pos), c="#0f4c81", marker="o",
                       s=55, alpha=0.8, label=f"Archipelago ({len(archipelago_pos)})", zorder=5)
        if coastal_pos:
            ax.scatter(*zip(*coastal_pos), c="#1b7f79", marker="s",
                       s=55, alpha=0.8, label=f"Coastal ({len(coastal_pos)})", zorder=5)
        if trawler_pos:
            ax.scatter(*zip(*trawler_pos), c="#cc3a3b", marker="^",
                       s=65, alpha=0.9, label=f"Trawler ({len(trawler_pos)})", zorder=5)

        # OPTIMISATION [P4] : set_xlim/set_ylim appelés une seule fois
        # (suppression du set_xlim dupliqué présent dans la version originale).
        ax.set_xlim(0, config.GRID_WIDTH)
        ax.set_ylim(config.GRID_HEIGHT, 0)
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_title(f"Positions des pêcheurs (Jour {model.current_step})")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_aspect("equal")

        self.draw()


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.model = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.step_simulation)
        self.current_config_path = None
        self._init_model_data()
        self.init_ui()

    # ------------------------------------------------------------------
    # Données de simulation
    # ------------------------------------------------------------------

    def _init_model_data(self) -> None:
        """Initialise (ou remet à zéro) le dict de données de simulation.

        OPTIMISATION [P5] : ajout de la clé 'daily_catch' calculée
        incrémentalement à chaque step, évitant le recalcul O(S) dans
        plot_economics à chaque rafraîchissement graphique.
        """
        self.model_data: dict[str, list] = {
            "stock_A":     [],
            "stock_B":     [],
            "stock_C":     [],
            "stock_D":     [],
            "total_catch": [],
            "daily_catch": [],   # [P5] différence journalière pré-calculée
            "avg_capital": [],
        }

    # ------------------------------------------------------------------
    # Construction de l'UI
    # ------------------------------------------------------------------

    def init_ui(self):
        self.setWindowTitle("FIBE - Fishery Model Simulation")
        self.setGeometry(100, 100, 1400, 900)
        self.apply_app_style()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- PANNEAU GAUCHE : Contrôles ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(430)

        title_box = QFrame()
        title_box.setObjectName("headerCard")
        title_layout = QVBoxLayout(title_box)
        title = QLabel("FIBE")
        title.setObjectName("appTitle")
        subtitle = QLabel("Simulateur socio-écologique de pêcheries")
        subtitle.setObjectName("appSubtitle")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        left_layout.addWidget(title_box)

        # Chargement JSON
        json_group = QGroupBox("Configuration")
        json_layout = QHBoxLayout()
        self.json_label = QLabel("Aucun fichier chargé")
        self.json_label.setWordWrap(True)
        self.load_btn = QPushButton("Charger JSON")
        self.load_btn.clicked.connect(self.load_config)
        json_layout.addWidget(self.json_label)
        json_layout.addWidget(self.load_btn)
        json_group.setLayout(json_layout)
        left_layout.addWidget(json_group)

        # Paramètres de simulation
        params_group = QGroupBox("Paramètres")
        params_layout = QGridLayout()

        params_layout.addWidget(QLabel("Durée (années) :"), 0, 0)
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 50)
        self.duration_spin.setValue(2)
        self.duration_spin.setSingleStep(1)
        params_layout.addWidget(self.duration_spin, 0, 1)
        self.duration_label = QLabel("= 730 jours")
        params_layout.addWidget(self.duration_label, 0, 2)
        self.duration_spin.valueChanged.connect(self.update_duration_label)

        params_layout.addWidget(QLabel("Archipelago :"), 1, 0)
        self.arch_spin = QSpinBox()
        self.arch_spin.setRange(0, 1000)
        self.arch_spin.setValue(10)
        params_layout.addWidget(self.arch_spin, 1, 1)

        params_layout.addWidget(QLabel("Coastal :"), 2, 0)
        self.coast_spin = QSpinBox()
        self.coast_spin.setRange(0, 1000)
        self.coast_spin.setValue(10)
        params_layout.addWidget(self.coast_spin, 2, 1)

        params_layout.addWidget(QLabel("Trawler :"), 3, 0)
        self.trawl_spin = QSpinBox()
        self.trawl_spin.setRange(0, 1000)
        self.trawl_spin.setValue(5)
        params_layout.addWidget(self.trawl_spin, 3, 1)

        self.ecospace_btn = QPushButton("Charger données Ecospace")
        self.ecospace_btn.clicked.connect(self.load_ecospace_data)
        params_layout.addWidget(self.ecospace_btn, 4, 0)
        self.ecospace_status = QLabel("Non chargées")
        params_layout.addWidget(self.ecospace_status, 4, 1)

        self.wind_farm_btn = QPushButton("Ajout Wind Farm")
        self.wind_farm_btn.clicked.connect(self.add_wind_farm)
        params_layout.addWidget(self.wind_farm_btn, 5, 0)
        self.wind_farm_status = QLabel("Non activé")
        params_layout.addWidget(self.wind_farm_status, 5, 1)

        params_layout.addWidget(QLabel("Taux de croissance :"), 6, 0)
        self.growth_spin = QDoubleSpinBox()
        self.growth_spin.setRange(0.0, 1.0)
        self.growth_spin.setSingleStep(0.01)
        self.growth_spin.setDecimals(3)
        self.growth_spin.setValue(config.GROWTH_RATE)
        params_layout.addWidget(self.growth_spin, 6, 1)

        params_layout.addWidget(QLabel("Prix du poisson :"), 7, 0)
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.0, 100.0)
        self.price_spin.setSingleStep(0.1)
        self.price_spin.setDecimals(2)
        self.price_spin.setValue(config.FISH_PRICE)
        params_layout.addWidget(self.price_spin, 7, 1)

        params_layout.addWidget(QLabel("Capital initial :"), 8, 0)
        self.capital_spin = QDoubleSpinBox()
        self.capital_spin.setRange(0.0, 1_000_000.0)
        self.capital_spin.setSingleStep(100.0)
        self.capital_spin.setDecimals(2)
        self.capital_spin.setValue(config.INITIAL_CAPITAL)
        params_layout.addWidget(self.capital_spin, 8, 1)

        params_layout.addWidget(QLabel("Prob. mauvais temps :"), 9, 0)
        self.weather_spin = QDoubleSpinBox()
        self.weather_spin.setRange(0.0, 1.0)
        self.weather_spin.setSingleStep(0.01)
        self.weather_spin.setDecimals(2)
        self.weather_spin.setValue(config.BAD_WEATHER_PROBABILITY)
        params_layout.addWidget(self.weather_spin, 9, 1)

        params_layout.addWidget(QLabel("Vitesse (ms/step) :"), 10, 0)
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(1, 500)
        self.speed_spin.setValue(20)
        self.speed_spin.setSingleStep(1)
        self.speed_spin.valueChanged.connect(self.update_speed)
        params_layout.addWidget(self.speed_spin, 10, 1)

        params_group.setLayout(params_layout)
        left_layout.addWidget(params_group)

        # Contrôles
        controls_group = QGroupBox("Contrôles")
        controls_layout = QVBoxLayout()

        self.start_btn = QPushButton("Démarrer")
        self.start_btn.clicked.connect(self.start_simulation)
        controls_layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.pause_simulation)
        self.pause_btn.setEnabled(False)
        controls_layout.addWidget(self.pause_btn)

        self.step_btn = QPushButton("Step")
        self.step_btn.clicked.connect(self.step_simulation)
        controls_layout.addWidget(self.step_btn)

        self.year_btn = QPushButton("Avancer 1 an")
        self.year_btn.clicked.connect(self.step_one_year)
        controls_layout.addWidget(self.year_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_simulation)
        controls_layout.addWidget(self.reset_btn)

        self.export_btn = QPushButton("Exporter données")
        self.export_btn.clicked.connect(self.export_data)
        self.export_btn.setEnabled(False)
        controls_layout.addWidget(self.export_btn)

        controls_group.setLayout(controls_layout)
        left_layout.addWidget(controls_group)

        self.status_label = QLabel("État : prêt")
        self.status_label.setObjectName("statusLabel")
        left_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("%p% - 0 / 0 jours")
        left_layout.addWidget(self.progress_bar)

        stats_group = QGroupBox("Statistiques")
        stats_layout = QVBoxLayout()
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(600)
        stats_layout.addWidget(self.stats_text)
        stats_group.setLayout(stats_layout)
        left_layout.addWidget(stats_group)

        left_layout.addStretch()

        # --- PANNEAU DROIT : Graphiques ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.tabs = QTabWidget()
        self.stocks_canvas = SimulationCanvas()
        self.tabs.addTab(self.stocks_canvas, "Stocks")
        self.economics_canvas = SimulationCanvas()
        self.tabs.addTab(self.economics_canvas, "Économie")
        self.grid_canvas = GridCanvas()
        self.tabs.addTab(self.grid_canvas, "Grille spatiale")
        right_layout.addWidget(self.tabs)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, stretch=1)

    # ------------------------------------------------------------------
    # Style
    # ------------------------------------------------------------------

    def apply_app_style(self):
        """Appliquer une identité visuelle claire et moderne."""
        self.setStyleSheet("""
            QWidget {
                background: #f5f7f2;
                color: #1f2937;
                font-family: 'DejaVu Sans';
                font-size: 12px;
            }
            #headerCard {
                border: 1px solid #d8dfcd;
                border-radius: 14px;
                background-color: #eaf1de;
                padding: 8px;
            }
            #appTitle {
                font-size: 28px;
                font-weight: 700;
                color: #2a5d34;
                letter-spacing: 1px;
            }
            #appSubtitle {
                font-size: 12px;
                color: #4b5563;
            }
            QGroupBox {
                border: 1px solid #d8dfcd;
                border-radius: 10px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: 600;
                background-color: #fbfcf8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QPushButton {
                border: 1px solid #b8c6a5;
                border-radius: 8px;
                padding: 6px 10px;
                background-color: #e6f0d8;
                font-weight: 600;
            }
            QPushButton:hover  { background-color: #d7e7c0; }
            QPushButton:disabled {
                color: #88939b;
                background-color: #eef2ea;
                border-color: #d7dfcf;
            }
            QProgressBar {
                border: 1px solid #c7d2be;
                border-radius: 8px;
                text-align: center;
                background-color: #eef3e8;
            }
            QProgressBar::chunk {
                background-color: #4c8b5f;
                border-radius: 6px;
            }
            QTextEdit {
                border: 1px solid #d8dfcd;
                border-radius: 10px;
                background-color: #ffffff;
                font-family: 'DejaVu Sans Mono';
                font-size: 11px;
            }
            #statusLabel {
                padding: 6px 8px;
                border: 1px solid #d8dfcd;
                border-radius: 8px;
                background-color: #f0f6e8;
                font-weight: 600;
            }
        """)

    # ------------------------------------------------------------------
    # Helpers UI
    # ------------------------------------------------------------------

    def _set_inputs_enabled(self, enabled: bool) -> None:
        for ctrl in (
            self.load_btn, self.duration_spin, self.arch_spin,
            self.coast_spin, self.trawl_spin, self.growth_spin,
            self.price_spin, self.capital_spin, self.weather_spin,
        ):
            ctrl.setEnabled(enabled)

    def _collect_runtime_parameters(self) -> dict:
        """Récupérer les paramètres dynamiques choisis dans l'interface."""
        return {
            "growth_rate":           float(self.growth_spin.value()),
            "fish_price":            float(self.price_spin.value()),
            "initial_capital":       float(self.capital_spin.value()),
            "bad_weather_probability": float(self.weather_spin.value()),
        }

    # ------------------------------------------------------------------
    # Chargement de configuration
    # ------------------------------------------------------------------

    def load_config(self):
        """Charger un fichier JSON et remplir les champs."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir une configuration", "configs/", "JSON Files (*.json)"
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)

            sim     = cfg.get("simulation", {})
            agents  = cfg.get("agents", {})
            params  = cfg.get("parameters", {})

            if "duration_years" in sim:
                self.duration_spin.setValue(sim["duration_years"])
            if "num_archipelago" in agents:
                self.arch_spin.setValue(agents["num_archipelago"])
            if "num_coastal" in agents:
                self.coast_spin.setValue(agents["num_coastal"])
            if "num_trawler" in agents:
                self.trawl_spin.setValue(agents["num_trawler"])

            fish = params.get("fish_dynamics", {})
            if "growth_rate" in fish:
                self.growth_spin.setValue(fish["growth_rate"])

            econ = params.get("economics", {})
            if "fish_price" in econ:
                self.price_spin.setValue(econ["fish_price"])
            if "initial_capital" in econ:
                self.capital_spin.setValue(econ["initial_capital"])

            weather = params.get("weather", {})
            if "bad_weather_probability" in weather:
                self.weather_spin.setValue(weather["bad_weather_probability"])

            self.current_config_path = path
            name = cfg.get("metadata", {}).get("name", Path(path).name)
            self.json_label.setText(f"OK – {name}")
            self.status_label.setText(f"État : config chargée ({name})")

        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible de charger le fichier :\n{exc}")

    def load_ecospace_data(self):
        """Charger les données Ecospace depuis des CSV sélectionnés par l'utilisateur."""
        try:
            ecospace_data = config.get_ecospace_data()
            if ecospace_data is not None:
                self.ecospace_status.setText("✓ Chargées")
                self.ecospace_status.setStyleSheet("color: green; font-weight: bold;")
                self.ecospace_btn.setEnabled(False)
                QMessageBox.information(
                    self, "Succès",
                    "Données Ecospace chargées avec succès !\n"
                    "Les hotspots dynamiques seront utilisés à partir de la prochaine simulation."
                )
            else:
                QMessageBox.warning(self, "Erreur", "Impossible de charger les données Ecospace.")
        except Exception as exc:
            QMessageBox.critical(self, "Erreur",
                                 f"Erreur lors du chargement des données Ecospace :\n{exc}")

    def add_wind_farm(self):
        """Ajouter le parc éolien à la topologie courante."""
        try:
            config.add_windfarm_to_topology()
            self.wind_farm_status.setText("✓ Activé")
            self.wind_farm_status.setStyleSheet("color: green; font-weight: bold;")
            self.wind_farm_btn.setEnabled(False)
        except Exception as exc:
            QMessageBox.critical(self, "Erreur",
                                 f"Erreur lors de l'ajout du parc éolien :\n{exc}")

    # ------------------------------------------------------------------
    # Contrôle de la simulation
    # ------------------------------------------------------------------

    def start_simulation(self):
        """Démarrer ou reprendre la simulation."""
        if self.model is None:
            runtime_params = self._collect_runtime_parameters()
            duration = self.duration_spin.value() * 365

            self.model = FisheryModel(
                end_of_sim=duration,
                num_archipelago=self.arch_spin.value(),
                num_coastal=self.coast_spin.value(),
                num_trawler=self.trawl_spin.value(),
                verbose=False,
                growth_rate=runtime_params["growth_rate"],
                fish_price=runtime_params["fish_price"],
                initial_capital=runtime_params["initial_capital"],
                bad_weather_probability=runtime_params["bad_weather_probability"],
            )

            self._init_model_data()
            self.progress_bar.setMaximum(duration)

            # OPTIMISATION [P1] : pré-initialiser les figures pour que le
            # premier draw() ne recrée pas les objets Axes depuis zéro.
            self.stocks_canvas._init_stock_plot()
            self.economics_canvas._init_economics_plot()

        self.timer.start(self.speed_spin.value())
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.export_btn.setEnabled(False)
        self._set_inputs_enabled(False)
        self.status_label.setText(
            f"État : simulation en cours ({self.speed_spin.value()} ms/step)"
        )

    def pause_simulation(self):
        """Mettre en pause."""
        self.timer.stop()
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.status_label.setText("État : en pause")

    def update_speed(self):
        """Mettre à jour la vitesse si la simulation tourne."""
        if self.timer.isActive():
            self.timer.setInterval(self.speed_spin.value())
            self.status_label.setText(
                f"État : simulation en cours ({self.speed_spin.value()} ms/step)"
            )

    def step_one_year(self):
        """Avancer manuellement d'une année (365 steps)."""
        if self.model is None:
            self.start_simulation()
            self.pause_simulation()

        if not self.model:
            return

        for _ in range(config.YEAR):
            if self.model.running:
                self.step_simulation()
            else:
                break

    def step_simulation(self):
        """Exécuter un pas de simulation.

        OPTIMISATION [P2] : un seul parcours des agents pour calculer
        total_catch et avg_capital (suppression de list(model.agents) et du
        générateur séparé pour total_catch).

        OPTIMISATION [P5] : daily_catch calculé incrémentalement ici en O(1)
        par step plutôt que recalculé en O(S) dans plot_economics.
        """
        if self.model is None:
            self.start_simulation()
            self.pause_simulation()

        if not (self.model and self.model.running):
            return

        self.model.step()

        # --- Collecte des données agents — un seul parcours [P2] ---
        total_catch   = 0
        total_capital = 0
        n_agents      = 0
        for agent in self.model.agents:
            total_catch   += agent.total_catch
            total_capital += agent.capital
            n_agents      += 1

        avg_capital = total_capital / n_agents if n_agents else 0

        # --- Stocks régionaux ---
        self.model_data["stock_A"].append(self.model.get_region_stock("A"))
        self.model_data["stock_B"].append(self.model.get_region_stock("B"))
        self.model_data["stock_C"].append(self.model.get_region_stock("C"))
        self.model_data["stock_D"].append(self.model.get_region_stock("D"))

        # --- Captures : cumul + différence journalière [P5] ---
        prev_total = self.model_data["total_catch"][-1] if self.model_data["total_catch"] else 0
        self.model_data["total_catch"].append(total_catch)
        self.model_data["daily_catch"].append(total_catch - prev_total)

        # --- Capital ---
        self.model_data["avg_capital"].append(avg_capital)

        # --- Mise à jour UI ---
        step = self.model.current_step
        self.progress_bar.setValue(step)
        self.progress_bar.setFormat(
            f"{int(step / self.model.end_of_sim * 100)}% – "
            f"{step} / {self.model.end_of_sim} jours"
        )
        self.update_stats()

        # Mise à jour graphiques tous les 15 jours
        if step % 15 == 0:
            self.update_graphs()

        # Fin de simulation
        if not self.model.running:
            self.timer.stop()
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            self.export_btn.setEnabled(True)
            self._set_inputs_enabled(True)
            self.status_label.setText("État : simulation terminée")
            self.update_graphs()

    def reset_simulation(self):
        """Réinitialiser la simulation et l'interface."""
        self.timer.stop()
        self.model = None
        self._init_model_data()

        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p% - 0 / 0 jours")
        self.stats_text.clear()

        # OPTIMISATION [P1/P3] : les canvas exposent reset_canvas() qui efface
        # l'état interne (lignes Line2D, cache home) sans détruire le widget.
        self.stocks_canvas.reset_canvas()
        self.economics_canvas.reset_canvas()
        self.grid_canvas.reset_canvas()

        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self._set_inputs_enabled(True)
        self.status_label.setText("État : prêt")

    # ------------------------------------------------------------------
    # Affichage
    # ------------------------------------------------------------------

    def update_stats(self):
        """Mettre à jour les statistiques affichées."""
        if not self.model:
            return

        summary = self.model.get_model_summary()
        text = (
            f"Jour : {summary['current_step']} / {self.model.end_of_sim}\n"
            f"Année : {summary['current_year']}\n\n"
            f"=== AGENTS ===\n"
            f"Total : {summary['num_agents']}\n"
            f"En mer : {summary['num_fishing']}\n"
            f"A pêché aujourd'hui : {summary.get('num_fished_today', 0)}\n"
            f"À la maison : {summary['num_at_home']}\n\n"
            f"=== STOCKS ===\n"
            f"Total : {summary['total_stock']:,.0f}\n"
            f"Région A : {summary['stock_A']:,.0f}\n"
            f"Région B : {summary['stock_B']:,.0f}\n"
            f"Région C : {summary['stock_C']:,.0f}\n"
            f"Région D : {summary['stock_D']:,.0f}\n\n"
            f"=== ÉCONOMIE ===\n"
            f"Captures totales : {summary['total_catch']:,.0f}\n"
            f"Capital moyen : {summary['avg_capital']:,.2f}\n\n"
            f"Météo : {'Mauvais temps' if summary['bad_weather'] else 'Beau temps'}"
        )
        self.stats_text.setText(text)

    def update_graphs(self):
        """Mettre à jour les trois graphiques."""
        self.stocks_canvas.plot_stocks(self.model_data)
        self.economics_canvas.plot_economics(self.model_data)
        if self.model:
            self.grid_canvas.plot_grid(self.model)

    def export_data(self):
        """Exporter les données de simulation."""
        if self.model:
            self.model.export_data()
            self.stats_text.append("\n\nOK – Données exportées")

    def update_duration_label(self, years: int):
        self.duration_label.setText(f"= {years * 365} jours")


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()