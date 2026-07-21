# Hardware Validation Tests

This directory contains manual Raspberry Pi hardware checks for the MedGate kiosk.

These scripts are not a pytest suite. Run each script directly and read its terminal output.

## Barcode Scanner

```bash
python3 "Unit Tests/BarcodeScanner_Tests/Test.py"
```

The test waits for a scan through standard input. The scanner must be configured as a USB keyboard and send Enter after the barcode.

## Touch Digitizer

```bash
python3 "Unit Tests/Display_Tests/test_display_touch.py"
```

Reads:

```text
/proc/bus/input/devices
```

and searches for touchscreen/digitizer signatures.

## Display Video Signal

```bash
python3 "Unit Tests/Display_Tests/test_display_video.py"
```

Checks the Linux DRM HDMI status and falls back to the framebuffer subsystem.

## Printer USB Connection

```bash
python3 "Unit Tests/Printer_Tests/test_printer_usb.py"
```

Runs `lsusb` and checks for a connected Brother device.

## CUPS Printer Queue

```bash
python3 "Unit Tests/Printer_Tests/test_printer_spooler.py"
```

Runs `lpstat -p` and verifies that a printer queue is enabled.

## Environment

The hardware tests are intended for Raspberry Pi OS or a compatible Linux system. Some tests will not work on Windows or macOS because they read Linux device paths or use Linux command-line utilities.
