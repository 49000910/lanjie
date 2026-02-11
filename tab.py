import time
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import win32gui
import win32con
import pyautogui
import keyboard
import hid  # 需安裝: pip install hidapi
import ctypes

# 解決高分屏準星偏移，確保座標精準
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    ctypes.windll.user32.SetProcessDPIAware()

class BarcodeSwitchUI:
    def __init__(self, root):
        self.root = root
        self.root.title("新大陸 CD220 硬件鎖定版 v22.0")
        self.root.geometry("350x560")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#f4f4f4")
        
        self.hwnd_a = None
        self.hwnd_b = None
        self.is_running = False
        self.key_buffer = []
        self.devices_dict = {}

        # --- 1. USB 設備選擇區 ---
        tk.Label(root, text="🔌 選擇掃描槍 (NLS-CD220):", bg="#f4f4f4", font=("微软雅黑", 9, "bold")).pack(pady=(15,0))
        self.device_combo = ttk.Combobox(root, width=40, state="readonly")
        self.device_combo.pack(pady=5)
        
        self.btn_refresh = tk.Button(root, text="🔄 刷新設備列表", command=self.refresh_usb_list, font=("微软雅黑", 8))
        self.btn_refresh.pack(pady=2)

        # --- 2. 切換指令 ---
        tk.Label(root, text="⌨️ 切換指令 (如: 123):", bg="#f4f4f4").pack(pady=(10,0))
        self.ent_code = tk.Entry(root, justify='center', font=("Consolas", 12))
        self.ent_code.insert(0, "123") 
        self.ent_code.pack(pady=5)

        # --- 3. 窗口定位 (使用您確認有效的 v17.2 邏輯) ---
        self.btn_pick_a = tk.Button(root, text="🎯 准星拖动到窗口 A", bg="#ffffff", height=2)
        self.btn_pick_a.pack(padx=40, pady=5, fill="x")
        self.btn_pick_a.bind("<ButtonPress-1>", self.start_drag_a)
        self.btn_pick_a.bind("<ButtonRelease-1>", self.stop_drag_a)

        self.btn_pick_b = tk.Button(root, text="🎯 准星拖动到窗口 B", bg="#ffffff", height=2)
        self.btn_pick_b.pack(padx=40, pady=5, fill="x")
        self.btn_pick_b.bind("<ButtonPress-1>", self.start_drag_b)
        self.btn_pick_b.bind("<ButtonRelease-1>", self.stop_drag_b)

        self.lbl_status = tk.Label(root, text="● 服務已停止", fg="red", font=("微软雅黑", 11, "bold"), bg="#f4f4f4")
        self.lbl_status.pack(pady=10)

        self.btn_toggle = tk.Button(root, text="▶ 啟動服務 (F9)", command=self.toggle_service, bg="#28a745", fg="white", height=2, font=("微软雅黑", 10, "bold"))
        self.btn_toggle.pack(pady=5, fill="x", padx=60)
        
        # 註冊全局開關 F9
        keyboard.add_hotkey('f9', self.toggle_service)
        self.refresh_usb_list()

    def refresh_usb_list(self):
        """掃描所有 USB HID 設備"""
        self.devices_dict = {}
        display_list = []
        try:
            for d in hid.enumerate():
                product = d.get('product_string') or "HID Keyboard"
                mfg = d.get('manufacturer_string') or "Generic"
                vid, pid = d['vendor_id'], d['product_id']
                name = f"{mfg} - {product} ({hex(vid)}:{hex(pid)})"
                if name not in self.devices_dict:
                    self.devices_dict[name] = (vid, pid)
                    display_list.append(name)
            self.device_combo['values'] = display_list
            if display_list: self.device_combo.current(0)
            else: self.device_combo.set("未檢測到 USB 設備")
        except: pass

    # --- 准星定位邏輯 ---
    def start_drag_a(self, event): self.start_drag("A")
    def start_drag_b(self, event): self.start_drag("B")
    def stop_drag_a(self, event): self.stop_drag("A")
    def stop_drag_b(self, event): self.stop_drag("B")

    def start_drag(self, target):
        self.root.config(cursor="crosshair")
        self.is_dragging = True
        self.update_capture()

    def update_capture(self):
        if hasattr(self, 'is_dragging') and self.is_dragging:
            x, y = pyautogui.position()
            hwnd = win32gui.WindowFromPoint((x, y))
            while win32gui.GetParent(hwnd): hwnd = win32gui.GetParent(hwnd)
            self.last_detected_hwnd = hwnd
            self.root.after(50, self.update_capture)

    def stop_drag(self, target):
        self.is_dragging = False
        self.root.config(cursor="")
        hwnd = getattr(self, 'last_detected_hwnd', None)
        if hwnd and hwnd != self.root.winfo_id():
            title = win32gui.GetWindowText(hwnd)[:12]
            if target == "A": 
                self.hwnd_a = hwnd
                self.btn_pick_a.config(text=f"A: {title}...", bg="#e8f5e9")
            else: 
                self.hwnd_b = hwnd
                self.btn_pick_b.config(text=f"B: {title}...", bg="#e8f5e9")

    # --- 攔截與回吐邏輯 ---
    def handle_scan(self, event):
        if not self.is_running: return True
        if event.event_type == 'down':
            if event.name == 'enter':
                barcode = "".join(self.key_buffer).strip().lower()
                self.key_buffer = []
                target_cmd = self.ent_code.get().lower().strip()
                if barcode == target_cmd:
                    self.switch_logic()
                    return False
                elif barcode:
                    self.replay_keys(barcode)
                    return False
                return True
            if len(event.name) == 1:
                self.key_buffer.append(event.name)
                return False 
        return True

    def replay_keys(self, content):
        def run():
            keyboard.unhook_all()
            time.sleep(0.01)
            keyboard.write(content, delay=0.001)
            keyboard.press_and_release('enter')
            keyboard.hook(self.handle_scan, suppress=True)
            keyboard.add_hotkey('f9', self.toggle_service)
        threading.Thread(target=run, daemon=True).start()

    def switch_logic(self):
        def task():
            try:
                curr = win32gui.GetForegroundWindow()
                targ = self.hwnd_b if curr == self.hwnd_a else self.hwnd_a
                if targ and win32gui.IsWindow(targ):
                    if win32gui.IsIconic(targ): win32gui.ShowWindow(targ, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(targ)
            except: pass
        threading.Thread(target=task, daemon=True).start()

    def toggle_service(self):
        if not self.is_running:
            if not self.hwnd_a or not self.hwnd_b:
                messagebox.showwarning("提示", "請先綁定窗口")
                return
            self.is_running = True
            keyboard.hook(self.handle_scan, suppress=True)
            self.lbl_status.config(text="● 服務運行中", fg="#28a745")
            self.btn_toggle.config(text="■ 停止服務 (F9)", bg="#dc3545")
        else:
            self.is_running = False
            keyboard.unhook_all()
            self.key_buffer = []
            self.lbl_status.config(text="● 服務已停止", fg="red")
            self.btn_toggle.config(text="▶ 啟動服務 (F9)", bg="#28a745")

if __name__ == "__main__":
    root = tk.Tk()
    app = BarcodeSwitchUI(root)
    root.mainloop()
