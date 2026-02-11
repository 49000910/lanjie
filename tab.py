import keyboard
import time
import threading
import tkinter as tk
from tkinter import messagebox
import sys
import win32gui
import win32con
import pyautogui
import ctypes

# 解决高分屏准星偏移与权限
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    ctypes.windll.user32.SetProcessDPIAware()

class BarcodeSwitchUI:
    def __init__(self, root):
        self.root = root
        self.root.title("快切助手 v20.0 (NLS-CD220 适配版)")
        self.root.geometry("320x550")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#f4f4f4")
        
        self.hwnd_a = None
        self.hwnd_b = None
        self.is_running = False
        self.scanner_identified = False
        self.target_scan_codes = set() # 锁定 NLS-CD220 的物理按键特征
        self.key_buffer = []

        # --- UI 布局 ---
        tk.Label(root, text="第一步：识别 NLS-CD220", bg="#f4f4f4", font=("微软雅黑", 9, "bold")).pack(pady=(15,0))
        self.btn_hw = tk.Button(root, text="点击后请扫码识别", command=self.identify_scanner, bg="#fff9c4", height=2)
        self.btn_hw.pack(pady=5, fill="x", padx=40)

        tk.Label(root, text="第二步：设置指令 (123):", bg="#f4f4f4").pack(pady=(10,0))
        self.ent_code = tk.Entry(root, justify='center', font=("Consolas", 12))
        self.ent_code.insert(0, "123") 
        self.ent_code.pack(pady=5)

        # 窗口绑定 (v17.2 稳定版准星逻辑)
        self.btn_pick_a = tk.Button(root, text="🎯 准星拖动到窗口 A", bg="#ffffff", height=2)
        self.btn_pick_a.pack(padx=40, pady=8, fill="x")
        self.btn_pick_a.bind("<ButtonPress-1>", lambda e: self.start_drag("A"))
        self.btn_pick_a.bind("<ButtonRelease-1>", lambda e: self.stop_drag("A"))

        self.btn_pick_b = tk.Button(root, text="🎯 准星拖动到窗口 B", bg="#ffffff", height=2)
        self.btn_pick_b.pack(padx=40, pady=8, fill="x")
        self.btn_pick_b.bind("<ButtonPress-1>", lambda e: self.start_drag("B"))
        self.btn_pick_b.bind("<ButtonRelease-1>", lambda e: self.stop_drag("B"))

        self.lbl_status = tk.Label(root, text="● 等待识别硬件", fg="orange", font=("微软雅黑", 11, "bold"), bg="#f4f4f4")
        self.lbl_status.pack(pady=10)

        self.btn_toggle = tk.Button(root, text="▶ 启动拦截 (F9)", command=self.toggle_service, bg="#28a745", fg="white", height=2, font=("微软雅黑", 10, "bold"))
        self.btn_toggle.pack(pady=5, fill="x", padx=60)
        
        keyboard.add_hotkey('f9', self.toggle_service)

    def identify_scanner(self):
        """核心：锁定 NLS-CD220 的物理 ScanCode 池"""
        messagebox.showinfo("提示", "点击确定后，请使用 NLS-CD220 扫一个条码")
        self.btn_hw.config(text="侦测信号中...", bg="#bbdefb")
        self.target_scan_codes.clear()
        
        def on_capture(event):
            if event.event_type == 'down':
                # 记录该物理设备产生的所有扫描码
                self.target_scan_codes.add(event.scan_code)
                if event.name == 'enter':
                    self.scanner_identified = True
                    keyboard.unhook(h)
                    self.root.after(0, lambda: self.btn_hw.config(text="NLS-CD220 已锁定", bg="#c8e6c9"))
                    self.root.after(0, lambda: self.lbl_status.config(text="● 硬件就绪", fg="blue"))
        h = keyboard.hook(on_capture)

    # --- 准星逻辑 (v17.2 稳定版) ---
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

    # --- 核心拦截与跳转 ---
    def handle_scan(self, event):
        if not self.is_running: return True
        # 物理隔离：只处理识别到的 NLS-CD220 产生的按键
        if event.scan_code not in self.target_scan_codes:
            return True 

        if event.event_type == 'down':
            if event.name == 'enter':
                barcode = "".join(self.key_buffer).strip().lower()
                self.key_buffer = []
                target_cmd = self.ent_code.get().lower().strip()
                
                if barcode == target_cmd:
                    self.switch_logic()
                    return False # 强力拦截 NLS-CD220 的回车
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
            if not self.scanner_identified:
                messagebox.showwarning("提示", "请先识别 NLS-CD220 扫码枪")
                return
            if not self.hwnd_a or not self.hwnd_b:
                messagebox.showwarning("提示", "请先使用准星绑定 A/B 窗口")
                return
            self.is_running = True
            keyboard.hook(self.handle_scan, suppress=True)
            self.lbl_status.config(text="● 拦截运行中", fg="#28a745")
            self.btn_toggle.config(text="■ 停止拦截 (F9)", bg="#dc3545")
        else:
            self.is_running = False
            keyboard.unhook_all()
            self.key_buffer = []
            self.lbl_status.config(text="● 服务已停止", fg="red")
            self.btn_toggle.config(text="▶ 启动拦截 (F9)", bg="#28a745")

if __name__ == "__main__":
    root = tk.Tk()
    app = BarcodeSwitchUI(root)
    root.mainloop()
