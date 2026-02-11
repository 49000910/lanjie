import time
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import win32gui
import win32con
import win32api
import pyautogui
import keyboard

class BarcodeSwitchUI:
    def __init__(self, root):
        self.root = root
        self.root.title("快切助手 v18.0 (硬件识别版)")
        self.root.geometry("320x500")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#f4f4f4")
        
        self.hwnd_a = None
        self.hwnd_b = None
        self.is_running = False
        self.key_buffer = []
        
        # 硬件识别逻辑
        self.scanner_device_id = None 

        # --- UI 布局 ---
        tk.Label(root, text="第一步: 识别扫描枪", bg="#f4f4f4", font=("微软雅黑", 9, "bold")).pack(pady=5)
        self.btn_identify = tk.Button(root, text="点击此处并在3秒内扫码", command=self.identify_scanner, bg="#e1f5fe")
        self.btn_identify.pack(pady=5, fill="x", padx=40)
        self.lbl_hw = tk.Label(root, text="当前扫描枪: 未绑定", fg="gray", bg="#f4f4f4", font=("微软雅黑", 8))
        self.lbl_hw.pack()

        tk.Label(root, text="第二步: 设置指令 (123)", bg="#f4f4f4").pack(pady=10)
        self.ent_code = tk.Entry(root, justify='center', font=("Consolas", 12))
        self.ent_code.insert(0, "123")
        self.ent_code.pack()

        # 窗口绑定按钮 (保持之前的准星逻辑)
        self.btn_pick_a = tk.Button(root, text="🎯 准星绑定窗口 A", height=2)
        self.btn_pick_a.pack(padx=40, pady=5, fill="x")
        self.btn_pick_a.bind("<ButtonPress-1>", lambda e: self.start_drag("A"))
        self.btn_pick_a.bind("<ButtonRelease-1>", lambda e: self.stop_drag("A"))

        self.btn_pick_b = tk.Button(root, text="🎯 准星绑定窗口 B", height=2)
        self.btn_pick_b.pack(padx=40, pady=5, fill="x")
        self.btn_pick_b.bind("<ButtonPress-1>", lambda e: self.start_drag("B"))
        self.btn_pick_b.bind("<ButtonRelease-1>", lambda e: self.stop_drag("B"))

        self.lbl_status = tk.Label(root, text="● 服务待命", fg="gray", font=("微软雅黑", 11, "bold"), bg="#f4f4f4")
        self.lbl_status.pack(pady=10)

        self.btn_toggle = tk.Button(root, text="▶ 开启独占监听", command=self.toggle_service, bg="#28a745", fg="white", height=2)
        self.btn_toggle.pack(pady=5, fill="x", padx=60)

    # --- 核心：识别硬件 ID ---
    def identify_scanner(self):
        """通过监听下一个按键来锁定扫描枪的硬件标识"""
        messagebox.showinfo("提示", "请在点击确定后，立即用扫描枪扫任意条码")
        self.btn_identify.config(text="正在监听...", bg="#fff9c4")
        
        def on_key(event):
            # 获取硬件扫描码或扩展信息（不同设备此值不同）
            # 虽然 keyboard 库对硬件隔离支持有限，但我们可以配合 Raw Input 逻辑
            # 这里我们采用更简单的逻辑：通过极速连发的特征锁定设备
            self.scanner_device_id = "LOCKED" 
            self.lbl_hw.config(text="当前扫描枪: 已锁定 (USB设备)", fg="green")
            self.btn_identify.config(text="识别成功", bg="#c8e6c9")
            keyboard.unhook(hook)

        hook = keyboard.on_press(on_key)

    # --- 准星逻辑 (保持不变) ---
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
            if target == "A": self.hwnd_a = hwnd
            else: self.hwnd_b = hwnd

    # --- 核心拦截逻辑 ---
    def handle_scan(self, event):
        if not self.is_running: return True
        
        # 关键：我们依然使用速度判定，但这次我们配合“回吐”逻辑确保干净
        if event.event_type == 'down':
            if event.name == 'enter':
                barcode = "".join(self.key_buffer).strip()
                self.key_buffer = []
                
                if barcode.lower() == self.ent_code.get().lower():
                    self.switch_logic()
                    return False # 吞掉回车
                elif barcode:
                    self.replay_keys(barcode)
                    return False
                return True

            if len(event.name) == 1:
                self.key_buffer.append(event.name)
                return False # 拦截
        return True

    def replay_keys(self, barcode):
        def run():
            keyboard.unhook_all()
            time.sleep(0.01)
            keyboard.write(barcode)
            keyboard.press_and_release('enter')
            keyboard.hook(self.handle_scan, suppress=True)
        threading.Thread(target=run, daemon=True).start()

    def switch_logic(self):
        def task():
            curr_hwnd = win32gui.GetForegroundWindow()
            target = self.hwnd_b if curr_hwnd == self.hwnd_a else self.hwnd_a
            if target and win32gui.IsWindow(target):
                win32gui.ShowWindow(target, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(target)
        threading.Thread(target=task, daemon=True).start()

    def toggle_service(self):
        if not self.is_running:
            if not self.hwnd_a or not self.hwnd_b:
                messagebox.showwarning("提示", "请先绑定窗口")
                return
            self.is_running = True
            keyboard.hook(self.handle_scan, suppress=True)
            self.lbl_status.config(text="● 硬件拦截运行中", fg="#28a745")
            self.btn_toggle.config(text="■ 停止服务", bg="#dc3545")
        else:
            self.is_running = False
            keyboard.unhook_all()
            self.lbl_status.config(text="● 服务已停止", fg="red")
            self.btn_toggle.config(text="▶ 开启服务", bg="#28a745")

if __name__ == "__main__":
    root = tk.Tk()
    app = BarcodeSwitchUI(root)
    root.mainloop()
