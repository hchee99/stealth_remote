import sys
import json
import os
import keyboard
# 🌟 다시 오류 없고 코덱이 빵빵한 PyQt5로 돌아왔습니다!
from PyQt5.QtCore import QUrl, Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSlider, QLabel, QPushButton, QDialog, QLineEdit, QFormLayout)
from PyQt5.QtWebEngineWidgets import QWebEngineView

CONFIG_FILE = 'stealth_config_live.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"opacity": 30, "panic_key": "F1", "hide_key": "F2", "exit_key": "Alt+q"}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

class SettingsDialog(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ 은폐 환경 설정 (Live Pro)")
        self.setFixedSize(280, 180)
        self.config = current_config
        
        layout = QFormLayout(self)
        
        self.opacity_input = QSlider(Qt.Horizontal)
        self.opacity_input.setRange(0, 100)
        self.opacity_input.setValue(self.config["opacity"])
        layout.addRow("기본 투명도(%):", self.opacity_input)
        
        self.panic_input = QLineEdit(self.config["panic_key"])
        layout.addRow("패닉 토글 (보스키):", self.panic_input)
        
        self.hide_input = QLineEdit(self.config["hide_key"])
        layout.addRow("컨트롤 바 숨기기:", self.hide_input)
        
        self.exit_input = QLineEdit(self.config["exit_key"])
        layout.addRow("긴급 프로그램 종료:", self.exit_input)
        
        save_btn = QPushButton("저장 및 즉시 적용")
        save_btn.clicked.connect(self.save_and_close)
        layout.addRow(save_btn)

    def save_and_close(self):
        self.config["opacity"] = self.opacity_input.value()
        self.config["panic_key"] = self.panic_input.text().strip().upper()
        self.config["hide_key"] = self.hide_input.text().strip().upper()
        self.config["exit_key"] = self.exit_input.text().strip().capitalize()
        save_config(self.config)
        self.accept()

class RemoteControl(QWidget):
    def __init__(self, player, config):
        super().__init__()
        self.player = player
        self.config = config

        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.main_widget = QWidget(self)
        self.main_widget.setStyleSheet("background-color: rgba(30, 30, 30, 220); color: white; border-radius: 8px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.main_widget)

        control_layout = QVBoxLayout(self.main_widget)
        control_layout.setContentsMargins(15, 10, 15, 10)

        top_control = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("이동할 URL 입력 후 Enter")
        self.url_input.setStyleSheet("background-color: #222; border: 1px solid #555; padding: 4px; border-radius: 3px;")
        self.url_input.returnPressed.connect(self.player.load_new_url)
        top_control.addWidget(self.url_input)

        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(30, 25)
        self.settings_btn.setStyleSheet("background-color: #555; border-radius: 3px;")
        self.settings_btn.clicked.connect(self.player.open_settings)
        top_control.addWidget(self.settings_btn)
        control_layout.addLayout(top_control)

        bottom_control = QHBoxLayout()
        bottom_control.addWidget(QLabel("투명도:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100) 
        self.opacity_slider.setValue(self.config["opacity"])
        self.opacity_slider.valueChanged.connect(self.player.change_opacity)
        bottom_control.addWidget(self.opacity_slider)

        bottom_control.addWidget(QLabel(" 크기:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(300, 1000) 
        self.size_slider.setValue(480)
        self.size_slider.valueChanged.connect(self.player.change_size)
        bottom_control.addWidget(self.size_slider)
        control_layout.addLayout(bottom_control)

        self.resize(400, 80)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPos = event.globalPos()
            
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            if hasattr(self, 'dragPos') and self.dragPos is not None:
                self.move(self.pos() + event.globalPos() - self.dragPos)
                self.dragPos = event.globalPos()
                event.accept()
                
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPos = None

class UltimateStealthPlayer(QMainWindow):
    panic_signal = pyqtSignal()
    hide_signal = pyqtSignal()
    exit_signal = pyqtSignal()

    def __init__(self, config):
        super().__init__()
        self.config = config

        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)

        self.panic_signal.connect(self.toggle_panic)
        self.hide_signal.connect(self.toggle_ui)
        self.exit_signal.connect(self.close)

        self.is_panic_mode = False
        self.previous_opacity = self.config["opacity"]
        
        self.current_opacity = self.config["opacity"] / 100.0
        self.setWindowOpacity(self.current_opacity)
        self.setGeometry(100, 100, 480, 270 + 25) 

        self.main_container = QWidget()
        self.main_layout = QVBoxLayout(self.main_container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0) 

        self.drag_handle = QLabel(" (여기를 잡고 이동) ")
        self.drag_handle.setFixedHeight(25)
        self.drag_handle.setStyleSheet("background-color: rgba(40, 40, 40, 220); color: silver; font-size: 10pt; font-weight: bold;")
        self.drag_handle.setCursor(Qt.SizeAllCursor) 
        self.drag_handle.setAlignment(Qt.AlignCenter) 
        self.main_layout.addWidget(self.drag_handle)

        self.browser = QWebEngineView()
        
        # 🌟 핵심 기술: 파이썬이 아닌 '최신 구글 크롬 브라우저'인 척 완벽하게 위장합니다!
        self.browser.page().profile().setHttpUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        
        # 기본 접속 화면을 유튜브 라이브 홈으로 설정했습니다.
        self.browser.setUrl(QUrl("https://www.youtube.com/live"))
        self.browser.loadFinished.connect(self.clean_ui) 
        self.main_layout.addWidget(self.browser)
        
        self.setCentralWidget(self.main_container)

        self.remote = RemoteControl(self, self.config)
        self.remote.move(self.x(), self.y() + self.height() + 10)
        self.remote.show()

        self.setup_global_shortcuts()

    # 🧹 치지직 & 유튜브 라이브 찌꺼기 공통 청소
    def clean_ui(self):
        js_code = """
        function cleanEverything() {
            let video = document.querySelector('video');
            if (video) {
                video.style.position = 'fixed';
                video.style.top = '0';
                video.style.left = '0';
                video.style.width = '100vw';
                video.style.height = '100vh';
                video.style.zIndex = '2147483647';
                video.style.objectFit = 'contain';
                video.style.backgroundColor = 'black';
            }
            
            // 유튜브와 치지직의 방해 요소를 모두 숨김
            let hideList = [
                'ytd-masthead', '#masthead-container', '#below', 'ytd-player-layout', // 유튜브
                'header', '.layout_side_bar__Q32Fp', '.layout_chat__3_h7f', '#layout_container', '.pzp-ui-container' // 치지직
            ];

            hideList.forEach(selector => {
                let elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    if (el) el.style.display = 'none';
                });
            });
            
            document.body.style.overflow = 'hidden';
            document.body.style.backgroundColor = 'black';
        }

        const observer = new MutationObserver(cleanEverything);
        observer.observe(document.body, { childList: true, subtree: true });
        setInterval(cleanEverything, 500);
        """
        self.browser.page().runJavaScript(js_code)

    def load_new_url(self):
        url_text = self.remote.url_input.text().strip()
        if not url_text.startswith("http"):
            url_text = "https://" + url_text
        self.browser.setUrl(QUrl(url_text))

    def setup_global_shortcuts(self):
        keyboard.unhook_all()
        keyboard.add_hotkey(self.config["panic_key"], self.panic_signal.emit)
        keyboard.add_hotkey(self.config["hide_key"], self.hide_signal.emit)
        keyboard.add_hotkey(self.config["exit_key"], self.exit_signal.emit)

    def open_settings(self):
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            self.config = dialog.config
            self.remote.opacity_slider.setValue(self.config["opacity"])
            self.setup_global_shortcuts()

    def change_opacity(self, value):
        self.setWindowOpacity(value / 100.0)
        if value == 0:
            self.browser.hide()
        else:
            self.browser.show()

    def change_size(self, width):
        height = int(width * 9 / 16) + 25 
        self.resize(width, height)

    def toggle_panic(self):
        if not self.is_panic_mode:
            self.previous_opacity = self.remote.opacity_slider.value()
            self.remote.opacity_slider.setValue(0)
            self.browser.page().setAudioMuted(True) 
            self.is_panic_mode = True
        else:
            self.remote.opacity_slider.setValue(self.previous_opacity)
            self.browser.page().setAudioMuted(False) 
            self.is_panic_mode = False

    def toggle_ui(self):
        if self.remote.isVisible():
            self.remote.hide()
        else:
            self.remote.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.drag_handle.underMouse():
                self.dragPos = event.globalPos()
                event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            if hasattr(self, 'dragPos') and self.dragPos is not None:
                self.move(self.pos() + event.globalPos() - self.dragPos)
                self.dragPos = event.globalPos()
                event.accept()
                
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPos = None

    def closeEvent(self, event):
        keyboard.unhook_all()
        self.remote.close()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    current_config = load_config()
    initial_dialog = SettingsDialog(current_config)
    
    if initial_dialog.exec_() == QDialog.Accepted:
        player = UltimateStealthPlayer(initial_dialog.config) 
        player.show()
        sys.exit(app.exec_())
    else:
        sys.exit()