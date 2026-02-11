import keyboard
import pyautogui
import time

# --- 配置区 ---
TARGET_CODE = "w123"  # 你设定的指令条码
SWITCH_DELAY = 0.3    # 切换窗口后的等待时间（秒），若焦点没跟上可调大

# 内部缓冲区
key_buffer = []

def handle_scan(event):
    global key_buffer
    
    if event.event_type == 'down':
        # 1. 识别到回车（扫码结束）
        if event.name == 'enter':
            full_code = "".join(key_buffer).lower()
            
            if full_code == TARGET_CODE:
                # 【指令模式】：拦截 w123，不输入，直接切换
                print(f">>> 匹配指令码 [{full_code}]：执行窗口切换")
                
                # 执行 Alt+Tab
                pyautogui.hotkey('alt', 'tab')
                
                # 等待窗口稳定后，模拟一次 Tab 键尝试找回光标（针对浏览器/EXE通用）
                time.sleep(SWITCH_DELAY)
                keyboard.press_and_release('tab')
                
            elif full_code:
                # 【普通模式】：补发刚才拦截的条码内容 + 回车
                print(f">>> 匹配普通码 [{full_code}]：执行数据补录")
                # 使用 write 直接输入字符串，速度极快
                keyboard.write(full_code)
                keyboard.press_and_release('enter')
            
            # 清空缓存
            key_buffer.clear()
            
        # 2. 拦截并缓存普通字符
        elif len(event.name) == 1:
            key_buffer.append(event.name)
            
        # 3. 拦截并缓存 Backspace (防止扫码枪带有退格校准)
        elif event.name == 'backspace':
            if key_buffer:
                key_buffer.pop()

# --- 启动区 ---
if __name__ == "__main__":
    print("========================================")
    print("   条码枪智能拦截切换脚本已启动")
    print(f"   当前指令码: {TARGET_CODE}")
    print("   退出脚本请按: Esc")
    print("========================================")
    print("注意：请务必【以管理员身份】运行此终端！")

    # 开启全局拦截 (suppress=True)，确保输入框不出现 w123 且回车不跳格
    keyboard.hook(handle_scan, suppress=True)

    # 保持程序运行，直到按下 Esc
    keyboard.wait('esc')
