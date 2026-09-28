import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import csv
import json
from datetime import datetime
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from dl24_lib import Instr_Atorch, LowLevelSerPort
except ImportError:
    # Dummy fallback class for environments without physical hardware/dl24_lib installed
    class LowLevelSerPort:
        def __init__(self, port, baud):
            pass

    class Instr_Atorch:
        def __init__(self):
            self.v = 5.0
            self.a = 0.0
            self.temp = 28.5
            self.is_on = False

        def initport(self, port):
            pass

        def connect(self):
            pass

        def close(self):
            pass

        def recvdata(self):
            pass

        def cmd_resetcounters(self):
            pass

        def cmd_getvolt(self):
            return self.v if self.is_on else 5.05

        def cmd_getamp(self):
            return self.a if self.is_on else 0.0

        def cmd_gettemp(self):
            return self.temp

        def setamp(self, amp, rel=False):
            self.a = amp

        def setON(self):
            self.is_on = True

        def setOFF(self):
            self.is_on = False

MODES = ["SKYFALL JIG Mode", "FA Direct Mode", "Battery Cycling Mode"]
ALL_PORTS = ["TBTB", "TBTC", "TBTD"]
CSV_HEADER = [
    "Timestamp", "PCBA_SN", "JIG_ID", "Test_Mode", "Port_ID",
    "Step_Current_A", "Measured_Volt_V", "Measured_Curr_A", "Vdrop_mV",
    "OCP_Status", "Step_Result", "Final_Port_Result"
]
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_config.json")

DEFAULT_CONFIG = {
    "SKYFALL_JIG_MODE": {
        "STEPS": [1.5, 2.5, 3.0],
        "STEP_DURATION_SEC": 5,
        "V3_0A_PASS_MIN": 4.52,
        "V3_0A_BORDERLINE_MIN": 4.47,
        "OCP_START_CURRENT": 3.5,
        "OCP_MAX_CURRENT": 4.0,
        "OCP_STEP_CURRENT": 0.1,
        "OCP_TRIP_MAX_VOLT": 1.0,
        "RECOVERY_MIN_VOLT": 4.75
    },
    "FA_DIRECT_MODE": {
        "DEFAULT_CURRENT": 1.0,
        "DEFAULT_DURATION": 5,
        "DEFAULT_VMIN": 4.75,
        "DEFAULT_VMAX": 5.25
    },
    "BATTERY_CYCLE_MODE": {
        "DEFAULT_MODE": "CC",
        "DISCHARGE_CURRENT_A": 2.0,
        "CUTOFF_VOLTAGE_V": 3.0,
        "OVER_TEMP_LIMIT_C": 55.0,
        "REST_TIME_SEC": 900,
        "MAX_CYCLES": 5,
        "SAMPLING_INTERVAL_SEC": 1.0
    }
}


def load_config():
    if not os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
        except Exception:
            pass
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            battery_defaults = DEFAULT_CONFIG["BATTERY_CYCLE_MODE"]
            battery_cfg = cfg.setdefault("BATTERY_CYCLE_MODE", {})
            for key, value in battery_defaults.items():
                battery_cfg.setdefault(key, value)
            return cfg
    except Exception:
        return DEFAULT_CONFIG


class DL24AutoTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DL24 生產線自動化與電池充放電熱循環測試工具 v4.0")
        self.root.geometry("1120x820")
        self.root.resizable(False, False)
        self.is_running = False
        self.instr = None
        self.load_stop_lock = threading.Lock()
        self.config = load_config()
        self.setup_ui()

    def setup_ui(self):
        ttk.Style().theme_use('clam')

        left_panel = ttk.Frame(self.root, width=510)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        left_panel.pack_propagate(False)

        right_panel = ttk.Frame(self.root)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Notebook tabs
        self.notebook = ttk.Notebook(left_panel)
        self.notebook.pack(fill=tk.X, pady=(0, 5))

        skyfall_tab = ttk.Frame(self.notebook)
        fa_tab = ttk.Frame(self.notebook)
        bat_tab = ttk.Frame(self.notebook)

        self.notebook.add(skyfall_tab, text="SKYFALL JIG Mode")
        self.notebook.add(fa_tab, text="FA Direct Mode")
        self.notebook.add(bat_tab, text="Battery Cycling Mode")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # ---------------- SKYFALL Tab Info ----------------
        skyfall_info = ttk.LabelFrame(skyfall_tab, text="SKYFALL JIG 自動化量產參數", padding=(10, 8))
        skyfall_info.pack(fill=tk.X, padx=5, pady=8)
        ttk.Label(skyfall_info, text="抽載步階: 1.5A -> 2.5A -> 3.0A -> 動態 OCP", font=("Arial", 10)).pack(anchor=tk.W, pady=2)
        ttk.Label(skyfall_info, text="3.0A PASS 門檻: >= 4.52V | 復歸判定: >= 4.75V", font=("Arial", 10)).pack(anchor=tk.W, pady=2)

        # ---------------- FA Direct Mode Tab Profile ----------------
        fa_cfg = self.config["FA_DIRECT_MODE"]
        fa_profile = ttk.LabelFrame(fa_tab, text="FA 單點測試參數 (Test Profile)", padding=(10, 8))
        fa_profile.pack(fill=tk.X, padx=5, pady=8)

        ttk.Label(fa_profile, text="Current (A):", font=("Arial", 11)).grid(row=0, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_current_var = tk.StringVar(value=str(fa_cfg["DEFAULT_CURRENT"]))
        ttk.Entry(fa_profile, textvariable=self.fa_current_var, width=10, font=("Arial", 11)).grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(fa_profile, text="Duration (Sec):", font=("Arial", 11)).grid(row=1, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_duration_var = tk.StringVar(value=str(fa_cfg["DEFAULT_DURATION"]))
        ttk.Entry(fa_profile, textvariable=self.fa_duration_var, width=10, font=("Arial", 11)).grid(row=1, column=1, padx=5, pady=4)

        ttk.Label(fa_profile, text="Vmin (V):", font=("Arial", 11)).grid(row=2, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_vmin_var = tk.StringVar(value=str(fa_cfg["DEFAULT_VMIN"]))
        ttk.Entry(fa_profile, textvariable=self.fa_vmin_var, width=10, font=("Arial", 11)).grid(row=2, column=1, padx=5, pady=4)

        ttk.Label(fa_profile, text="Vmax (V):", font=("Arial", 11)).grid(row=3, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_vmax_var = tk.StringVar(value=str(fa_cfg["DEFAULT_VMAX"]))
        ttk.Entry(fa_profile, textvariable=self.fa_vmax_var, width=10, font=("Arial", 11)).grid(row=3, column=1, padx=5, pady=4)

        # ---------------- Battery Cycling Mode Tab Profile ----------------
        bat_cfg = self.config["BATTERY_CYCLE_MODE"]
        bat_profile = ttk.LabelFrame(bat_tab, text="電池放電容量與熱循環參數", padding=(10, 8))
        bat_profile.pack(fill=tk.X, padx=5, pady=8)

        ttk.Label(bat_profile, text="Discharge Current (A):", font=("Arial", 10)).grid(row=0, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_current_var = tk.StringVar(value=str(bat_cfg["DISCHARGE_CURRENT_A"]))
        ttk.Entry(bat_profile, textvariable=self.bat_current_var, width=10, font=("Arial", 10)).grid(row=0, column=1, padx=4, pady=3)

        ttk.Label(bat_profile, text="Cutoff Voltage (V):", font=("Arial", 10)).grid(row=1, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_cutoff_v_var = tk.StringVar(value=str(bat_cfg["CUTOFF_VOLTAGE_V"]))
        ttk.Entry(bat_profile, textvariable=self.bat_cutoff_v_var, width=10, font=("Arial", 10)).grid(row=1, column=1, padx=4, pady=3)

        ttk.Label(bat_profile, text="Over-Temp Limit (°C):", font=("Arial", 10)).grid(row=2, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_overtemp_var = tk.StringVar(value=str(bat_cfg["OVER_TEMP_LIMIT_C"]))
        ttk.Entry(bat_profile, textvariable=self.bat_overtemp_var, width=10, font=("Arial", 10)).grid(row=2, column=1, padx=4, pady=3)

        ttk.Label(bat_profile, text="Rest Duration (Sec):", font=("Arial", 10)).grid(row=3, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_rest_time_var = tk.StringVar(value=str(bat_cfg["REST_TIME_SEC"]))
        ttk.Entry(bat_profile, textvariable=self.bat_rest_time_var, width=10, font=("Arial", 10)).grid(row=3, column=1, padx=4, pady=3)

        ttk.Label(bat_profile, text="Total Cycles:", font=("Arial", 10)).grid(row=4, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_max_cycles_var = tk.StringVar(value=str(bat_cfg["MAX_CYCLES"]))
        ttk.Entry(bat_profile, textvariable=self.bat_max_cycles_var, width=10, font=("Arial", 10)).grid(row=4, column=1, padx=4, pady=3)

        # ---------------- Connection Settings ----------------
        conn_frame = ttk.LabelFrame(left_panel, text="連線設定 (Connection)", padding=(10, 8))
        conn_frame.pack(fill=tk.X, pady=4)

        ttk.Label(conn_frame, text="COM Port:", font=("Arial", 10)).grid(row=0, column=0, padx=5, pady=4, sticky=tk.W)
        self.port_var = tk.StringVar(value="COM3")
        ttk.Entry(conn_frame, textvariable=self.port_var, width=12, font=("Arial", 10)).grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(conn_frame, text="Baud Rate:", font=("Arial", 10)).grid(row=0, column=2, padx=5, pady=4, sticky=tk.W)
        self.baud_var = tk.StringVar(value="9600")
        ttk.Entry(conn_frame, textvariable=self.baud_var, width=12, font=("Arial", 10)).grid(row=0, column=3, padx=5, pady=4)

        # ---------------- Traceability ----------------
        trace_frame = ttk.LabelFrame(left_panel, text="資料追蹤 (Traceability)", padding=(10, 8))
        trace_frame.pack(fill=tk.X, pady=4)

        ttk.Label(trace_frame, text="PCBA S/N:", font=("Arial", 10)).grid(row=0, column=0, padx=5, pady=4, sticky=tk.W)
        self.pcba_sn_var = tk.StringVar()
        self.pcba_sn_entry = ttk.Entry(trace_frame, textvariable=self.pcba_sn_var, width=25, font=("Arial", 11, "bold"))
        self.pcba_sn_entry.grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(trace_frame, text="JIG ID:", font=("Arial", 10)).grid(row=1, column=0, padx=5, pady=4, sticky=tk.W)
        self.jig_id_var = tk.StringVar()
        self.jig_id_entry = ttk.Entry(trace_frame, textvariable=self.jig_id_var, width=25, font=("Arial", 11))
        self.jig_id_entry.grid(row=1, column=1, padx=5, pady=4)

        self.autofocus_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(trace_frame, text="測試完成後自動聚焦 PCBA S/N 欄位", variable=self.autofocus_var).grid(row=2, column=0, columnspan=2, padx=5, pady=3, sticky=tk.W)

        # ---------------- Port Selection ----------------
        port_frame = ttk.LabelFrame(left_panel, text="測試連接埠 (Ports)", padding=(10, 8))
        port_frame.pack(fill=tk.X, pady=4)

        self.port_mode_var = tk.StringVar(value="ALL")
        ttk.Radiobutton(port_frame, text="自動測試所有埠 (TBTB -> TBTC -> TBTD)", variable=self.port_mode_var, value="ALL").grid(row=0, column=0, columnspan=2, padx=5, pady=3, sticky=tk.W)
        ttk.Radiobutton(port_frame, text="單一埠測試:", variable=self.port_mode_var, value="SINGLE").grid(row=1, column=0, padx=5, pady=3, sticky=tk.W)

        self.single_port_var = tk.StringVar(value="TBTB")
        self.single_port_cb = ttk.Combobox(port_frame, textvariable=self.single_port_var, values=ALL_PORTS, state="readonly", width=12, font=("Arial", 10))
        self.single_port_cb.grid(row=1, column=1, padx=5, pady=3, sticky=tk.W)

        # ---------------- Controls ----------------
        control_frame = ttk.Frame(left_panel)
        control_frame.pack(fill=tk.X, pady=10)

        self.start_btn = tk.Button(control_frame, text="開始測試\n(START)", font=("Arial", 16, "bold"), bg="#4CAF50", fg="white", height=2, command=self.start_test)
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        self.stop_btn = tk.Button(control_frame, text="強制停止\n(STOP)", font=("Arial", 16, "bold"), bg="#F44336", fg="white", height=2, command=self.stop_test, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        # ---------------- Live Monitor (Right Panel) ----------------
        monitor_frame = ttk.LabelFrame(right_panel, text="即時監控 (Live Monitor)", padding=(15, 12))
        monitor_frame.pack(fill=tk.X, pady=(0, 8))

        info_frame = ttk.Frame(monitor_frame)
        info_frame.pack(fill=tk.X, pady=3)

        self.lbl_active_port = tk.Label(info_frame, text="---", font=("Arial", 18, "bold"), fg="blue")
        self.lbl_active_port.pack(side=tk.LEFT, padx=5)

        self.lbl_active_step = tk.Label(info_frame, text="準備中", font=("Arial", 16))
        self.lbl_active_step.pack(side=tk.LEFT, padx=15)

        self.lbl_target_curr = tk.Label(info_frame, text="Target: 0.0 A", font=("Arial", 14, "bold"), fg="darkorange")
        self.lbl_target_curr.pack(side=tk.RIGHT, padx=5)

        # Primary Volt / Curr Readings
        reading_frame = ttk.Frame(monitor_frame)
        reading_frame.pack(fill=tk.X, pady=6)

        v_frame = ttk.Frame(reading_frame)
        v_frame.pack(side=tk.LEFT, expand=True)
        tk.Label(v_frame, text="Voltage (V)", font=("Arial", 12)).pack()
        self.lbl_volt = tk.Label(v_frame, text="0.00", font=("Consolas", 36, "bold"), fg="black")
        self.lbl_volt.pack()

        a_frame = ttk.Frame(reading_frame)
        a_frame.pack(side=tk.LEFT, expand=True)
        tk.Label(a_frame, text="Current (A)", font=("Arial", 12)).pack()
        self.lbl_curr = tk.Label(a_frame, text="0.00", font=("Consolas", 36, "bold"), fg="black")
        self.lbl_curr.pack()

        # Dedicated Battery Cycling Indicators Panel
        bat_meter_frame = ttk.LabelFrame(monitor_frame, text="電池放電與熱數據 (Battery Cycling Metrics)", padding=(8, 6))
        bat_meter_frame.pack(fill=tk.X, pady=6)

        m1 = ttk.Frame(bat_meter_frame)
        m1.pack(fill=tk.X, pady=2)

        tk.Label(m1, text="Capacity (Ah):", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=4)
        self.lbl_ah = tk.Label(m1, text="0.0000", font=("Consolas", 12, "bold"), fg="#1976D2")
        self.lbl_ah.grid(row=0, column=1, sticky=tk.W, padx=4)

        tk.Label(m1, text="Energy (Wh):", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky=tk.W, padx=12)
        self.lbl_wh = tk.Label(m1, text="0.0000", font=("Consolas", 12, "bold"), fg="#388E3C")
        self.lbl_wh.grid(row=0, column=3, sticky=tk.W, padx=4)

        m2 = ttk.Frame(bat_meter_frame)
        m2.pack(fill=tk.X, pady=2)

        tk.Label(m2, text="Temp (°C):", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=4)
        self.lbl_temp = tk.Label(m2, text="--.-", font=("Consolas", 12, "bold"), fg="#D32F2F")
        self.lbl_temp.grid(row=0, column=1, sticky=tk.W, padx=4)

        tk.Label(m2, text="Cycle Progress:", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky=tk.W, padx=12)
        self.lbl_cycle = tk.Label(m2, text="Cycle 0 / 0", font=("Consolas", 12, "bold"), fg="#7B1FA2")
        self.lbl_cycle.grid(row=0, column=3, sticky=tk.W, padx=4)

        # Big Result Banner
        self.result_label = tk.Label(monitor_frame, text="WAITING", font=("Arial", 28, "bold"), fg="white", bg="gray")
        self.result_label.pack(fill=tk.X, pady=8)

        # Logs Frame
        log_frame = ttk.LabelFrame(right_panel, text="測試日誌 (Logs)", padding=(5, 5))
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, font=("Consolas", 10), state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def on_tab_changed(self, event):
        tab_idx = self.notebook.index(self.notebook.select())
        mode = MODES[tab_idx]
        if mode == "FA Direct Mode":
            self.jig_id_var.set("DIRECT_NO_JIG")
            self.jig_id_entry.config(state=tk.DISABLED)
        elif mode == "Battery Cycling Mode":
            if not self.jig_id_var.get() or self.jig_id_var.get() == "DIRECT_NO_JIG":
                self.jig_id_var.set("BATTERY_TEST")
            self.jig_id_entry.config(state=tk.NORMAL)
        else:
            if self.jig_id_var.get() in ["DIRECT_NO_JIG", "BATTERY_TEST"]:
                self.jig_id_var.set("")
            self.jig_id_entry.config(state=tk.NORMAL)

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def update_monitor(self, port=None, step_text=None, volt=None, curr=None, target_a=None, ah=None, wh=None, temp=None, cycle_str=None):
        if port is not None:
            self.lbl_active_port.config(text=f"Port: {port}")
        if step_text is not None:
            self.lbl_active_step.config(text=step_text)
        if volt is not None:
            self.lbl_volt.config(text=f"{volt:.2f}")
        if curr is not None:
            self.lbl_curr.config(text=f"{curr:.2f}")
        if target_a is not None:
            self.lbl_target_curr.config(text=f"Target: {target_a:.1f} A")
        if ah is not None:
            self.lbl_ah.config(text=f"{ah:.4f}")
        if wh is not None:
            self.lbl_wh.config(text=f"{wh:.4f}")
        if temp is not None:
            self.lbl_temp.config(text=f"{temp:.1f}")
        if cycle_str is not None:
            self.lbl_cycle.config(text=cycle_str)
        self.root.update_idletasks()

    def set_ui_state(self, running):
        state = tk.DISABLED if running else tk.NORMAL
        self.start_btn.config(state=state)
        self.stop_btn.config(state=tk.NORMAL if running else tk.DISABLED)
        self.pcba_sn_entry.config(state=state)
        self.single_port_cb.config(state=state)
        tab_idx = self.notebook.index(self.notebook.select())
        if not running and MODES[tab_idx] == "FA Direct Mode":
            self.jig_id_entry.config(state=tk.DISABLED)
        else:
            self.jig_id_entry.config(state=state)

    def set_big_status(self, text, bg_color):
        self.result_label.config(text=text, bg=bg_color, fg="white" if bg_color not in ["yellow", "lime"] else "black")
        self.root.update_idletasks()

    def get_temp_safe(self):
        if self.instr and hasattr(self.instr, "cmd_gettemp"):
            try:
                t = self.instr.cmd_gettemp()
                if t is not None:
                    return float(t)
            except Exception:
                pass
        return 28.5  # Default ambient temperature fallback

    def start_test(self):
        pcba_sn = self.pcba_sn_var.get().strip()
        jig_id = self.jig_id_var.get().strip()
        if not pcba_sn:
            messagebox.showerror("錯誤", "請輸入 PCBA S/N")
            return
        tab_idx = self.notebook.index(self.notebook.select())
        mode = MODES[tab_idx]
        if mode == "SKYFALL JIG Mode" and not jig_id:
            messagebox.showerror("錯誤", "請輸入 JIG ID")
            return
        try:
            port = self.port_var.get()
            baud = int(self.baud_var.get())
        except ValueError:
            messagebox.showerror("錯誤", "Baud Rate 格式錯誤")
            return
        self.is_running = True
        self.set_ui_state(True)
        self.set_big_status("TESTING", "blue")
        self.update_monitor("---", "Initializing...", 0.0, 0.0, 0.0, ah=0.0, wh=0.0, temp=25.0, cycle_str="Cycle 0/0")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log(f"=== 開始新測試: {mode} ===")
        threading.Thread(target=self.run_full_sequence, args=(port, baud, mode, pcba_sn, jig_id), daemon=True).start()

    def stop_test(self):
        self.log("收到停止指令，正在中斷測試並關閉負載...")
        self.is_running = False
        self.stop_load()

    def stop_load(self):
        with self.load_stop_lock:
            if not self.instr:
                return
            try:
                self.instr.setamp(0, rel=False)
            except Exception:
                pass
            try:
                self.instr.setOFF()
            except Exception:
                pass

    def run_full_sequence(self, com_port, baud, mode, pcba_sn, jig_id):
        final_result_overall = "PASS"
        self.instr = None
        try:
            self.log(f"嘗試連線至 {com_port} ({baud} bps)...")
            self.instr = Instr_Atorch()
            self.instr.initport(LowLevelSerPort(com_port, baud))
            self.instr.connect()
            self.log("串列埠已開啟，等待設備回應...")
            time.sleep(1.0)
            for _ in range(5):
                self.instr.recvdata()
                time.sleep(0.1)
            self.log("連線成功，重置計數器...")
            self.instr.cmd_resetcounters()
            time.sleep(0.5)
            test_v = self.instr.cmd_getvolt()
            if test_v is None:
                self.log("警告: 無法讀取電壓，請確認 DL24 已開機並連接正確 COM Port")
            else:
                self.log(f"通訊確認成功，目前電壓: {test_v} V")

            if mode == "FA Direct Mode":
                final_result_overall = self.run_fa_direct(pcba_sn, jig_id)
            elif mode == "Battery Cycling Mode":
                final_result_overall = self.run_battery_cycling(pcba_sn, jig_id)
            else:
                ports_to_test = ALL_PORTS if self.port_mode_var.get() == "ALL" else [self.single_port_var.get()]
                for i, p in enumerate(ports_to_test):
                    if not self.is_running:
                        break
                    if i > 0 and self.is_running:
                        self.set_big_status("WAITING", "orange")
                        self.update_monitor(p, "Waiting for cable change", 0.0, 0.0, 0.0)
                        response = messagebox.askokcancel("換線提示", f"Please move TBT5 0.8m cable to Port {p} and press [OK] to Continue...", parent=self.root)
                        if not response:
                            self.log("使用者取消後續測試。")
                            self.is_running = False
                            break
                        self.set_big_status("TESTING", "blue")
                    self.log(f"\n--- 準備測試連接埠: {p} ---")
                    port_result = self.run_skyfall_port(pcba_sn, jig_id, p)
                    if port_result == "FAIL":
                        final_result_overall = "FAIL"
                    elif port_result == "BORDERLINE" and final_result_overall == "PASS":
                        final_result_overall = "BORDERLINE"
        except Exception as e:
            self.log(f"發生錯誤: {str(e)}")
            final_result_overall = "FAIL"
        finally:
            if self.instr:
                try:
                    self.stop_load()
                    self.instr.close()
                except Exception:
                    pass
            self.root.after(0, self.finish_test, final_result_overall)

    def measure_stable(self, retries=3):
        v, a = 0.0, 0.0
        time.sleep(0.5)
        if self.instr:
            for _ in range(2):
                self.instr.recvdata()
                time.sleep(0.05)
            for _ in range(retries):
                if not self.is_running:
                    break
                v_tmp = self.instr.cmd_getvolt()
                if v_tmp is not None:
                    v = v_tmp
                a_tmp = self.instr.cmd_getamp()
                if a_tmp is not None:
                    a = a_tmp
                time.sleep(0.05)
        return v, a

    # ---------------- FA Direct Mode ----------------
    def run_fa_direct(self, pcba_sn, jig_id):
        try:
            current = float(self.fa_current_var.get())
            duration = int(self.fa_duration_var.get())
            vmin = float(self.fa_vmin_var.get())
            vmax = float(self.fa_vmax_var.get())
        except ValueError:
            self.log("FA Direct Mode 參數格式錯誤")
            return "FAIL"

        self.update_monitor(port="DIRECT", step_text=f"Load {current}A", target_a=current)
        self.log(f"[FA] 設定電流 {current} A，持續 {duration} 秒")
        self.instr.setamp(current, rel=False)
        time.sleep(0.5)
        self.instr.setON()

        for i in range(duration):
            if not self.is_running:
                self.log("[FA] 使用者中斷測試")
                break
            self.log(f"[FA] 抽載中... 剩餘 {duration - i} 秒")
            time.sleep(1)

        v_meas, a_meas = self.measure_stable()
        self.update_monitor(volt=v_meas, curr=a_meas)
        self.instr.setamp(0, rel=False)
        self.instr.setOFF()

        if vmin <= v_meas <= vmax:
            step_result = "PASS"
        else:
            step_result = "FAIL"

        self.log(f"[FA] 測量: {v_meas} V, {a_meas} A -> {step_result}")
        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "FA Direct Mode", "DIRECT", current,
            v_meas, a_meas, 0.0, "N/A", step_result, step_result
        ])
        return step_result

    # ---------------- SKYFALL JIG Mode ----------------
    def run_skyfall_port(self, pcba_sn, jig_id, port_id):
        cfg = self.config["SKYFALL_JIG_MODE"]
        steps = cfg["STEPS"]
        step_dur = cfg["STEP_DURATION_SEC"]
        pass_min = cfg["V3_0A_PASS_MIN"]
        border_min = cfg["V3_0A_BORDERLINE_MIN"]
        ocp_start = cfg["OCP_START_CURRENT"]
        ocp_max = cfg["OCP_MAX_CURRENT"]
        ocp_step = cfg["OCP_STEP_CURRENT"]
        ocp_trip_v = cfg["OCP_TRIP_MAX_VOLT"]
        recovery_min = cfg["RECOVERY_MIN_VOLT"]

        port_final_result = "PASS"

        # Measure V_idle
        self.update_monitor(port=port_id, step_text="Measuring V_idle...", target_a=0.0)
        self.instr.setamp(0, rel=False)
        self.instr.setOFF()
        v_idle, _ = self.measure_stable()
        self.log(f"[{port_id}] 空載電壓 V_idle: {v_idle} V")
        self.update_monitor(volt=v_idle, curr=0.0)

        self.instr.setON()
        time.sleep(0.5)

        # Fixed current steps
        for step_a in steps:
            if not self.is_running:
                break
            self.log(f"[{port_id}] 執行電流步階: {step_a} A")
            self.update_monitor(step_text=f"Step {step_a}A", target_a=step_a)
            self.instr.setamp(step_a, rel=False)

            for _ in range(step_dur):
                if not self.is_running:
                    break
                time.sleep(1)

            v_meas, a_meas = self.measure_stable()
            self.update_monitor(volt=v_meas, curr=a_meas)
            vdrop_mv = (v_idle - v_meas) * 1000.0 if v_idle > 0 else 0.0
            step_result = "PASS"

            if step_a == 3.0:
                if v_meas >= pass_min:
                    step_result = "PASS"
                elif v_meas >= border_min:
                    step_result = "BORDERLINE"
                else:
                    step_result = "FAIL"
                self.log(f"   -> 3.0A 判定: {v_meas} V -> {step_result}")

            if step_result == "FAIL":
                port_final_result = "FAIL"
            elif step_result == "BORDERLINE" and port_final_result == "PASS":
                port_final_result = "BORDERLINE"

            self.log(f"   -> 測量: {v_meas} V, {a_meas} A, Vdrop: {vdrop_mv:.1f} mV")
            self.save_csv_row([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                pcba_sn, jig_id, "SKYFALL JIG Mode", port_id, step_a,
                v_meas, a_meas, round(vdrop_mv, 1), "N/A", step_result, "PENDING"
            ])

        if not self.is_running:
            return port_final_result

        # Dynamic OCP ramp
        self.log(f"[{port_id}] 開始 OCP 動態爬升測試 ({ocp_start}A -> {ocp_max}A)")
        ocp_result = "FAIL (NO_TRIP)"
        ocp_tripped_at = None
        ocp_current = ocp_start

        while ocp_current <= ocp_max + 0.001 and self.is_running:
            ocp_current = round(ocp_current, 2)
            self.log(f"[{port_id}] OCP 測試電流: {ocp_current} A")
            self.update_monitor(step_text=f"OCP {ocp_current}A", target_a=ocp_current)
            self.instr.setamp(ocp_current, rel=False)
            time.sleep(1.5)
            for _ in range(3):
                self.instr.recvdata()
                time.sleep(0.1)
            v_ocp = self.instr.cmd_getvolt()
            if v_ocp is None:
                v_ocp = 0.0
            self.update_monitor(volt=v_ocp)
            self.log(f"   -> OCP 電壓: {v_ocp} V")

            if v_ocp <= ocp_trip_v:
                ocp_result = f"TRIPPED @ {ocp_current}A"
                ocp_tripped_at = ocp_current
                self.log(f"[{port_id}] eFuse 觸發成功！@ {ocp_current} A, V={v_ocp} V")
                break
            ocp_current += ocp_step

        vdrop_ocp = (v_idle - (v_ocp if v_ocp else 0)) * 1000.0 if v_idle > 0 else 0.0
        ocp_step_result = "PASS" if ocp_tripped_at is not None else "FAIL"
        if ocp_step_result == "FAIL":
            port_final_result = "FAIL"

        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "SKYFALL JIG Mode", port_id,
            ocp_current if ocp_tripped_at else ocp_max,
            v_ocp if v_ocp else 0.0, 0.0, round(vdrop_ocp, 1),
            ocp_result, ocp_step_result, "PENDING"
        ])

        # eFuse recovery verification
        if ocp_tripped_at is not None and self.is_running:
            self.instr.setamp(0, rel=False)
            self.instr.setOFF()
            self.update_monitor(step_text="等待 eFuse 復歸...", target_a=0.0)
            messagebox.showinfo(
                "eFuse 復歸確認",
                f"eFuse 已成功觸發保護！\n請重新插拔 Type-C 端子以復歸 eFuse，完成後按下【確定】",
                parent=self.root
            )
            self.log(f"[{port_id}] 使用者已重新插拔，等待 1 秒後讀取復歸電壓...")
            time.sleep(1.0)
            for _ in range(3):
                self.instr.recvdata()
                time.sleep(0.1)
            v_recovery = self.instr.cmd_getvolt()
            if v_recovery is None:
                v_recovery = 0.0
            self.update_monitor(volt=v_recovery, curr=0.0)
            self.log(f"[{port_id}] 復歸電壓: {v_recovery} V")

            if v_recovery >= recovery_min:
                recovery_result = "PASS"
                self.log(f"[{port_id}] eFuse 復歸判定: PASS ({v_recovery} V >= {recovery_min} V)")
            else:
                recovery_result = "FAIL (NO_RECOVERY)"
                port_final_result = "FAIL"
                self.log(f"[{port_id}] eFuse 復歸判定: FAIL ({v_recovery} V < {recovery_min} V)")

            self.save_csv_row([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                pcba_sn, jig_id, "SKYFALL JIG Mode", port_id, 0.0,
                v_recovery, 0.0, 0.0, "RECOVERY", recovery_result, "PENDING"
            ])

        # Final reset
        self.update_monitor(step_text="Finishing & Reset", target_a=0.0)
        self.instr.setamp(0, rel=False)
        self.instr.setOFF()
        time.sleep(0.5)

        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "SKYFALL JIG Mode", port_id, 0.0,
            0.0, 0.0, 0.0, "N/A", "DONE", port_final_result
        ])
        self.log(f"--- 連接埠 {port_id} 測試結束，結果: {port_final_result} ---")
        return port_final_result

    # ---------------- Battery Cycling Mode ----------------
    def run_battery_cycling(self, pcba_sn, jig_id):
        try:
            discharge_curr = float(self.bat_current_var.get())
            cutoff_v = float(self.bat_cutoff_v_var.get())
            overtemp_limit = float(self.bat_overtemp_var.get())
            rest_sec = int(self.bat_rest_time_var.get())
            max_cycles = int(self.bat_max_cycles_var.get())
            sampling_interval = float(self.config["BATTERY_CYCLE_MODE"].get("SAMPLING_INTERVAL_SEC", 1.0))
            if sampling_interval <= 0:
                raise ValueError
        except ValueError:
            self.log("Battery Cycling Mode 參數格式錯誤")
            return "FAIL"

        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        ts_log_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"battery_cycle_{pcba_sn}_{timestamp_str}.csv"
        )

        try:
            with open(ts_log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "Cycle_Index", "Phase", "Voltage_V",
                    "Current_A", "Power_W", "Temp_C", "Capacity_Ah", "Energy_Wh", "Status"
                ])
        except Exception as e:
            self.log(f"無法建立電池放電時間序列日誌: {e}")

        total_ah = 0.0
        total_wh = 0.0
        overall_status = "PASS"

        self.log(f"=== 開始電池放電容量與熱循環測試 ===")
        self.log(f"目標: {max_cycles} 輪次 | 電流: {discharge_curr}A | 截止: {cutoff_v}V | 過溫: {overtemp_limit}°C | 靜置: {rest_sec}s")

        for cycle_idx in range(1, max_cycles + 1):
            if not self.is_running:
                break

            cycle_str = f"Cycle {cycle_idx} / {max_cycles}"
            self.log(f"\n>>> 開始 {cycle_str} - 放電階段 (DISCHARGE) <<<")
            self.update_monitor(
                port="BATTERY",
                step_text=f"{cycle_str} - DISCHARGING",
                target_a=discharge_curr,
                ah=total_ah,
                wh=total_wh,
                cycle_str=cycle_str
            )

            # Enable DL24 load
            self.instr.setamp(discharge_curr, rel=False)
            time.sleep(0.5)
            self.instr.setON()

            last_time = time.monotonic()
            last_v, last_a = self.measure_stable()
            last_temp = self.get_temp_safe()
            last_p = last_v * last_a

            discharge_phase_active = True

            while discharge_phase_active and self.is_running:
                sample_deadline = last_time + sampling_interval
                time.sleep(max(0.0, sample_deadline - time.monotonic()))
                curr_time = time.monotonic()
                dt = curr_time - last_time

                v_k, a_k = self.measure_stable()
                temp_k = self.get_temp_safe()
                p_k = v_k * a_k

                # Trapezoidal integration for Ah & Wh
                delta_ah = ((a_k + last_a) / 2.0) * (dt / 3600.0)
                delta_wh = ((p_k + last_p) / 2.0) * (dt / 3600.0)
                total_ah += delta_ah
                total_wh += delta_wh

                self.update_monitor(
                    volt=v_k,
                    curr=a_k,
                    ah=total_ah,
                    wh=total_wh,
                    temp=temp_k,
                    cycle_str=cycle_str
                )

                now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Safety Check: Over-Temp Alarm
                if temp_k >= overtemp_limit:
                    self.log(f"⚠️ [過溫保護觸發] 溫度 {temp_k:.1f}°C 超過上限 {overtemp_limit}°C！緊急切斷負載！")
                    self.stop_load()
                    self.update_monitor(step_text="OVER_TEMP_ALARM")
                    overall_status = "FAIL (OVER_TEMP)"
                    self.append_ts_log(ts_log_file, [
                        now_ts, cycle_idx, "DISCHARGE", round(v_k, 3), round(a_k, 3),
                        round(p_k, 3), round(temp_k, 1), round(total_ah, 4), round(total_wh, 4), "OVER_TEMP_ALARM"
                    ])
                    discharge_phase_active = False
                    self.is_running = False
                    break

                # Termination Check: Cutoff Voltage
                if v_k <= cutoff_v:
                    self.log(f"✅ [截止電壓到達] 電壓 {v_k:.2f}V <= {cutoff_v}V，完成本輪放電。")
                    self.stop_load()
                    self.append_ts_log(ts_log_file, [
                        now_ts, cycle_idx, "DISCHARGE", round(v_k, 3), round(a_k, 3),
                        round(p_k, 3), round(temp_k, 1), round(total_ah, 4), round(total_wh, 4), "CUTOFF_REACHED"
                    ])
                    discharge_phase_active = False
                    break

                # Normal running log entry
                self.append_ts_log(ts_log_file, [
                    now_ts, cycle_idx, "DISCHARGE", round(v_k, 3), round(a_k, 3),
                    round(p_k, 3), round(temp_k, 1), round(total_ah, 4), round(total_wh, 4), "RUNNING"
                ])

                last_time, last_v, last_a, last_p, last_temp = curr_time, v_k, a_k, p_k, temp_k

            if not self.is_running or overall_status.startswith("FAIL"):
                break

            # Phase B: REST PHASE
            self.instr.setamp(0, rel=False)
            self.instr.setOFF()
            self.log(f">>> 進入 {cycle_str} - 靜置冷卻階段 (REST)，時長: {rest_sec} 秒 <<<")

            for sec in range(rest_sec, 0, -1):
                if not self.is_running:
                    break
                v_rest, a_rest = self.measure_stable()
                temp_rest = self.get_temp_safe()
                self.update_monitor(
                    step_text=f"{cycle_str} - RESTING ({sec}s)",
                    target_a=0.0,
                    volt=v_rest,
                    curr=a_rest,
                    temp=temp_rest
                )
                self.append_ts_log(ts_log_file, [
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    cycle_idx, "REST", round(v_rest, 3), round(a_rest, 3),
                    0.0, round(temp_rest, 1), round(total_ah, 4), round(total_wh, 4), "RESTING"
                ])
                time.sleep(1.0)

        # Final Cleanup & Logging
        self.stop_load()

        self.log(f"\n=== 電池放電熱循環測試結束 ===")
        self.log(f"總累計放電容量: {total_ah:.4f} Ah | 總能量: {total_wh:.4f} Wh | 結果: {overall_status}")

        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "Battery Cycling Mode", "BATTERY", discharge_curr,
            0.0, 0.0, 0.0, f"Ah={total_ah:.4f},Wh={total_wh:.4f}", overall_status, overall_status
        ])

        return overall_status

    def append_ts_log(self, filepath, row):
        try:
            with open(filepath, 'a', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow(row)
        except Exception as e:
            self.log(f"時間序列 Log 寫入失敗: {e}")

    def save_csv_row(self, row):
        filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "production_test_datalog.csv")
        file_exists = os.path.isfile(filename)
        try:
            with open(filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(CSV_HEADER)
                writer.writerow(row)
        except Exception as e:
            self.log(f"CSV寫入失敗: {e}")

    def finish_test(self, final_result):
        self.is_running = False
        self.set_ui_state(False)
        self.update_monitor(step_text="COMPLETE")
        if final_result in ["PASS", "COMPLETE"]:
            self.set_big_status("PASS", "lime")
        elif final_result == "BORDERLINE":
            self.set_big_status("BORDERLINE", "yellow")
        else:
            self.set_big_status("FAIL", "red")
        self.log("\n測試序列完成。")
        if self.autofocus_var.get():
            self.pcba_sn_entry.delete(0, tk.END)
            self.pcba_sn_entry.focus_set()


if __name__ == "__main__":
    root = tk.Tk()
    app = DL24AutoTestApp(root)
    root.mainloop()
