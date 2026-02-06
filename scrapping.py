from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
import sys
import os
import time
import re
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import threading
from queue import Queue

# Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# PySide6
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QTextEdit, QProgressBar,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QSplitter, QTabWidget,
    QListWidget, QListWidgetItem, QStyleFactory, QSpinBox
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QTextCursor, QIcon, QAction

# ==============================================
# CONFIGURATION DES SUPERMARCHÉS - MISE À JOUR
# ==============================================

SUPERMARKETS = {
    "geant": {
        "name": "Géant",
        "base_url": "https://www.geantdrive.tn",
        "city_param": "tunis-city",
        "categories": {
            "boissons": "10-boissons",
            "epicerie": "31-epicerie",
            "cremerie_et_surgele": "130-cremerie-et-surgele",
            "le_marche": "160-le-marche",
            "hygiene_et_beaute": "210-hygiene-et-beaute",
            "univers_bebes": "322-univers-bebes",
            "produits_menagers": "268-produits-menagers",
            "maison": "821-maison"
        },
        "selectors": {
            "product": "div.product-item, article.product, .product-card, .product, .item",
            "name": ".product-title, h2.product-name, .product-list-name, .title, h2, h3",
            "price": ".price, .product-price, .current-price, [class*='price'], .amount",
            "image": "img.product-image, img[src*='product'], img, .product-image",
            "link": "a.product-link, a[href*='product'], a"
        }
    },
    "carrefour": {
        "name": "Carrefour",
        "base_url": "https://www.carrefour.tn",
        "drive_url": "https://www.carrefour.tn/default/drive",
        "categories": {
            "boissons": "boissons",
            "epicerie": "epicerie-salee",
            "fruits_legumes": "fruits-et-legumes",
            "viandes_poissons": "viandes-poissons-traiteur",
            "produits_laitiers": "produits-laitiers-et-oeufs",
            "boulangerie": "boulangerie-et-patisserie",
            "surgeles": "surgeles",
            "hygiene_beaute": "hygiene-et-beaute",
            "entretien": "entretien-et-nettoyage"
        },
        "selectors": {
            "product": ".product-item, .item-product, .product-tile, article, .product, .item",
            "name": ".product-name, .product-title, .product-list-name, h2, h3, .name",
            "price": ".price, .sales, .value, .product-price, [class*='price']",
            "image": "img.product-image, img[src*='product'], img",
            "link": "a.product-link, a[href*='/p/'], a"
        }
    },
    "mg": {
        "name": "Monoprix",
        "base_url": "https://www.monoprix.tn",
        "drive_url": "https://www.monoprix.tn/drive",
        "categories": {
            "epicerie": "epicerie",
            "boissons": "boissons",
            "frais": "frais",
            "surgeles": "surgeles",
            "hygiene": "hygiene-beaute",
            "bebe": "bebe",
            "entretien": "entretien-maison"
        },
        "selectors": {
            "product": "div.product, .product-item, .item, article, .card, .product-card",
            "name": ".product-name, .product-title, h2, h3, .title, .name",
            "price": ".price, .product-price, .amount, [class*='price'], .value",
            "image": "img, .product-image, img[src*='jpg'], img[src*='png']",
            "link": "a, .product-link, [href*='product']"
        }
    },
    "aziza": {
        "name": "Aziza",
        "base_url": "https://www.aziza.tn",
        "categories": {
            "alimentation": "alimentation",
            "boissons": "boissons",
            "hygiene": "hygiene-beaute",
            "maison": "maison"
        },
        "selectors": {
            "product": ".product, .product-block, .item, article, .card",
            "name": ".product-name, .product-title, h2, h3",
            "price": ".price, .product-price, [class*='price']",
            "image": "img.product-image, img",
            "link": "a.product-link, a"
        }
    }
}


# ==============================================
# UTILITAIRES AMÉLIORÉS
# ==============================================

def analyze_screenshot(filename):
    """Analyse un screenshot pour aider au débogage"""
    print(f"\n=== Analyse de {filename} ===")
    print("1. Ouvrez le screenshot dans un visualiseur d'images")
    print("2. Cherchez des éléments qui ressemblent à des produits")
    print("3. Notez:")
    print("   - La structure des cartes produits")
    print("   - Les classes CSS utilisées")
    print("   - La disposition des éléments")
    print("4. Ajoutez ces sélecteurs dans la configuration")
    return True


def create_chrome_options(headless=True, disable_images=False):
    """Crée des options Chrome optimisées"""
    chrome_options = Options()

    # Arguments de base
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')

    # Éviter la détection
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # User-agent
    chrome_options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )

    # Mode headless
    if headless:
        chrome_options.add_argument('--headless=new')

    # Images
    if disable_images:
        prefs = {"profile.managed_default_content_settings.images": 2}
        chrome_options.add_experimental_option("prefs", prefs)

    return chrome_options


def setup_driver_simple(headless=True):
    """Configuration simple du driver"""
    chrome_options = create_chrome_options(headless)

    # Désactiver les logs
    chrome_options.add_argument('--log-level=3')

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Masquer l'automation
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Timeouts
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(5)

        return driver
    except Exception as e:
        print(f"Erreur création driver: {e}")
        raise


def find_products_advanced(driver, supermarket_key):
    """Recherche avancée de produits avec multiples stratégies"""
    elements_found = []

    # Stratégie 1: Sélecteurs spécifiques
    selectors = SUPERMARKETS[supermarket_key].get('selectors', {})
    product_selectors = selectors.get('product', '').split(', ')

    # Ajouter des sélecteurs génériques
    all_selectors = product_selectors + [
        'div[class*="product"]', 'article[class*="product"]',
        '.item', '.card', '.product-card', '.product-block',
        '.product-tile', '.product-item', '.product-list-item',
        'div.product', 'article.product', 'section.product',
        'div.item', 'article.item', 'div.card', 'article.card'
    ]

    for selector in all_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector.strip())
            if elements:
                elements_found.extend(elements)
                print(f"  Trouvé {len(elements)} avec '{selector}'")
        except:
            continue

    # Stratégie 2: Recherche par contenu
    if len(elements_found) < 5:
        try:
            all_divs = driver.find_elements(By.CSS_SELECTOR, 'div, article, section, li')

            for elem in all_divs[:300]:  # Limiter pour performance
                try:
                    text = elem.text.strip()
                    if 10 < len(text) < 500:  # Taille raisonnable pour un produit
                        # Vérifier si ça ressemble à un produit
                        has_price = bool(re.search(r'\d[\d\s,\.]*(DT|TND|€|\$|دت)', text))
                        has_product_words = any(word in text.lower() for word in
                                                ['produit', 'article', 'item', 'product', 'prix', 'price'])

                        if has_price or has_product_words:
                            elements_found.append(elem)
                except:
                    continue
        except:
            pass

    # Éliminer les doublons
    unique_elements = []
    seen = set()
    for elem in elements_found:
        try:
            elem_id = elem.id
            if elem_id not in seen:
                seen.add(elem_id)
                unique_elements.append(elem)
        except:
            unique_elements.append(elem)

    return unique_elements[:200]  # Limiter à 200 éléments


def extract_data_smart(element, supermarket_key):
    """Extraction intelligente des données"""
    try:
        product = {
            'nom': '',
            'prix': '',
            'image_url': '',
            'product_url': '',
            'date_scraping': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # 1. Extraire tout le texte
        all_text = element.text.strip()
        lines = [line.strip() for line in all_text.split('\n') if line.strip()]

        # 2. Analyser les lignes pour trouver nom et prix
        if lines:
            # Chercher le prix dans toutes les lignes
            for line in lines:
                # Recherche de prix
                price_matches = re.findall(r'(\d[\d\s,\.]*)\s*(?:DT|TND|€|\$|دت|دينار)?', line)
                if price_matches:
                    price_str = price_matches[-1].replace(' ', '').replace(',', '.')
                    product['prix'] = price_str
                    break

            # Le nom est souvent la première ligne significative
            for line in lines:
                if len(line) > 3 and not re.search(r'\d[\d\s,\.]*(?:DT|TND|€|\$)', line):
                    product['nom'] = line[:100]
                    break

        # 3. Chercher une image
        try:
            images = element.find_elements(By.TAG_NAME, 'img')
            for img in images:
                src = img.get_attribute('src') or img.get_attribute('data-src')
                if src:
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = SUPERMARKETS[supermarket_key]['base_url'] + src
                    product['image_url'] = src
                    break
        except:
            pass

        # 4. Chercher un lien
        try:
            links = element.find_elements(By.TAG_NAME, 'a')
            for link in links:
                href = link.get_attribute('href')
                if href and ('http' in href or 'www' in href):
                    product['product_url'] = href
                    break
        except:
            pass

        # 5. Validation
        if not product['nom'] or len(product['nom']) < 2:
            # Essayer de récupérer le nom depuis les attributs
            try:
                name_attr = element.get_attribute('data-name') or element.get_attribute('alt') or element.get_attribute(
                    'title')
                if name_attr:
                    product['nom'] = name_attr[:100]
            except:
                pass

        if not product['nom'] or len(product['nom']) < 2:
            return None

        # Prix par défaut si non trouvé
        if not product['prix']:
            product['prix'] = '0.00'

        return product

    except Exception as e:
        print(f"Erreur extraction: {e}")
        return None


def scrape_url(driver, url, supermarket_key, category_name):
    """Scrape une URL spécifique"""
    products = []

    try:
        print(f"  Chargement: {url}")
        driver.get(url)
        time.sleep(4)  # Attente initiale

        # Vérifier si la page est chargée
        if "404" in driver.title or "erreur" in driver.title.lower():
            print(f"  ❌ Page non trouvée: {url}")
            return products

        # Attendre que le contenu soit chargé
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            pass

        # Défilement pour charger le contenu dynamique
        print("  Défilement...")
        for i in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)

        time.sleep(2)

        # Recherche des produits
        print("  Recherche des produits...")
        elements = find_products_advanced(driver, supermarket_key)

        if elements:
            print(f"  ⚡ {len(elements)} éléments trouvés")

            # Limiter le nombre d'éléments
            max_elements = min(len(elements), 100)

            for i, element in enumerate(elements[:max_elements]):
                try:
                    product_data = extract_data_smart(element, supermarket_key)
                    if product_data:
                        products.append(product_data)

                        # Affichage de progression
                        if len(products) % 10 == 0:
                            print(f"    {len(products)} produits extraits...")
                except:
                    continue
        else:
            print("  ⚠️ Aucun élément trouvé")

            # Prendre un screenshot pour analyse
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"debug_{supermarket_key}_{category_name}_{timestamp}.png"
                driver.save_screenshot(filename)
                print(f"  📸 Screenshot: {filename}")

                # Analyser le screenshot
                analyze_screenshot(filename)
            except:
                pass

    except Exception as e:
        print(f"  ❌ Erreur: {str(e)[:100]}")

    return products


# ==============================================
# THREAD DE SCRAPING ADAPTATIF
# ==============================================

class AdaptiveScrapingThread(QThread):
    """Thread de scraping adaptatif"""

    # Signaux
    log_signal = Signal(str, str)
    progress_signal = Signal(int, int)
    status_signal = Signal(str)
    product_signal = Signal(list)
    finished_signal = Signal(list)
    error_signal = Signal(str)

    def __init__(self, supermarket_key, categories, headless=True):
        super().__init__()
        self.supermarket_key = supermarket_key
        self.categories = categories
        self.headless = headless
        self.stop_requested = False

    def run(self):
        """Méthode principale"""
        all_products = []
        driver = None

        try:
            self.log_signal.emit(f"Scraping démarré pour {SUPERMARKETS[self.supermarket_key]['name']}", "info")
            self.status_signal.emit("Initialisation...")

            # Initialiser le driver
            driver = setup_driver_simple(self.headless)

            total_categories = len(self.categories)

            for i, (cat_key, cat_value) in enumerate(self.categories.items(), 1):
                if self.stop_requested:
                    break

                self.log_signal.emit(f"Catégorie {i}/{total_categories}: {cat_key}", "info")
                self.status_signal.emit(f"Traitement: {cat_key}")
                self.progress_signal.emit(i - 1, total_categories)

                # Générer l'URL
                supermarket = SUPERMARKETS[self.supermarket_key]
                if self.supermarket_key == "geant":
                    url = f"{supermarket['base_url']}/{supermarket['city_param']}/{cat_value}"
                elif self.supermarket_key == "carrefour":
                    url = f"{supermarket['drive_url']}/{cat_value}"
                elif self.supermarket_key == "mg":
                    url = f"{supermarket['drive_url']}/{cat_value}"
                elif self.supermarket_key == "aziza":
                    url = f"{supermarket['base_url']}/{cat_value}"
                else:
                    url = ""

                if url:
                    # Scraper l'URL
                    products = scrape_url(driver, url, self.supermarket_key, cat_key)

                    if products:
                        for product in products:
                            product['supermarche'] = SUPERMARKETS[self.supermarket_key]['name']
                            product['categorie'] = cat_key

                        all_products.extend(products)
                        self.product_signal.emit(products)

                        self.log_signal.emit(f"✓ {len(products)} produits trouvés", "success")
                        self.log_signal.emit(f"  Ex: {products[0].get('nom', 'N/A')[:50]}...", "info")
                    else:
                        self.log_signal.emit(f"✗ Aucun produit trouvé", "warning")

                # Pause entre les catégories
                if not self.stop_requested and i < total_categories:
                    time.sleep(3)

            if not self.stop_requested:
                self.progress_signal.emit(total_categories, total_categories)
                self.status_signal.emit("Terminé!")

                if all_products:
                    self.log_signal.emit(f"\n✅ Scraping terminé avec succès!", "success")
                    self.log_signal.emit(f"📊 Total: {len(all_products)} produits", "info")
                else:
                    self.log_signal.emit("\n⚠️ Aucun produit collecté", "warning")

            self.finished_signal.emit(all_products)

        except Exception as e:
            self.error_signal.emit(str(e))
            import traceback
            self.log_signal.emit(f"❌ Erreur critique: {str(e)}", "error")
            self.log_signal.emit(traceback.format_exc(), "error")

        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def stop(self):
        """Arrête le scraping"""
        self.stop_requested = True


# ==============================================
# OUTIL D'ANALYSE DE PAGES
# ==============================================

class PageAnalyzer:
    """Outil pour analyser les pages web et trouver les bons sélecteurs"""

    @staticmethod
    def analyze_page(url, supermarket_key):
        """Analyse une page pour trouver la structure des produits"""
        driver = None
        try:
            print(f"\n🔍 Analyse de: {url}")
            print("=" * 50)

            driver = setup_driver_simple(headless=False)
            driver.get(url)
            time.sleep(5)

            # 1. Analyser la structure HTML
            print("\n1. Structure HTML:")
            print("-" * 30)

            # Chercher des conteneurs potentiels
            selectors_to_check = ['div', 'article', 'section', 'li']

            for selector in selectors_to_check:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"  {selector}: {len(elements)} éléments")

                # Analyser quelques éléments
                for i, elem in enumerate(elements[:3]):
                    try:
                        classes = elem.get_attribute('class')
                        if classes:
                            print(f"    Élément {i + 1} classes: {classes}")
                    except:
                        pass

            # 2. Chercher des produits
            print("\n2. Recherche de produits:")
            print("-" * 30)

            product_patterns = [
                'product', 'item', 'card', 'article', 'produit'
            ]

            all_divs = driver.find_elements(By.CSS_SELECTOR, 'div')
            potential_products = []

            for div in all_divs[:100]:
                try:
                    classes = div.get_attribute('class')
                    text = div.text.strip()

                    if classes and any(pattern in classes.lower() for pattern in product_patterns):
                        print(f"  📦 Div avec classes product-like: {classes}")
                        potential_products.append(div)

                    if 20 < len(text) < 200:
                        if re.search(r'\d[\d\s,\.]*(DT|TND|€)', text):
                            print(f"  💰 Texte avec prix: {text[:50]}...")
                            potential_products.append(div)
                except:
                    continue

            print(f"\n  🎯 {len(potential_products)} produits potentiels trouvés")

            # 3. Analyser quelques produits potentiels
            if potential_products:
                print("\n3. Analyse détaillée:")
                print("-" * 30)

                for i, product in enumerate(potential_products[:3]):
                    print(f"\n  Produit {i + 1}:")
                    print(f"  {'=' * 20}")

                    # Afficher le HTML
                    try:
                        html = product.get_attribute('outerHTML')[:500]
                        print(f"  HTML: {html}...")
                    except:
                        pass

                    # Afficher le texte
                    try:
                        text = product.text.strip()
                        print(f"  Texte: {text}")
                    except:
                        pass

                    # Chercher des images
                    try:
                        images = product.find_elements(By.TAG_NAME, 'img')
                        for img in images[:2]:
                            src = img.get_attribute('src')
                            alt = img.get_attribute('alt')
                            print(f"  Image: src={src[:50] if src else 'N/A'}, alt={alt}")
                    except:
                        pass

            # 4. Suggestions de sélecteurs
            print("\n4. Suggestions de sélecteurs:")
            print("-" * 30)

            suggestions = []

            # Analyser les classes courantes
            class_counts = {}
            for div in all_divs[:200]:
                try:
                    classes = div.get_attribute('class')
                    if classes:
                        for cls in classes.split():
                            class_counts[cls] = class_counts.get(cls, 0) + 1
                except:
                    continue

            # Trouver les classes les plus courantes contenant des mots-clés
            product_keywords = ['product', 'item', 'card', 'article', 'prod', 'shop']

            for cls, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
                cls_lower = cls.lower()
                if any(keyword in cls_lower for keyword in product_keywords):
                    suggestions.append(f".{cls}")
                    print(f"  .{cls}: {count} occurrences")

            # Prendre un screenshot
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"analysis_{supermarket_key}_{timestamp}.png"
            driver.save_screenshot(filename)
            print(f"\n📸 Screenshot: {filename}")

            return suggestions

        except Exception as e:
            print(f"❌ Erreur d'analyse: {e}")
            return []

        finally:
            if driver:
                driver.quit()


# ==============================================
# APPLICATION PRINCIPALE
# ==============================================

class SupermarketScraperApp(QMainWindow):
    """Application principale avec analyseur intégré"""

    def __init__(self):
        super().__init__()
        self.products = []
        self.scraping_thread = None

        self.init_ui()
        self.create_menu()

    def init_ui(self):
        """Initialise l'interface"""
        self.setWindowTitle("🛒 Scraper Supermarchés - Version Analyse")
        self.setGeometry(100, 100, 1300, 750)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Titre
        title_label = QLabel("🛒 SCRAPER SUPERMARCHÉS TUNISIENS")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Splitter
        splitter = QSplitter(Qt.Horizontal)

        # Panel gauche
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # Panel droit
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([450, 850])
        main_layout.addWidget(splitter)

        # Barre de progression
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

        # Barre de statut
        self.status_bar = self.statusBar()
        self.status_label = QLabel("Prêt")
        self.status_bar.addPermanentWidget(self.status_label)

    def create_left_panel(self):
        """Crée le panel gauche"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        # Supermarché
        group1 = QGroupBox("Supermarché")
        layout1 = QVBoxLayout()

        self.supermarket_combo = QComboBox()
        for key, info in SUPERMARKETS.items():
            self.supermarket_combo.addItem(f"{info['name']} ({key})", key)

        layout1.addWidget(QLabel("Sélection:"))
        layout1.addWidget(self.supermarket_combo)
        group1.setLayout(layout1)
        layout.addWidget(group1)

        # Catégories
        group2 = QGroupBox("Catégories")
        layout2 = QVBoxLayout()

        self.categories_list = QListWidget()
        self.categories_list.setSelectionMode(QListWidget.MultiSelection)

        layout2.addWidget(QLabel("Sélectionnez:"))
        layout2.addWidget(self.categories_list)

        # Boutons
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("✅ Tout")
        select_all_btn.clicked.connect(self.select_all_categories)
        select_none_btn = QPushButton("❌ Rien")
        select_none_btn.clicked.connect(self.select_none_categories)

        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(select_none_btn)
        layout2.addLayout(btn_layout)

        group2.setLayout(layout2)
        layout.addWidget(group2)

        # Mode
        group3 = QGroupBox("Mode")
        layout3 = QVBoxLayout()

        self.headless_check = QCheckBox("Mode invisible (headless)")
        self.headless_check.setChecked(True)

        self.test_mode_check = QCheckBox("Mode test (1ère catégorie)")
        self.test_mode_check.setChecked(True)

        layout3.addWidget(self.headless_check)
        layout3.addWidget(self.test_mode_check)
        group3.setLayout(layout3)
        layout.addWidget(group3)

        # Actions
        group4 = QGroupBox("Actions")
        layout4 = QVBoxLayout()

        self.start_btn = QPushButton("🚀 Démarrer le scraping")
        self.start_btn.clicked.connect(self.start_scraping)

        self.analyze_btn = QPushButton("🔍 Analyser la page")
        self.analyze_btn.clicked.connect(self.analyze_page)

        self.stop_btn = QPushButton("⏹️ Arrêter")
        self.stop_btn.clicked.connect(self.stop_scraping)
        self.stop_btn.setEnabled(False)

        layout4.addWidget(self.start_btn)
        layout4.addWidget(self.analyze_btn)
        layout4.addWidget(self.stop_btn)
        group4.setLayout(layout4)
        layout.addWidget(group4)

        layout.addStretch()

        # Initialiser les catégories
        self.update_categories()

        return panel

    def create_right_panel(self):
        """Crée le panel droit"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Onglets
        self.tab_widget = QTabWidget()

        # Onglet Logs
        logs_tab = self.create_logs_tab()
        self.tab_widget.addTab(logs_tab, "📝 Logs")

        # Onglet Résultats
        results_tab = self.create_results_tab()
        self.tab_widget.addTab(results_tab, "📊 Résultats")

        # Onglet Analyse
        analysis_tab = self.create_analysis_tab()
        self.tab_widget.addTab(analysis_tab, "🔧 Analyse")

        layout.addWidget(self.tab_widget)

        return panel

    def create_logs_tab(self):
        """Crée l'onglet logs"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))

        layout.addWidget(self.log_text)

        return tab

    def create_results_tab(self):
        """Crée l'onglet résultats"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Supermarché", "Catégorie", "Nom", "Prix", "URL", "Date"
        ])

        layout.addWidget(self.results_table)

        return tab

    def create_analysis_tab(self):
        """Crée l'onglet analyse"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(False)
        self.analysis_text.setFont(QFont("Consolas", 9))
        self.analysis_text.setPlaceholderText(
            "Ici s'afficheront les résultats de l'analyse de page...\n\n"
            "Cliquez sur 'Analyser la page' pour examiner la structure d'une page web."
        )

        layout.addWidget(self.analysis_text)

        return tab

    def create_menu(self):
        """Crée le menu"""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Fichier")

        export_action = QAction("Exporter résultats", self)
        export_action.triggered.connect(self.export_results)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("Quitter", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def update_categories(self):
        """Met à jour les catégories"""
        self.categories_list.clear()

        supermarket_key = self.supermarket_combo.currentData()
        if not supermarket_key:
            return

        categories = SUPERMARKETS[supermarket_key]['categories']

        for cat_key, cat_value in categories.items():
            item = QListWidgetItem(cat_key.replace('_', ' ').title())
            item.setData(Qt.UserRole, (cat_key, cat_value))
            item.setCheckState(Qt.Checked)
            self.categories_list.addItem(item)

    def get_selected_categories(self):
        """Récupère les catégories sélectionnées"""
        selected_categories = {}

        # Si mode test, prendre seulement la première catégorie
        if self.test_mode_check.isChecked():
            for i in range(self.categories_list.count()):
                item = self.categories_list.item(i)
                if item.checkState() == Qt.Checked:
                    cat_key, cat_value = item.data(Qt.UserRole)
                    selected_categories[cat_key] = cat_value
                    break
        else:
            for i in range(self.categories_list.count()):
                item = self.categories_list.item(i)
                if item.checkState() == Qt.Checked:
                    cat_key, cat_value = item.data(Qt.UserRole)
                    selected_categories[cat_key] = cat_value

        return selected_categories

    def select_all_categories(self):
        """Sélectionne toutes les catégories"""
        for i in range(self.categories_list.count()):
            item = self.categories_list.item(i)
            item.setCheckState(Qt.Checked)

    def select_none_categories(self):
        """Désélectionne toutes les catégories"""
        for i in range(self.categories_list.count()):
            item = self.categories_list.item(i)
            item.setCheckState(Qt.Unchecked)

    def add_log(self, message, level="info"):
        """Ajoute un message au log"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        colors = {
            "info": "blue",
            "success": "green",
            "warning": "orange",
            "error": "red"
        }

        color = colors.get(level, "black")
        html = f'<span style="color:{color}">[{timestamp}] {message}</span><br>'

        self.log_text.moveCursor(QTextCursor.End)
        self.log_text.insertHtml(html)
        self.log_text.moveCursor(QTextCursor.End)

    def start_scraping(self):
        """Démarre le scraping"""
        supermarket_key = self.supermarket_combo.currentData()
        categories = self.get_selected_categories()

        if not categories:
            QMessageBox.warning(self, "Attention", "Sélectionnez au moins une catégorie!")
            return

        # Réinitialiser
        self.products = []
        self.log_text.clear()
        self.results_table.setRowCount(0)

        # Log
        self.add_log(f"Démarrage pour {SUPERMARKETS[supermarket_key]['name']}", "info")
        if self.test_mode_check.isChecked():
            self.add_log("Mode test activé", "warning")

        # Désactiver contrôles
        self.start_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # Créer thread
        self.scraping_thread = AdaptiveScrapingThread(
            supermarket_key,
            categories,
            self.headless_check.isChecked()
        )

        # Connecter signaux
        self.scraping_thread.log_signal.connect(self.add_log)
        self.scraping_thread.progress_signal.connect(self.update_progress)
        self.scraping_thread.status_signal.connect(self.update_status)
        self.scraping_thread.product_signal.connect(self.add_products)
        self.scraping_thread.finished_signal.connect(self.scraping_finished)
        self.scraping_thread.error_signal.connect(self.scraping_error)

        # Démarrer
        self.scraping_thread.start()

    def analyze_page(self):
        """Analyse une page pour trouver la structure"""
        supermarket_key = self.supermarket_combo.currentData()
        categories = self.get_selected_categories()

        if not categories:
            QMessageBox.warning(self, "Attention", "Sélectionnez au moins une catégorie!")
            return

        # Prendre la première catégorie
        cat_key, cat_value = list(categories.items())[0]

        # Générer URL
        supermarket = SUPERMARKETS[supermarket_key]
        if supermarket_key == "geant":
            url = f"{supermarket['base_url']}/{supermarket['city_param']}/{cat_value}"
        elif supermarket_key == "carrefour":
            url = f"{supermarket['drive_url']}/{cat_value}"
        elif supermarket_key == "mg":
            url = f"{supermarket['drive_url']}/{cat_value}"
        elif supermarket_key == "aziza":
            url = f"{supermarket['base_url']}/{cat_value}"
        else:
            url = ""

        if not url:
            QMessageBox.warning(self, "Erreur", "URL non générée!")
            return

        self.add_log(f"🔍 Analyse de: {url}", "info")

        # Désactiver boutons
        self.analyze_btn.setEnabled(False)
        self.start_btn.setEnabled(False)

        # Lancer analyse dans un thread
        analysis_thread = threading.Thread(
            target=self.run_analysis,
            args=(url, supermarket_key),
            daemon=True
        )
        analysis_thread.start()

    def run_analysis(self, url, supermarket_key):
        """Exécute l'analyse"""
        try:
            suggestions = PageAnalyzer.analyze_page(url, supermarket_key)

            # Afficher résultats
            self.analysis_text.clear()

            report = f"=== RAPPORT D'ANALYSE ===\n"
            report += f"URL: {url}\n"
            report += f"Supermarché: {SUPERMARKETS[supermarket_key]['name']}\n"
            report += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

            if suggestions:
                report += "SUGGESTIONS DE SÉLECTEURS:\n"
                report += "=" * 30 + "\n\n"
                for i, selector in enumerate(suggestions, 1):
                    report += f"{i}. {selector}\n"

                report += "\nAjoutez ces sélecteurs dans SUPERMARKETS:\n"
                report += f"SUPERMARKETS['{supermarket_key}']['selectors']['product'] = \"{', '.join(suggestions[:5])}\""
            else:
                report += "❌ Aucun sélecteur trouvé. Le site utilise peut-être:\n"
                report += "   - JavaScript pour charger le contenu\n"
                report += "   - Une structure personnalisée\n"
                report += "   - Des iframes\n\n"
                report += "CONSEILS:\n"
                report += "1. Désactivez le mode headless\n"
                report += "2. Inspectez la page avec F12\n"
                report += "3. Cherchez les classes des produits\n"

            self.analysis_text.setPlainText(report)
            self.add_log("✅ Analyse terminée", "success")

        except Exception as e:
            self.add_log(f"❌ Erreur analyse: {e}", "error")

        finally:
            # Réactiver boutons
            self.analyze_btn.setEnabled(True)
            self.start_btn.setEnabled(True)

    def stop_scraping(self):
        """Arrête le scraping"""
        if self.scraping_thread and self.scraping_thread.isRunning():
            self.scraping_thread.stop()
            self.add_log("Arrêt demandé...", "warning")

    def update_progress(self, current, total):
        """Met à jour la progression"""
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)

    def update_status(self, message):
        """Met à jour le statut"""
        self.status_label.setText(message)

    def add_products(self, products):
        """Ajoute des produits"""
        self.products.extend(products)

        # Mettre à jour le tableau
        self.results_table.setRowCount(len(self.products))

        for i, product in enumerate(self.products):
            self.results_table.setItem(i, 0, QTableWidgetItem(product.get('supermarche', '')))
            self.results_table.setItem(i, 1, QTableWidgetItem(product.get('categorie', '')))
            self.results_table.setItem(i, 2, QTableWidgetItem(product.get('nom', '')[:100]))
            self.results_table.setItem(i, 3, QTableWidgetItem(product.get('prix', '')))

            # URL raccourcie
            url = product.get('product_url', '')
            url_display = url[:50] + "..." if len(url) > 50 else url
            url_item = QTableWidgetItem(url_display)
            if url:
                url_item.setToolTip(url)
            self.results_table.setItem(i, 4, url_item)

            self.results_table.setItem(i, 5, QTableWidgetItem(product.get('date_scraping', '')))

    def scraping_finished(self, products):
        """Scraping terminé"""
        self.products = products

        # Réactiver contrôles
        self.start_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # Message
        if products:
            self.add_log(f"✅ Terminé! {len(products)} produits", "success")
            self.update_status(f"Terminé - {len(products)} produits")

            # Sauvegarder
            self.save_results()
        else:
            self.add_log("⚠️ Aucun produit trouvé", "warning")
            self.update_status("Terminé - Aucun produit")

            # Afficher conseils
            self.add_log("\n💡 CONSEILS:", "info")
            self.add_log("1. Essayez le mode visible (désactivez headless)", "info")
            self.add_log("2. Utilisez l'outil d'analyse pour trouver les bons sélecteurs", "info")
            self.add_log("3. Vérifiez si le site nécessite JavaScript", "info")

    def scraping_error(self, error_message):
        """Erreur de scraping"""
        self.add_log(f"❌ Erreur: {error_message}", "error")

        # Réactiver contrôles
        self.start_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        self.update_status("Erreur")

    def save_results(self):
        """Sauvegarde les résultats"""
        if not self.products:
            return

        try:
            os.makedirs('resultats', exist_ok=True)

            df = pd.DataFrame(self.products)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            supermarket_key = self.supermarket_combo.currentData()
            supermarket_name = SUPERMARKETS[supermarket_key]['name']

            # CSV
            csv_file = f"resultats/{supermarket_name}_{timestamp}.csv"
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')

            self.add_log(f"💾 Sauvegardé: {csv_file}", "success")

        except Exception as e:
            self.add_log(f"❌ Erreur sauvegarde: {e}", "error")

    def export_results(self):
        """Exporte les résultats"""
        if not self.products:
            QMessageBox.warning(self, "Attention", "Aucun résultat à exporter!")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Exporter", "", "CSV (*.csv);;Excel (*.xlsx);;Tous (*.*)"
        )

        if filename:
            try:
                df = pd.DataFrame(self.products)

                if filename.endswith('.xlsx'):
                    df.to_excel(filename, index=False)
                else:
                    df.to_csv(filename, index=False, encoding='utf-8-sig')

                QMessageBox.information(self, "Succès", f"Exporté vers:\n{filename}")

            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur export:\n{e}")


# ==============================================
# LANCEMENT
# ==============================================

def main():
    """Fonction principale"""
    app = QApplication(sys.argv)

    # Style
    app.setStyle(QStyleFactory.create("Fusion"))

    # Créer dossiers
    for folder in ['resultats', 'debug', 'analysis']:
        os.makedirs(folder, exist_ok=True)

    # Fenêtre
    window = SupermarketScraperApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()