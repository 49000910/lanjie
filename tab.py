import keyboard
import time
import threading
import tkinter as tk
from tkinter import messagebox
import sys
import win32gui
import win32con
import pyperclip
import pyautogui

class BarcodeSwitchUI:
    def __init__(self, root):
        self.root = root
        self.root.title("快切助手 v8.0")
        self.root.geometry("320x420")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#f4f4f4")
        
        self.hwnd_a = None
        self.hwnd_b = None
        self.is_running = False
        self.key_buffer = []
        self.last_key_time = 0
        self.scan_threshold = 0.05  # 识别扫描枪的灵敏度，建议0.04-0.06

        # --- UI 布局 ---
        tk.Label(root, text="⌨️ 切换指令条码:", bg="#f4f4f4", font=("微软雅黑", 9)).pack(pady=(15,0))
        self.ent_code = tk.Entry(root, justify='center', font=("Consolas", 12), fg="blue")
        self.ent_code.insert(0, "123") 
        self.ent_code.pack(pady=5)

        # 窗口 A 绑定器
        self.btn_pick_a = tk.Button(root, text="🎯 按住并拖动到窗口 A", bg="#ffffff", relief="groove", height=2)
        self.btn_pick_a.pack(padx=40, pady=8, fill="x")
        self.btn_pick_a.bind("<ButtonPress-1>", lambda e: self.start_drag("A"))
        self.btn_pick_a.bind("<ButtonRelease-1>", lambda e: self.stop_drag("A"))

        # 窗口 B 绑定器
        self.btn_pick_b = tk.Button(root, text="🎯 按住并拖动到窗口 B", bg="#ffffff", relief="groove", height=2)
        self.btn_pick_b.pack(padx=40, pady=8, fill="x")
        self.btn_pick_b.bind("<ButtonPress-1>", lambda e: self.start_drag("B"))
        self.btn_pick_b.bind("<ButtonRelease-1>", lambda e: self.stop_drag("B"))

        self.lbl_info = tk.Label(root, text="状态: A(待定) | B(待定)", bg="#f4f4f4", fg="#666", font=("微软雅黑", 8))
        self.lbl_info.pack(pady=5)

        self.lbl_status = tk.Label(root, text="● 服务待命", fg="gray", font=("微软雅黑", 11, "bold"), bg="#f4f4f4")
        self.lbl_status.pack(pady=10)

        self.btn_toggle = tk.Button(root, text="▶ 启动服务", command=self.toggle_service, bg="#28a745", fg="white", height=2, font=("微软雅黑", 10, "bold"), bd=0)
        self.btn_toggle.pack(pady=10, fill="x", padx=60)

    # --- 准星定位逻辑 ---
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
                self.btn_pick_a.config(text=f"已锁: {title}...", bg="#e3f2fd")
            else: 
                self.hwnd_b = hwnd
                self.btn_pick_b.config(text=f"已锁: {title}...", bg="#e3f2fd")
            self.lbl_info.config(text=f"A({'已就绪' if self.hwnd_a else '空'}) | B({'已就绪' if self.hwnd_b else '空'})")

    # --- 核心拦截与指令处理 ---
    def handle_scan(self, event):
        if not self.is_running: return True
        
        now = time.time()
        interval = now - self.last_key_time
        self.last_key_time = now

        if event.event_type == 'down':
            # 1. 如果输入间隔过长，视为手动输入，不拦截（保证手动输入干净）
            if interval > self.scan_threshold and event.name != 'enter':
                self.key_buffer.clear()
                return True 

            # 2. 捕捉到扫描枪发送的【回车】信号
            if event.name == 'enter':
                barcode = "".join(self.key_buffer).lower()
                self.key_buffer.clear()
                
                target_cmd = self.ent_code.get().lower()
                
                # 情况 A：匹配到指令 '123'
                if barcode == target_cmd:
                    self.switch_logic() # 切换窗口
                    return False # 【拦截】吞掉回车，确保窗口切换后是干净的
                
                # 情况 B：匹配到普通条码内容
                elif barcode:
                    self.smart_paste(barcode) # 执行粘贴+补回车
                    return False # 【拦截】吞掉原始回车，由程序补发可控回车
                
                return True

            # 3. 实时拦截扫描过程中的单个字符，存入缓存
            if len(event.name) == 1:
                self.key_buffer.append(event.name)
                return False # 【拦截】不让字符打在输入框里
                
        return True

    def smart_paste(self, content):
        """剪切板粘贴逻辑：确保内容干净上屏并自动补回车"""
        def run():
            old_clip = pyperclip.paste()
            pyperclip.copy(content)
            
            keyboard.unhook_all() # 临时解绑防止自拦截
            
            # 模拟 Ctrl+V
            keyboard.press_and_release('ctrl+v')
            time.sleep(0.08) # 给目标软件留出一点响应粘贴的时间
            # 补偿回车
            keyboard.press_and_release('enter')
            
            time.sleep(0.08)
            pyperclip.copy(old_clip) # 还原用户之前的剪切板
            keyboard.hook(self.handle_scan, suppress=True) # 重新挂载拦截器
            
        threading.Thread(target=run, daemon=True).start()

    def switch_logic(self):
        """基于句柄的硬跳转逻辑"""
        def task():
            curr_hwnd = win32gui.GetForegroundWindow()
            # 逻辑：非 A 即 B
            target = self.hwnd_b if curr_hwnd == self.hwnd_a else self.hwnd_a
            if target and win32gui.IsWindow(target):
                if win32gui.IsIconic(target):
                    win32gui.ShowWindow(target, win32con.SW_RESTORE)
                # 强行带到前台
                win32gui.SetForegroundWindow(target)
        threading.Thread(target=task, daemon=True).start()

    def toggle_service(self):
        if not self.is_running:
            if not self.hwnd_a or not self.hwnd_b:
                messagebox.showwarning("提示", "请先用准星【拖拽绑定】两个窗口")
                return
            self.is_running = True
            keyboard.hook(self.handle_scan, suppress=True)
            self.lbl_status.config(text="● 服务运行中", fg="#28a745")
            self.btn_toggle.config(text="■ 停止服务", bg="#dc3545")
        else:
            self.is_running = False
            keyboard.unhook_all()
            self.lbl_status.config(text="● 服务已停止", fg="red")
            self.btn_toggle.config(text="▶ 启动服务", bg="#28a745")

if __name__ == "__main__":
    root = tk.Tk()
    app = BarcodeSwitchUI(root)
    root.mainloop()
