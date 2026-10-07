**English** | [Français](README.fr.md)

# AndroWake

A Windows desktop tool to control an Android device from your PC through **adb**, with a simple graphical interface (Python + Tkinter). It detects devices in Android, Recovery, Sideload and Bootloader (fastboot) modes, and bundles the everyday tasks — screenshots, app management, file transfer, remote control, screen mirroring, logcat — in one window.

## Download & install

1. Download `AndroWakeSetup.exe` from the [Releases](https://github.com/Swanboss01/AndroWake/releases) page.
2. Run the installer. No administrator rights are needed: AndroWake installs into `%LOCALAPPDATA%\AndroWake`, so it can download its tools next to itself.
3. On first launch, AndroWake offers to download **adb** (Google's official `platform-tools`) into its own folder. Nothing is installed system-wide and your `PATH` is untouched.

On the phone:

1. Enable **Developer options** (tap *Build number* seven times in *Settings → About phone*).
2. Enable **USB debugging**.
3. Plug in the USB cable and accept the RSA fingerprint prompt the first time.

## Features

| Area | What you get |
|---|---|
| **Device detection** | Lists devices in *Android*, *Recovery*, *Recovery (sideload)*, *Bootloader (fastboot)*, *Unauthorized* and *Offline* states. The list refreshes automatically every 3 seconds. |
| **Screen** | Wake the screen, put the device to sleep, toggle *stay awake* while charging, save a screenshot as PNG. |
| **Device info** | Brand, model, Android version, SDK level, build ID, CPU ABI, battery status. |
| **App manager** | Search installed apps, show system apps, launch, force-stop, clear data, extract the APK, uninstall (with confirmation). Install APKs from disk. |
| **Files** | Push a file to `/sdcard/Download/`, pull any path from the device. |
| **Recovery** | Sideload a ZIP while the device is in recovery (*Apply update from ADB*). |
| **Reboot** | Normal, recovery or bootloader. Uses adb or fastboot depending on the device mode. |
| **Connection** | One-click **Wi-Fi ADB** (reads the device IP, enables `adb tcpip`, connects), or connect by IP address. |
| **Remote control** | Back, Home, Recents, Volume, Power, D-pad, media keys, notifications; text input; open a URL; tap and swipe by coordinates. |
| **Screen mirroring** | Powered by [scrcpy](https://github.com/Genymobile/scrcpy), downloaded on demand into the AndroWake folder. |
| **Logcat** | Live stream with minimum level, keyword filter applied on the fly, coloured warnings/errors, clear and export to a text file. |
| **Shell** | An `adb shell` command line with output in the main log. |
| **Interface** | Light and dark themes. All adb calls run in background threads, so the window never freezes. |

## Typical workflows

- **Go wireless:** plug the phone in over USB → *Wi-Fi ADB in one click* → unplug the cable.
- **Debug an app:** pick the minimum log level, type part of your package name in the keyword box, press *Start*, then *Export* when done.
- **Flash an update zip:** reboot to recovery, choose *Apply update from ADB* on the device, then use *Sideload ZIP*.

## Requirements

- Windows 10 or 11 (64-bit)
- An Android device with USB debugging enabled
- Internet access on first launch (to fetch adb, and scrcpy if you use mirroring)

## Run from source

Requires Python 3.10+ with Tkinter (included in the standard Windows installer).

```
git clone https://github.com/Swanboss01/AndroWake.git
cd AndroWake
python androwake.py
```

Build the executable and the installer (needs Pillow for the icon and [NSIS](https://nsis.sourceforge.io)):

```
python make_icon.py        # generates icon.ico
python build_exe.py        # dist/AndroWake/AndroWake.exe (PyInstaller)
makensis installer.nsi     # AndroWakeSetup.exe
```

## Project layout

| File | Role |
|---|---|
| `androwake.py` | Main window: device list, actions, logcat, theme |
| `tools.py` | App manager and remote control windows |
| `adb_client.py` | adb/fastboot wrapper, adb and scrcpy downloaders |
| `make_icon.py` | Generates `icon.ico` |
| `build_exe.py` | PyInstaller build script |
| `installer.nsi` | NSIS installer script |

## Warning

Reboot, uninstall, clear-data and sideload actions can be irreversible or leave a device unbootable. Use AndroWake on your own devices and at your own risk.

## Credits

AndroWake downloads Google's [Android platform-tools](https://developer.android.com/tools/releases/platform-tools) and Genymobile's [scrcpy](https://github.com/Genymobile/scrcpy) at runtime; both remain under their own licenses.
