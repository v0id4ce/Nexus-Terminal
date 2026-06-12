import customtkinter as ctk
import tkinter as tk
import threading
import time
import random
import math
import pyautogui
import ctypes
import json
import os
import hashlib
import base64

"""
Nexus 桌面效率助手
Copyright (c) 2026 v0id4ce
License: MIT
"""

# ================= 信息加密模块 (PBKDF2 + XOR + Base64) =================

_SALT = b'NexusSalt2026_v0id4ce'
_KEY = hashlib.pbkdf2_hmac('sha256', b'Nexus-Terminal', _SALT, 100000, dklen=32)

def _decrypt(b64_cipher):
    """解密 Base64 密文，返回明文字符串"""
    try:
        cipher = base64.b64decode(b64_cipher)
        plain = bytes([cipher[i] ^ _KEY[i % len(_KEY)] for i in range(len(cipher))])
        return plain.decode('utf-8')
    except Exception:
        return "[解密失败]"

# 密文存储区 — 运行时解密
_ENC_AUTHOR = "JyEB0wp6rw=="
_ENC_GITHUB = "OWUcx00j5QIXGuLbh5hGZVUtpQu7SMti07k="
_ENC_COPYRIGHT = "En4YzkxwrUUEU77Q29paNgh2qgu7SMti07ms0z1kLgIdeAvSUGqvAw=="

def get_author():
    return _decrypt(_ENC_AUTHOR)

def get_github_url():
    return _decrypt(_ENC_GITHUB)

def get_copyright():
    return _decrypt(_ENC_COPYRIGHT)

# ================= 尝试导入串口库，若未安装则提供静默降级
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

# ================= Windows API 容错封装 =================
user32 = ctypes.windll.user32
VK_Q = 0x51

def is_q_pressed():
    try:
        return user32.GetAsyncKeyState(VK_Q) & 0x8000 != 0
    except Exception:
        return False

# ================= 核心环境初始化 =================
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
try:
    ctypes.windll.winmm.timeBeginPeriod(1)
except Exception:
    pass

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True
ctk.set_appearance_mode("Dark")

MORANDI = {
    "bg_main": "#1e1e24", "bg_card": "#2b2b36", "text_h1": "#f0f0f5",
    "text_p": "#9a9aa6", "accent_blue": "#6b8e8e", "accent_blue_hover": "#5a7a7a",
    "accent_red": "#b57b7b", "accent_red_hover": "#9a6666", "border": "#3d3d4a",
    "led_off": "#4d4d5e", "led_warn": "#d4a373", "led_on": "#8fbc8f"
}

# ================= 硬件通信桥梁 (Serial Bridge) =================

class HardwareBridge:
    def __init__(self):
        self.serial_port = None
        self.is_active = False
        self.lock = threading.Lock()

    def connect(self, port_name):
        """军工级握手验证：防误判、防乱码拦截"""
        if not SERIAL_AVAILABLE: return False, "缺少 pyserial 库"
        
        self.disconnect()
        try:
            self.serial_port = serial.Serial(port_name, 115200, timeout=0.2)
            time.sleep(2.0) 
            
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            
            self.serial_port.write(b"NEXUS_REQ\n")
            self.serial_port.flush()
            
            start_wait = time.time()
            while time.time() - start_wait < 2.0:
                if self.serial_port.in_waiting:
                    response = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if response == "NEXUS_ACK":
                        self.is_active = True
                        return True, "硬件握手成功"
            
            self.disconnect()
            return False, "无对应暗号回应 (拒绝接入)"
            
        except Exception as e:
            self.disconnect()
            return False, f"端口占用/无权限: {e}"

    def disconnect(self):
        self.is_active = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.serial_port = None

    def send_command(self, cmd):
        if not self.is_active: return
        with self.lock:
            try:
                self.serial_port.write(f"{cmd}\n".encode('utf-8'))
            except Exception:
                self.is_active = False 

# ================= 自动化执行引擎 (智能双路路由 + 极限容错) =================

class AutoExecutionEngine:
    def __init__(self, hardware_bridge):
        self.hw = hardware_bridge

    def route_move(self, x, y):
        """【修复1】三级降级链：硬件 -> user32 -> pyautogui -> 忽略"""
        if self.hw.is_active:
            self.hw.send_command(f"M,{int(x)},{int(y)}")
        else:
            try:
                user32.SetCursorPos(int(x), int(y))
            except Exception:
                try:
                    pyautogui.moveTo(int(x), int(y))
                except Exception:
                    pass

    def route_mouse_event(self, action):
        """【修复2】加入 try/except，防止软件点击因防呆机制或系统异常崩溃"""
        if self.hw.is_active:
            self.hw.send_command(f"{action}")
        else:
            try:
                if action == "D": pyautogui.mouseDown()
                elif action == "U": pyautogui.mouseUp()
            except Exception:
                pass

    def get_gaussian_point(self, x1, y1, x2, y2):
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        sx, sy = max((x2 - x1) / 6.0, 1), max((y2 - y1) / 6.0, 1)
        while True:
            tx, ty = int(random.gauss(cx, sx)), int(random.gauss(cy, sy))
            if (x1 + 2) <= tx <= (x2 - 2) and (y1 + 2) <= ty <= (y2 - 2):
                return tx, ty

    def _dt_move(self, sx, sy, tx, ty, duration, easing="out"):
        start_t = time.perf_counter()
        arc = min(math.hypot(tx-sx, ty-sy) * 0.1, 40)
        dir_val = 1 if random.random() > 0.5 else -1
        cp1x = sx + (tx - sx) * 0.4 + random.uniform(-arc, arc) * dir_val
        cp1y = sy + (ty - sy) * 0.4 + random.uniform(-arc, arc) * dir_val
        cp2x = sx + (tx - sx) * 0.8 + random.uniform(-arc, arc) * dir_val
        cp2y = sy + (ty - sy) * 0.8 + random.uniform(-arc, arc) * dir_val

        while True:
            elapsed = time.perf_counter() - start_t
            if elapsed >= duration:
                self.route_move(tx, ty)
                break
            
            raw_t = elapsed / duration
            if easing == "out": t = 1 - (1 - raw_t)**3 
            else: t = raw_t * raw_t * (3 - 2 * raw_t) 
            
            x = (1-t)**3*sx + 3*(1-t)**2*t*cp1x + 3*(1-t)*t**2*cp2x + t**3*tx
            y = (1-t)**3*sy + 3*(1-t)**2*t*cp1y + 3*(1-t)*t**2*cp2y + t**3*ty
            
            self.route_move(x, y)
            time.sleep(0.001)

    def execute_action(self, x1, y1, x2, y2, click_range=(1,1), dwell_time=1.0, tremor_intensity=1.0):
        tx, ty = self.get_gaussian_point(x1, y1, x2, y2)
        sx, sy = pyautogui.position()
        dist = math.hypot(tx - sx, ty - sy)
        W = max(min(x2 - x1, y2 - y1), 5.0) 

        try:
            if dist < 30:
                self._dt_move(sx, sy, tx, ty, random.uniform(0.08, 0.15), "out")
            else:
                total_dur = 0.1 + 0.15 * math.log2(1 + dist / W)
                if dist > 150 and random.random() < 0.3:
                    ratio = random.uniform(1.02, 1.06) 
                    ox, oy = sx + (tx - sx) * ratio, sy + (ty - sy) * ratio
                    self._dt_move(sx, sy, ox, oy, total_dur * 0.7, "out")
                    time.sleep(random.uniform(0.02, 0.05)) 
                    self._dt_move(ox, oy, tx, ty, total_dur * 0.3, "inout")
                else:
                    ratio = random.uniform(0.85, 0.95)
                    bx = sx + (tx - sx) * ratio + random.uniform(-W/3, W/3)
                    by = sy + (ty - sy) * ratio + random.uniform(-W/3, W/3)
                    self._dt_move(sx, sy, bx, by, total_dur * 0.65, "out")
                    time.sleep(random.uniform(0.03, 0.08)) 
                    corrections = random.randint(1, 2)
                    cx, cy = bx, by
                    for i in range(corrections):
                        nx, ny = (tx, ty) if i == corrections - 1 else (cx + (tx - cx) * random.uniform(0.6, 0.8), cy + (ty - cy) * random.uniform(0.6, 0.8))
                        self._dt_move(cx, cy, nx, ny, total_dur * (0.35 / corrections), "inout")
                        cx, cy = nx, ny
                        if i < corrections - 1: time.sleep(random.uniform(0.01, 0.03))

            actual_dwell = max(0.1, random.gauss(dwell_time, dwell_time * 0.1))
            end_dwell = time.time() + actual_dwell
            while time.time() < end_dwell:
                if tremor_intensity > 0 and random.random() < 0.2:
                    cx, cy = pyautogui.position()
                    dx, dy = random.gauss(0, tremor_intensity * 0.5), random.gauss(0, tremor_intensity * 0.5)
                    if abs(dx) >= 0.5 or abs(dy) >= 0.5: self.route_move(cx + dx, cy + dy)
                time.sleep(0.01) 

            actual_clicks = random.randint(click_range[0], click_range[1])
            for i in range(actual_clicks):
                self.route_mouse_event("D") 
                if random.random() < min(0.3 + (tremor_intensity * 0.15), 0.9) and tremor_intensity > 0:
                    cx, cy = pyautogui.position()
                    sd = max(1.0, tremor_intensity * 0.8)
                    self.route_move(cx + random.uniform(-sd, sd), cy + random.uniform(-sd, sd))

                press_dur = random.lognormvariate(-2.81, 0.3)
                time.sleep(max(0.02, min(press_dur, 0.25)))
                self.route_mouse_event("U") 

                if i < actual_clicks - 1:
                    interval = random.lognormvariate(-2.3, 0.3)
                    time.sleep(max(0.05, min(interval, 0.35)))

            return pyautogui.position()
        except Exception:
            return None

# ================= 多屏选区工具 =================

class AreaLocator:
    def __init__(self, master, callback):
        self.callback = callback
        self.snip_window = tk.Toplevel(master)
        self.snip_window.attributes('-alpha', 0.3)
        self.snip_window.attributes("-topmost", True)
        self.snip_window.overrideredirect(True) 
        
        try:
            self.vx = user32.GetSystemMetrics(76) 
            self.vy = user32.GetSystemMetrics(77) 
            vw = user32.GetSystemMetrics(78)      
            vh = user32.GetSystemMetrics(79)      
            self.snip_window.geometry(f"{vw}x{vh}+{self.vx}+{self.vy}")
        except Exception:
            self.vx, self.vy = 0, 0
            self.snip_window.attributes('-fullscreen', True)
            
        self.canvas = tk.Canvas(self.snip_window, cursor="cross", bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.abs_start_x = None
        self.abs_start_y = None
        self.rect = None
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.snip_window.bind("<Button-3>", self.cancel) 
        self.snip_window.bind("<Escape>", self.cancel)
        self.snip_window.focus_force()

    def on_press(self, event):
        self.abs_start_x = self.snip_window.winfo_pointerx()
        self.abs_start_y = self.snip_window.winfo_pointery()
        cx = self.abs_start_x - self.vx
        cy = self.abs_start_y - self.vy
        self.rect = self.canvas.create_rectangle(cx, cy, cx, cy, outline='#6b8e8e', width=2, fill="gray")

    def on_drag(self, event):
        if self.rect:
            abs_cur_x = self.snip_window.winfo_pointerx()
            abs_cur_y = self.snip_window.winfo_pointery()
            self.canvas.coords(self.rect, self.abs_start_x - self.vx, self.abs_start_y - self.vy, abs_cur_x - self.vx, abs_cur_y - self.vy)

    def on_release(self, event):
        if self.abs_start_x is None: return self.cancel()
        abs_end_x = self.snip_window.winfo_pointerx()
        abs_end_y = self.snip_window.winfo_pointery()
        self.snip_window.destroy()
        x1, x2 = sorted([int(self.abs_start_x), int(abs_end_x)])
        y1, y2 = sorted([int(self.abs_start_y), int(abs_end_y)])
        self.callback((x1, y1, x2, y2))

    def cancel(self, event=None):
        self.snip_window.destroy()
        self.callback(None)

# ================= 桌面效率助手 GUI =================

class EfficiencyTerminal(ctk.CTk):
    CONFIG_FILE = "nexus_config.json"

    def __init__(self):
        super().__init__()
        self.title("Nexus 桌面效率助手")
        self.geometry("740x500")
        self.resizable(False, False)
        self.configure(fg_color=MORANDI["bg_main"])

        self.task_areas = [] 
        self.data_lock = threading.Lock() 
        self.stop_event = threading.Event()
        
        self.hardware_bridge = HardwareBridge()
        self.engine = AutoExecutionEngine(self.hardware_bridge)
        
        self.setup_ui()
        self.load_config() 

    def setup_ui(self):
        self.card_area = ctk.CTkFrame(self, corner_radius=15, fg_color=MORANDI["bg_card"], border_width=1, border_color=MORANDI["border"])
        self.card_area.place(relx=0.03, rely=0.05, relwidth=0.45, relheight=0.6)
        
        ctk.CTkLabel(self.card_area, text="任务区域队列", font=("Microsoft YaHei UI", 18, "bold"), text_color=MORANDI["text_h1"]).pack(pady=(20, 5))
        self.lbl_coords = ctk.CTkLabel(self.card_area, text="尚未添加任务区域\n支持多显示器跨屏框选", text_color=MORANDI["text_p"], font=("Microsoft YaHei UI", 13))
        self.lbl_coords.pack(pady=10, expand=True)
        
        btn_box = ctk.CTkFrame(self.card_area, fg_color="transparent")
        btn_box.pack(pady=15)
        self.btn_select = ctk.CTkButton(btn_box, text="添加区域", width=100, corner_radius=20, fg_color=MORANDI["accent_blue"], hover_color=MORANDI["accent_blue_hover"], command=self.start_locating)
        self.btn_select.pack(side="left", padx=5)
        self.btn_clear = ctk.CTkButton(btn_box, text="清空队列", width=80, corner_radius=20, fg_color=MORANDI["accent_red"], hover_color=MORANDI["accent_red_hover"], command=self.clear_areas)
        self.btn_clear.pack(side="left", padx=5)

        self.card_strategy = ctk.CTkFrame(self, corner_radius=15, fg_color=MORANDI["bg_card"], border_width=1, border_color=MORANDI["border"])
        self.card_strategy.place(relx=0.52, rely=0.05, relwidth=0.45, relheight=0.6)
        
        ctk.CTkLabel(self.card_strategy, text="运行参数配置", font=("Microsoft YaHei UI", 18, "bold"), text_color=MORANDI["text_h1"]).pack(pady=(15, 5))
        cfg_frame = ctk.CTkFrame(self.card_strategy, fg_color="transparent")
        cfg_frame.pack(fill="x", padx=15)
        
        r1 = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        r1.pack(fill="x", pady=8)
        ctk.CTkLabel(r1, text="连按次数:", text_color=MORANDI["text_p"]).pack(side="left")
        self.combo_clicks = ctk.CTkComboBox(r1, values=["1 次", "2~3 次", "3~5 次", "5~8 次"], width=85, border_color=MORANDI["border"], button_color=MORANDI["accent_blue"])
        self.combo_clicks.set("1 次")
        self.combo_clicks.pack(side="left", padx=5)
        
        self.entry_dwell = ctk.CTkEntry(r1, width=45, border_color=MORANDI["border"])
        self.entry_dwell.insert(0, "1.0")
        self.entry_dwell.pack(side="right")
        ctk.CTkLabel(r1, text="操作停留(秒):", text_color=MORANDI["text_p"]).pack(side="right", padx=5)

        r2 = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        r2.pack(fill="x", pady=8)
        ctk.CTkLabel(r2, text="循环间隔:", text_color=MORANDI["text_p"]).pack(side="left")
        self.entry_max = ctk.CTkEntry(r2, width=45, border_color=MORANDI["border"])
        self.entry_max.insert(0, "4.5")
        self.entry_max.pack(side="right")
        ctk.CTkLabel(r2, text="~", text_color=MORANDI["text_p"]).pack(side="right", padx=2)
        self.entry_min = ctk.CTkEntry(r2, width=45, border_color=MORANDI["border"])
        self.entry_min.insert(0, "2.0")
        self.entry_min.pack(side="right")

        r3 = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        r3.pack(fill="x", pady=8)
        self.lbl_tremor = ctk.CTkLabel(r3, text="自然偏移: 1.0", text_color=MORANDI["text_p"])
        self.lbl_tremor.pack(side="left")
        self.slider_tremor = ctk.CTkSlider(r3, from_=0.0, to=4.0, number_of_steps=40, width=120, button_color=MORANDI["accent_blue"], progress_color=MORANDI["accent_blue_hover"], command=self.update_tremor)
        self.slider_tremor.set(1.0)
        self.slider_tremor.pack(side="right")

        self.use_macro_fatigue = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(self.card_strategy, text="智能休息模式 (模拟劳逸结合)", text_color=MORANDI["text_p"], progress_color=MORANDI["accent_blue"], variable=self.use_macro_fatigue).pack(pady=10)

        # --- 底部控制面板 ---
        self.card_ctrl = ctk.CTkFrame(self, corner_radius=15, fg_color=MORANDI["bg_card"], border_width=1, border_color=MORANDI["border"])
        self.card_ctrl.place(relx=0.03, rely=0.68, relwidth=0.94, relheight=0.28)
        
        # 硬件握手连接区
        hw_frame = ctk.CTkFrame(self.card_ctrl, fg_color="transparent")
        hw_frame.pack(fill="x", padx=15, pady=(10, 5))
        
        self.canvas_led = tk.Canvas(hw_frame, width=12, height=12, bg=MORANDI["bg_card"], highlightthickness=0)
        self.led_id = self.canvas_led.create_oval(1, 1, 11, 11, fill=MORANDI["led_off"], outline="")
        self.canvas_led.pack(side="left", padx=(0, 5), pady=2)
        
        self.lbl_hw_status = ctk.CTkLabel(hw_frame, text="纯软件模式 (无需硬件)", text_color=MORANDI["text_p"])
        self.lbl_hw_status.pack(side="left")
        
        self.btn_hw_connect = ctk.CTkButton(hw_frame, text="连接设备", width=70, height=24, corner_radius=12, fg_color=MORANDI["bg_main"], border_width=1, border_color=MORANDI["border"], hover_color=MORANDI["accent_blue_hover"], command=self.connect_hardware)
        self.btn_hw_connect.pack(side="right")
        
        # 【修复3】添加无感热插拔刷新按钮
        self.btn_refresh = ctk.CTkButton(hw_frame, text="🔄", width=30, height=24, fg_color="transparent", hover_color=MORANDI["bg_main"], command=self.refresh_ports)
        self.btn_refresh.pack(side="right", padx=(0, 5))

        self.combo_ports = ctk.CTkComboBox(hw_frame, values=self.get_ports(), width=80, height=24, border_color=MORANDI["border"], button_color=MORANDI["accent_blue"])
        self.combo_ports.pack(side="right", padx=0)
        
        tk.Frame(self.card_ctrl, height=1, bg=MORANDI["border"]).pack(fill="x", padx=15, pady=2)

        ctrl_bottom = ctk.CTkFrame(self.card_ctrl, fg_color="transparent")
        ctrl_bottom.pack(fill="both", expand=True, padx=15)
        
        self.lbl_status = ctk.CTkLabel(ctrl_bottom, text="> 系统已就绪，等待添加任务...", font=("Consolas", 13), text_color=MORANDI["accent_blue"])
        self.lbl_status.pack(side="left", pady=10)

        self.btn_stop = ctk.CTkButton(ctrl_bottom, text="⏹ 挂起", width=70, corner_radius=20, fg_color=MORANDI["bg_main"], border_width=1, border_color=MORANDI["border"], hover_color=MORANDI["accent_red_hover"], text_color=MORANDI["text_p"], state="disabled", command=lambda: self.stop_assisting(from_thread=False))
        self.btn_stop.pack(side="right", pady=10)
        
        self.btn_start = ctk.CTkButton(ctrl_bottom, text="▶ 启动", width=90, corner_radius=20, fg_color=MORANDI["accent_blue"], hover_color=MORANDI["accent_blue_hover"], command=self.start_assisting)
        self.btn_start.pack(side="right", padx=10, pady=10)

        # 关于按钮
        self.btn_about = ctk.CTkButton(ctrl_bottom, text="ℹ", width=28, height=28, corner_radius=14,
                                        fg_color="transparent", hover_color=MORANDI["border"],
                                        text_color=MORANDI["text_p"], font=("Segoe UI", 14),
                                        command=self.show_about)
        self.btn_about.pack(side="right", padx=(0, 5), pady=10)

    # ================= 关于窗口 =================

    def show_about(self):
        dialog = tk.Toplevel(self)
        dialog.title("关于")
        dialog.geometry("320x240")
        dialog.resizable(False, False)
        dialog.configure(bg=MORANDI["bg_card"])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 320) // 2
        y = self.winfo_y() + (self.winfo_height() - 240) // 2
        dialog.geometry(f"+{x}+{y}")

        title_frame = tk.Frame(dialog, bg=MORANDI["bg_card"])
        title_frame.pack(pady=(25, 10))

        tk.Label(title_frame, text="Nexus", font=("Microsoft YaHei UI", 20, "bold"),
                 fg=MORANDI["text_h1"], bg=MORANDI["bg_card"]).pack()
        tk.Label(title_frame, text="桌面效率助手 v4.1", font=("Microsoft YaHei UI", 11),
                 fg=MORANDI["text_p"], bg=MORANDI["bg_card"]).pack()

        tk.Frame(dialog, height=1, bg=MORANDI["border"]).pack(fill="x", padx=40, pady=10)

        info_frame = tk.Frame(dialog, bg=MORANDI["bg_card"])
        info_frame.pack(pady=5)

        author = get_author()
        tk.Label(info_frame, text=f"作者: {author}", font=("Microsoft YaHei UI", 11),
                 fg=MORANDI["text_h1"], bg=MORANDI["bg_card"]).pack(pady=2)

        # 可点击的 GitHub 链接
        github_url = get_github_url()
        link_btn = tk.Label(info_frame, text=github_url, font=("Segoe UI", 10, "underline"),
                            fg=MORANDI["accent_blue"], bg=MORANDI["bg_card"], cursor="hand2")
        link_btn.pack(pady=2)
        link_btn.bind("<Button-1>", lambda e: os.startfile(github_url))

        tk.Frame(dialog, height=1, bg=MORANDI["border"]).pack(fill="x", padx=40, pady=10)

        copyright_text = get_copyright()
        tk.Label(dialog, text=copyright_text, font=("Segoe UI", 9),
                 fg=MORANDI["text_p"], bg=MORANDI["bg_card"]).pack(pady=5)

        ctk.CTkButton(dialog, text="关闭", width=80, corner_radius=15,
                       fg_color=MORANDI["bg_main"], hover_color=MORANDI["border"],
                       command=dialog.destroy).pack(pady=10)

    # ================= 硬件状态管理 =================
    
    def get_ports(self):
        if not SERIAL_AVAILABLE: return ["未装库"]
        ports = [p.device for p in serial.tools.list_ports.comports()]
        return ports if ports else ["无设备"]

    def refresh_ports(self):
        """【修复3】热刷新端口列表，无需重启"""
        ports = self.get_ports()
        self.combo_ports.configure(values=ports)
        if ports and ports[0] not in ["未装库", "无设备"]:
            self.combo_ports.set(ports[-1]) # 默认选中最新插入的设备
        else:
            self.combo_ports.set(ports[0] if ports else "")

    def connect_hardware(self):
        port = self.combo_ports.get()
        if port in ["未装库", "无设备", ""]: return
        
        self.lbl_hw_status.configure(text="握手中...", text_color=MORANDI["led_warn"])
        self.canvas_led.itemconfig(self.led_id, fill=MORANDI["led_warn"])
        self.update()
        
        success, msg = self.hardware_bridge.connect(port)
        if success:
            self.lbl_hw_status.configure(text=f"物理通道就绪 ({port})", text_color=MORANDI["led_on"])
            self.canvas_led.itemconfig(self.led_id, fill=MORANDI["led_on"])
            self.btn_hw_connect.configure(text="断开")
        else:
            self.lbl_hw_status.configure(text=f"已回退软件模式 ({msg})", text_color=MORANDI["led_warn"])
            self.canvas_led.itemconfig(self.led_id, fill=MORANDI["led_warn"])
            
    # ================= 配置持久化 =================
    
    def save_config(self):
        try:
            config = {
                "clicks": self.combo_clicks.get(),
                "dwell": self.entry_dwell.get(),
                "min_int": self.entry_min.get(),
                "max_int": self.entry_max.get(),
                "tremor": self.slider_tremor.get(),
                "fatigue": self.use_macro_fatigue.get()
            }
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception:
            pass

    def load_config(self):
        if not os.path.exists(self.CONFIG_FILE): return
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.combo_clicks.set(config.get("clicks", "1 次"))
            self.entry_dwell.delete(0, 'end')
            self.entry_dwell.insert(0, config.get("dwell", "1.0"))
            self.entry_min.delete(0, 'end')
            self.entry_min.insert(0, config.get("min_int", "2.0"))
            self.entry_max.delete(0, 'end')
            self.entry_max.insert(0, config.get("max_int", "4.5"))
            t_val = config.get("tremor", 1.0)
            self.slider_tremor.set(t_val)
            self.update_tremor(t_val)
            self.use_macro_fatigue.set(config.get("fatigue", True))
        except Exception:
            pass

    # ================= 交互逻辑 =================
    
    def update_status_safe(self, text, color=None):
        self.after(0, lambda: self.lbl_status.configure(text=text, text_color=color if color else MORANDI["text_p"]))

    def update_tremor(self, value):
        self.lbl_tremor.configure(text=f"自然偏移: {float(value):.1f}")

    def start_locating(self):
        self.iconify() 
        time.sleep(0.3) 
        AreaLocator(self, self.on_focus_selected)

    def on_focus_selected(self, coords):
        self.deiconify()
        if coords is None: return 
        if coords[2] - coords[0] < 5 or coords[3] - coords[1] < 5:
            self.lbl_status.configure(text="> 提示：框选区域过小，请重新操作", text_color=MORANDI["accent_red"])
            return
            
        with self.data_lock: 
            self.task_areas.append(coords)
            count = len(self.task_areas)
            
        self.lbl_coords.configure(text=f"已记录 {count} 个任务区域\n队列将按顺序自动循环执行", text_color=MORANDI["text_h1"])
        
    def clear_areas(self):
        with self.data_lock: 
            self.task_areas.clear()
        self.lbl_coords.configure(text="队列已清空\n请重新框选任务区域", text_color=MORANDI["text_p"])

    def assist_thread(self, min_w, max_w, c_range, t_val, d_val):
        total, idx, start_time, last_rest = 0, 0, time.time(), time.time()

        while not self.stop_event.is_set():
            if is_q_pressed(): break

            with self.data_lock:
                if not self.task_areas: break
                area = self.task_areas[idx]
                queue_len = len(self.task_areas)

            self.engine.execute_action(*area, click_range=c_range, dwell_time=d_val, tremor_intensity=t_val)
            total += 1
            idx = (idx + 1) % queue_len
            
            run_dur = time.time() - start_time
            self.update_status_safe(f"> [运行中] 累计处理: {total} 次 | 即将前往区域: #{idx + 1}")

            if self.use_macro_fatigue.get():
                if run_dur > 3600 and (time.time() - last_rest) > 2400 and random.random() < 0.015:
                    r = random.uniform(180, 480)
                    self.update_status_safe(f"> [休息模式] 触发深度休息，系统挂起 {r//60:.0f} 分钟...", MORANDI["accent_red"])
                    self.sleep_safe(r)
                    last_rest = time.time(); continue
                elif run_dur > 1800 and (time.time() - last_rest) > 900 and random.random() < 0.03:
                    r = random.uniform(20, 60)
                    self.update_status_safe(f"> [休息模式] 触发随机停顿，系统暂停 {r:.0f} 秒...", MORANDI["accent_red"])
                    self.sleep_safe(r)
                    last_rest = time.time(); continue

            self.sleep_safe(random.uniform(min_w, max_w))
            
        self.stop_assisting(from_thread=True)

    def sleep_safe(self, sleep_time):
        end = time.time() + sleep_time
        last_drift = time.time()
        
        while time.time() < end:
            if self.stop_event.wait(0.05) or is_q_pressed(): 
                return
            
            if time.time() - last_drift > random.uniform(1.0, 3.0):
                cx, cy = pyautogui.position()
                dx, dy = random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
                if dx != 0 or dy != 0:
                    self.engine.route_move(cx + dx, cy + dy)
                last_drift = time.time()

    def start_assisting(self):
        with self.data_lock:
            if not self.task_areas:
                self.lbl_status.configure(text="> 提示：队列为空，请先添加任务区域", text_color=MORANDI["accent_red"])
                return
                
        try:
            min_w, max_w = float(self.entry_min.get()), float(self.entry_max.get())
            d_val = float(self.entry_dwell.get())
            c_val = self.combo_clicks.get()
            c_range = (2, 3) if "2~3" in c_val else (3, 5) if "3~5" in c_val else (5, 8) if "5~8" in c_val else (1, 1)
            t_val = float(self.slider_tremor.get())
        except ValueError: 
            self.lbl_status.configure(text="> 错误：参数格式有误，请检查", text_color=MORANDI["accent_red"])
            return
        
        self.save_config() 
        self.stop_event.clear()
        
        self.btn_start.configure(state="disabled", fg_color=MORANDI["bg_main"], border_width=1)
        self.btn_select.configure(state="disabled")
        self.btn_clear.configure(state="disabled")
        self.btn_stop.configure(state="normal", fg_color=MORANDI["accent_red"])
        self.lbl_status.configure(text=f"> 流水线已启动... (自然偏移度: {t_val:.1f} | 操作停留: {d_val}s)", text_color=MORANDI["accent_blue"])
        
        threading.Thread(target=self.assist_thread, args=(min_w, max_w, c_range, t_val, d_val), daemon=True).start()

    def stop_assisting(self, from_thread=False):
        self.stop_event.set()
        if from_thread:
            self.after(0, self._reset_ui)
        else:
            self._reset_ui()
            
    def _reset_ui(self):
        self.btn_start.configure(state="normal", fg_color=MORANDI["accent_blue"], border_width=0)
        self.btn_select.configure(state="normal")
        self.btn_clear.configure(state="normal")
        self.btn_stop.configure(state="disabled", fg_color=MORANDI["bg_main"])
        self.lbl_status.configure(text="> 任务已停止，系统进入待机状态", text_color=MORANDI["text_p"])

if __name__ == "__main__":
    app = EfficiencyTerminal()
    app.protocol("WM_DELETE_WINDOW", lambda: (app.save_config(), app.hardware_bridge.disconnect(), app.destroy()))
    app.mainloop()