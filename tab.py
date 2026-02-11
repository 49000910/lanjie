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

# 解決高分屏準星偏移與權限問題
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    ctypes.windll.user32.SetProcessDPIAware()

class BarcodeSwitchUI:
    def __init__(self, root):
        self.root = root
        self.root.title("快切助手 v18.2 (硬件隔離修復版)")
        self.root.geometry("320x550")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#f4f4f4")
        
        self.hwnd_a = None
        self.hwnd_b = None
        self.is_running = False
        self.target_device = None  # 存儲硬件唯一標識
        self.key_buffer = []

        # --- UI 佈局 ---
        tk.Label(root, text="第一步：鎖定掃碼槍硬件", bg="#f4f4f4", font=("微软雅黑", 9, "bold")).pack(pady=(15,0))
        self.btn_hw = tk.Button(root, text="點擊此處並掃任意碼綁定", command=self.lock_hardware, bg="#fff9c4", height=2)
        self.btn_hw.pack(pady=5, fill="x", padx=40)

        tk.Label(root, text="第二步：設置指令 (如: 123):", bg="#f4f4f4").pack(pady=(10,0))
        self.ent_code = tk.Entry(root, justify='center', font=("Consolas", 12))
        self.ent_code.insert(0, "123") 
        self.ent_code.pack(pady=5)

        # 窗口綁定 (使用 v17.2 穩定準星邏輯)
        self.btn_pick_a = tk.Button(root, text="🎯 准星拖动到窗口 A", bg="#ffffff", height=2)
        self.btn_pick_a.pack(padx=40, pady=8, fill="x")
        self.btn_pick_a.bind("<ButtonPress-1>", lambda e: self.start_drag("A"))
        self.btn_pick_a.bind("<ButtonRelease-1>", lambda e: self.stop_drag("A"))

        self.btn_pick_b = tk.Button(root, text="🎯 准星拖动到窗口 B", bg="#ffffff", height=2)
        self.btn_pick_b.pack(padx=40, pady=8, fill="x")
        self.btn_pick_b.bind("<ButtonPress-1>", lambda e: self.start_drag("B"))
        self.btn_pick_b.bind("<ButtonRelease-1>", lambda e: self.stop_drag("B"))

        self.lbl_status = tk.Label(root, text="● 請先綁定硬件", fg="orange", font=("微软雅黑", 11, "bold"), bg="#f4f4f4")
        self.lbl_status.pack(pady=10)

        self.btn_toggle = tk.Button(root, text="▶ 啟動服務 (F9)", command=self.toggle_service, bg="#28a745", fg="white", height=2, font=("微软雅黑", 10, "bold"))
        self.btn_toggle.pack(pady=5, fill="x", padx=60)
        
        # 註冊全局快捷鍵 F9
        keyboard.add_hotkey('f9', self.toggle_service)

    def lock_hardware(self):
        """修復版：如果 Device ID 為 None，則使用 Scan Code 鎖定"""
        messagebox.showinfo("提示", "點擊確定後，請立即用掃碼槍掃一個碼進行識別")
        self.btn_hw.config(text="正在偵測硬件...", bg="#bbdefb")
        
        def on_hw_scan(event):
            # 優先使用設備 ID，若為 None 則生成基於硬件碼的虛擬 ID
            dev_id = event.device if event.device is not None else f"SCANNER_HW_{event.scan_code}"
            self.target_device = dev_id
            
            # 回到 UI 線程更新
            self.root.after(0, lambda: self.btn_hw.config(text=f"已綁定: {dev_id}", bg="#c8e6c9"))
            self.root.after(0, lambda: self.lbl_status.config(text="● 硬件就緒", fg="blue"))
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
        
        # 獲取當前按鍵的標識 (與綁定邏輯一致)
        curr_dev = event.device if event.device is not None else f"SCANNER_HW_{event.scan_code}"
        
        # 【核心修復】若非綁定硬件，直接放行鍵盤輸入
        if self.target_device is not None and curr_dev != self.target_device:
            return True 
        
        if event.event_type == 'down':
            if event.name == 'enter':
                barcode = "".join(self.key_buffer).strip()
                self.key_buffer = []
                
                target_cmds = [c.strip().lower() for c in self.ent_code.get().split(',')]
                
                if barcode.lower() in target_cmds:
                    self.switch_logic()
                    return False # 吞掉指令回車
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
                messagebox.showwarning("提示", "請先綁定掃碼槍硬件")
                return
            if not self.hwnd_a or not self.hwnd_b:
                messagebox.showwarning("提示", "請先綁定窗口 A 和 B")
                return
            self.is_running = True
            keyboard.hook(self.handle_scan, suppress=True)
            self.lbl_status.config(text="● 硬件隔離運行中", fg="#28a745")
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
