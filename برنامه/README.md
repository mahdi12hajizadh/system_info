# System Info Viewer — Build & Publish Guide

This turns `system_info.py` into a standalone Windows `.exe` that anyone
can double-click to run — no Python installation needed on their machine.

## ⚠️ Important: build ON Windows

PyInstaller cannot cross-compile. You must run the build step on an actual
Windows machine (Windows 10/11), not on Linux or Mac. If you don't have
Windows, options are: a Windows VM, a friend's PC, or a free Windows runner
on GitHub Actions (see the "Automated build" section below).

## Files in this package

| File                  | Purpose                                          |
|------------------------|--------------------------------------------------|
| `system_info.py`      | The app itself                                   |
| `requirements.txt`    | Python packages needed                           |
| `build.bat`           | One-click build script (run on Windows)          |
| `app_icon.ico`        | App icon (feel free to replace with your own)    |
| `version_info.txt`    | Metadata embedded in the .exe (edit the name/copyright fields) |

## Step 1 — Install Python (on Windows)

Download and install Python 3.11+ from https://python.org
✅ During install, check **"Add python.exe to PATH"**.

## Step 2 — Put all files in one folder

Put `system_info.py`, `requirements.txt`, `build.bat`, `app_icon.ico`,
and `version_info.txt` all in the same folder.

## Step 3 — Run the build

Double-click `build.bat` (or run it from a terminal: `build.bat`).
It will:
1. Install `psutil`, `ttkbootstrap`, and `pyinstaller`
2. Package everything into a single `.exe`

When it finishes, your app is at:
```
dist\SystemInfoViewer.exe
```

That one file is fully standalone — you can copy it to any Windows PC and
run it directly.

## Step 4 — Test it

Run `dist\SystemInfoViewer.exe` on a **different** Windows machine (or a
clean VM) if possible, to confirm it works without your dev environment.

### About antivirus / SmartScreen warnings

This is normal and expected for unsigned PyInstaller executables — it
happens to nearly every small indie app, not just yours:
- **Windows SmartScreen** may show "Windows protected your PC" the first
  time it's run on an unfamiliar machine. Users click "More info" → "Run
  anyway". This fades over time as more people download and run it.
- Some antivirus engines flag PyInstaller `.exe` files as suspicious
  (a known false-positive pattern, since malware also uses PyInstaller).
  You can check your build on https://www.virustotal.com before
  publishing, and submit it to Microsoft as a false positive at
  https://www.microsoft.com/en-us/wdsi/filesubmission if needed.
- The permanent fix is **code signing** (an Authenticode certificate,
  ~$100-400/year from a CA like DigiCert or SSL.com), which removes most
  warnings. Optional for a first release, but worth it if you plan to grow
  this.

## Step 5 — Publish it

Common free options for indie/hobby Windows apps:

1. **GitHub Releases** (most common, free, easy updates)
   - Create a repo, go to "Releases" → "Draft a new release"
   - Upload `SystemInfoViewer.exe` as a release asset
   - Users download directly from your repo's Releases page

2. **itch.io** — free hosting for small desktop apps/tools, has a simple
   upload flow and even an installer app (butler) for auto-updates.

3. **Your own site / a shared link** (Google Drive, Mega, etc.) — simplest,
   but less discoverable and no update mechanism.

Whichever you choose, include:
- A short description + a screenshot
- The `.exe` (or a `.zip` containing it)
- Optionally a SHA-256 checksum so users can verify the download:
  ```
  certutil -hashfile SystemInfoViewer.exe SHA256
  ```

## Optional: Automated build via GitHub Actions (no Windows PC needed)

If you don't own a Windows machine, GitHub can build it for you for free
using a Windows runner. Push your files to a GitHub repo, then add a
workflow file `.github/workflows/build.yml`:

```yaml
name: Build Windows EXE
on: [workflow_dispatch, push]
jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pyinstaller --noconfirm --onefile --windowed --name "SystemInfoViewer" --icon "app_icon.ico" --version-file "version_info.txt" system_info.py
      - uses: actions/upload-artifact@v4
        with:
          name: SystemInfoViewer
          path: dist/SystemInfoViewer.exe
```

Push to GitHub → go to the "Actions" tab → run the workflow → download the
built `.exe` from the run's artifacts. No local Windows machine required.

## Before you publish — a few polish suggestions

- Edit `version_info.txt`: replace `Your Name` with your actual name or
  project name.
- Rename the app / pick a final name — currently "System Info Viewer".
- Consider adding a short LICENSE file (MIT is a common permissive choice
  for a free tool like this).
- `ttkbootstrap` and `psutil` are both permissively licensed (MIT / BSD),
  so bundling them in your `.exe` for distribution is fine.
