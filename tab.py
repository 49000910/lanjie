import keyboard
import time
import threading
import tkinter as tk
from tkinter import messagebox
import sys
import win32gui
import win32con
import pyautogui

class BarcodeSwitchUI:
    def __init__(self, root):
        self.root = root
        self.root.title("快切助手 v16.0 (增强双重判定)")
        self.root.geometry("320x450")
        self.root.attributes("-topmost", True)
        
        self.hwnd_a = None
        self.hwnd_b = None
        self.is_running = False
        
        # --- 核心变量 ---
        self.last_key_time = 0
        self.SCAN_SPEED_THRESHOLD = 0.08  # 速度阈值
        self.key_buffer = []

        # --- UI 布局 ---
        tk.Label(root, text="⌨️ 切换指令 (可用逗号分隔):", fg="#555").pack(pady=(10,0))
        self.ent_code = tk.Entry(root, justify='center', font=("Consolas", 12))
        self.ent_code.insert(0, "123") 
        self.ent_code.pack(pady=5)

        self.btn_pick_a = tk.Button(root, text="🎯 准星拖动到窗口 A", bg="#ffffff", height=2)
        self.btn_pick_a.pack(padx=40, pady=5, fill="x")
        self.btn_pick_a.bind("<ButtonPress-1>", lambda e: self.start_drag("A"))
        self.btn_pick_a.bind("<ButtonRelease-1>", lambda e: self.stop_drag("A"))

        self.btn_pick_b = tk.Button(root, text="🎯 准星拖动到窗口 B", bg="#ffffff", height=2)
        self.btn_pick_b.pack(padx=40, pady=5, fill="x")
        self.btn_pick_b.bind("<ButtonPress-1>", lambda e: self.start_drag("B"))
        self.btn_pick_b.bind("<ButtonRelease-1>", lambda e: self.stop_drag("B"))

        self.lbl_status = tk.Label(root, text="● 已停止 (F9启动)", fg="red", font=("微软雅黑", 11, "bold"))
        self.lbl_status.pack(pady=10)

        self.btn_toggle = tk.Button(root, text="▶ 启动服务 (F9)", command=self.toggle_service, bg="#28a745", fg="white", height=2)
        self.btn_toggle.pack(pady=5, fill="x", padx=60)
        
        tk.Label(root, text="提示：按 F9 可全局快速开关拦截", fg="#999", font=("微软雅黑", 8)).pack()

        # 注册全局快捷键 F9
        keyboard.add_hotkey('f9', self.toggle_service)

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

    def handle_scan(self, event):
        if not self.is_running: return True
        if event.event_type == 'down':
            current_time = time.time()
            interval = current_time - self.last_key_time
            self.last_key_time = current_time

            # 速度判定：超过阈值则释放缓存
            if interval > self.SCAN_SPEED_THRESHOLD and len(self.key_buffer) > 0:
                self.flush_buffer()
                return True 

            if event.name == 'enter':
                full_code = "".join(self.key_buffer).lower().strip()
                self.key_buffer = []
                
                # 指令列表解析
                target_cmds = [c.strip().lower() for c in self.ent_code.get().split(',')]
                
                if full_code in target_cmds:
                    self.switch_logic()
                    return False # 吞掉指令回车
                elif full_code:
                    self.release_and_write("", append_enter=True)
                    return False
                return True

            elif len(event.name) == 1:
                self.key_buffer.append(event.name)
                return False 
        return True

    def flush_buffer(self):
        remaining = "".join(self.key_buffer)
        self.key_buffer = []
        if remaining:
            self.release_and_write(remaining)

    def release_and_write(self, content, append_enter=False):
        def run():
            keyboard.unhook_all()
            if content:
                keyboard.write(content, delay=0.005) # 极小延迟提高兼容性
            if append_enter:
                keyboard.press_and_release('enter')
            keyboard.hook(self.handle_scan, suppress=True)
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
            except:
                pass
        threading.Thread(target=task, daemon=True).start()

    def toggle_service(self):
        if not self.is_running:
            if not self.hwnd_a or not self.hwnd_b:
                messagebox.showwarning("提示", "请先绑定 A/B 窗口")
                return
            self.is_running = True
            keyboard.hook(self.handle_scan, suppress=True)
            self.lbl_status.config(text="● 服务运行中", fg="#28a745")
            self.btn_toggle.config(text="■ 停止服务 (F9)", bg="#dc3545")
        else:
            self.is_running = False
            keyboard.unhook_all()
            self.key_buffer = []
            self.lbl_status.config(text="● 已停止 (F9)", fg="red")
            self.btn_toggle.config(text="▶ 启动服务 (F9)", bg="#28a745")

if __name__ == "__main__":
    root = tk.Tk()
    app = BarcodeSwitchUI(root)
    root.mainloop()
