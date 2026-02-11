import keyboard
import time
import pygetwindow as gw
import pyautogui
import threading
import tkinter as tk
from tkinter import messagebox
import sys

class BarcodeSwitchUI:
    def __init__(self, root):
        self.root = root
        self.root.title("快切助手 v5.5")
        self.root.geometry("320x360")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#f0f0f0")
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.is_running = False
        self.key_buffer = []
        self.last_key_time = 0
        self.scan_threshold = 0.03 
        
        # --- UI 布局 ---
        tk.Label(root, text="⌨️ 指令条码:", bg="#f0f0f0").pack(pady=(10,0))
        self.ent_code = tk.Entry(root, justify='center', font=("Consolas", 10))
        self.ent_code.insert(0, "w123")
        self.ent_code.pack(pady=2)

        tk.Label(root, text="🔲 窗口 A 关键词 (如: Excel):", bg="#f0f0f0").pack()
        self.ent_a = tk.Entry(root, justify='center')
        self.ent_a.insert(0, "Excel")
        self.ent_a.pack(pady=2)

        tk.Label(root, text="🔲 窗口 B 关键词 (如: Chrome):", bg="#f0f0f0").pack()
        self.ent_b = tk.Entry(root, justify='center')
        self.ent_b.insert(0, "Chrome")
        self.ent_b.pack(pady=2)

        self.intercept_normal = tk.BooleanVar(value=True)
        tk.Checkbutton(root, text="拦截并补发普通条码 (防止错乱)", 
                       variable=self.intercept_normal, bg="#f0f0f0", font=("微软雅黑", 8)).pack(pady=5)

        self.lbl_status = tk.Label(root, text="● 已停止", fg="red", font=("微软雅黑", 10, "bold"), bg="#f0f0f0")
        self.lbl_status.pack(pady=5)

        self.btn_toggle = tk.Button(root, text="启动服务", command=self.toggle_service, 
                                   bg="#4caf50", fg="white", width=20, height=2, bd=0)
        self.btn_toggle.pack(pady=5)
        
        tk.Label(root, text="输入关键词即可模糊匹配窗口", fg="#999", font=("微软雅黑", 7), bg="#f0f0f0").pack()

    def toggle_service(self):
        if not self.is_running:
            self.target_code = self.ent_code.get().lower()
            self.win_a_key = self.ent_a.get().strip()
            self.win_b_key = self.ent_b.get().strip()
            
            if not self.win_a_key or not self.win_b_key:
                messagebox.showwarning("提示", "请填写窗口关键词")
                return
            
            self.is_running = True
            keyboard.hook(self.handle_scan, suppress=True)
            self.lbl_status.config(text="● 运行中", fg="green")
            self.btn_toggle.config(text="停止服务", bg="#f44336")
        else:
            self.stop_service()

    def stop_service(self):
        self.is_running = False
        keyboard.unhook_all()
        self.lbl_status.config(text="● 已停止", fg="red")
        self.btn_toggle.config(text="启动服务", bg="#4caf50")

    def on_closing(self):
        self.stop_service()
        self.root.destroy()
        sys.exit(0)

    def switch_logic(self):
        """核心模糊匹配跳转逻辑"""
        def task():
            try:
                active_win = gw.getActiveWindow()
                active_title = active_win.title.lower() if active_win else ""
                
                # 判定当前在哪个窗口，决定跳向哪一个
                # 使用 in 进行模糊匹配，且不区分大小写
                if self.win_a_key.lower() in active_title:
                    target_key = self.win_b_key
                else:
                    target_key = self.win_a_key
                
                # 在所有窗口中寻找包含关键词的窗口
                all_wins = gw.getAllWindows()
                matched_wins = [w for w in all_wins if target_key.lower() in w.title.lower()]
                
                if matched_wins:
                    target_win = matched_wins[0] # 取第一个匹配到的
                    if target_win.isMinimized:
                        target_win.restore()
                    target_win.activate()
                else:
                    # 没搜到关键词窗口则执行默认切换
                    pyautogui.hotkey('alt', 'tab')
            except:
                pyautogui.hotkey('alt', 'tab')
        threading.Thread(target=task, daemon=True).start()

    def handle_scan(self, event):
        if not self.is_running: return True
        now = time.time()
        interval = now - self.last_key_time
        self.last_key_time = now

        if event.event_type == 'down':
            if interval > self.scan_threshold and event.name != 'enter':
                self.key_buffer.clear()
                return True

            if event.name == 'enter':
                full_code = "".join(self.key_buffer).lower()
                self.key_buffer.clear()
                if full_code == self.target_code:
                    self.switch_logic()
                    return False
                elif full_code:
                    if self.intercept_normal.get():
                        keyboard.unhook_all() 
                        keyboard.write(full_code)
                        keyboard.press_and_release('enter')
                        keyboard.hook(self.handle_scan, suppress=True)
                        return False
                return True

            if len(event.name) == 1:
                self.key_buffer.append(event.name)
                return True if not self.intercept_normal.get() else False
        return True if not self.intercept_normal.get() else False

if __name__ == "__main__":
    root = tk.Tk()
    app = BarcodeSwitchUI(root)
    root.mainloop()
