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
except ImportError as e:
    messagebox.showerror("Error", f"Could not import dl24_lib. Error: {e}\nPlease ensure dl24_lib/__init__.py exists and pyserial is installed.")
    sys.exit(1)

MODES = ["SKYFALL JIG Mode", "FA Direct Mode"]
ALL_PORTS = ["TBTB", "TBTC", "TBTD"]
CSV_HEADER = ["Timestamp", "PCBA_SN", "JIG_ID", "Test_Mode", "Port_ID", "Step_Current_A", "Measured_Volt_V", "Measured_Curr_A", "Vdrop_mV", "OCP_Status", "Step_Result", "Final_Port_Result"]
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
    }
}

def load_config():
    if not os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG


class DL24AutoTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DL24 生產線自動化測試工具 - 進階版")
        self.root.geometry("1100x780")
        self.root.resizable(False, False)
        self.is_running = False
        self.instr = None
        self.config = load_config()
        self.setup_ui()

    def setup_ui(self):
        ttk.Style().theme_use('clam')

        left_panel = ttk.Frame(self.root, width=500)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        left_panel.pack_propagate(False)

        right_panel = ttk.Frame(self.root)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Notebook tabs
        self.notebook = ttk.Notebook(left_panel)
        self.notebook.pack(fill=tk.X, pady=(0, 5))

        skyfall_tab = ttk.Frame(self.notebook)
        fa_tab = ttk.Frame(self.notebook)
        self.notebook.add(skyfall_tab, text="SKYFALL JIG Mode")
        self.notebook.add(fa_tab, text="FA Direct Mode")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # FA Direct Mode tab: Test Profile
        fa_cfg = self.config["FA_DIRECT_MODE"]
        fa_profile = ttk.LabelFrame(fa_tab, text="Test Profile", padding=(10, 8))
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

        # Connection settings
        conn_frame = ttk.LabelFrame(left_panel, text="連線設定 (Connection)", padding=(10, 10))
        conn_frame.pack(fill=tk.X, pady=5)

        ttk.Label(conn_frame, text="COM Port:", font=("Arial", 11)).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.port_var = tk.StringVar(value="COM3")
        ttk.Entry(conn_frame, textvariable=self.port_var, width=15, font=("Arial", 11)).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(conn_frame, text="Baud Rate:", font=("Arial", 11)).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.baud_var = tk.StringVar(value="9600")
        ttk.Entry(conn_frame, textvariable=self.baud_var, width=15, font=("Arial", 11)).grid(row=0, column=3, padx=5, pady=5)

        # Traceability
        trace_frame = ttk.LabelFrame(left_panel, text="資料追蹤 (Traceability)", padding=(10, 10))
        trace_frame.pack(fill=tk.X, pady=5)

        ttk.Label(trace_frame, text="PCBA S/N:", font=("Arial", 11)).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.pcba_sn_var = tk.StringVar()
        self.pcba_sn_entry = ttk.Entry(trace_frame, textvariable=self.pcba_sn_var, width=25, font=("Arial", 12, "bold"))
        self.pcba_sn_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(trace_frame, text="JIG ID:", font=("Arial", 11)).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.jig_id_var = tk.StringVar()
        self.jig_id_entry = ttk.Entry(trace_frame, textvariable=self.jig_id_var, width=25, font=("Arial", 12))
        self.jig_id_entry.grid(row=1, column=1, padx=5, pady=5)

        self.autofocus_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(trace_frame, text="測試完成後自動聚焦 PCBA S/N 欄位", variable=self.autofocus_var).grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)

        # Port selection
        port_frame = ttk.LabelFrame(left_panel, text="測試連接埠 (Ports)", padding=(10, 10))
        port_frame.pack(fill=tk.X, pady=5)

        self.port_mode_var = tk.StringVar(value="ALL")
        ttk.Radiobutton(port_frame, text="自動測試所有埠 (TBTB -> TBTC -> TBTD)", variable=self.port_mode_var, value="ALL").grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)
        ttk.Radiobutton(port_frame, text="單一埠測試:", variable=self.port_mode_var, value="SINGLE").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        self.single_port_var = tk.StringVar(value="TBTB")
        self.single_port_cb = ttk.Combobox(port_frame, textvariable=self.single_port_var, values=ALL_PORTS, state="readonly", width=15, font=("Arial", 11))
        self.single_port_cb.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # Controls
        control_frame = ttk.Frame(left_panel)
        control_frame.pack(fill=tk.X, pady=15)

        self.start_btn = tk.Button(control_frame, text="開始測試\n(START)", font=("Arial", 18, "bold"), bg="#4CAF50", fg="white", height=2, command=self.start_test)
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.stop_btn = tk.Button(control_frame, text="強制停止\n(STOP)", font=("Arial", 18, "bold"), bg="#F44336", fg="white", height=2, command=self.stop_test, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        # Live Monitor
        monitor_frame = ttk.LabelFrame(right_panel, text="即時監控 (Live Monitor)", padding=(20, 20))
        monitor_frame.pack(fill=tk.X, pady=(0, 10))

        info_frame = ttk.Frame(monitor_frame)
        info_frame.pack(fill=tk.X, pady=5)

        self.lbl_active_port = tk.Label(info_frame, text="---", font=("Arial", 20, "bold"), fg="blue")
        self.lbl_active_port.pack(side=tk.LEFT, padx=10)

        self.lbl_active_step = tk.Label(info_frame, text="準備中", font=("Arial", 18))
        self.lbl_active_step.pack(side=tk.LEFT, padx=20)

        self.lbl_target_curr = tk.Label(info_frame, text="Target: 0.0 A", font=("Arial", 16, "bold"), fg="darkorange")
        self.lbl_target_curr.pack(side=tk.RIGHT, padx=10)

        reading_frame = ttk.Frame(monitor_frame)
        reading_frame.pack(fill=tk.X, pady=10)

        v_frame = ttk.Frame(reading_frame)
        v_frame.pack(side=tk.LEFT, expand=True)
        tk.Label(v_frame, text="Voltage (V)", font=("Arial", 14)).pack()
        self.lbl_volt = tk.Label(v_frame, text="0.00", font=("Consolas", 42, "bold"), fg="black")
        self.lbl_volt.pack()

        a_frame = ttk.Frame(reading_frame)
        a_frame.pack(side=tk.LEFT, expand=True)
        tk.Label(a_frame, text="Current (A)", font=("Arial", 14)).pack()
        self.lbl_curr = tk.Label(a_frame, text="0.00", font=("Consolas", 42, "bold"), fg="black")
        self.lbl_curr.pack()

        self.result_label = tk.Label(monitor_frame, text="WAITING", font=("Arial", 32, "bold"), fg="white", bg="gray")
        self.result_label.pack(fill=tk.X, pady=10)

        # Logs
        log_frame = ttk.LabelFrame(right_panel, text="測試日誌 (Logs)", padding=(5, 5))
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, font=("Consolas", 11), state=tk.DISABLED)
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
        else:
            if self.jig_id_var.get() == "DIRECT_NO_JIG":
                self.jig_id_var.set("")
            self.jig_id_entry.config(state=tk.NORMAL)

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def update_monitor(self, port=None, step_text=None, volt=None, curr=None, target_a=None):
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

    def start_test(self):
        pcba_sn = self.pcba_sn_var.get().strip()
        jig_id = self.jig_id_var.get().strip()
        if not pcba_sn:
            messagebox.showerror("錯誤", "請輸入 PCBA S/N")
            return
        tab_idx = self.notebook.index(self.notebook.select())
        mode = MODES[tab_idx]
        if mode != "FA Direct Mode" and not jig_id:
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
        self.update_monitor("---", "Initializing...", 0.0, 0.0, 0.0)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log("=== 開始新測試 ===")
        threading.Thread(target=self.run_full_sequence, args=(port, baud, mode, pcba_sn, jig_id), daemon=True).start()

    def stop_test(self):
        self.log("收到停止指令，正在中斷測試...")
        self.is_running = False

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
                    self.instr.setamp(0, rel=False)
                    self.instr.setOFF()
                    self.instr.close()
                except:
                    pass
            self.root.after(0, self.finish_test, final_result_overall)

    def measure_stable(self, retries=3):
        v, a = 0.0, 0.0
        time.sleep(1.0)
        for _ in range(3):
            self.instr.recvdata()
            time.sleep(0.1)
        for _ in range(retries):
            if not self.is_running:
                break
            v_tmp = self.instr.cmd_getvolt()
            if v_tmp is not None:
                v = v_tmp
            a_tmp = self.instr.cmd_getamp()
            if a_tmp is not None:
                a = a_tmp
            time.sleep(0.1)
        return v, a

    # --- FA Direct Mode ---
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

    # --- SKYFALL JIG Mode ---
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

            # Wait step_dur seconds
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

        # eFuse recovery verification (only if tripped)
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
        self.update_monitor(step_text="TEST COMPLETE")
        if final_result == "PASS":
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
