# 🖥️ System Info Viewer

A lightweight Windows desktop application for viewing detailed system information through a clean graphical interface.

System Info Viewer is built with **Python**, **Tkinter/ttkbootstrap**, and **psutil**. It provides a convenient way to inspect important hardware and operating-system information without using command-line tools.

---

## ✨ Features

* 🖥️ Operating system information
* ⚙️ CPU information and usage
* 🧠 RAM information and usage
* 💾 Disk information
* 🌐 Network information
* 🔋 System and hardware details
* 📊 Real-time resource monitoring
* 🎨 Modern graphical interface using `ttkbootstrap`
* 📦 Can be packaged as a standalone Windows `.exe`

---

## 🛠️ Technologies

| Technology   | Purpose                         |
| ------------ | ------------------------------- |
| Python       | Application development         |
| Tkinter      | GUI framework                   |
| ttkbootstrap | Modern UI styling               |
| psutil       | System and hardware information |
| PyInstaller  | Windows executable packaging    |

---

## 📁 Project Structure

```text
system_info/
│
├── system_info.py
├── system_info_updated .py
│
├── برنامه/
│   ├── system_info.py
│   ├── README.md
│   ├── requirements.txt
│   ├── build.bat
│   ├── app_icon.ico
│   ├── LICENSE.txt
│   ├── SystemInfoViewer.spec
│   └── version_info.txt
│
├── برنامه اپدیت/
│   ├── system_info_updated.py
│   ├── build_SystemInfo.bat
│   └── SystemInfo.spec
│
└── .gitignore
```

---

## 🚀 Run from Source

### 1. Clone the repository

```bash
git clone https://github.com/mahdi12hajizadh/system_info.git
cd system_info
```

### 2. Install dependencies

```bash
pip install -r "برنامه/requirements.txt"
```

### 3. Run the application

```bash
python "برنامه/system_info.py"
```

---

## 🪟 Build Windows EXE

The application can be packaged into a standalone Windows executable using **PyInstaller**.

> ⚠️ The Windows executable should be built on Windows.

Open the project on Windows and run:

```bat
build.bat
```

The generated executable will be available in:

```text
dist\SystemInfoViewer.exe
```

The resulting `.exe` can be distributed to Windows users without requiring Python to be installed.

---

## 🤖 Automated Windows Build

The project can also be built automatically using **GitHub Actions** with a Windows runner.

This makes it possible to generate the Windows `.exe` without having a Windows development environment locally.

---

## 📦 Dependencies

Main dependencies include:

```text
psutil
ttkbootstrap
pyinstaller
```

See [`برنامه/requirements.txt`](برنامه/requirements.txt) for the complete dependency list.

---

## 🔐 Security & Privacy

System Info Viewer is designed to display information from the local computer.

The application does not require an online account or external service to display basic system information.

---

## 📸 Screenshots

Screenshots can be added here:

```text
docs/
└── screenshot.png
```

Example:

![System Info Viewer](docs/screenshot.png)

---

## 📄 License

See [`برنامه/LICENSE.txt`](برنامه/LICENSE.txt) for license information.

---

## 👨‍💻 Author

**Mahdi Hajizadh**

GitHub: [@mahdi12hajizadh](https://github.com/mahdi12hajizadh)

---

## ⭐ Support

If you find this project useful, consider giving it a ⭐ on GitHub.

---

### Project Status

🚧 **Active Development**

The project may receive improvements, UI updates, additional system-information modules, and performance enhancements in future releases.
