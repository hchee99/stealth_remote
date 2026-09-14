import sys
import json
import os
import ctypes
from ctypes import wintypes
from PyQt5.QtCore import QUrl, Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QSlider, QLabel, QPushButton, QDialog, QLineEdit, QFormLayout,
                             QFrame, QKeySequenceEdit, QMessageBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView

APP_DIR = os.path.dirname(
    os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
)
CONFIG_FILE = os.path.join(APP_DIR, 'stealth_merged_config.json')

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

MODIFIER_KEYS = {
    "ALT": MOD_ALT,
    "CTRL": MOD_CONTROL,
    "CONTROL": MOD_CONTROL,
    "SHIFT": MOD_SHIFT,
    "WIN": MOD_WIN,
    "META": MOD_WIN,
}

VIRTUAL_KEYS = {
    "BACKSPACE": 0x08,
    "TAB": 0x09,
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "PAUSE": 0x13,
    "CAPSLOCK": 0x14,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "SPACE": 0x20,
    "PGUP": 0x21,
    "PAGEUP": 0x21,
    "PGDOWN": 0x22,
    "PAGEDOWN": 0x22,
    "END": 0x23,
    "HOME": 0x24,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "PRINT": 0x2C,
    "PRINTSCREEN": 0x2C,
    "INS": 0x2D,
    "INSERT": 0x2D,
    "DEL": 0x2E,
    "DELETE": 0x2E,
    ";": 0xBA,
    "=": 0xBB,
    ",": 0xBC,
    "-": 0xBD,
    ".": 0xBE,
    "/": 0xBF,
    "`": 0xC0,
    "[": 0xDB,
    "\\": 0xDC,
    "]": 0xDD,
    "'": 0xDE,
}


def parse_hotkey(sequence):
    """Qt 키 조합 문자열을 Windows RegisterHotKey 값으로 변환합니다."""
    sequence = sequence.strip()
    if not sequence:
        raise ValueError("키 조합이 비어 있습니다.")

    # Qt는 + 키를 "+", Ctrl과 함께 누르면 "Ctrl++"로 표현합니다.
    # 마지막 +는 조합 구분자가 아니라 실제 키이므로 따로 보존합니다.
    plus_key = sequence.endswith("+")
    modifier_text = sequence[:-1] if plus_key else sequence
    parts = [part.strip().upper() for part in modifier_text.split("+") if part.strip()]

    modifiers = 0
    use_numpad = False
    key_names = ["+"] if plus_key else []
    for part in parts:
        if part == "NUM":
            use_numpad = True
        elif part in MODIFIER_KEYS:
            modifiers |= MODIFIER_KEYS[part]
        else:
            key_names.append(part)

    if len(key_names) != 1:
        raise ValueError(f"한 번에 하나의 일반 키만 지정할 수 있습니다: {sequence}")

    key_name = key_names[0]
    if use_numpad and key_name == "+":
        virtual_key = 0x6B  # VK_ADD
    elif use_numpad and key_name == "-":
        virtual_key = 0x6D  # VK_SUBTRACT
    elif use_numpad:
        raise ValueError(f"현재 숫자 키패드에서는 +와 -만 지원합니다: {sequence}")
    elif key_name == "+":
        # 상단 숫자열의 +는 Shift와 OEM_PLUS(=) 조합입니다.
        modifiers |= MOD_SHIFT
        virtual_key = 0xBB
    elif len(key_name) == 1 and key_name.isalnum():
        virtual_key = ord(key_name)
    elif key_name.startswith("F") and key_name[1:].isdigit() and 1 <= int(key_name[1:]) <= 24:
        virtual_key = 0x70 + int(key_name[1:]) - 1
    else:
        virtual_key = VIRTUAL_KEYS.get(key_name)

    if virtual_key is None:
        raise ValueError(f"지원하지 않는 키입니다: {key_name}")

    return modifiers, virtual_key


class HotkeySequenceEdit(QKeySequenceEdit):
    """숫자 키패드의 +/- 구분을 유지하는 단축키 입력 위젯입니다."""

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.KeypadModifier and event.key() in (Qt.Key_Plus, Qt.Key_Minus):
            regular_modifiers = event.modifiers() & (
                Qt.ControlModifier | Qt.AltModifier | Qt.ShiftModifier | Qt.MetaModifier
            )
            sequence_value = int(regular_modifiers | Qt.KeypadModifier) | event.key()
            self.setKeySequence(QKeySequence(sequence_value))
            event.accept()
            return
        super().keyPressEvent(event)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "opacity": 30,
        "ext_opacity": 30,
        "panic_key": "F6",
        "hide_key": "INSERT",
        "exit_key": "alt+q",
        "last_url": "https://www.youtube.com",
        "pip_url": "https://chzzk.naver.com/live"
    }

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


# ──────────────────────────────────────────────
# 설정 다이얼로그
# ──────────────────────────────────────────────
class SettingsDialog(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⌨️ 전역 핫키 설정")
        self.setFixedSize(360, 190)
        self.config = dict(current_config)

        layout = QFormLayout(self)

        guide = QLabel("입력칸을 클릭한 뒤 원하는 키 조합을 누르세요.")
        guide.setWordWrap(True)
        layout.addRow(guide)

        self.panic_input = HotkeySequenceEdit(QKeySequence(self.config.get("panic_key", "F6")))
        layout.addRow("전체 패닉 (보스키):", self.panic_input)

        self.hide_input = HotkeySequenceEdit(QKeySequence(self.config.get("hide_key", "INSERT")))
        layout.addRow("리모컨 숨기기:", self.hide_input)

        self.exit_input = HotkeySequenceEdit(QKeySequence(self.config.get("exit_key", "Alt+Q")))
        layout.addRow("긴급 완전 종료:", self.exit_input)

        save_btn = QPushButton("저장 및 즉시 적용")
        save_btn.clicked.connect(self.save_and_close)
        layout.addRow(save_btn)

    def save_and_close(self):
        hotkeys = {
            "panic_key": self.panic_input.keySequence().toString(QKeySequence.PortableText),
            "hide_key": self.hide_input.keySequence().toString(QKeySequence.PortableText),
            "exit_key": self.exit_input.keySequence().toString(QKeySequence.PortableText),
        }

        try:
            parsed = [parse_hotkey(sequence) for sequence in hotkeys.values()]
        except ValueError as error:
            QMessageBox.warning(self, "핫키 입력 오류", str(error))
            return

        if len(set(parsed)) != len(parsed):
            QMessageBox.warning(self, "핫키 중복", "세 기능에는 서로 다른 키 조합을 지정해주세요.")
            return

        self.config.update(hotkeys)
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
            QPushButton { border-radius: 4px; padding: 5px 8px; }
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

        # ── 탭 버튼 ──────────────────────────
        tab_row = QHBoxLayout()
        tab_row.setSpacing(4)
        self.btn_browser_tab = QPushButton("📺 내장 브라우저")
        self.btn_pip_tab     = QPushButton("🌐 PIP 모드")
        for btn in (self.btn_browser_tab, self.btn_pip_tab):
            btn.setFixedHeight(28)
            tab_row.addWidget(btn)
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(30, 28)
        settings_btn.setStyleSheet("background-color: #444;")
        settings_btn.clicked.connect(self.player.open_settings)
        tab_row.addWidget(settings_btn)
        self.root_layout.addLayout(tab_row)

        self.root_layout.addWidget(self._line())

        # ── 📺 내장 브라우저 패널 ─────────────
        self.browser_panel = QWidget()
        bp = QVBoxLayout(self.browser_panel)
        bp.setContentsMargins(0, 0, 0, 0)
        bp.setSpacing(6)

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

        # ── 🌐 PIP 패널 ──────────────────────
        self.pip_panel = QWidget()
        pp = QVBoxLayout(self.pip_panel)
        pp.setContentsMargins(0, 0, 0, 0)
        pp.setSpacing(6)

        chrome_row = QHBoxLayout()
        self.chrome_url_input = QLineEdit()
        self.chrome_url_input.setPlaceholderText("치지직/방송 URL")
        self.chrome_url_input.setText(self.config.get("pip_url", "https://chzzk.naver.com/live"))
        chrome_row.addWidget(self.chrome_url_input)
        chrome_btn = QPushButton("🌐 크롬 띄우기")
        chrome_btn.setStyleSheet("background-color: #0078D7; font-weight: bold;")
        chrome_btn.clicked.connect(self.player.launch_chrome)
        chrome_row.addWidget(chrome_btn)
        pp.addLayout(chrome_row)

        pip_row = QHBoxLayout()
        ext_btn = QPushButton("🎯 PIP창 타겟 (3초)")
        ext_btn.setStyleSheet("background-color: #28a745; font-weight: bold;")
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

        # 탭 연결
        self.btn_browser_tab.clicked.connect(lambda: self.set_mode("browser"))
        self.btn_pip_tab.clicked.connect(lambda: self.set_mode("pip"))
        self.set_mode("browser")

    def _line(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #444;")
        return line

    def set_mode(self, mode):
        self.current_mode = mode
        is_browser = (mode == "browser")

        self.player.set_mode(mode)

        active   = "background-color: #0078D7; font-weight: bold;"
        inactive = "background-color: #333; font-weight: normal;"
        self.btn_browser_tab.setStyleSheet(active   if is_browser else inactive)
        self.btn_pip_tab.setStyleSheet    (inactive if is_browser else active)

        self.browser_panel.setVisible(is_browser)
        self.pip_panel.setVisible(not is_browser)
        self.browser_panel.setMaximumHeight(16777215 if is_browser else 0)
        self.pip_panel.setMaximumHeight(0 if is_browser else 16777215)

        self.adjustSize()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, 'dragPos') and self.dragPos:
            self.move(self.pos() + event.globalPos() - self.dragPos)
            self.dragPos = event.globalPos()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPos = None


# ──────────────────────────────────────────────
# 메인 플레이어
# ──────────────────────────────────────────────
class StealthPlayer(QMainWindow):
    panic_signal = pyqtSignal()
    hide_signal  = pyqtSignal()
    exit_signal  = pyqtSignal()

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.ext_hwnd = None
        self.chrome_process = None
        self.chrome_pid = None
        self.registered_hotkey_ids = []

        self.is_panic_mode   = False
        self.is_ui_hidden    = False
        self.was_ui_visible  = True
        self.normal_remote_pos = None
        self.previous_browser_opacity = self.config.get("opacity", 30)

        self.panic_signal.connect(self.toggle_panic)
        self.hide_signal.connect(self.toggle_ui)
        self.exit_signal.connect(self.close)

        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setWindowOpacity(self.config.get("opacity", 30) / 100.0)
        self.setGeometry(100, 100, 480, 295)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.drag_handle = QLabel()
        self.drag_handle.setFixedHeight(25)
        self.drag_handle.setStyleSheet("background-color: rgba(35,35,35,230); color: #888; font-size: 8pt;")
        self.drag_handle.setCursor(Qt.SizeAllCursor)
        self.drag_handle.setAlignment(Qt.AlignCenter)
        self._update_hotkey_label()
        main_layout.addWidget(self.drag_handle)

        self.browser = QWebEngineView()
        self.browser.loadFinished.connect(self.clean_ui)
        main_layout.addWidget(self.browser)

        self.setCentralWidget(container)

        self.remote = RemoteControl(self, self.config)
        self.remote.move(self.x(), self.y() + self.height() + 10)
        self.remote.show()

        self._load_url(self.config.get("last_url", "https://www.youtube.com"))
        try:
            self.setup_global_shortcuts(self.config)
        except (ValueError, RuntimeError) as error:
            QMessageBox.warning(
                self,
                "전역 핫키 등록 실패",
                f"일부 핫키를 등록하지 못했습니다.\n설정에서 다른 조합을 선택해주세요.\n\n{error}",
            )

    # ── URL ─────────────────────────────────
    def _load_url(self, url):
        if not url.startswith("http"):
            url = "https://" + url
        self.browser.setUrl(QUrl(url))

    def load_url_from_remote(self):
        url = self.remote.url_input.text().strip()
        self.config["last_url"] = url
        save_config(self.config)
        self._load_url(url)

    # ── 유튜브 UI 제거 ──────────────────────
    def clean_ui(self):
        js = """
        (function() {
            function clean() {
                let v = document.querySelector('video');
                if (v) v.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:2147483647;object-fit:contain;background:black;';
                ['ytd-masthead','#masthead-container','#below','ytd-player-layout'].forEach(s =>
                    document.querySelectorAll(s).forEach(el => el.style.display = 'none'));
                document.body.style.overflow = 'hidden';
                document.body.style.background = 'black';
            }
            new MutationObserver(clean).observe(document.body, {childList:true, subtree:true});
            setInterval(clean, 500);
            clean();
        })();
        """
        self.browser.page().runJavaScript(js)

    # ── 크롬 PIP ────────────────────────────
    def launch_chrome(self):
        url = self.remote.chrome_url_input.text().strip()
        if not url.startswith("http"):
            url = "https://" + url
        self.config["pip_url"] = url
        save_config(self.config)

        # 크롬 경로 후보 (설치 위치별)
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), None)

        if chrome_exe:
            import subprocess
            self.chrome_process = subprocess.Popen(
                [chrome_exe, f"--app={url}", "--window-size=480,270"]
            )
            self.chrome_pid = self.chrome_process.pid
        else:
            os.system(f'start "" "{url}"')
            self.chrome_pid = None

    # ── 모드 전환 ────────────────────────────
    def set_mode(self, mode):
        if mode == "browser":
            self.show()
            opacity = self.remote.browser_opacity_slider.value() if hasattr(self, 'remote') else self.config.get("opacity", 30)
            self.change_browser_opacity(opacity)
        else:
            self.setWindowOpacity(0)
            self.browser.setVisible(False)
            self.browser.page().setAudioMuted(True)

    # ── 내장 브라우저 투명도/크기 ────────────
    def change_browser_opacity(self, value):
        if not self.is_panic_mode:
            self.setWindowOpacity(value / 100.0)
            self.browser.setVisible(value > 0)

    def change_size(self, width):
        height = int(width * 9 / 16) + 25
        self.resize(width, height)

    # ── PIP창 타겟 ──────────────────────────
    def start_ext_capture(self):
        self.remote.ext_status_label.setText("3초! PIP창 클릭 후 대기...")
        self.remote.ext_status_label.setStyleSheet("color: #ffaa00; font-size: 9pt;")
        QTimer.singleShot(3000, self._apply_ext_stealth)

    def _apply_ext_stealth(self):
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd and hwnd != int(self.winId()) and hwnd != int(self.remote.winId()):
            self.ext_hwnd = hwnd
            self._set_layered_topmost(hwnd)
            self.change_ext_opacity(self.remote.ext_opacity_slider.value())
            self.remote.ext_status_label.setText("✅ PIP창 스텔스 완료!")
            self.remote.ext_status_label.setStyleSheet("color: #00ff00; font-size: 9pt;")
        else:
            self.remote.ext_status_label.setText("⚠️ 다른 창을 선택하세요")
            self.remote.ext_status_label.setStyleSheet("color: #ff4444; font-size: 9pt;")

    def change_ext_opacity(self, value):
        if self.ext_hwnd and not self.is_panic_mode:
            ctypes.windll.user32.SetLayeredWindowAttributes(
                self.ext_hwnd, 0, int(255 * value / 100.0), 2)

    def _set_layered_topmost(self, hwnd):
        user32 = ctypes.windll.user32
        GWL_EXSTYLE, WS_EX_LAYERED, HWND_TOPMOST = -20, 0x00080000, -1
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED)
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, 0x0002 | 0x0001)

    # ── Windows 전역 핫키 ────────────────────
    def _unregister_global_shortcuts(self):
        hwnd = int(self.winId())
        for hotkey_id in self.registered_hotkey_ids:
            ctypes.windll.user32.UnregisterHotKey(hwnd, hotkey_id)
        self.registered_hotkey_ids.clear()

    def setup_global_shortcuts(self, config):
        """키보드 훅 대신 Windows가 제공하는 전역 핫키를 등록합니다."""
        self._unregister_global_shortcuts()
        hwnd = int(self.winId())
        hotkeys = (
            (1, "전체 패닉", config.get("panic_key", "F6")),
            (2, "리모컨 숨기기", config.get("hide_key", "INSERT")),
            (3, "완전 종료", config.get("exit_key", "Alt+Q")),
        )

        try:
            for hotkey_id, label, sequence in hotkeys:
                modifiers, virtual_key = parse_hotkey(sequence)
                succeeded = ctypes.windll.user32.RegisterHotKey(
                    hwnd,
                    hotkey_id,
                    modifiers | MOD_NOREPEAT,
                    virtual_key,
                )
                if not succeeded:
                    raise RuntimeError(
                        f"'{sequence}' ({label}) 조합이 다른 프로그램에서 사용 중일 수 있습니다."
                    )
                self.registered_hotkey_ids.append(hotkey_id)
        except Exception:
            self._unregister_global_shortcuts()
            raise

    def nativeEvent(self, event_type, message):
        msg = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents
        if msg.message == WM_HOTKEY:
            if msg.wParam == 1:
                self.panic_signal.emit()
            elif msg.wParam == 2:
                self.hide_signal.emit()
            elif msg.wParam == 3:
                self.exit_signal.emit()
            return True, 0
        return super().nativeEvent(event_type, message)

    def _update_hotkey_label(self):
        panic = self.config.get("panic_key", "F6")
        hide = self.config.get("hide_key", "INSERT")
        exit_key = self.config.get("exit_key", "Alt+Q")
        self.drag_handle.setText(
            f"  ⠿  스텔스 플레이어  |  {panic}: 전체패닉  {hide}: 리모컨  {exit_key}: 종료"
        )

    def open_settings(self):
        previous_config = dict(self.config)
        # 기존 핫키가 입력창의 키 입력보다 먼저 실행되는 것을 막습니다.
        self._unregister_global_shortcuts()
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_() != QDialog.Accepted:
            try:
                self.setup_global_shortcuts(previous_config)
            except (ValueError, RuntimeError) as error:
                QMessageBox.warning(self, "전역 핫키 복원 실패", str(error))
            return

        try:
            self.setup_global_shortcuts(dialog.config)
        except (ValueError, RuntimeError) as error:
            try:
                self.setup_global_shortcuts(previous_config)
            except (ValueError, RuntimeError):
                pass
            QMessageBox.warning(self, "전역 핫키 등록 실패", str(error))
            return

        self.config = dialog.config
        save_config(self.config)
        self._update_hotkey_label()

    # ── F6: 전체 패닉 ────────────────────────
    def toggle_panic(self):
        user32 = ctypes.windll.user32

        if not self.is_panic_mode:
            self.was_ui_visible = not self.is_ui_hidden
            self.previous_browser_opacity = self.remote.browser_opacity_slider.value()

            self.setWindowOpacity(0)
            self.browser.setVisible(False)
            self.browser.page().setAudioMuted(True)

            if self.ext_hwnd:
                user32.ShowWindow(self.ext_hwnd, 0)

            if not self.is_ui_hidden:
                self.normal_remote_pos = self.remote.pos()
            self.remote.move(-10000, -10000)
            self.is_ui_hidden = True
            self.is_panic_mode = True

        else:
            if self.remote.current_mode == "browser":
                self.setWindowOpacity(self.previous_browser_opacity / 100.0)
                self.browser.setVisible(self.previous_browser_opacity > 0)
                self.browser.page().setAudioMuted(False)

            if self.ext_hwnd:
                user32.ShowWindow(self.ext_hwnd, 5)
                self.change_ext_opacity(self.remote.ext_opacity_slider.value())

            self.is_panic_mode = False

            if self.was_ui_visible:
                self.is_ui_hidden = False
                pos = self.normal_remote_pos
                self.remote.move(pos if (pos and pos.x() > -5000) else self.remote.pos())

    # ── INSERT: 리모컨 토글 ──────────────────
    def toggle_ui(self):
        if self.is_panic_mode:
            return
        if not self.is_ui_hidden:
            self.normal_remote_pos = self.remote.pos()
            self.remote.move(-10000, -10000)
            self.is_ui_hidden = True
        else:
            pos = self.normal_remote_pos
            self.remote.move(pos if (pos and pos.x() > -5000) else self.remote.pos())
            self.is_ui_hidden = False

    # ── 드래그 ──────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.drag_handle.underMouse():
            self.dragPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, 'dragPos') and self.dragPos:
            self.move(self.pos() + event.globalPos() - self.dragPos)
            self.dragPos = event.globalPos()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPos = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    # ── 종료 ────────────────────────────────
    def closeEvent(self, event):
        self._unregister_global_shortcuts()

        user32 = ctypes.windll.user32

        # 크롬 띄우기로 열었던 창 종료 (WM_CLOSE로 해당 창만)
        if self.chrome_pid:
            try:
                os.system(f'taskkill /f /t /pid {self.chrome_pid} >nul 2>&1')
            except:
                pass
        elif self.chrome_process:
            try:
                self.chrome_process.terminate()
            except:
                pass

        # 🎯 타겟으로 잡은 외부창은 WM_CLOSE로 해당 창만 닫기
        if self.ext_hwnd:
            try:
                user32.ShowWindow(self.ext_hwnd, 5)
                user32.SetLayeredWindowAttributes(self.ext_hwnd, 0, 255, 2)
                user32.PostMessageW(self.ext_hwnd, 0x0010, 0, 0)  # WM_CLOSE
            except:
                pass

        self.remote.close()
        super().closeEvent(event)


# ──────────────────────────────────────────────
if __name__ == '__main__':
    app = QApplication(sys.argv)
    config = load_config()
    player = StealthPlayer(config)
    player.show()
    sys.exit(app.exec_())

# 파이썬이 설치되어 있다면 
# pip install PyQt5 PyQtWebEngine
# python claude_stealth.py

# exe파일로 다운받으려면
# pyinstaller --onedir --noconsole --name "StealthPlayer" --hidden-import PyQt5.QtWebEngineWidgets --hidden-import PyQt5.QtWebEngine claude_stealth.py
