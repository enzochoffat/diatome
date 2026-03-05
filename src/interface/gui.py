import sys
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSpinBox, QProgressBar, QTextEdit, QGroupBox,
    QGridLayout, QTabWidget, QDoubleSpinBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import QTimer, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from src.model import FisheryModel
import src.config as config
import random
import numpy as np
from src.config import *


class SimulationCanvas(FigureCanvas):
    """Widget pour afficher les graphiques"""
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(10, 6))
        super().__init__(self.fig)
        self.setParent(parent)
        
    def plot_stocks(self, model_data):
        """Afficher l'évolution des stocks"""
        self.fig.clear()

        if model_data and any(len(model_data[k]) > 0 for k in ['stock_A', 'stock_B', 'stock_C', 'stock_D']):
            steps = list(range(len(model_data['stock_A'])))

            regions = [
                ('stock_A', 'Région A (Archipelago)', 'lightblue', 'blue', config.CARRYING_CAPACITY_A_INITIAL),
                ('stock_B', 'Région B (Coastal 1)',   'lightgreen', 'green', config.CARRYING_CAPACITY_B_INITIAL),
                ('stock_C', 'Région C (Coastal 2)',   'lightyellow', 'orange', config.CARRYING_CAPACITY_C_INITIAL),
                ('stock_D', 'Région D (Open Sea)',    'peachpuff', 'red', config.CARRYING_CAPACITY_D_INITIAL),
            ]

            for i, (key, title, bg_color, line_color, carrying_capacity) in enumerate(regions):
                ax = self.fig.add_subplot(2, 2, i + 1)
                ax.set_facecolor(bg_color)
                ax.plot(steps, model_data[key], color=line_color, linewidth=1.5)
                msy = carrying_capacity / 2
                ax.axhline(y=msy, color='red', linestyle='--', linewidth=1, label=f'MSY = {msy:,.0f}')
                ax.set_title(title, fontsize=9)
                ax.set_xlabel('Jours', fontsize=8)
                ax.set_ylabel('Stock', fontsize=8)
                ax.grid(True, alpha=0.4)
                ax.tick_params(labelsize=7)

            self.fig.tight_layout(pad=2.0)

        self.draw()
        
    def plot_economics(self, model_data):
        """Afficher les métriques économiques"""
        self.fig.clear()
        
        if model_data:
            ax1 = self.fig.add_subplot(211)
            steps = list(range(len(model_data['total_catch'])))
            ax1.plot(steps, model_data['total_catch'], 'g-', label='Captures totales')
            ax1.set_ylabel('Captures')
            ax1.legend()
            ax1.grid(True)
            
            ax2 = self.fig.add_subplot(212)
            ax2.plot(steps, model_data['avg_capital'], 'b-', label='Capital moyen')
            ax2.set_xlabel('Jours')
            ax2.set_ylabel('Capital')
            ax2.legend()
            ax2.grid(True)
            
        self.draw()

class GridCanvas(FigureCanvas):
    """Widget pour afficher la grille spatiale avec les pêcheurs"""
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(8, 8))
        super().__init__(self.fig)
        self.setParent(parent)
        
    def plot_grid(self, model):
        """Afficher la grille avec les positions des pêcheurs"""
        self.fig.clear()
        ax = self.fig.add_subplot(111)

        if not model:
            return

        # Mapping densité → alpha
        density_alpha = {
            model.LOW: 0.25,
            model.LOW_MEDIUM: 0.375,
            model.MEDIUM: 0.5,
            model.MEDIUM_HIGH: 0.65,
            model.HIGH: 0.8,
        }

        # Mapping région → couleur
        region_color = {
            'A': 'lightblue',
            'B': 'lightgreen',
            'C': 'lightyellow',
            'D': 'peachpuff',
        }

        # Dessiner les patches selon densité
        for (x, y), patch in model.patches.items():
            region = patch.get('region')
            density = patch.get('density')

            if region in ['LAND', 'NULL'] or density is None:
                continue

            alpha = density_alpha.get(density, 0.1)
            color = region_color.get(region, 'grey')

            ax.add_patch(plt.Rectangle(
                (x, y), 1, 1,
                alpha=alpha,
                color=color,
                linewidth=0
            ))

        # Collecter positions des agents
        archipelago_pos = []
        coastal_pos = []
        trawler_pos = []

        for agent in model.agents:
            if agent.current_location and agent.will_fish:
                pos = agent.current_location
            elif agent.display_location and agent.will_fish:
                pos = agent.display_location
            else:
                x = random.randint(25, 50)
                y = random.randint(0, 24)
                pos = (x, y)
                if agent.fisher_type == "archipelago":
                    archipelago_pos.append(pos)
                elif agent.fisher_type == "coastal":
                    coastal_pos.append(pos)
                elif agent.fisher_type == "trawler":
                    trawler_pos.append(pos)
                

            if agent.fisher_type == "archipelago":
                archipelago_pos.append(pos)
            elif agent.fisher_type == "coastal":
                coastal_pos.append(pos)
            elif agent.fisher_type == "trawler":
                trawler_pos.append(pos)

        # Dessiner les agents
        if archipelago_pos:
            ax.scatter(*zip(*archipelago_pos), c='blue', marker='o',
                      s=50, alpha=0.7, label=f'Archipelago',
                      zorder=5)

        if coastal_pos:
            ax.scatter(*zip(*coastal_pos), c='green', marker='s',
                      s=50, alpha=0.7, label=f'Coastal',
                      zorder=5)

        if trawler_pos:
            ax.scatter(*zip(*trawler_pos), c='red', marker='^',
                      s=50, alpha=0.7, label=f'Trawler',
                      zorder=5)

        ax.set_xlim(0, config.GRID_WIDTH)
        ax.set_ylim(0, config.GRID_HEIGHT)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_title(f'Positions des pêcheurs (Jour {model.current_step})')
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')

        self.draw()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.model = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.step_simulation)
        self.model_data = {
            'stock_A': [], 'stock_B': [], 'stock_C': [], 'stock_D': [],
            'total_catch': [], 'avg_capital': []
        }
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('FIBE - Fishery Model Simulation')
        self.setGeometry(100, 100, 1400, 900)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # --- PANNEAU GAUCHE : Contrôles ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(400)
        
        # --- Chargement JSON ---
        json_group = QGroupBox("Configuration")
        json_layout = QHBoxLayout()
        self.json_label = QLabel("Aucun fichier chargé")
        self.json_label.setWordWrap(True)
        load_btn = QPushButton("Charger JSON")
        load_btn.clicked.connect(self.load_config)
        json_layout.addWidget(self.json_label)
        json_layout.addWidget(load_btn)
        json_group.setLayout(json_layout)
        left_layout.addWidget(json_group)
        
        # Paramètres de simulation
        params_group = QGroupBox("Paramètres")
        params_layout = QGridLayout()
        
        # Durée
        params_layout.addWidget(QLabel("Durée (années):"), 0, 0)
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 50)
        self.duration_spin.setValue(2)
        self.duration_spin.setSingleStep(1)
        params_layout.addWidget(self.duration_spin, 0, 1)
        self.duration_label = QLabel("= 730 jours")
        params_layout.addWidget(self.duration_label, 0, 2)
        self.duration_spin.valueChanged.connect(self.update_duration_label)
        
        # Agents
        params_layout.addWidget(QLabel("Archipelago:"), 1, 0)
        self.arch_spin = QSpinBox()
        self.arch_spin.setRange(0, 1000)
        self.arch_spin.setValue(0)
        params_layout.addWidget(self.arch_spin, 1, 1)
        
        params_layout.addWidget(QLabel("Coastal:"), 2, 0)
        self.coast_spin = QSpinBox()
        self.coast_spin.setRange(0, 1000)
        self.coast_spin.setValue(0)
        params_layout.addWidget(self.coast_spin, 2, 1)
        
        params_layout.addWidget(QLabel("Trawler:"), 3, 0)
        self.trawl_spin = QSpinBox()
        self.trawl_spin.setRange(0, 1000)
        self.trawl_spin.setValue(0)
        params_layout.addWidget(self.trawl_spin, 3, 1)
        
        # Paramètres avancés (depuis JSON)
        params_layout.addWidget(QLabel("Taux de croissance:"), 4, 0)
        self.growth_spin = QDoubleSpinBox()
        self.growth_spin.setRange(0.0, 1.0)
        self.growth_spin.setSingleStep(0.01)
        self.growth_spin.setDecimals(3)
        self.growth_spin.setValue(0.1)
        params_layout.addWidget(self.growth_spin, 4, 1)

        params_layout.addWidget(QLabel("Prix du poisson:"), 5, 0)
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.0, 100.0)
        self.price_spin.setSingleStep(0.1)
        self.price_spin.setDecimals(2)
        self.price_spin.setValue(1.0)
        params_layout.addWidget(self.price_spin, 5, 1)

        params_layout.addWidget(QLabel("Capital initial:"), 6, 0)
        self.capital_spin = QDoubleSpinBox()
        self.capital_spin.setRange(0.0, 1000000.0)
        self.capital_spin.setSingleStep(100.0)
        self.capital_spin.setDecimals(2)
        self.capital_spin.setValue(1000.0)
        params_layout.addWidget(self.capital_spin, 6, 1)

        params_layout.addWidget(QLabel("Prob. mauvais temps:"), 7, 0)
        self.weather_spin = QDoubleSpinBox()
        self.weather_spin.setRange(0.0, 1.0)
        self.weather_spin.setSingleStep(0.01)
        self.weather_spin.setDecimals(2)
        self.weather_spin.setValue(0.1)
        params_layout.addWidget(self.weather_spin, 7, 1)
        
        params_group.setLayout(params_layout)
        left_layout.addWidget(params_group)
        
        # ...existing code...  (contrôles, progress bar, stats)
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
        
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_simulation)
        controls_layout.addWidget(self.reset_btn)
        
        self.export_btn = QPushButton("Exporter données")
        self.export_btn.clicked.connect(self.export_data)
        self.export_btn.setEnabled(False)
        controls_layout.addWidget(self.export_btn)
        
        controls_group.setLayout(controls_layout)
        left_layout.addWidget(controls_group)
        
        self.progress_bar = QProgressBar()
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
        
    def load_config(self):
        """Charger un fichier JSON et remplir les champs"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir une configuration", "configs/", "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            with open(path, 'r') as f:
                cfg = json.load(f)

            sim = cfg.get("simulation", {})
            agents = cfg.get("agents", {})
            params = cfg.get("parameters", {})

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

            name = cfg.get("metadata", {}).get("name", path.split("/")[-1])
            self.json_label.setText(f"✓ {name}")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de charger le fichier :\n{e}")


    def start_simulation(self):
        """Démarrer ou reprendre la simulation"""
        if self.model is None:
            # Créer nouveau modèle
            duration = self.duration_spin.value() * 365
            n_arch = self.arch_spin.value()
            n_coast = self.coast_spin.value()
            n_trawl = self.trawl_spin.value()
            
            self.model = FisheryModel(
                end_of_sim=duration,
                num_archipelago=n_arch,
                num_coastal=n_coast,
                num_trawler=n_trawl,
                verbose=False
            )
            
            self.model_data = {
                'stock_A': [], 'stock_B': [], 'stock_C': [], 'stock_D': [],
                'total_catch': [], 'avg_capital': []
            }
            
            self.progress_bar.setMaximum(duration)
            
        self.timer.start(10)  # 10ms entre chaque step
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.export_btn.setEnabled(False)
        
    def pause_simulation(self):
        """Mettre en pause"""
        self.timer.stop()
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        
    def step_simulation(self):
        """Exécuter un pas de simulation"""
        if self.model and self.model.running:
            self.model.step()
            
            # Collecter données
            self.model_data['stock_A'].append(self.model.get_region_stock('A'))
            self.model_data['stock_B'].append(self.model.get_region_stock('B'))
            self.model_data['stock_C'].append(self.model.get_region_stock('C'))
            self.model_data['stock_D'].append(self.model.get_region_stock('D'))
            self.model_data['total_catch'].append(sum(a.total_catch for a in self.model.agents))
            agents = list(self.model.agents)
            self.model_data['avg_capital'].append(
                sum(a.capital for a in agents) / len(agents) if agents else 0
            )
            
            # Mise à jour UI
            self.progress_bar.setValue(self.model.current_step)
            self.update_stats()
            
            # Mise à jour graphiques tous les 30 jours
            if self.model.current_step % 10 == 0:
                self.update_graphs()
            
            # Fin de simulation
            if not self.model.running:
                self.timer.stop()
                self.start_btn.setEnabled(False)
                self.pause_btn.setEnabled(False)
                self.export_btn.setEnabled(True)
                self.update_graphs()
                
    def reset_simulation(self):
        """Réinitialiser"""
        self.timer.stop()
        self.model = None
        self.model_data = {
            'stock_A': [], 'stock_B': [], 'stock_C': [], 'stock_D': [],
            'total_catch': [], 'avg_capital': []
        }
        self.progress_bar.setValue(0)
        self.stats_text.clear()
        self.stocks_canvas.fig.clear()
        self.stocks_canvas.draw()
        self.economics_canvas.fig.clear()
        self.economics_canvas.draw()
        
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        
    def update_stats(self):
        """Mettre à jour les statistiques affichées"""
        if self.model:
            summary = self.model.get_model_summary()
            
            text = f"""
                    Jour: {summary['current_step']} / {self.model.end_of_sim}
                    Année: {summary['current_year']}

                    === AGENTS ===
                    Total: {summary['num_agents']}
                    En mer: {summary['num_fishing']}
                    À la maison: {summary['num_at_home']}

                    === STOCKS ===
                    Total: {summary['total_stock']:,.0f}
                    Région A: {summary['stock_A']:,.0f}
                    Région B: {summary['stock_B']:,.0f}
                    Région C: {summary['stock_C']:,.0f}
                    Région D: {summary['stock_D']:,.0f}

                    === ÉCONOMIE ===
                    Captures totales: {summary['total_catch']:,.0f}
                    Capital moyen: {summary['avg_capital']:,.2f}

                    Météo: {'Mauvais temps' if summary['bad_weather'] else 'Beau temps'}
                    """
            self.stats_text.setText(text)
            
    def update_graphs(self):
        """Mettre à jour les graphiques"""
        self.stocks_canvas.plot_stocks(self.model_data)
        self.economics_canvas.plot_economics(self.model_data)
        if self.model:
            self.grid_canvas.plot_grid(self.model)
        
    def export_data(self):
        """Exporter les données"""
        if self.model:
            self.model.export_data()
            self.stats_text.append("\n✓ Données exportées!")
            
    def update_duration_label(self, years):
        days = years * 365
        self.duration_label.setText(f"= {days} jours")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()