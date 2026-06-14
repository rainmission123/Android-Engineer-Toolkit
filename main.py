#!/usr/bin/env python3

import subprocess
import time
import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn

console = Console()

GREEN = "bright_green"
CYAN = "bright_cyan"
RED = "bright_red"
YELLOW = "yellow"


def run_cmd(cmd):
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            text=True,
            capture_output=True,
            timeout=8
        )
        return result.stdout.strip()
    except Exception as e:
        return str(e)


def adb(cmd):
    return run_cmd(f"adb shell {cmd}")


def is_connected():
    out = run_cmd("adb devices")
    lines = out.splitlines()
    for line in lines:
        if "\tdevice" in line:
            return True
    return False


def getprop(prop):
    return adb(f"getprop {prop}")


def get_battery():
    out = adb("dumpsys battery")
    info = {}
    for line in out.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip()] = v.strip()
    return info


def get_mem():
    out = adb("cat /proc/meminfo")
    mem = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            mem[parts[0].replace(":", "")] = int(parts[1])
    total = mem.get("MemTotal", 1)
    available = mem.get("MemAvailable", 0)
    used = total - available
    percent = int((used / total) * 100)
    return total, used, available, percent


def get_storage():
    out = adb("df /data")
    lines = out.splitlines()
    if len(lines) >= 2:
        parts = lines[1].split()
        if len(parts) >= 5:
            return parts[1], parts[2], parts[3], parts[4]
    return "?", "?", "?", "?"


def get_cpu_top():
    out = adb("top -b -n 1 | head -20")
    return out


def get_services_count():
    out = adb("service list | head -1")
    return out.replace("Found ", "").replace(" services:", "")


def get_device_info():
    return {
        "Device": getprop("ro.product.model") or "Unknown",
        "Manufacturer": getprop("ro.product.manufacturer") or "Unknown",
        "Android": getprop("ro.build.version.release") or "Unknown",
        "SDK": getprop("ro.build.version.sdk") or "Unknown",
        "Security Patch": getprop("ro.build.version.security_patch") or "Unknown",
        "Kernel": adb("uname -r") or "Unknown",
        "ABI": getprop("ro.product.cpu.abi") or "Unknown",
    }


def bar(percent):
    filled = int(percent / 5)
    empty = 20 - filled
    return f"[{GREEN}]{'█' * filled}{'░' * empty}[/] {percent}%"


def logo():
    return Text(
        """
 █████╗ ███╗   ██╗██████╗ ██████╗  ██████╗ ██╗██████╗ 
██╔══██╗████╗  ██║██╔══██╗██╔══██╗██╔═══██╗██║██╔══██╗
███████║██╔██╗ ██║██║  ██║██████╔╝██║   ██║██║██║  ██║
██╔══██║██║╚██╗██║██║  ██║██╔══██╗██║   ██║██║██║  ██║
██║  ██║██║ ╚████║██████╔╝██║  ██║╚██████╔╝██║██████╔╝
╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝╚═════╝ 

        ANDROID ENGINEER TOOLKIT v1.0
        """,
        style=GREEN
    )


def make_dashboard():
    connected = is_connected()
    device = get_device_info() if connected else {}
    battery = get_battery() if connected else {}
    services = get_services_count() if connected else "0"

    try:
        total, used, available, mem_percent = get_mem()
        total_gb = total / 1024 / 1024
        used_gb = used / 1024 / 1024
    except:
        mem_percent = 0
        total_gb = 0
        used_gb = 0

    try:
        size, used_storage, free_storage, storage_percent = get_storage()
    except:
        size, used_storage, free_storage, storage_percent = "?", "?", "?", "?"

    layout = Layout()
    layout.split_column(
        Layout(name="top", size=10),
        Layout(name="main"),
        Layout(name="bottom", size=3),
    )

    layout["main"].split_row(
        Layout(name="left", ratio=1),
        Layout(name="middle", ratio=1),
        Layout(name="right", ratio=1),
    )

    layout["left"].split_column(
        Layout(name="device", size=11),
        Layout(name="menu"),
    )

    layout["middle"].split_column(
        Layout(name="overview", size=13),
        Layout(name="quick", size=11),
        Layout(name="activity"),
    )

    layout["right"].split_column(
        Layout(name="cpu", size=12),
        Layout(name="memory", size=10),
        Layout(name="system", size=10),
    )

    layout["top"].update(Panel(logo(), border_style=GREEN))

    dev_table = Table.grid(padding=(0, 1))
    dev_table.add_column(style=GREEN)
    dev_table.add_column(style=CYAN)
    dev_table.add_row("Device", device.get("Device", "No device"))
    dev_table.add_row("Android", device.get("Android", "?"))
    dev_table.add_row("SDK", device.get("SDK", "?"))
    dev_table.add_row("Manufacturer", device.get("Manufacturer", "?"))
    dev_table.add_row("ADB Status", "🟢 Connected" if connected else "🔴 Disconnected")
    dev_table.add_row("Kernel", device.get("Kernel", "?"))
    layout["device"].update(Panel(dev_table, title="📱 DEVICE INFORMATION", border_style=GREEN))

    menu = """
[1] 📜 Live Logcat
[2] ⚡ CPU Monitor
[3] 🧠 RAM Monitor
[4] 🔋 Battery Information
[5] 🎮 FPS / Graphics Monitor
[6] ⚙  Android Services
[7] 📦 Installed Applications
[8] 📱 Device Information
[9] 🌡  Temperature Monitor
[10] 🏃 Running Processes
[11] 🔍 Package Inspector
[12] 📂 File Explorer (/sdcard)
[13] 📡 Network Monitor
[14] 🚀 Performance Test

[0] ❌ Exit
"""
    layout["menu"].update(Panel(menu, title="☰ MAIN MENU", border_style=GREEN))

    overview = Table.grid(padding=(0, 1))
    overview.add_column(style=GREEN)
    overview.add_column(style=CYAN)
    overview.add_row("CPU Usage", "Use option 2")
    overview.add_row("RAM Usage", bar(mem_percent))
    overview.add_row("RAM", f"{used_gb:.2f} GB / {total_gb:.2f} GB")
    overview.add_row("Storage", f"{storage_percent} used")
    overview.add_row("Battery", f"{battery.get('level', '?')}%")
    overview.add_row("Charging", battery.get("status", "?"))
    overview.add_row("Security Patch", device.get("Security Patch", "?"))
    layout["overview"].update(Panel(overview, title="📊 SYSTEM OVERVIEW", border_style=GREEN))

    quick = """
l  → Live Logcat        i  → Device Info
c  → CPU Monitor        t  → Temperature
m  → RAM Monitor        n  → Network Monitor
b  → Battery Info       f  → FPS Monitor
s  → Services           x  → Exit
p  → Installed Apps
"""
    layout["quick"].update(Panel(quick, title="🚀 QUICK ACCESS", border_style=GREEN))

    recent = f"""
Device checked
ADB status: {"Connected" if connected else "Disconnected"}
Services detected: {services}
RAM usage: {mem_percent}%
Battery: {battery.get("level", "?")}%
"""
    layout["activity"].update(Panel(recent, title="🕘 RECENT ACTIVITY", border_style=GREEN))

    cpu_text = adb("top -b -n 1 | head -10") if connected else "No device connected"
    layout["cpu"].update(Panel(cpu_text, title="⚡ TOP PROCESSES", border_style=GREEN))

    memory = f"""
Used      : {used_gb:.2f} GB
Total     : {total_gb:.2f} GB
Available : {available / 1024 / 1024:.2f} GB
Usage     : {mem_percent}%

{bar(mem_percent)}
"""
    layout["memory"].update(Panel(memory, title="🧠 MEMORY BREAKDOWN", border_style=GREEN))

    system = f"""
Services : {services}
Storage  : {storage_percent}
Data Used: {used_storage}
Data Free: {free_storage}
ABI      : {device.get("ABI", "?")}
"""
    layout["system"].update(Panel(system, title="⚙ SYSTEM INFO", border_style=GREEN))

    layout["bottom"].update(
        Panel(
            "[bright_green]Android Engineer Toolkit v1.0.0[/] | Built for Android Developers & System Engineers",
            border_style=GREEN
        )
    )

    return layout


def pause():
    input("\nPress ENTER to return to menu...")


def live_logcat():
    os.system("clear")
    console.print("[bright_green]Starting Live Logcat... Press CTRL+C to stop[/]")
    os.system("adb logcat")
    pause()


def cpu_monitor():
    os.system("clear")
    os.system("adb shell top")
    pause()


def ram_monitor():
    os.system("clear")
    console.print(Panel(adb("dumpsys meminfo"), title="RAM MONITOR", border_style=GREEN))
    pause()


def battery_info():
    os.system("clear")
    console.print(Panel(adb("dumpsys battery"), title="BATTERY INFORMATION", border_style=GREEN))
    pause()


def fps_monitor():
    os.system("clear")
    console.print("[bright_green]Collecting FPS / GFX info...[/]")
    console.print(Panel(adb("dumpsys gfxinfo"), title="FPS / GFX INFO", border_style=GREEN))
    pause()


def android_services():
    os.system("clear")
    console.print(Panel(adb("service list"), title="ANDROID SERVICES", border_style=GREEN))
    pause()


def installed_apps():
    os.system("clear")
    console.print(Panel(adb("pm list packages"), title="INSTALLED APPLICATIONS", border_style=GREEN))
    pause()


def device_information():
    os.system("clear")
    console.print(Panel(adb("getprop"), title="DEVICE INFORMATION / GETPROP", border_style=GREEN))
    pause()


def temperature_monitor():
    os.system("clear")
    paths = adb("find /sys/class/thermal -name temp 2>/dev/null")
    output = ""
    for path in paths.splitlines():
        val = adb(f"cat {path}")
        if val:
            output += f"{path}: {val}\n"
    console.print(Panel(output or "No thermal data accessible", title="TEMPERATURE MONITOR", border_style=GREEN))
    pause()


def running_processes():
    os.system("clear")
    console.print(Panel(adb("ps -A"), title="RUNNING PROCESSES", border_style=GREEN))
    pause()


def package_inspector():
    package = input("Enter package name: ")
    os.system("clear")
    console.print(Panel(adb(f"dumpsys package {package}"), title=f"PACKAGE INSPECTOR: {package}", border_style=GREEN))
    pause()


def file_explorer():
    os.system("clear")
    console.print(Panel(adb("ls -la /sdcard | head -100"), title="FILE EXPLORER /sdcard", border_style=GREEN))
    pause()


def network_monitor():
    os.system("clear")
    output = adb("ip addr")
    console.print(Panel(output, title="NETWORK MONITOR", border_style=GREEN))
    pause()


def performance_test():
    os.system("clear")
    report = ""
    report += "===== CPU =====\n"
    report += adb("top -b -n 1 | head -15") + "\n\n"
    report += "===== MEMORY =====\n"
    report += adb("cat /proc/meminfo | head -20") + "\n\n"
    report += "===== BATTERY =====\n"
    report += adb("dumpsys battery") + "\n\n"
    report += "===== STORAGE =====\n"
    report += adb("df -h") + "\n\n"
    report += "===== CURRENT ACTIVITY =====\n"
    report += adb("dumpsys activity activities | grep -E 'ResumedActivity|topResumedActivity|mFocusedApp' | head -20")
    console.print(Panel(report, title="PERFORMANCE TEST REPORT", border_style=GREEN))
    pause()


def main():
    while True:
        os.system("clear")
        console.print(make_dashboard())
        choice = input("Select option: ").strip().lower()

        if choice in ["1", "l"]:
            live_logcat()
        elif choice in ["2", "c"]:
            cpu_monitor()
        elif choice in ["3", "m"]:
            ram_monitor()
        elif choice in ["4", "b"]:
            battery_info()
        elif choice in ["5", "f"]:
            fps_monitor()
        elif choice in ["6", "s"]:
            android_services()
        elif choice in ["7", "p"]:
            installed_apps()
        elif choice in ["8", "i"]:
            device_information()
        elif choice in ["9", "t"]:
            temperature_monitor()
        elif choice == "10":
            running_processes()
        elif choice == "11":
            package_inspector()
        elif choice == "12":
            file_explorer()
        elif choice in ["13", "n"]:
            network_monitor()
        elif choice == "14":
            performance_test()
        elif choice in ["0", "x", "q"]:
            console.print("[bright_green]Exiting Android Engineer Toolkit...[/]")
            break
        else:
            console.print("[red]Invalid option[/]")
            time.sleep(1)


if __name__ == "__main__":
    main()
