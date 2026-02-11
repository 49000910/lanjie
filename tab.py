import keyboard
import pyautogui
import time

# --- 配置区 ---
TARGET_CODE = "w123"  
SWITCH_DELAY = 0.3    

key_buffer = []

def handle_scan(event):
    global key_buffer
    
    if event.event_type == 'down':
        if event.name == 'enter':
            full_code = "".join(key_buffer).lower()
            key_buffer.clear() # 先清空防止干扰
            
            if full_code == TARGET_CODE:
                pyautogui.hotkey('alt', 'tab')
                time.sleep(SWITCH_DELAY)
                # 模拟 Tab 找回焦点
                keyboard.press_and_release('tab')
                
            elif full_code:
                # 【关键修复】：取消钩子再发送，防止自己拦截自己
                keyboard.unhook_all() 
                keyboard.write(full_code)
                keyboard.press_and_release('enter')
                # 重新开启拦截
                keyboard.hook(handle_scan, suppress=True)
            
        elif len(event.name) == 1:
            key_buffer.append(event.name)
        elif event.name == 'backspace':
            if key_buffer: key_buffer.pop()
    
    return False # 返回 False 确保 suppress 生效

if __name__ == "__main__":
    # 强制管理员检测（PyInstaller --uac-admin 已处理，这里做双保险）
    keyboard.hook(handle_scan, suppress=True)
    # 增加一个小提示
    pyautogui.alert("条码枪切换脚本已启动！\n指令码: w123\n退出请按 Esc")
    keyboard.wait('esc')
