#!/usr/bin/env python3
"""
System Info GUI
A Windows/Linux/macOS desktop app that shows detailed system information:
OS, CPU, RAM, GPU, Storage, Network, Battery and Users.

Additional hardware information:
- Battery charge, health and cycle count (where the OS exposes it)
- Physical drive model, SSD/HDD/NVMe type, interface and health
- RAM type (DDR3/DDR4/DDR5...), speed, manufacturer and part number

Requirements:
    pip install psutil ttkbootstrap

Run:
    python system_info_updated.py
"""

import platform
import socket
import uuid
import datetime
import subprocess
import re
import os
import json

import psutil
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import scrolledtext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_size(bytes_val, suffix="B"):
    if bytes_val is None:
        return "N/A"

    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes_val < factor:
            return f"{bytes_val:.2f} {unit}{suffix}"
        bytes_val /= factor
    return f"{bytes_val:.2f} P{suffix}"


def run_cmd(cmd):
    """Run a shell command safely and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="ignore",
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def run_powershell(script):
    """Run PowerShell and return stdout, or None on failure."""
    if platform.system() != "Windows":
        return None

    # ConvertTo-Json makes CIM output much easier to parse reliably.
    cmd = (
        'powershell -NoProfile -ExecutionPolicy Bypass -Command '
        f'"{script}"'
    )
    return run_cmd(cmd)


def safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# CPU / GPU
# ---------------------------------------------------------------------------

def get_cpu_model():
    system = platform.system()

    if system == "Windows":
        out = run_cmd("wmic cpu get name")
        if out:
            lines = [
                l.strip() for l in out.splitlines()
                if l.strip() and "Name" not in l
            ]
            if lines:
                return lines[0]

        out = run_powershell(
            "(Get-CimInstance Win32_Processor).Name"
        )
        if out:
            return out.strip()

    elif system == "Linux":
        try:
            with open("/proc/cpuinfo", encoding="utf-8", errors="ignore") as f:
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

    return platform.processor() or "Unknown"


def get_gpu_model():
    system = platform.system()
    gpus = []

    if system == "Windows":
        out = run_cmd("wmic path win32_VideoController get name")
        if out:
            lines = [
                l.strip() for l in out.splitlines()
                if l.strip() and "Name" not in l
            ]
            gpus.extend(lines)

        if not gpus:
            out = run_powershell(
                "(Get-CimInstance Win32_VideoController).Name"
            )
            if out:
                gpus.extend(
                    [l.strip() for l in out.splitlines() if l.strip()]
                )

    elif system == "Linux":
        out = run_cmd("lspci | grep -Ei 'vga|3d|display'")
        if out:
            for line in out.splitlines():
                gpus.append(line.split(":", 2)[-1].strip())

        if not gpus:
            out = run_cmd(
                "nvidia-smi --query-gpu=name --format=csv,noheader"
            )
            if out:
                gpus.extend(
                    [l.strip() for l in out.splitlines() if l.strip()]
                )

    elif system == "Darwin":
        out = run_cmd(
            "system_profiler SPDisplaysDataType | grep 'Chipset Model'"
        )
        if out:
            for line in out.splitlines():
                if ":" in line:
                    gpus.append(line.split(":", 1)[1].strip())

    if not gpus:
        return "Unknown / Not detected"

    return ", ".join(dict.fromkeys(gpus))


# ---------------------------------------------------------------------------
# Battery
# ---------------------------------------------------------------------------

def get_battery_health():
    """
    Returns:
        charge_percent, health_percent, cycle_count, status_text

    Health:
        Full Charge Capacity / Design Capacity * 100
    """
    system = platform.system()
    charge_pct = None
    health_pct = None
    cycle_count = None
    status = "No battery detected"

    battery = psutil.sensors_battery()

    if battery:
        charge_pct = battery.percent
        status = "Charging" if battery.power_plugged else "On battery"

    if system == "Linux":
        base = "/sys/class/power_supply"

        try:
            for bat in os.listdir(base):
                if not bat.startswith("BAT"):
                    continue

                bat_path = os.path.join(base, bat)

                def read_val(name):
                    path = os.path.join(bat_path, name)
                    if os.path.exists(path):
                        try:
                            with open(path, encoding="utf-8") as f:
                                return int(f.read().strip())
                        except Exception:
                            return None
                    return None

                full = read_val("charge_full") or read_val("energy_full")
                design = (
                    read_val("charge_full_design")
                    or read_val("energy_full_design")
                )

                if full and design:
                    health_pct = round(full / design * 100, 1)

                # Some Linux batteries expose cycle_count directly.
                cycle_count = read_val("cycle_count")
                break

        except Exception:
            pass

    elif system == "Windows":
        try:
            # Battery report XML is supported on modern Windows.
            report_path = os.path.join(
                os.environ.get("TEMP", "."),
                "battery_report.xml",
            )

            run_cmd(
                f'powercfg /batteryreport /xml '
                f'/output "{report_path}" /duration 1'
            )

            if os.path.exists(report_path):
                with open(
                    report_path,
                    encoding="utf-8",
                    errors="ignore",
                ) as f:
                    content = f.read()

                design_match = re.search(
                    r"<DesignCapacity>(\d+)</DesignCapacity>",
                    content,
                    re.I,
                )
                full_match = re.search(
                    r"<FullChargeCapacity>(\d+)</FullChargeCapacity>",
                    content,
                    re.I,
                )

                if design_match and full_match:
                    design = int(design_match.group(1))
                    full = int(full_match.group(1))

                    if design > 0:
                        health_pct = round(full / design * 100, 1)

                # Windows battery report versions may expose
                # CycleCount under BatteryInformation.
                cycle_match = re.search(
                    r"<CycleCount>(\d+)</CycleCount>",
                    content,
                    re.I,
                )
                if cycle_match:
                    cycle_count = int(cycle_match.group(1))

        except Exception:
            pass

        # Fallback: query WMI/CIM if the report did not expose cycles.
        if cycle_count is None:
            out = run_powershell(
                "(Get-CimInstance Win32_Battery | "
                "Select-Object -ExpandProperty CycleCount)"
            )
            if out:
                cycle_count = safe_int(out.splitlines()[0].strip())

    elif system == "Darwin":
        out = run_cmd("system_profiler SPPowerDataType")

        if out:
            max_match = re.search(
                r"Maximum Capacity:\s*(\d+)%",
                out,
                re.I,
            )
            if max_match:
                health_pct = float(max_match.group(1))

            cycle_match = re.search(
                r"Cycle Count:\s*(\d+)",
                out,
                re.I,
            )
            if cycle_match:
                cycle_count = int(cycle_match.group(1))

            cond_match = re.search(
                r"Condition:\s*(.+)",
                out,
                re.I,
            )
            if cond_match:
                status += f" | Condition: {cond_match.group(1).strip()}"

    return charge_pct, health_pct, cycle_count, status


# ---------------------------------------------------------------------------
# RAM information
# ---------------------------------------------------------------------------

def get_ram_details():
    """
    Returns detailed physical RAM information.

    Windows:
        Uses Win32_PhysicalMemory through PowerShell/CIM.
    Linux/macOS:
        Uses available system tools when possible.
    """
    details = []

    if platform.system() == "Windows":
        script = (
            "Get-CimInstance Win32_PhysicalMemory | "
            "Select-Object Capacity,Speed,ConfiguredClockSpeed,"
            "Manufacturer,PartNumber,SMBIOSMemoryType,MemoryType,DeviceLocator | "
            "ConvertTo-Json -Compress"
        )

        out = run_powershell(script)

        if out:
            try:
                data = json.loads(out)
                if isinstance(data, dict):
                    data = [data]

                for item in data:
                    capacity = safe_int(item.get("Capacity"))
                    speed = (
                        safe_int(item.get("ConfiguredClockSpeed"))
                        or safe_int(item.get("Speed"))
                    )

                    smbios_type = safe_int(item.get("SMBIOSMemoryType"))
                    memory_type = safe_int(item.get("MemoryType"))

                    # SMBIOS memory type values:
                    # 20 = DDR, 21 = DDR2, 22 = DDR2 FB-DIMM,
                    # 24 = DDR3, 26 = DDR4, 34 = DDR5.
                    ddr_map = {
                        20: "DDR",
                        21: "DDR2",
                        22: "DDR2",
                        24: "DDR3",
                        26: "DDR4",
                        34: "DDR5",
                    }

                    ram_type = (
                        ddr_map.get(smbios_type)
                        or ddr_map.get(memory_type)
                        or "Unknown"
                    )

                    details.append({
                        "slot": item.get("DeviceLocator") or "Unknown",
                        "capacity": get_size(capacity),
                        "type": ram_type,
                        "speed": f"{speed} MHz" if speed else "N/A",
                        "manufacturer": (
                            str(item.get("Manufacturer")).strip()
                            if item.get("Manufacturer")
                            else "Unknown"
                        ),
                        "part_number": (
                            str(item.get("PartNumber")).strip()
                            if item.get("PartNumber")
                            else "Unknown"
                        ),
                    })

                if details:
                    return details

            except (json.JSONDecodeError, TypeError, ValueError):
                pass

    # Linux fallback
    if platform.system() == "Linux":
        out = run_cmd("dmidecode --type memory")
        if out:
            blocks = re.split(r"\n\s*\n", out)

            for block in blocks:
                if "Memory Device" not in block:
                    continue

                def field(pattern):
                    match = re.search(pattern, block, re.I)
                    return match.group(1).strip() if match else "Unknown"

                details.append({
                    "slot": field(r"Locator:\s*(.+)"),
                    "capacity": field(r"Size:\s*(.+)"),
                    "type": field(r"Type:\s*(.+)"),
                    "speed": field(r"Speed:\s*(.+)"),
                    "manufacturer": field(r"Manufacturer:\s*(.+)"),
                    "part_number": field(r"Part Number:\s*(.+)"),
                })

    return details


# ---------------------------------------------------------------------------
# Storage information
# ---------------------------------------------------------------------------

def get_storage_details():
    """
    Returns physical drive information.

    Windows:
        Model, serial, media type, bus type, health status and size.

    Health Status is the OS-reported status, not a SMART percentage.
    A true SMART/NVMe percentage requires vendor/controller-specific data.
    """
    drives = []

    if platform.system() == "Windows":
        script = (
            "Get-PhysicalDisk | "
            "Select-Object FriendlyName,SerialNumber,MediaType,BusType,"
            "HealthStatus,OperationalStatus,Size,CanPool,SpindleSpeed | "
            "ConvertTo-Json -Compress"
        )

        out = run_powershell(script)

        if out:
            try:
                data = json.loads(out)
                if isinstance(data, dict):
                    data = [data]

                for item in data:
                    size = safe_int(item.get("Size"))
                    media = str(item.get("MediaType") or "Unknown")

                    # NVMe drives are normally SSDs, even when the
                    # MediaType field is not populated correctly.
                    bus = str(item.get("BusType") or "Unknown")
                    if media.lower() == "unspecified" and bus.lower() == "nvme":
                        media = "SSD"

                    drives.append({
                        "model": item.get("FriendlyName") or "Unknown",
                        "serial": item.get("SerialNumber") or "Unknown",
                        "type": media,
                        "interface": bus,
                        "health": item.get("HealthStatus") or "Unknown",
                        "operational": item.get("OperationalStatus") or "Unknown",
                        "capacity": get_size(size),
                        "spindle_speed": (
                            f"{item.get('SpindleSpeed')} RPM"
                            if item.get("SpindleSpeed")
                            else "N/A"
                        ),
                    })

                if drives:
                    return drives

            except (json.JSONDecodeError, TypeError, ValueError):
                pass

    # Linux fallback
    if platform.system() == "Linux":
        out = run_cmd(
            "lsblk -d -o NAME,MODEL,SIZE,ROTA,TRAN,TYPE --json"
        )

        if out:
            try:
                data = json.loads(out)
                for item in data.get("blockdevices", []):
                    rota = item.get("rota")
                    media = "HDD" if rota else "SSD"

                    drives.append({
                        "model": item.get("model") or "Unknown",
                        "serial": "N/A",
                        "type": media,
                        "interface": item.get("tran") or "Unknown",
                        "health": "OS health unavailable",
                        "operational": "N/A",
                        "capacity": item.get("size") or "Unknown",
                        "spindle_speed": "N/A",
                    })

                if drives:
                    return drives

            except (json.JSONDecodeError, TypeError, ValueError):
                pass

    # macOS fallback
    if platform.system() == "Darwin":
        out = run_cmd("system_profiler SPStorageDataType")
        if out:
            drives.append({
                "model": "See macOS Storage Utility",
                "serial": "N/A",
                "type": "SSD/HDD depends on device",
                "interface": "N/A",
                "health": "OS health unavailable",
                "operational": "N/A",
                "capacity": "See Storage tab",
                "spindle_speed": "N/A",
            })

    return drives


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class SystemInfoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System Info")
        self.root.geometry("1050x760")
        self.root.minsize(900, 650)

        self.running = True

        # Header
        header = tb.Frame(root, padding=15)
        header.pack(fill=X)

        tb.Label(
            header,
            text="System Info Viewer",
            font=("Segoe UI", 18, "bold"),
        ).pack(side=LEFT)

        self.theme_var = tb.StringVar(value="darkly")
        theme_switch = tb.Combobox(
            header,
            textvariable=self.theme_var,
            values=[
                "darkly",
                "flatly",
                "cyborg",
                "superhero",
                "cosmo",
                "solar",
            ],
            width=12,
            state="readonly",
        )
        theme_switch.pack(side=RIGHT, padx=5)
        theme_switch.bind("<<ComboboxSelected>>", self.change_theme)

        tb.Label(header, text="Theme:").pack(side=RIGHT, padx=5)

        # Summary cards
        self.summary_frame = tb.Frame(
            root,
            padding=(15, 0, 15, 10),
        )
        self.summary_frame.pack(fill=X)

        self.cpu_card = self.make_summary_card(
            self.summary_frame,
            "CPU Usage",
            "success",
        )

        self.ram_card = self.make_summary_card(
            self.summary_frame,
            "RAM Usage",
            "info",
        )

        self.disk_card = self.make_summary_card(
            self.summary_frame,
            "Disk Usage",
            "warning",
        )

        self.battery_card = self.make_summary_card(
            self.summary_frame,
            "Battery Health",
            "danger",
        )

        # Tabs
        self.notebook = tb.Notebook(root, padding=10)
        self.notebook.pack(
            fill=BOTH,
            expand=True,
            padx=10,
            pady=10,
        )

        self.tabs = {}

        tab_names = [
            "Operating System",
            "CPU",
            "RAM",
            "GPU",
            "Disk",
            "Network",
            "Battery",
            "Users",
        ]

        for name in tab_names:
            frame = tb.Frame(self.notebook, padding=10)

            text = scrolledtext.ScrolledText(
                frame,
                wrap="word",
                font=("Consolas", 11),
                relief="flat",
                borderwidth=0,
            )
            text.pack(fill=BOTH, expand=True)
            text.configure(state="disabled")

            self.notebook.add(frame, text=name)
            self.tabs[name] = text

        # Footer
        footer = tb.Frame(root, padding=10)
        footer.pack(fill=X)

        self.refresh_btn = tb.Button(
            footer,
            text="Refresh All",
            bootstyle="primary",
            command=self.refresh_static_tabs,
        )
        self.refresh_btn.pack(side=LEFT)

        self.status_label = tb.Label(
            footer,
            text="",
            font=("Segoe UI", 9),
        )
        self.status_label.pack(side=RIGHT)

        # Cache slow hardware queries.
        self._cpu_model = get_cpu_model()
        self._gpu_model = get_gpu_model()

        self.refresh_static_tabs()
        self.update_loop()

    def make_summary_card(self, parent, title, style):
        card = tb.Labelframe(
            parent,
            text=title,
            bootstyle=style,
            padding=10,
        )
        card.pack(
            side=LEFT,
            expand=True,
            fill=BOTH,
            padx=5,
        )

        value_label = tb.Label(
            card,
            text="...",
            font=("Segoe UI", 16, "bold"),
        )
        value_label.pack()

        bar = tb.Progressbar(
            card,
            bootstyle=f"{style}-striped",
            length=150,
        )
        bar.pack(pady=5)

        return {
            "value": value_label,
            "bar": bar,
        }

    def change_theme(self, event=None):
        self.root.style.theme_use(self.theme_var.get())

    def set_text(self, tab_name, content):
        widget = self.tabs[tab_name]
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", content)
        widget.configure(state="disabled")

    # -----------------------------------------------------------------------
    # Static tab builders
    # -----------------------------------------------------------------------

    def refresh_static_tabs(self):
        self.set_text("Operating System", self.get_os_info())
        self.set_text("CPU", self.get_cpu_info())
        self.set_text("RAM", self.get_ram_info())
        self.set_text("GPU", self.get_gpu_info())
        self.set_text("Disk", self.get_disk_info())
        self.set_text("Network", self.get_network_info())
        self.set_text("Battery", self.get_battery_info())
        self.set_text("Users", self.get_users_info())

        self.status_label.configure(
            text=(
                "Hardware information refreshed: "
                f"{datetime.datetime.now().strftime('%H:%M:%S')}"
            )
        )

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

        lines.append(f"Total Usage       : {psutil.cpu_percent()}%")

        lines.append("\nPer Core Usage:")
        for i, pct in enumerate(psutil.cpu_percent(percpu=True)):
            lines.append(f"  Core {i}: {pct}%")

        return "\n".join(lines)

    def get_ram_info(self):
        v = psutil.virtual_memory()
        s = psutil.swap_memory()
        modules = get_ram_details()

        lines = [
            "=== RAM SUMMARY ===",
            f"Total             : {get_size(v.total)}",
            f"Available         : {get_size(v.available)}",
            f"Used              : {get_size(v.used)}",
            f"Usage             : {v.percent}%",
            "",
            f"Swap Total        : {get_size(s.total)}",
            f"Swap Used         : {get_size(s.used)}",
            f"Swap Usage        : {s.percent}%",
            "",
            "=== PHYSICAL RAM MODULES ===",
        ]

        if not modules:
            lines.append("Detailed physical RAM information: N/A")
            return "\n".join(lines)

        lines.append(f"Modules Detected  : {len(modules)}")
        lines.append("")

        for index, module in enumerate(modules, 1):
            lines.extend([
                f"[RAM Module {index}]",
                f"Slot              : {module['slot']}",
                f"Capacity          : {module['capacity']}",
                f"Type              : {module['type']}",
                f"Speed             : {module['speed']}",
                f"Manufacturer      : {module['manufacturer']}",
                f"Part Number       : {module['part_number']}",
                "",
            ])

        return "\n".join(lines)

    def get_gpu_info(self):
        return f"GPU Model(s)      : {self._gpu_model}\n"

    def get_disk_info(self):
        lines = [
            "=== PHYSICAL DRIVES ===",
            "",
        ]

        drives = get_storage_details()

        if drives:
            for index, drive in enumerate(drives, 1):
                lines.extend([
                    f"[Drive {index}]",
                    f"Model             : {drive['model']}",
                    f"Serial Number     : {drive['serial']}",
                    f"Type              : {drive['type']}",
                    f"Interface         : {drive['interface']}",
                    f"Capacity          : {drive['capacity']}",
                    f"Health Status     : {drive['health']}",
                    f"Operational       : {drive['operational']}",
                    f"Spindle Speed     : {drive['spindle_speed']}",
                    "",
                ])
        else:
            lines.append("Physical drive information: N/A")

        lines.extend([
            "=== PARTITION USAGE ===",
            "",
        ])

        for part in psutil.disk_partitions(all=False):
            lines.append(f"Device      : {part.device}")
            lines.append(f"Mountpoint  : {part.mountpoint}")
            lines.append(f"File System : {part.fstype}")

            try:
                usage = psutil.disk_usage(part.mountpoint)
                lines.append(f"  Total  : {get_size(usage.total)}")
                lines.append(f"  Used   : {get_size(usage.used)}")
                lines.append(f"  Free   : {get_size(usage.free)}")
                lines.append(f"  Usage  : {usage.percent}%")
            except (PermissionError, OSError):
                lines.append("  Access denied.")

            lines.append("")

        io = psutil.disk_io_counters()

        if io:
            lines.extend([
                "=== DISK I/O SINCE BOOT ===",
                f"Total Read  : {get_size(io.read_bytes)}",
                f"Total Write : {get_size(io.write_bytes)}",
            ])

        lines.extend([
            "",
            "NOTE:",
            "Health Status is the OS/controller health state.",
            "A true SMART/NVMe percentage is not universally available",
            "through standard Windows APIs and depends on the drive.",
        ])

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

        mac = ":".join(
            [
                "{:02x}".format(
                    (uuid.getnode() >> ele) & 0xff
                )
                for ele in range(0, 8 * 6, 8)
            ][::-1]
        )

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
        charge, health, cycles, status = get_battery_health()

        lines = [
            "=== BATTERY ===",
            f"Status            : {status}",
            f"Charge Level      : "
            f"{charge if charge is not None else 'N/A'}%",
            f"Battery Health    : "
            f"{health if health is not None else 'N/A'}%",
            f"Cycle Count       : "
            f"{cycles if cycles is not None else 'N/A'}",
            "",
            "Health = Full Charge Capacity / Design Capacity.",
        ]

        if health is None:
            lines.extend([
                "",
                "Battery health could not be read from the OS.",
            ])

        if cycles is None:
            lines.extend([
                "",
                "Cycle count is hardware/firmware dependent.",
                "Some laptop BIOS/firmware does not expose it to Windows.",
            ])

        return "\n".join(lines)

    def get_users_info(self):
        lines = []

        for user in psutil.users():
            started = datetime.datetime.fromtimestamp(user.started)
            lines.append(
                f"User: {user.name} | "
                f"Terminal: {user.terminal} | "
                f"Login: {started}"
            )

        if not lines:
            lines.append("No active users found.")

        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Live update
    # -----------------------------------------------------------------------

    def update_loop(self):
        if not self.running:
            return

        cpu_pct = psutil.cpu_percent()
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        charge, health, _, _ = get_battery_health()

        self.cpu_card["value"].configure(text=f"{cpu_pct}%")
        self.cpu_card["bar"]["value"] = cpu_pct

        self.ram_card["value"].configure(text=f"{ram.percent}%")
        self.ram_card["bar"]["value"] = ram.percent

        self.disk_card["value"].configure(text=f"{disk.percent}%")
        self.disk_card["bar"]["value"] = disk.percent

        if health is not None:
            self.battery_card["value"].configure(
                text=f"{health}%"
            )
            self.battery_card["bar"]["value"] = health
        else:
            self.battery_card["value"].configure(text="N/A")
            self.battery_card["bar"]["value"] = 0

        self.set_text("CPU", self.get_cpu_info())
        self.set_text("RAM", self.get_ram_info())

        self.status_label.configure(
            text=f"Last updated: "
            f"{datetime.datetime.now().strftime('%H:%M:%S')}"
        )

        self.root.after(3000, self.update_loop)


def main():
    app_root = tb.Window(themename="darkly")
    SystemInfoApp(app_root)

    def on_close():
        app = app_root
        app.running = False
        app.destroy()

    app_root.protocol("WM_DELETE_WINDOW", on_close)
    app_root.mainloop()


if __name__ == "__main__":
    main()
