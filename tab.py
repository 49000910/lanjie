import time
import keyboard
# ... 其余库保持不变 ...

class SpeedFilterSwitcher:
    def __init__(self, root):
        # ... 初始化 UI ...
        self.last_key_time = 0
        self.SCAN_SPEED_THRESHOLD = 0.08  # 判定阈值：小于0.08秒视为扫码枪
        self.key_buffer = []

    def handle_scan(self, event):
        if event.event_type == 'down':
            current_time = time.time()
            interval = current_time - self.last_key_time
            self.last_key_time = current_time

            # 1. 如果间隔太长，判定为人手
            if interval > self.SCAN_SPEED_THRESHOLD and len(self.key_buffer) > 0:
                # 判定为人手输入：将缓冲区内容吐出来，并清空
                remaining = "".join(self.key_buffer)
                self.key_buffer = []
                keyboard.write(remaining) # 补发之前被拦截的字符
                # 注意：此处不 return，让当前按键继续往下走

            # 2. 正常拦截与逻辑处理
            if event.name == 'enter':
                full_code = "".join(self.key_buffer).lower()
                # ... (此处保持原有的 w123 判定与窗口切换逻辑) ...
                self.key_buffer = []
            elif len(event.name) == 1:
                self.key_buffer.append(event.name)
