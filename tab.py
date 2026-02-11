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

# 解决高分屏准星偏移
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    ctypes.windll.user32.SetProcessDPIAware()

class BarcodeSwitchUI:
    def __init__(self, root):
        self.root = root
        self.root.title("快切助手 v18.0 (硬件识别版)")
        self.root.geometry("320x550")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#f4f4f4")
        
        self.hwnd_a = None
        self.hwnd_b = None
        self.is_running = False
        self.key_buffer = []

        # --- UI 布局 ---
        tk.Label(root, text="第一步：锁定扫码枪硬件", bg="#f4f4f4", font=("微软雅黑", 9, "bold")).pack(pady=(15,0))
        self.btn_hw = tk.Button(root, text="点击此处并扫任意码绑定", command=self.lock_hardware, bg="#fff9c4")
        self.btn_hw.pack(pady=5, fill="x", padx=40)
        self.target_device = None # 存储扫码枪的硬件标识

        tk.Label(root, text="第二步：设置指令 (如: 123):", bg="#f4f4f4").pack(pady=(10,0))
        self.ent_code = tk.Entry(root, justify='center', font=("Consolas", 12))
        self.ent_code.insert(0, "123") 
        self.ent_code.pack(pady=5)

        # 准星绑定 (沿用你确认有效的 v17.2 逻辑)
        self.btn_pick_a = tk.Button(root, text="🎯 准星拖动到窗口 A", bg="#ffffff", height=2)
        self.btn_pick_a.pack(padx=40, pady=8, fill="x")
        self.btn_pick_a.bind("<ButtonPress-1>", lambda e: self.start_drag("A"))
        self.btn_pick_a.bind("<ButtonRelease-1>", lambda e: self.stop_drag("A"))

        self.btn_pick_b = tk.Button(root, text="🎯 准星拖动到窗口 B", bg="#ffffff", height=2)
        self.btn_pick_b.pack(padx=40, pady=8, fill="x")
        self.btn_pick_b.bind("<ButtonPress-1>", lambda e: self.start_drag("B"))
        self.btn_pick_b.bind("<ButtonRelease-1>", lambda e: self.stop_drag("B"))

        self.lbl_status = tk.Label(root, text="● 请先绑定硬件", fg="orange", font=("微软雅黑", 11, "bold"), bg="#f4f4f4")
        self.lbl_status.pack(pady=10)

        self.btn_toggle = tk.Button(root, text="▶ 启动服务 (F9)", command=self.toggle_service, bg="#28a745", fg="white", height=2, font=("微软雅黑", 10, "bold"))
        self.btn_toggle.pack(pady=5, fill="x", padx=60)

        keyboard.add_hotkey('f9', self.toggle_service)

    def lock_hardware(self):
        """通过捕获下一次按键的 device_id 锁定扫码枪"""
        messagebox.showinfo("提示", "点击确定后，请立即用扫码枪扫一个码")
        def on_hw_scan(event):
            self.target_device = event.device
            self.root.after(0, lambda: self.btn_hw.config(text=f"已绑定设备: {event.device}", bg="#c8e6c9"))
            self.root.after(0, lambda: self.lbl_status.config(text="● 硬件就绪", fg="blue"))
            keyboard.unhook(hw_hook)
        hw_hook = keyboard.on_press(on_hw_scan)

    def start_drag(self, target):
        self.root.config(cursor="crosshair")
        self.is_dragging = True
        self.update_capture()

    def update_capture(self):
        if hasattr(self, 'is_dragging') and self.is_dragging:
            x, y = pyautogui.position()
            hwnd = win32gui.WindowFromPoint((x, y))
            while win32gui.GetParent(hwnd): 
                hwnd = win32gui.GetParent(hwnd)
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

    def handle_scan(self, event):
        if not self.is_running: return True
        
        # 【核心变化】只拦截来自“目标扫码枪”硬件 ID 的按键
        if self.target_device is not None and event.device != self.target_device:
            return True # 键盘按键，直接放行，完全不干扰
        
        if event.event_type == 'down':
            if event.name == 'enter':
                barcode = "".join(self.key_buffer).strip()
                self.key_buffer = []
                target_cmds = [c.strip().lower() for c in self.ent_code.get().split(',')]
                
                if barcode.lower() in target_cmds:
                    self.switch_logic()
                    return False
                elif barcode:
                    self.release_and_write(barcode, append_enter=True)
                    return False
                return True

            if len(event.name) == 1:
                self.key_buffer.append(event.name)
                return False 
        return True

    def release_and_write(self, content, append_enter=False):
        def run():
            keyboard.unhook_all()
            time.sleep(0.01)
            keyboard.write(content, delay=0.001)
            if append_enter:
                keyboard.press_and_release('enter')
            keyboard.hook(self.handle_scan, suppress=True)
            keyboard.add_hotkey('f9', self.toggle_service)
        threading.Thread(target=run, daemon=True).start()

    def switch_logic(self):
        def task():
            try:
                curr_hwnd = win32gui.GetForegroundWindow()
                target = self.hwnd_b if curr_hwnd == self.hwnd_a else self.hwnd_a
                if target and win32gui.IsWindow(target):
                    if win32gui.IsIconic(target):
                        win32gui.ShowWindow(target, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(target)
            except: pass
        threading.Thread(target=task, daemon=True).start()

    def toggle_service(self):
        if not self.is_running:
            if self.target_device is None:
                messagebox.showwarning("提示", "请先绑定扫码枪硬件")
                return
            if not self.hwnd_a or not self.hwnd_b:
                messagebox.showwarning("提示", "请先绑定窗口")
                return
            self.is_running = True
            keyboard.hook(self.handle_scan, suppress=True)
            self.lbl_status.config(text="● 硬件独占运行中", fg="#28a745")
            self.btn_toggle.config(text="■ 停止服务 (F9)", bg="#dc3545")
        else:
            self.is_running = False
            keyboard.unhook_all()
            self.key_buffer = []
            self.lbl_status.config(text="● 服务已停止", fg="red")
            self.btn_toggle.config(text="▶ 启动服务 (F9)", bg="#28a745")

if __name__ == "__main__":
    root = tk.Tk()
    app = BarcodeSwitchUI(root)
    root.mainloop()
