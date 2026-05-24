# 📸 Sync Timestamps to Date Taken

A Python script that sets a file's **last modified** and **last accessed** timestamps to the actual date the photo was taken – using EXIF metadata or, as a fallback, WhatsApp‑style filename patterns.  
Perfect for organizing WhatsApp images that may have correct metadata but wrong filesystem dates.

## ✨ Features

- 🔍 Reads EXIF `DateTimeOriginal` or `DateTime` from JPEG images.
- 🧩 Fallback to parsing **WhatsApp filename patterns** (e.g., `IMG-20240601-WA0001.jpg`) if EXIF is missing.
- 🤖 **Auto‑detects** your WhatsApp media folder – no need to remember paths.
- 🧪 Dry‑run mode to preview changes.
- 🗂️ Process single files, folders, or entire directory trees recursively.
- ⚡ Works in **Termux** (Android) and any standard Python environment.

## 📦 Requirements

- Python 3.6+
- [Pillow](https://python-pillow.org/) (automatically installed if missing)

### For Android / Termux

After installing Termux, grant storage access:

```bash
termux-setup-storage