"""Consume only configured hotkeys, forwarding actions to the Qt window queue."""
import ctypes
from ctypes import wintypes


class KeyboardEvent(ctypes.Structure):
    _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("extraInfo", ctypes.c_size_t)]


class PriorityHotkeys:
    def __init__(self):
        self.api = ctypes.WinDLL("user32", use_last_error=True)
        self.callback_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
        self.api.SetWindowsHookExW.argtypes = [ctypes.c_int, self.callback_type,
                                              wintypes.HINSTANCE, wintypes.DWORD]
        self.api.SetWindowsHookExW.restype = wintypes.HANDLE
        self.api.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                           wintypes.WPARAM, wintypes.LPARAM]
        self.api.CallNextHookEx.restype = ctypes.c_ssize_t
        self.api.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
        self.api.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT,
                                          wintypes.WPARAM, wintypes.LPARAM]
        self.handle = None
        self.callback = self.callback_type(self._callback)
        self.bindings = {}
        self.consumed = set()
        self.hwnd = None

    def start(self, hwnd, bindings):
        self.stop()
        self.hwnd = hwnd
        self.bindings = dict(bindings)
        self.handle = self.api.SetWindowsHookExW(13, self.callback, None, 0)
        if not self.handle:
            raise RuntimeError(f"우선 핫키 등록 실패: {ctypes.get_last_error()}")

    def stop(self):
        if self.handle:
            self.api.UnhookWindowsHookEx(self.handle)
            self.handle = None
        self.consumed.clear()
        self.bindings.clear()

    def process_key(self, key, pressed, modifiers):
        if not pressed:
            if key in self.consumed:
                self.consumed.remove(key)
                return True
            return False
        if key in self.consumed:
            return True  # Holding the key must not toggle repeatedly.
        action = self.bindings.get((modifiers, key))
        if action is None:
            return False
        self.api.PostMessageW(self.hwnd, 0x0312, action, 0)
        self.consumed.add(key)
        return True

    def _callback(self, code, message, data):
        if code >= 0 and message in (0x100, 0x101, 0x104, 0x105):
            event = ctypes.cast(data, ctypes.POINTER(KeyboardEvent)).contents
            modifiers = 0
            for mask, keys in ((1, (0x12,)), (2, (0x11,)),
                               (4, (0x10,)), (8, (0x5B, 0x5C))):
                if any(self.api.GetAsyncKeyState(key) & 0x8000 for key in keys):
                    modifiers |= mask
            if self.process_key(event.vkCode, message in (0x100, 0x104), modifiers):
                return 1
        return self.api.CallNextHookEx(self.handle, code, message, data)
