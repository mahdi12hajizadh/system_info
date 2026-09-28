#!/usr/bin/env python3
"""
System Info GUI
A desktop app (Python + ttkbootstrap) that shows detailed system specs:
OS, CPU (with model name), RAM, Disk, Network, GPU model, and battery health.

Requirements (install once):
    pip install psutil ttkbootstrap

Run:
    python system_info_gui.py
"""

import platform
import socket
import uuid
import datetime
import subprocess
import re
import os

import psutil
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import scrolledtext


def get_size(bytes_val, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes_val < factor:
            return f"{bytes_val:.2f} {unit}{suffix}"
        bytes_val /= factor
    return f"{bytes_val:.2f} P{suffix}"


def run_cmd(cmd):
    """Run a shell command safely and return its stdout, or None on failure."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_cpu_model():
    """Best-effort CPU model name across Windows / Linux / macOS."""
    system = platform.system()

    if system == "Windows":
        out = run_cmd("wmic cpu get name")
        if out:
            lines = [l.strip() for l in out.splitlines() if l.strip() and "Name" not in l]
            if lines:
                return lines[0]
        out = run_cmd('powershell -Command "(Get-CimInstance Win32_Processor).Name"')
        if out:
            return out.strip()

    elif system == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":", 1)[1].strip()
        except Exception:
            pass
        out = run_cmd("lscpu | grep 'Model name'")
        if out:
            return out.split(":", 1)[1].strip()

    elif system == "Darwin":
        out = run_cmd("sysctl -n machdep.cpu.brand_string")
        if out:
            return out

    fallback = platform.processor()
    return fallback if fallback else "Unknown"


def get_gpu_model():
    """Best-effort GPU model name(s) across Windows / Linux / macOS."""
    system = platform.system()
    gpus = []

    if system == "Windows":
        out = run_cmd("wmic path win32_VideoController get name")
        if out:
            lines = [l.strip() for l in out.splitlines() if l.strip() and "Name" not in l]
            gpus.extend(lines)
        if not gpus:
            out = run_cmd('powershell -Command "(Get-CimInstance Win32_VideoController).Name"')
            if out:
                gpus.extend([l.strip() for l in out.splitlines() if l.strip()])

    elif system == "Linux":
        out = run_cmd("lspci | grep -Ei 'vga|3d|display'")
        if out:
            for line in out.splitlines():
                gpus.append(line.split(":", 2)[-1].strip())
        if not gpus:
            out = run_cmd("nvidia-smi --query-gpu=name --format=csv,noheader")
            if out:
                gpus.extend([l.strip() for l in out.splitlines() if l.strip()])

    elif system == "Darwin":
        out = run_cmd("system_profiler SPDisplaysDataType | grep 'Chipset Model'")
        if out:
            for line in out.splitlines():
                gpus.append(line.split(":", 1)[1].strip())

    if not gpus:
        return "Unknown / Not detected"
    return ", ".join(dict.fromkeys(gpus))  # dedupe, keep order


def get_battery_health():
    """
    Returns (charge_percent, health_percent, status_text)
    health_percent = full_charge_capacity / design_capacity * 100 (best-effort)
    """
    system = platform.system()
    charge_pct = None
    health_pct = None
    status = "No battery detected"

    battery = psutil.sensors_battery()
    if battery:
        charge_pct = battery.percent
        status = "Charging" if battery.power_plugged else "On battery"

    if system == "Linux":
        base = "/sys/class/power_supply"
        try:
            for bat in os.listdir(base):
                if bat.startswith("BAT"):
                    bat_path = os.path.join(base, bat)

                    def read_val(name):
                        p = os.path.join(bat_path, name)
                        if os.path.exists(p):
                            with open(p) as f:
                                return int(f.read().strip())
                        return None

                    full = read_val("charge_full") or read_val("energy_full")
                    design = read_val("charge_full_design") or read_val("energy_full_design")
                    if full and design:
                        health_pct = round(full / design * 100, 1)
                    break
        except Exception:
            pass

    elif system == "Windows":
        # Requires generating a battery report first
        try:
            report_path = os.path.join(os.environ.get("TEMP", "."), "battery_report.xml")
            run_cmd(f'powercfg /batteryreport /xml /output "{report_path}" /duration 1')
            if os.path.exists(report_path):
                with open(report_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                design_match = re.search(r"<DesignCapacity>(\d+)</DesignCapacity>", content)
                full_match = re.search(r"<FullChargeCapacity>(\d+)</FullChargeCapacity>", content)
                if design_match and full_match:
                    design = int(design_match.group(1))
                    full = int(full_match.group(1))
                    if design > 0:
                        health_pct = round(full / design * 100, 1)
        except Exception:
            pass

    elif system == "Darwin":
        out = run_cmd("system_profiler SPPowerDataType")
        if out:
            max_match = re.search(r"Maximum Capacity:\s*(\d+)%", out)
            if max_match:
                health_pct = float(max_match.group(1))
            cond_match = re.search(r"Condition:\s*(.+)", out)
            if cond_match:
                status += f" | Condition: {cond_match.group(1).strip()}"

    return charge_pct, health_pct, status


class SystemInfoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System Info")
        self.root.geometry("950x680")

        self.running = True

        # ---------- Header ----------
        header = tb.Frame(root, padding=15)
        header.pack(fill=X)

        tb.Label(
            header, text="System Info Viewer",
            font=("Segoe UI", 18, "bold")
        ).pack(side=LEFT)

        self.theme_var = tb.StringVar(value="darkly")
        theme_switch = tb.Combobox(
            header, textvariable=self.theme_var,
            values=["darkly", "flatly", "cyborg", "superhero", "cosmo", "solar"],
            width=12, state="readonly"
        )
        theme_switch.pack(side=RIGHT, padx=5)
        theme_switch.bind("<<ComboboxSelected>>", self.change_theme)
        tb.Label(header, text="Theme:").pack(side=RIGHT, padx=5)

        # ---------- Top summary cards ----------
        self.summary_frame = tb.Frame(root, padding=(15, 0, 15, 10))
        self.summary_frame.pack(fill=X)

        self.cpu_card = self.make_summary_card(self.summary_frame, "CPU Usage", "success")
        self.ram_card = self.make_summary_card(self.summary_frame, "RAM Usage", "info")
        self.disk_card = self.make_summary_card(self.summary_frame, "Disk Usage", "warning")
        self.battery_card = self.make_summary_card(self.summary_frame, "Battery Health", "danger")

        # ---------- Tabs ----------
        self.notebook = tb.Notebook(root, padding=10)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)

        self.tabs = {}
        for name in ["Operating System", "CPU", "RAM", "GPU", "Disk", "Network", "Battery", "Users"]:
            frame = tb.Frame(self.notebook, padding=10)
            text = scrolledtext.ScrolledText(
                frame, wrap="word", font=("Consolas", 11),
                relief="flat", borderwidth=0
            )
            text.pack(fill=BOTH, expand=True)
            text.configure(state="disabled")
            self.notebook.add(frame, text=name)
            self.tabs[name] = text

        # ---------- Footer ----------
        footer = tb.Frame(root, padding=10)
        footer.pack(fill=X)
        self.refresh_btn = tb.Button(
            footer, text="Refresh All", bootstyle="primary",
            command=self.refresh_static_tabs
        )
        self.refresh_btn.pack(side=LEFT)

        self.status_label = tb.Label(footer, text="", font=("Segoe UI", 9))
        self.status_label.pack(side=RIGHT)

        # cache slow-to-fetch values so we don't re-run subprocess commands every 3s
        self._cpu_model = get_cpu_model()
        self._gpu_model = get_gpu_model()

        self.refresh_static_tabs()
        self.update_loop()

    def make_summary_card(self, parent, title, style):
        card = tb.Labelframe(parent, text=title, bootstyle=style, padding=10)
        card.pack(side=LEFT, expand=True, fill=BOTH, padx=5)
        value_label = tb.Label(card, text="...", font=("Segoe UI", 16, "bold"))
        value_label.pack()
        bar = tb.Progressbar(card, bootstyle=f"{style}-striped", length=150)
        bar.pack(pady=5)
        return {"value": value_label, "bar": bar}

    def change_theme(self, event=None):
        self.root.style.theme_use(self.theme_var.get())

    def set_text(self, tab_name, content):
        widget = self.tabs[tab_name]
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", content)
        widget.configure(state="disabled")

    # ---------- Tab content builders ----------
    def refresh_static_tabs(self):
        self.set_text("Operating System", self.get_os_info())
        self.set_text("GPU", self.get_gpu_info())
        self.set_text("Disk", self.get_disk_info())
        self.set_text("Network", self.get_network_info())
        self.set_text("Battery", self.get_battery_info())
        self.set_text("Users", self.get_users_info())

    def get_os_info(self):
        u = platform.uname()
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        return (
            f"OS               : {u.system}\n"
            f"Hostname         : {u.node}\n"
            f"Release          : {u.release}\n"
            f"Full Version     : {u.version}\n"
            f"Architecture     : {u.machine}\n"
            f"Python Version   : {platform.python_version()}\n"
            f"Boot Time        : {boot_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

    def get_cpu_info(self):
        freq = psutil.cpu_freq()
        lines = [
            f"CPU Model         : {self._cpu_model}",
            f"Physical Cores    : {psutil.cpu_count(logical=False)}",
            f"Logical Cores     : {psutil.cpu_count(logical=True)}",
        ]
        if freq:
            lines.append(f"Current Frequency : {freq.current:.2f} MHz")
            lines.append(f"Max Frequency     : {freq.max:.2f} MHz")
        lines.append(f"Total Usage       : {psutil.cpu_percent()}%\n")
        for i, pct in enumerate(psutil.cpu_percent(percpu=True)):
            lines.append(f"  Core {i}: {pct}%")
        return "\n".join(lines)

    def get_ram_info(self):
        v = psutil.virtual_memory()
        s = psutil.swap_memory()
        return (
            f"Total             : {get_size(v.total)}\n"
            f"Available         : {get_size(v.available)}\n"
            f"Used              : {get_size(v.used)}\n"
            f"Usage             : {v.percent}%\n\n"
            f"Swap Total        : {get_size(s.total)}\n"
            f"Swap Used         : {get_size(s.used)}\n"
            f"Swap Usage        : {s.percent}%\n"
        )

    def get_gpu_info(self):
        return f"GPU Model(s)      : {self._gpu_model}\n"

    def get_disk_info(self):
        lines = []
        for part in psutil.disk_partitions():
            lines.append(f"Device      : {part.device}")
            lines.append(f"Mountpoint  : {part.mountpoint}")
            lines.append(f"File System : {part.fstype}")
            try:
                usage = psutil.disk_usage(part.mountpoint)
                lines.append(f"  Total  : {get_size(usage.total)}")
                lines.append(f"  Used   : {get_size(usage.used)}")
                lines.append(f"  Free   : {get_size(usage.free)}")
                lines.append(f"  Usage  : {usage.percent}%")
            except PermissionError:
                lines.append("  Access denied.")
            lines.append("")
        io = psutil.disk_io_counters()
        if io:
            lines.append(f"Total Read  : {get_size(io.read_bytes)}")
            lines.append(f"Total Write : {get_size(io.write_bytes)}")
        return "\n".join(lines)

    def get_network_info(self):
        lines = []
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            lines.append(f"Hostname   : {hostname}")
            lines.append(f"Local IP   : {ip_address}")
        except Exception:
            pass
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                         for ele in range(0, 8 * 6, 8)][::-1])
        lines.append(f"MAC Address: {mac}\n")

        for name, addrs in psutil.net_if_addrs().items():
            lines.append(f"Interface: {name}")
            for addr in addrs:
                fam = str(addr.family)
                if "AF_INET" in fam and "AF_INET6" not in fam:
                    lines.append(f"  IP  : {addr.address}")
                elif "link" in fam.lower() or "packet" in fam.lower():
                    lines.append(f"  MAC : {addr.address}")
            lines.append("")

        net_io = psutil.net_io_counters()
        lines.append(f"Total Received: {get_size(net_io.bytes_recv)}")
        lines.append(f"Total Sent    : {get_size(net_io.bytes_sent)}")
        return "\n".join(lines)

    def get_battery_info(self):
        charge, health, status = get_battery_health()
        lines = [f"Status            : {status}"]
        lines.append(f"Charge Level      : {charge if charge is not None else 'N/A'}%")
        lines.append(f"Estimated Health  : {health if health is not None else 'N/A'}%")
        if health is None:
            lines.append(
                "\n(Health data requires OS-level support: sysfs on Linux,\n"
                "powercfg battery report on Windows, or system_profiler on macOS.\n"
                "Not available on desktops or unsupported hardware.)"
            )
        return "\n".join(lines)

    def get_users_info(self):
        lines = []
        for user in psutil.users():
            started = datetime.datetime.fromtimestamp(user.started)
            lines.append(f"User: {user.name} | Terminal: {user.terminal} | Login: {started}")
        if not lines:
            lines.append("No active users found.")
        return "\n".join(lines)

    # ---------- Live update loop (CPU/RAM/Disk/Battery) ----------
    def update_loop(self):
        if not self.running:
            return

        cpu_pct = psutil.cpu_percent()
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        charge, health, _ = get_battery_health()

        self.cpu_card["value"].configure(text=f"{cpu_pct}%")
        self.cpu_card["bar"]["value"] = cpu_pct

        self.ram_card["value"].configure(text=f"{ram.percent}%")
        self.ram_card["bar"]["value"] = ram.percent

        self.disk_card["value"].configure(text=f"{disk.percent}%")
        self.disk_card["bar"]["value"] = disk.percent

        if health is not None:
            self.battery_card["value"].configure(text=f"{health}%")
            self.battery_card["bar"]["value"] = health
        else:
            self.battery_card["value"].configure(text="N/A")
            self.battery_card["bar"]["value"] = 0

        self.set_text("CPU", self.get_cpu_info())
        self.set_text("RAM", self.get_ram_info())

        self.status_label.configure(
            text=f"Last updated: {datetime.datetime.now().strftime('%H:%M:%S')}"
        )

        self.root.after(3000, self.update_loop)


def main():
    app_root = tb.Window(themename="darkly")
    SystemInfoApp(app_root)
    app_root.mainloop()


if __name__ == "__main__":
    main()
