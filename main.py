import sys
import os
import json
import base64
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
import email.utils

# Try importing feedparser; provide fallback if not installed yet
try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    import xml.etree.ElementTree as ET
    HAS_FEEDPARSER = False

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QGroupBox, QSplitter,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
    QTextBrowser, QDialog, QFormLayout, QSpinBox, QMessageBox,
    QMenu, QSystemTrayIcon, QFrame, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QDesktopServices, QColor

# ---------------------------------------------------------
# CONSTANTS & CYBERPUNK PALETTE
# ---------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
FEEDS_FILE = os.path.join(APP_DIR, "feeds.json")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")

CP_BG = "#050505"
CP_PANEL = "#111111"
CP_YELLOW = "#FCEE0A"
CP_CYAN = "#00F0FF"
CP_RED = "#FF003C"
CP_GREEN = "#00ff21"
CP_ORANGE = "#ff934b"
CP_DIM = "#3a3a3a"
CP_TEXT = "#E0E0E0"
CP_SUBTEXT = "#808080"

CYBER_STYLE = f"""
QMainWindow, QDialog {{
    background-color: {CP_BG};
}}
QWidget {{
    color: {CP_TEXT};
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 10pt;
}}
QLineEdit, QSpinBox, QTextEdit, QTextBrowser {{
    background-color: {CP_PANEL};
    color: {CP_CYAN};
    border: 1px solid {CP_DIM};
    padding: 5px;
    selection-background-color: {CP_CYAN};
    selection-color: {CP_BG};
}}
QLineEdit:focus, QSpinBox:focus, QTextBrowser:focus {{
    border: 1px solid {CP_CYAN};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 0px;
    border: none;
}}
QPushButton {{
    background-color: {CP_DIM};
    border: 1px solid {CP_DIM};
    color: white;
    padding: 6px 12px;
    font-weight: bold;
    border-radius: 0px;
}}
QPushButton:hover {{
    background-color: #222222;
    border: 1px solid {CP_YELLOW};
    color: {CP_YELLOW};
}}
QPushButton:pressed {{
    background-color: {CP_YELLOW};
    color: {CP_BG};
}}
QGroupBox {{
    border: 1px solid {CP_DIM};
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
    color: {CP_YELLOW};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
}}
QTreeWidget, QListWidget {{
    background-color: {CP_PANEL};
    border: 1px solid {CP_DIM};
    color: {CP_TEXT};
    outline: none;
}}
QTreeWidget::item, QListWidget::item {{
    padding: 5px;
    border-bottom: 1px solid #1a1a1a;
}}
QTreeWidget::item:hover, QListWidget::item:hover {{
    background-color: #1a1a1a;
    color: {CP_CYAN};
}}
QTreeWidget::item:selected, QListWidget::item:selected {{
    background-color: #222222;
    border-left: 3px solid {CP_CYAN};
    color: {CP_YELLOW};
}}
QMenu {{
    background-color: {CP_PANEL};
    color: {CP_TEXT};
    border: 1px solid {CP_CYAN};
}}
QMenu::item {{
    padding: 6px 20px 6px 15px;
}}
QMenu::item:selected {{
    background-color: {CP_CYAN};
    color: {CP_BG};
}}
QSplitter::handle {{
    background-color: {CP_DIM};
}}
QSplitter::handle:hover {{
    background-color: {CP_CYAN};
}}
QScrollBar:vertical {{
    background: {CP_BG};
    width: 10px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {CP_CYAN};
    min-height: 20px;
    border-radius: 0px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    background: none;
}}
QScrollBar:horizontal {{
    background: {CP_BG};
    height: 10px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background: {CP_CYAN};
    min-width: 20px;
    border-radius: 0px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: none;
}}
"""

# ---------------------------------------------------------
# UTILITY FUNCTIONS
# ---------------------------------------------------------
def parse_date(date_str):
    if not date_str:
        return datetime.now(timezone.utc)
    try:
        # Try ISO 8601
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    try:
        # Try RFC 2822 / 822
        dt = email.utils.parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)

def fetch_favicon_base64(feed_url):
    try:
        netloc = urllib.parse.urlparse(feed_url).netloc
        if not netloc:
            return ""
        fav_url = f"https://www.google.com/s2/favicons?domain={netloc}&sz=32"
        req = urllib.request.Request(fav_url, headers={"User-Agent": "myRSS/1.0"})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = response.read()
            if data:
                return base64.b64encode(data).decode("utf-8")
    except Exception:
        pass
    return ""

def base64_to_pixmap(b64_str):
    if not b64_str:
        return None
    try:
        data = base64.b64decode(b64_str)
        pix = QPixmap()
        if pix.loadFromData(data):
            return pix.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    except Exception:
        pass
    return None

def fallback_parse_feed(url):
    req = urllib.request.Request(url, headers={"User-Agent": "myRSS/1.0 CyberTerminal"})
    with urllib.request.urlopen(req, timeout=12) as response:
        content = response.read()

    root = ET.fromstring(content)
    tag = root.tag.lower()
    articles = []
    feed_title = "Untitled Feed"

    # RSS 2.0 / RSS 1.0
    channel = root.find("channel")
    if channel is not None:
        title_el = channel.find("title")
        if title_el is not None and title_el.text:
            feed_title = title_el.text.strip()
        for item in channel.findall("item"):
            t = item.find("title")
            l = item.find("link")
            d = item.find("description")
            p = item.find("pubDate")
            g = item.find("guid")

            link_val = l.text.strip() if (l is not None and l.text) else ""
            guid_val = g.text.strip() if (g is not None and g.text) else link_val
            articles.append({
                "id": guid_val or link_val,
                "title": t.text.strip() if (t is not None and t.text) else "Untitled",
                "link": link_val,
                "published": p.text.strip() if (p is not None and p.text) else datetime.now(timezone.utc).isoformat(),
                "read": False,
                "starred": False,
                "summary": d.text.strip() if (d is not None and d.text) else ""
            })
        return feed_title, articles

    # Atom Feed
    if "feed" in tag:
        t = root.find("{http://www.w3.org/2005/Atom}title")
        if t is not None and t.text:
            feed_title = t.text.strip()
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            et = entry.find("{http://www.w3.org/2005/Atom}title")
            el = entry.find("{http://www.w3.org/2005/Atom}link")
            es = entry.find("{http://www.w3.org/2005/Atom}summary")
            ec = entry.find("{http://www.w3.org/2005/Atom}content")
            ep = entry.find("{http://www.w3.org/2005/Atom}published")
            eu = entry.find("{http://www.w3.org/2005/Atom}updated")
            ei = entry.find("{http://www.w3.org/2005/Atom}id")

            link_val = el.attrib.get("href", "") if el is not None else ""
            guid_val = ei.text.strip() if (ei is not None and ei.text) else link_val
            summary_val = ""
            if es is not None and es.text:
                summary_val = es.text.strip()
            elif ec is not None and ec.text:
                summary_val = ec.text.strip()

            pub_val = datetime.now(timezone.utc).isoformat()
            if ep is not None and ep.text:
                pub_val = ep.text.strip()
            elif eu is not None and eu.text:
                pub_val = eu.text.strip()

            articles.append({
                "id": guid_val or link_val,
                "title": et.text.strip() if (et is not None and et.text) else "Untitled",
                "link": link_val,
                "published": pub_val,
                "read": False,
                "starred": False,
                "summary": summary_val
            })
        return feed_title, articles

    return feed_title, articles

# ---------------------------------------------------------
# BACKGROUND FETCH WORKER
# ---------------------------------------------------------
class FeedFetchWorker(QThread):
    finished_feed = pyqtSignal(dict, list, str, str, str)  # feed_data, new_articles, error, title, favicon
    all_done = pyqtSignal(int)

    def __init__(self, feeds):
        super().__init__()
        self.feeds = feeds

    def run(self):
        total_new_items = 0
        for feed in self.feeds:
            url = feed.get("url", "")
            if not url:
                continue

            error_msg = None
            fetched_articles = []
            feed_title = feed.get("title", "")
            favicon = feed.get("favicon", "")

            if not favicon:
                favicon = fetch_favicon_base64(url)

            try:
                if HAS_FEEDPARSER:
                    parsed = feedparser.parse(url)
                    if getattr(parsed, "bozo", 0) and not parsed.entries:
                        error_msg = str(getattr(parsed, "bozo_exception", "Parse error"))
                    else:
                        if not feed_title and hasattr(parsed, "feed") and hasattr(parsed.feed, "title"):
                            feed_title = parsed.feed.title
                        for entry in parsed.entries:
                            guid = entry.get("id", entry.get("link", ""))
                            title = entry.get("title", "Untitled")
                            link = entry.get("link", "")
                            summary = entry.get("summary", entry.get("description", ""))
                            pub = entry.get("published", entry.get("updated", datetime.now(timezone.utc).isoformat()))
                            fetched_articles.append({
                                "id": guid,
                                "title": title,
                                "link": link,
                                "published": pub,
                                "read": False,
                                "starred": False,
                                "summary": summary
                            })
                else:
                    parsed_title, fetched_articles = fallback_parse_feed(url)
                    if not feed_title:
                        feed_title = parsed_title
            except Exception as e:
                error_msg = str(e)

            existing_ids = {a.get("id", a.get("link")) for a in feed.get("articles", [])}
            new_articles = [a for a in fetched_articles if (a.get("id") or a.get("link")) not in existing_ids]
            total_new_items += len(new_articles)

            self.finished_feed.emit(feed, new_articles, error_msg or "", feed_title, favicon)

        self.all_done.emit(total_new_items)

# ---------------------------------------------------------
# DIALOGS
# ---------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle("// SETTINGS TERMINAL")
        self.resize(380, 240)
        self.settings = settings or {}

        layout = QVBoxLayout(self)
        grp = QGroupBox("CONFIG PROTOCOLS")
        form = QFormLayout()

        self.retention_spin = QSpinBox()
        self.retention_spin.setRange(1, 365)
        self.retention_spin.setValue(int(self.settings.get("retention_days", 7)))
        self.retention_spin.setSuffix(" DAYS")

        self.refresh_spin = QSpinBox()
        self.refresh_spin.setRange(1, 1440)
        self.refresh_spin.setValue(int(self.settings.get("auto_refresh_minutes", 30)))
        self.refresh_spin.setSuffix(" MINS")

        form.addRow("RETENTION PURGE:", self.retention_spin)
        form.addRow("AUTO-SYNC INTERVAL:", self.refresh_spin)
        grp.setLayout(form)

        btn_box = QHBoxLayout()
        save_btn = QPushButton("EXECUTE [SAVE]")
        save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton("ABORT")
        cancel_btn.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(save_btn)

        layout.addWidget(grp)
        layout.addStretch()
        layout.addLayout(btn_box)

    def save_and_close(self):
        self.settings["retention_days"] = self.retention_spin.value()
        self.settings["auto_refresh_minutes"] = self.refresh_spin.value()
        self.accept()

class AddEditFeedDialog(QDialog):
    def __init__(self, parent=None, feed=None):
        super().__init__(parent)
        self.feed = feed or {}
        is_edit = bool(feed)
        self.setWindowTitle("// EDIT INTEL STREAM" if is_edit else "// NEW INTEL STREAM")
        self.resize(460, 260)

        layout = QVBoxLayout(self)
        grp = QGroupBox("FEED SPECIFICATIONS")
        form = QFormLayout()

        self.url_input = QLineEdit(self.feed.get("url", ""))
        self.url_input.setPlaceholderText("https://domain/feed.xml")
        self.title_input = QLineEdit(self.feed.get("title", ""))
        self.title_input.setPlaceholderText("Leave empty to auto-detect")
        self.cat_input = QLineEdit(self.feed.get("category", "General"))
        self.tags_input = QLineEdit(", ".join(self.feed.get("tags", [])))
        self.tags_input.setPlaceholderText("tech, cyber, ai")

        form.addRow("URL:", self.url_input)
        form.addRow("TITLE:", self.title_input)
        form.addRow("CATEGORY:", self.cat_input)
        form.addRow("TAGS:", self.tags_input)
        grp.setLayout(form)

        btn_box = QHBoxLayout()
        ok_btn = QPushButton("CONFIRM")
        ok_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("CANCEL")
        cancel_btn.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(ok_btn)

        layout.addWidget(grp)
        layout.addLayout(btn_box)

    def save(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "INPUT ERROR", "Feed URL cannot be empty.")
            return
        self.feed["url"] = url
        self.feed["title"] = self.title_input.text().strip()
        self.feed["category"] = self.cat_input.text().strip() or "General"
        raw_tags = [t.strip() for t in self.tags_input.text().split(",") if t.strip()]
        self.feed["tags"] = raw_tags
        self.accept()

# ---------------------------------------------------------
# MAIN WINDOW
# ---------------------------------------------------------
class MyRSSApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("myRSS // CYBER INTEL TERMINAL")
        self.resize(1200, 750)
        self.setStyleSheet(CYBER_STYLE)

        self.current_filter_mode = "ALL"  # ALL, UNREAD, STARRED
        self.selected_filter_type = "ALL_FEEDS"  # ALL_FEEDS, CATEGORY, FEED, TAG, STARRED
        self.selected_filter_data = None
        self.current_article = None
        self.displayed_articles = []
        self.fetch_worker = None

        self.init_settings()
        self.load_feeds_data()
        self.apply_retention_purge()

        self.init_system_tray()
        self.init_ui()
        self.populate_sidebar()
        self.refresh_article_list()

        # Auto-refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.sync_all_feeds)
        interval_ms = max(1, self.settings.get("auto_refresh_minutes", 30)) * 60 * 1000
        self.refresh_timer.start(interval_ms)

        # Trigger initial sync if feeds exist
        if self.feeds:
            QTimer.singleShot(1000, self.sync_all_feeds)

    # --- SETTINGS & PERSISTENCE ---
    def init_settings(self):
        self.settings = {"retention_days": 7, "auto_refresh_minutes": 30}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    self.settings.update(json.load(f))
            except Exception:
                pass

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def load_feeds_data(self):
        self.feeds = []
        if os.path.exists(FEEDS_FILE):
            try:
                with open(FEEDS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.feeds = data.get("feeds", [])
            except Exception:
                self.feeds = []
        else:
            # Seed default starter feeds for immediate usability
            self.feeds = [
                {
                    "url": "https://feeds.arstechnica.com/arstechnica/index",
                    "title": "Ars Technica",
                    "category": "Tech",
                    "tags": ["tech", "science"],
                    "favicon": "",
                    "last_fetched": None,
                    "fetch_error": None,
                    "articles": []
                },
                {
                    "url": "https://news.ycombinator.com/rss",
                    "title": "Hacker News",
                    "category": "Tech",
                    "tags": ["tech", "startups"],
                    "favicon": "",
                    "last_fetched": None,
                    "fetch_error": None,
                    "articles": []
                }
            ]
            self.save_feeds_data()

    def save_feeds_data(self):
        try:
            with open(FEEDS_FILE, "w", encoding="utf-8") as f:
                json.dump({"feeds": self.feeds}, f, indent=2)
        except Exception as e:
            print(f"Error saving feeds: {e}")

    def apply_retention_purge(self):
        days = self.settings.get("retention_days", 7)
        threshold = datetime.now(timezone.utc) - timedelta(days=days)
        purged_count = 0
        for feed in self.feeds:
            surviving = []
            for art in feed.get("articles", []):
                if art.get("starred", False):
                    surviving.append(art)
                    continue
                pub_dt = parse_date(art.get("published", ""))
                if pub_dt >= threshold:
                    surviving.append(art)
                else:
                    purged_count += 1
            feed["articles"] = surviving
        if purged_count > 0:
            self.save_feeds_data()

    def init_system_tray(self):
        pix = QPixmap(16, 16)
        pix.fill(QColor(CP_CYAN))
        self.tray_icon = QSystemTrayIcon(QIcon(pix), self)
        self.tray_icon.show()

    # --- UI INITIALIZATION ---
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # 1. TOP HEADER / CONTROL STRIP
        top_bar = QHBoxLayout()
        title_lbl = QLabel("// myRSS // INTEL_TERMINAL")
        title_lbl.setStyleSheet(f"color: {CP_CYAN}; font-size: 13pt; font-weight: bold;")
        top_bar.addWidget(title_lbl)
        top_bar.addStretch()

        add_btn = QPushButton("+ ADD FEED")
        add_btn.setStyleSheet(f"border-color: {CP_GREEN}; color: {CP_GREEN};")
        add_btn.clicked.connect(self.action_add_feed)

        sync_btn = QPushButton("⟳ SYNC ALL")
        sync_btn.setStyleSheet(f"border-color: {CP_CYAN}; color: {CP_CYAN};")
        sync_btn.clicked.connect(self.sync_all_feeds)

        mark_all_read_btn = QPushButton("✓ MARK ALL READ")
        mark_all_read_btn.clicked.connect(self.action_mark_all_read)

        settings_btn = QPushButton("⚙ SETTINGS")
        settings_btn.clicked.connect(self.open_settings)

        restart_btn = QPushButton("↺ RESTART")
        restart_btn.setStyleSheet(f"border-color: {CP_RED}; color: {CP_RED};")
        restart_btn.clicked.connect(self.restart_app)

        top_bar.addWidget(add_btn)
        top_bar.addWidget(sync_btn)
        top_bar.addWidget(mark_all_read_btn)
        top_bar.addWidget(settings_btn)
        top_bar.addWidget(restart_btn)
        root_layout.addLayout(top_bar)

        # 2. MAIN HORIZONTAL SPLITTER
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # SIDEBAR (LEFT)
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 5, 0)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search headlines & summaries...")
        self.search_input.textChanged.connect(self.on_search_changed)
        sidebar_layout.addWidget(self.search_input)

        # Quick State Buttons
        state_filter_box = QHBoxLayout()
        self.btn_filter_all = QPushButton("ALL")
        self.btn_filter_unread = QPushButton("UNREAD")
        self.btn_filter_starred = QPushButton("★ STARRED")

        for b in [self.btn_filter_all, self.btn_filter_unread, self.btn_filter_starred]:
            b.setCheckable(True)
        self.btn_filter_all.setChecked(True)

        self.btn_filter_all.clicked.connect(lambda: self.set_state_filter("ALL"))
        self.btn_filter_unread.clicked.connect(lambda: self.set_state_filter("UNREAD"))
        self.btn_filter_starred.clicked.connect(lambda: self.set_state_filter("STARRED"))

        state_filter_box.addWidget(self.btn_filter_all)
        state_filter_box.addWidget(self.btn_filter_unread)
        state_filter_box.addWidget(self.btn_filter_starred)
        sidebar_layout.addLayout(state_filter_box)

        # Navigation Tree
        self.nav_tree = QTreeWidget()
        self.nav_tree.setHeaderHidden(True)
        self.nav_tree.setRootIsDecorated(False)
        self.nav_tree.setIndentation(0)
        self.nav_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.nav_tree.customContextMenuRequested.connect(self.show_sidebar_context_menu)
        self.nav_tree.itemClicked.connect(self.on_sidebar_item_clicked)
        sidebar_layout.addWidget(self.nav_tree, 1)

        splitter.addWidget(sidebar_widget)

        # ARTICLE LIST (CENTER)
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(5, 0, 5, 0)

        self.list_header = QLabel("FEED // INCOMING TRANSMISSIONS")
        self.list_header.setStyleSheet(f"color: {CP_YELLOW}; font-weight: bold; padding: 4px 0;")
        list_layout.addWidget(self.list_header)

        self.article_list_widget = QListWidget()
        self.article_list_widget.setWordWrap(True)
        self.article_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.article_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.article_list_widget.customContextMenuRequested.connect(self.show_article_context_menu)
        self.article_list_widget.itemClicked.connect(self.on_article_selected)
        list_layout.addWidget(self.article_list_widget, 1)

        splitter.addWidget(list_container)

        # ARTICLE READER PANE (RIGHT)
        reader_container = QWidget()
        reader_layout = QVBoxLayout(reader_container)
        reader_layout.setContentsMargins(5, 0, 0, 0)

        # Article Header Strip
        self.reader_title = QLabel("NO TRANSMISSION SELECTED")
        self.reader_title.setWordWrap(True)
        self.reader_title.setStyleSheet(f"color: {CP_CYAN}; font-size: 13pt; font-weight: bold;")

        self.reader_meta = QLabel("// SELECT AN INTEL RECORD TO DECRYPT")
        self.reader_meta.setStyleSheet(f"color: {CP_SUBTEXT}; font-size: 9pt;")

        reader_toolbar = QHBoxLayout()
        self.btn_toggle_star = QPushButton("★ STAR")
        self.btn_toggle_star.clicked.connect(self.action_toggle_star_current)
        self.btn_toggle_read = QPushButton("MARK READ")
        self.btn_toggle_read.clicked.connect(self.action_toggle_read_current)
        self.btn_copy_link = QPushButton("🔗 COPY LINK")
        self.btn_copy_link.clicked.connect(self.action_copy_current_link)
        self.btn_open_browser = QPushButton("↗ OPEN IN BROWSER")
        self.btn_open_browser.setStyleSheet(f"border-color: {CP_YELLOW}; color: {CP_YELLOW};")
        self.btn_open_browser.clicked.connect(self.action_open_browser_current)

        reader_toolbar.addWidget(self.btn_toggle_star)
        reader_toolbar.addWidget(self.btn_toggle_read)
        reader_toolbar.addWidget(self.btn_copy_link)
        reader_toolbar.addWidget(self.btn_open_browser)
        reader_toolbar.addStretch()

        reader_layout.addWidget(self.reader_title)
        reader_layout.addWidget(self.reader_meta)
        reader_layout.addLayout(reader_toolbar)

        # Text Viewer
        self.article_browser = QTextBrowser()
        self.article_browser.setOpenExternalLinks(True)
        reader_layout.addWidget(self.article_browser, 1)

        splitter.addWidget(reader_container)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 4)
        root_layout.addWidget(splitter, 1)

        # 3. STATUS BAR (Fixed compact height with panel border)
        self.status_bar_lbl = QLabel("// SYSTEM READY // INTEL STREAM ACTIVE")
        self.status_bar_lbl.setFixedHeight(22)
        self.status_bar_lbl.setStyleSheet(f"""
            background-color: {CP_PANEL};
            color: {CP_SUBTEXT};
            border-top: 1px solid {CP_DIM};
            font-size: 9pt;
            padding: 2px 6px;
        """)
        root_layout.addWidget(self.status_bar_lbl, 0)

    # --- SIDEBAR POPULATION ---
    def populate_sidebar(self):
        self.nav_tree.clear()

        # Keep the sidebar focused on one flat list of feeds.
        for feed in self.feeds:
            unread_count = len([a for a in feed.get("articles", []) if not a.get("read", False)])
            feed_item = QTreeWidgetItem(self.nav_tree, [f"{feed.get('title') or feed.get('url')} [{unread_count}]"])
            feed_item.setData(0, Qt.ItemDataRole.UserRole, ("FEED", feed))
            pix = base64_to_pixmap(feed.get("favicon", ""))
            if pix:
                feed_item.setIcon(0, QIcon(pix))
            if feed.get("fetch_error"):
                feed_item.setForeground(0, QColor(CP_RED))

        self.nav_tree.expandAll()

    # --- SIDEBAR CLICKS & FILTERING ---
    def on_sidebar_item_clicked(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data[0] == "SECTION":
            return
        filter_type, filter_payload = data
        self.selected_filter_type = filter_type
        self.selected_filter_data = filter_payload
        self.refresh_article_list()

    def set_state_filter(self, mode):
        self.current_filter_mode = mode
        self.btn_filter_all.setChecked(mode == "ALL")
        self.btn_filter_unread.setChecked(mode == "UNREAD")
        self.btn_filter_starred.setChecked(mode == "STARRED")
        self.refresh_article_list()

    def on_search_changed(self):
        self.refresh_article_list()

    # --- ARTICLE LIST REFRESH & POPULATION ---
    def refresh_article_list(self):
        self.article_list_widget.clear()
        self.displayed_articles = []

        query = self.search_input.text().strip().lower()

        # Gather base candidates according to selected navigation node
        candidate_articles = []
        feed_title_lookup = {}
        for feed in self.feeds:
            title = feed.get("title") or feed.get("url")
            feed_title_lookup[feed.get("url")] = title

            match = False
            if self.selected_filter_type == "ALL_FEEDS":
                match = True
            elif self.selected_filter_type == "FEED":
                match = (feed.get("url") == self.selected_filter_data.get("url"))
            elif self.selected_filter_type == "CATEGORY":
                match = (feed.get("category", "General") == self.selected_filter_data)
            elif self.selected_filter_type == "TAG":
                match = (self.selected_filter_data in feed.get("tags", []))

            if match:
                for a in feed.get("articles", []):
                    candidate_articles.append((a, feed))

        # Filter by state (ALL, UNREAD, STARRED)
        filtered = []
        for a, f in candidate_articles:
            if self.current_filter_mode == "UNREAD" and a.get("read", False):
                continue
            if self.current_filter_mode == "STARRED" and not a.get("starred", False):
                continue

            # Filter by search
            if query:
                t_match = query in a.get("title", "").lower()
                s_match = query in a.get("summary", "").lower()
                if not (t_match or s_match):
                    continue

            filtered.append((a, f))

        # Sort descending by published datetime
        filtered.sort(key=lambda pair: parse_date(pair[0].get("published")), reverse=True)
        self.displayed_articles = filtered

        # Update Header
        scope_name = "ALL TRANSMISSIONS"
        if self.selected_filter_type == "FEED":
            scope_name = self.selected_filter_data.get("title") or self.selected_filter_data.get("url")
        elif self.selected_filter_type == "CATEGORY":
            scope_name = f"CATEGORY: {self.selected_filter_data}"
        elif self.selected_filter_type == "TAG":
            scope_name = f"TAG: #{self.selected_filter_data}"

        self.list_header.setText(f"// {scope_name} [{len(filtered)} ITEMS]")

        for art, feed in filtered:
            is_read = art.get("read", False)
            is_starred = art.get("starred", False)
            star_symbol = "★" if is_starred else "☆"
            read_marker = " " if is_read else "●"

            title = art.get("title", "Untitled")
            pub_str = art.get("published", "")
            feed_name = feed.get("title") or feed.get("url")

            item_text = f"{star_symbol} {read_marker} {title}\n    [{feed_name}] {pub_str}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, (art, feed))

            if not is_read:
                item.setForeground(QColor(CP_CYAN))
            else:
                item.setForeground(QColor(CP_SUBTEXT))

            if is_starred:
                item.setForeground(QColor(CP_YELLOW))

            self.article_list_widget.addItem(item)

    # --- ARTICLE SELECTION & READING ---
    def on_article_selected(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        art, feed = data
        self.current_article = (art, feed)

        # Mark read on open
        if not art.get("read", False):
            art["read"] = True
            self.save_feeds_data()
            self.populate_sidebar()
            # Update list item color
            item.setForeground(QColor(CP_YELLOW) if art.get("starred") else QColor(CP_SUBTEXT))
            item.setText(item.text().replace("●", " "))

        self.display_article_content(art, feed)

    def display_article_content(self, art, feed):
        self.reader_title.setText(art.get("title", "Untitled"))
        feed_title = feed.get("title") or feed.get("url")
        pub = art.get("published", "Unknown Date")
        self.reader_meta.setText(f"SOURCE: {feed_title} // PUBLISHED: {pub} // CATEGORY: {feed.get('category')}")

        self.btn_toggle_star.setText("★ UNSTAR" if art.get("starred") else "★ STAR")
        self.btn_toggle_read.setText("MARK UNREAD" if art.get("read") else "MARK READ")

        # Cyberpunk Styled HTML Reader View
        body_content = art.get("summary", "No transmission content available.")
        html = f"""
        <html>
        <head>
            <style>
                body {{
                    background-color: {CP_PANEL};
                    color: {CP_TEXT};
                    font-family: 'Consolas', monospace;
                    font-size: 10pt;
                    line-height: 1.6;
                    padding: 10px;
                }}
                a {{
                    color: {CP_CYAN};
                    text-decoration: none;
                    font-weight: bold;
                }}
                a:hover {{
                    color: {CP_YELLOW};
                    text-decoration: underline;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                    border: 1px solid {CP_DIM};
                }}
                blockquote {{
                    border-left: 3px solid {CP_CYAN};
                    margin-left: 0;
                    padding-left: 10px;
                    color: {CP_SUBTEXT};
                }}
                h1, h2, h3, h4 {{
                    color: {CP_YELLOW};
                    margin-top: 15px;
                }}
                code, pre {{
                    background-color: #050505;
                    border: 1px solid {CP_DIM};
                    padding: 3px;
                    color: {CP_GREEN};
                }}
            </style>
        </head>
        <body>
            {body_content}
        </body>
        </html>
        """
        self.article_browser.setHtml(html)

    # --- ACTIONS & CONTEXT MENUS ---
    def action_toggle_star_current(self):
        if not self.current_article:
            return
        art, feed = self.current_article
        art["starred"] = not art.get("starred", False)
        self.save_feeds_data()
        self.btn_toggle_star.setText("★ UNSTAR" if art.get("starred") else "★ STAR")
        self.refresh_article_list()

    def action_toggle_read_current(self):
        if not self.current_article:
            return
        art, feed = self.current_article
        art["read"] = not art.get("read", False)
        self.save_feeds_data()
        self.populate_sidebar()
        self.refresh_article_list()
        self.btn_toggle_read.setText("MARK UNREAD" if art.get("read") else "MARK READ")

    def action_copy_current_link(self):
        if not self.current_article:
            return
        art, _ = self.current_article
        link = art.get("link", "")
        if link:
            QApplication.clipboard().setText(link)
            self.status_bar_lbl.setText(f"// LINK COPIED TO CLIPBOARD: {link}")

    def action_open_browser_current(self):
        if not self.current_article:
            return
        art, _ = self.current_article
        link = art.get("link", "")
        if link:
            QDesktopServices.openUrl(QUrl(link))

    def action_add_feed(self):
        dlg = AddEditFeedDialog(self)
        if dlg.exec():
            new_feed = dlg.feed
            new_feed["favicon"] = ""
            new_feed["last_fetched"] = None
            new_feed["fetch_error"] = None
            new_feed["articles"] = []
            self.feeds.append(new_feed)
            self.save_feeds_data()
            self.populate_sidebar()
            self.sync_all_feeds()

    def action_mark_all_read(self):
        for feed in self.feeds:
            for art in feed.get("articles", []):
                art["read"] = True
        self.save_feeds_data()
        self.populate_sidebar()
        self.refresh_article_list()
        self.status_bar_lbl.setText("// ALL ARTICLES MARKED READ")

    def show_sidebar_context_menu(self, pos):
        item = self.nav_tree.itemAt(pos)
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        node_type, payload = data

        menu = QMenu(self)
        if node_type == "FEED":
            feed = payload
            act_sync = menu.addAction("⟳ Sync Feed")
            act_edit = menu.addAction("⚙ Edit Feed")
            act_mark = menu.addAction("✓ Mark Feed Read")
            act_copy_url = menu.addAction("🔗 Copy Feed URL")
            act_delete = menu.addAction("✖ Delete Feed")

            action = menu.exec(self.nav_tree.viewport().mapToGlobal(pos))
            if action == act_sync:
                self.sync_single_feed(feed)
            elif action == act_edit:
                dlg = AddEditFeedDialog(self, feed)
                if dlg.exec():
                    self.save_feeds_data()
                    self.populate_sidebar()
            elif action == act_mark:
                for a in feed.get("articles", []):
                    a["read"] = True
                self.save_feeds_data()
                self.populate_sidebar()
                self.refresh_article_list()
            elif action == act_copy_url:
                QApplication.clipboard().setText(feed.get("url", ""))
            elif action == act_delete:
                if QMessageBox.question(self, "DELETE STREAM", f"Terminate stream '{feed.get('title')}'?") == QMessageBox.StandardButton.Yes:
                    self.feeds.remove(feed)
                    self.save_feeds_data()
                    self.populate_sidebar()
                    self.refresh_article_list()

    def show_article_context_menu(self, pos):
        item = self.article_list_widget.itemAt(pos)
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        art, feed = data

        menu = QMenu(self)
        act_open = menu.addAction("↗ Open in Browser")
        act_copy = menu.addAction("🔗 Copy Article Link")
        act_star = menu.addAction("★ Unstar" if art.get("starred") else "★ Star")
        act_read = menu.addAction("Mark as Unread" if art.get("read") else "Mark as Read")

        action = menu.exec(self.article_list_widget.viewport().mapToGlobal(pos))
        if action == act_open:
            QDesktopServices.openUrl(QUrl(art.get("link", "")))
        elif action == act_copy:
            QApplication.clipboard().setText(art.get("link", ""))
        elif action == act_star:
            art["starred"] = not art.get("starred", False)
            self.save_feeds_data()
            self.refresh_article_list()
        elif action == act_read:
            art["read"] = not art.get("read", False)
            self.save_feeds_data()
            self.populate_sidebar()
            self.refresh_article_list()

    # --- FEED SYNC & WORKER ---
    def sync_all_feeds(self):
        if self.fetch_worker and self.fetch_worker.isRunning():
            self.status_bar_lbl.setText("// SYNC IN PROGRESS... PLEASE WAIT")
            return

        self.status_bar_lbl.setText("// CONTACTING INTEL NODES... SYNCING")
        self.fetch_worker = FeedFetchWorker(self.feeds)
        self.fetch_worker.finished_feed.connect(self.on_feed_sync_finished)
        self.fetch_worker.all_done.connect(self.on_all_feeds_synced)
        self.fetch_worker.start()

    def sync_single_feed(self, feed):
        if self.fetch_worker and self.fetch_worker.isRunning():
            return
        self.fetch_worker = FeedFetchWorker([feed])
        self.fetch_worker.finished_feed.connect(self.on_feed_sync_finished)
        self.fetch_worker.all_done.connect(self.on_all_feeds_synced)
        self.fetch_worker.start()

    def on_feed_sync_finished(self, feed, new_articles, error_msg, title, favicon):
        feed["last_fetched"] = datetime.now(timezone.utc).isoformat()
        feed["fetch_error"] = error_msg if error_msg else None
        if title and not feed.get("title"):
            feed["title"] = title
        if favicon and not feed.get("favicon"):
            feed["favicon"] = favicon

        if new_articles:
            if "articles" not in feed:
                feed["articles"] = []
            # Prepend new articles
            feed["articles"] = new_articles + feed["articles"]

    def on_all_feeds_synced(self, total_new):
        self.save_feeds_data()
        self.populate_sidebar()
        self.refresh_article_list()

        now_str = datetime.now().strftime("%H:%M:%S")
        self.status_bar_lbl.setText(f"// SYNC COMPLETE AT {now_str} // {total_new} NEW ITEMS DETECTED")

        # Desktop Toast Notification
        if total_new > 0 and self.tray_icon:
            self.tray_icon.showMessage(
                "myRSS // NEW INTEL TRANSMISSION",
                f"Discovered {total_new} new article(s) across intel nodes.",
                QSystemTrayIcon.MessageIcon.Information,
                4000
            )

    # --- SETTINGS & RESTART ---
    def open_settings(self):
        dlg = SettingsDialog(self, self.settings)
        if dlg.exec():
            self.save_settings()
            # Update auto-refresh interval
            mins = max(1, self.settings.get("auto_refresh_minutes", 30))
            self.refresh_timer.start(mins * 60 * 1000)
            # Reapply retention purge
            self.apply_retention_purge()
            self.populate_sidebar()
            self.refresh_article_list()
            self.status_bar_lbl.setText(f"// CONFIG SAVED: RETENTION={self.settings.get('retention_days')}d, SYNC={mins}m")

    def restart_app(self):
        os.execv(sys.executable, [sys.executable] + sys.argv)

# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    window = MyRSSApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
