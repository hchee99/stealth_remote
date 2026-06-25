import sys
import json
import os
import ctypes
from ctypes import wintypes
import logging

from PyQt5.QtCore import QUrl, Qt, pyqtSignal, QTimer, QPoint
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QSlider, QLabel, QPushButton, QDialog, QLineEdit, QFormLayout,
                             QFrame)
from PyQt5.QtWebEngineWidgets import QWebEngineView

# 로그 설정
logging.basicConfig(filename='stealth_debug.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("=== 스텔스 플레이어 시작 (AHK 연동 모드) ===")

CONFIG_FILE = 'stealth_merged_config.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {"opacity": 30, "ext_opacity": 30, "last_url": "https://www.youtube.com", "pip_url": "https://chzzk.naver.com/live"}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# ──────────────────────────────────────────────
# 설정 다이얼로그 (단축키 입력창 제거 - AHK에서 직접 제어)
# ──────────────────────────────────────────────
class SettingsDialog(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ 스텔스 설정")
        self.setFixedSize(300, 120)
        self.config = dict(current_config)

        layout = QFormLayout(self)
        self.opacity_input = QSlider(Qt.Horizontal)
        self.opacity_input.setRange(0, 100)
        self.opacity_input.setValue(self.config.get("opacity", 30))
        layout.addRow("내장 브라우저 투명도(%):", self.opacity_input)

        self.ext_opacity_input = QSlider(Qt.Horizontal)
        self.ext_opacity_input.setRange(0, 100)
        self.ext_opacity_input.setValue(self.config.get("ext_opacity", 30))
        layout.addRow("PIP창 투명도(%):", self.ext_opacity_input)

        save_btn = QPushButton("저장 및 적용")
        save_btn.clicked.connect(self.save_and_close)
        layout.addRow(save_btn)

    def save_and_close(self):
        self.config["opacity"] = self.opacity_input.value()
        self.config["ext_opacity"] = self.ext_opacity_input.value()
        save_config(self.config)
        self.accept()

# ──────────────────────────────────────────────
# 리모컨 위젯
# ──────────────────────────────────────────────
class RemoteControl(QWidget):
    def __init__(self, player, config):
        super().__init__()
        self.player = player
        self.config = config
        self.current_mode = "browser"

        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.main_widget = QWidget(self)
        self.main_widget.setStyleSheet("""
            QWidget     { background-color: rgba(20,20,20,248); color: white; border-radius: 10px; }
            QPushButton { border-radius: 4px; padding: 5px 8px; font-weight: bold; }
            QLineEdit   { background-color: #111; border: 1px solid #555; padding: 5px; border-radius: 3px; color: white; }
            QSlider::groove:horizontal { height: 4px; background: #444; border-radius: 2px; }
            QSlider::handle:horizontal { width: 12px; height: 12px; margin: -4px 0; background: #aaa; border-radius: 6px; }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.main_widget)
        self.root_layout = QVBoxLayout(self.main_widget)
        self.root_layout.setContentsMargins(12, 10, 12, 10)
        self.root_layout.setSpacing(7)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(4)
        
        self.btn_browser_tab = QPushButton("📺 내장")
        self.btn_pip_tab     = QPushButton("🌐 PIP")
        self.btn_hide = QPushButton("👻 잠수")
        self.btn_hide.setStyleSheet("background-color: #6c757d;")
        self.btn_hide.clicked.connect(self.player.hide_signal.emit)

        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedWidth(30)
        settings_btn.setStyleSheet("background-color: #444;")
        settings_btn.clicked.connect(self.player.open_settings)
        
        exit_btn = QPushButton("❌")
        exit_btn.setFixedWidth(30)
        exit_btn.setStyleSheet("background-color: #dc3545;")
        exit_btn.clicked.connect(self.player.exit_signal.emit)

        for btn in (self.btn_browser_tab, self.btn_pip_tab, self.btn_hide, settings_btn, exit_btn):
            btn.setFixedHeight(28)
            tab_row.addWidget(btn)
            
        self.root_layout.addLayout(tab_row)
        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setStyleSheet("color: #444;")
        self.root_layout.addWidget(line)

        # 내장 브라우저 패널
        self.browser_panel = QWidget()
        bp = QVBoxLayout(self.browser_panel); bp.setContentsMargins(0, 0, 0, 0); bp.setSpacing(6)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("유튜브 URL 입력 후 Enter")
        self.url_input.setText(self.config.get("last_url", "https://www.youtube.com"))
        self.url_input.returnPressed.connect(self.player.load_url_from_remote)
        bp.addWidget(self.url_input)

        br_row = QHBoxLayout()
        br_row.addWidget(QLabel("투명도:"))
        self.browser_opacity_slider = QSlider(Qt.Horizontal)
        self.browser_opacity_slider.setRange(0, 100)
        self.browser_opacity_slider.setValue(self.config.get("opacity", 30))
        self.browser_opacity_slider.valueChanged.connect(self.player.change_browser_opacity)
        br_row.addWidget(self.browser_opacity_slider)
        br_row.addWidget(QLabel("  크기:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(300, 1000)
        self.size_slider.setValue(480)
        self.size_slider.valueChanged.connect(self.player.change_size)
        br_row.addWidget(self.size_slider)
        bp.addLayout(br_row)
        self.root_layout.addWidget(self.browser_panel)

        # PIP 패널
        self.pip_panel = QWidget()
        pp = QVBoxLayout(self.pip_panel); pp.setContentsMargins(0, 0, 0, 0); pp.setSpacing(6)
        chrome_row = QHBoxLayout()
        self.chrome_url_input = QLineEdit()
        self.chrome_url_input.setText(self.config.get("pip_url", "https://chzzk.naver.com/live"))
        chrome_row.addWidget(self.chrome_url_input)
        chrome_btn = QPushButton("🌐 크롬 띄우기")
        chrome_btn.setStyleSheet("background-color: #0078D7;")
        chrome_btn.clicked.connect(self.player.launch_chrome)
        chrome_row.addWidget(chrome_btn)
        pp.addLayout(chrome_row)

        pip_row = QHBoxLayout()
        ext_btn = QPushButton("🎯 PIP창 타겟 (3초)")
        ext_btn.setStyleSheet("background-color: #28a745;")
        ext_btn.clicked.connect(self.player.start_ext_capture)
        pip_row.addWidget(ext_btn)
        self.ext_status_label = QLabel("대기중...")
        self.ext_status_label.setStyleSheet("color: silver; font-size: 9pt;")
        pip_row.addWidget(self.ext_status_label)
        pip_row.addStretch()
        pip_row.addWidget(QLabel("투명도:"))
        self.ext_opacity_slider = QSlider(Qt.Horizontal)
        self.ext_opacity_slider.setRange(0, 100)
        self.ext_opacity_slider.setValue(self.config.get("ext_opacity", 30))
        self.ext_opacity_slider.valueChanged.connect(self.player.change_ext_opacity)
        self.ext_opacity_slider.setFixedWidth(90)
        pip_row.addWidget(self.ext_opacity_slider)
        pp.addLayout(pip_row)
        self.root_layout.addWidget(self.pip_panel)

        self.btn_browser_tab.clicked.connect(lambda: self.set_mode("browser"))
        self.btn_pip_tab.clicked.connect(lambda: self.set_mode("pip"))
        self.set_mode("pip")

    def set_mode(self, mode):
        self.current_mode = mode
        is_browser = (mode == "browser")
        self.player.set_mode(mode)
        active, inactive = "background-color: #0078D7; font-weight: bold;", "background-color: #333; font-weight: normal;"
        self.btn_browser_tab.setStyleSheet(active if is_browser else inactive)
        self.btn_pip_tab.setStyleSheet(inactive if is_browser else active)
        self.browser_panel.setVisible(is_browser)
        self.pip_panel.setVisible(not is_browser)
        self.browser_panel.setMaximumHeight(16777215 if is_browser else 0)
        self.pip_panel.setMaximumHeight(0 if is_browser else 16777215)
        self.adjustSize()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.dragPos = e.globalPos()
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and hasattr(self, 'dragPos') and self.dragPos:
            self.move(self.pos() + e.globalPos() - self.dragPos)
            self.dragPos = e.globalPos()
            e.accept()
    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton: self.dragPos = None

# ──────────────────────────────────────────────
# 메인 플레이어 (AHK 수신 전용)
# ──────────────────────────────────────────────
class StealthPlayer(QMainWindow):
    panic_signal = pyqtSignal()
    hide_signal  = pyqtSignal()
    exit_signal  = pyqtSignal()

    def __init__(self, config):
        super().__init__()
        
        # 🌟 AHK가 창을 정확히 찾을 수 있도록 고정된 영문 제목을 부여합니다.
        self.setWindowTitle("StealthPlayerWindow")

        self.config = config
        self.ext_hwnd = None
        self.chrome_process = None
        self.chrome_pid = None

        self.is_panic_mode, self.is_ui_hidden, self.was_ui_visible = False, False, True
        self.normal_remote_pos, self.normal_player_pos = None, None

        self.panic_signal.connect(self.toggle_panic)
        self.hide_signal.connect(self.toggle_ui)
        self.exit_signal.connect(self.close)

        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setGeometry(100, 100, 480, 295)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.drag_handle = QLabel("  ⠿  스텔스 플레이어  |  F6: 패닉  INSERT: 리모컨  Alt+Q: 종료")
        self.drag_handle.setFixedHeight(25)
        self.drag_handle.setStyleSheet("background-color: rgba(35,35,35,230); color: #888; font-size: 8pt;")
        self.drag_handle.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.drag_handle)

        self.browser = QWebEngineView()
        self.browser.loadFinished.connect(self.clean_ui)
        main_layout.addWidget(self.browser)

        self.setCentralWidget(container)

        self.remote = RemoteControl(self, self.config)
        self.remote.move(100, 405) 
        self.remote.show()

        self._load_url(self.config.get("last_url", "https://www.youtube.com"))
        self.change_browser_opacity(self.config.get("opacity", 30))
        
        # 파이썬 시작 시 AHK 프로그램(stealth_hotkey.exe)도 같이 켭니다.
        if os.path.exists("stealth_hotkey.exe"):
            os.system('start stealth_hotkey.exe')
            logging.info("✅ AHK 핫키 보조 프로그램 자동 실행 완료")

    # 🌟 [핵심] 윈도우 우체부가 배달해주는 AHK의 메시지를 받는 곳
    def nativeEvent(self, eventType, message):
        try:
            msg = ctypes.cast(message.__int__(), ctypes.POINTER(wintypes.MSG)).contents
            if msg.message == 0x0400:  # WM_USER (AHK가 보낸 메시지 코드)
                hotkey_id = msg.wParam
                if hotkey_id == 1:
                    self.panic_signal.emit()
                elif hotkey_id == 2:
                    self.hide_signal.emit()
                elif hotkey_id == 3:
                    self.exit_signal.emit()
                return True, 0
        except Exception:
            pass
        return super().nativeEvent(eventType, message)

    def _load_url(self, url):
        if not url.startswith("http"): url = "https://" + url
        self.browser.setUrl(QUrl(url))

    def load_url_from_remote(self):
        url = self.remote.url_input.text().strip()
        self.config["last_url"] = url
        save_config(self.config)
        self._load_url(url)

    def clean_ui(self):
        js = """
        (function() {
            function clean() {
                let v = document.querySelector('video');
                if (v) v.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:2147483647;object-fit:contain;background:black;';
                ['ytd-masthead','#masthead-container','#below','ytd-player-layout'].forEach(s =>
                    document.querySelectorAll(s).forEach(el => el.style.display = 'none'));
                document.body.style.overflow = 'hidden'; document.body.style.background = 'black';
            }
            new MutationObserver(clean).observe(document.body, {childList:true, subtree:true});
            setInterval(clean, 500); clean();
        })();
        """
        self.browser.page().runJavaScript(js)

    def launch_chrome(self):
        url = self.remote.chrome_url_input.text().strip()
        if not url.startswith("http"): url = "https://" + url
        self.config["pip_url"] = url
        save_config(self.config)

        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), None)

        if chrome_exe:
            import subprocess
            self.chrome_process = subprocess.Popen([chrome_exe, f"--app={url}", "--window-size=480,270"])
            self.chrome_pid = self.chrome_process.pid
        else:
            os.system(f'start "" "{url}"')

    def set_mode(self, mode):
        if mode == "browser":
            pos = self.normal_player_pos if hasattr(self, 'normal_player_pos') else None
            self.move(pos if (pos and pos.x() > -5000) else QPoint(100, 100))
            self.change_browser_opacity(self.remote.browser_opacity_slider.value() if hasattr(self, 'remote') else self.config.get("opacity", 30))
        else:
            if self.x() > -5000: self.normal_player_pos = self.pos()
            self.move(-20000, -20000)
            self.browser.page().setAudioMuted(True)

    def change_browser_opacity(self, value):
        if not self.is_panic_mode:
            self.setWindowOpacity(0.01 if value == 0 else value / 100.0)

    def change_size(self, width):
        self.resize(width, int(width * 9 / 16) + 25)

    def start_ext_capture(self):
        self.remote.ext_status_label.setText("3초! PIP창 클릭...")
        QTimer.singleShot(3000, self._apply_ext_stealth)

    def _apply_ext_stealth(self):
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd and hwnd != int(self.winId()) and hwnd != int(self.remote.winId()):
            self.ext_hwnd = hwnd
            self._set_layered_topmost(hwnd)
            self.change_ext_opacity(self.remote.ext_opacity_slider.value())
            self.remote.ext_status_label.setText("✅ 스텔스 완료!")
        else:
            self.remote.ext_status_label.setText("⚠️ 실패 (다른창)")

    def change_ext_opacity(self, value):
        if self.ext_hwnd and not self.is_panic_mode:
            ctypes.windll.user32.SetLayeredWindowAttributes(self.ext_hwnd, 0, int(255 * value / 100.0), 2)

    def _set_layered_topmost(self, hwnd):
        user32 = ctypes.windll.user32
        GWL_EXSTYLE, WS_EX_LAYERED, HWND_TOPMOST = -20, 0x00080000, -1
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED)
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, 0x0002 | 0x0001)

    def open_settings(self):
        if SettingsDialog(self.config, self).exec_() == QDialog.Accepted:
            self.remote.browser_opacity_slider.setValue(self.config["opacity"])
            self.remote.ext_opacity_slider.setValue(self.config["ext_opacity"])

    def toggle_panic(self):
        user32 = ctypes.windll.user32
        if not self.is_panic_mode:
            self.was_ui_visible = not self.is_ui_hidden
            if self.x() > -5000: self.normal_player_pos = self.pos()
            self.move(-20000, -20000)
            self.browser.page().setAudioMuted(True)
            if self.ext_hwnd: user32.ShowWindow(self.ext_hwnd, 0)
            if not self.is_ui_hidden:
                if self.remote.x() > -5000: self.normal_remote_pos = self.remote.pos()
            self.remote.move(-20000, -20000)
            self.is_ui_hidden = self.is_panic_mode = True
        else:
            if self.remote.current_mode == "browser":
                self.browser.page().setAudioMuted(False)
                pos = self.normal_player_pos if hasattr(self, 'normal_player_pos') else None
                self.move(pos if (pos and pos.x() > -5000) else QPoint(100, 100))
            if self.ext_hwnd:
                user32.ShowWindow(self.ext_hwnd, 5)
                self.change_ext_opacity(self.remote.ext_opacity_slider.value())
            self.is_panic_mode = False
            if self.was_ui_visible:
                self.is_ui_hidden = False
                pos = self.normal_remote_pos
                self.remote.move(pos if (pos and pos.x() > -5000) else self.remote.pos())

    def toggle_ui(self):
        if self.is_panic_mode: return
        if not self.is_ui_hidden:
            if self.remote.x() > -5000: self.normal_remote_pos = self.remote.pos()
            self.remote.move(-20000, -20000)
            self.is_ui_hidden = True
        else:
            pos = self.normal_remote_pos
            self.remote.move(pos if (pos and pos.x() > -5000) else self.remote.pos())
            self.is_ui_hidden = False

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.drag_handle.underMouse(): self.dragPos = e.globalPos()
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and hasattr(self, 'dragPos') and self.dragPos:
            self.move(self.pos() + e.globalPos() - self.dragPos)
            self.dragPos = e.globalPos()
            e.accept()
    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton: self.dragPos = None

    def closeEvent(self, event):
        # AHK 찌꺼기도 파이썬이 꺼질 때 같이 죽입니다.
        os.system('taskkill /f /im stealth_hotkey.exe >nul 2>&1')

        if self.chrome_pid: os.system(f'taskkill /f /t /pid {self.chrome_pid} >nul 2>&1')
        elif self.chrome_process: self.chrome_process.terminate()
        
        if self.ext_hwnd:
            ctypes.windll.user32.ShowWindow(self.ext_hwnd, 5)
            ctypes.windll.user32.SetLayeredWindowAttributes(self.ext_hwnd, 0, 255, 2)
            
        self.remote.close()
        super().closeEvent(event)
        os._exit(0)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    config = load_config()
    player = StealthPlayer(config)
    player.show()
    sys.exit(app.exec_())

    # pip install pyinstaller
    # pyinstaller --onedir --noconsole --name "StealthPlayer" --hidden-import PyQt5.QtWebEngineWidgets --hidden-import PyQt5.QtWebEngine stealth_merge.py