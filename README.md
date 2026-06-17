# WhatsApp EXIF Date Fixer for Termux

> Fix missing EXIF dates on WhatsApp images and sync filesystem timestamps on Android via Termux

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Termux-important.svg)](https://termux.com)

## 📋 Overview

This script automatically detects WhatsApp images without proper EXIF date metadata, extracts the date from the filename pattern, and adds it to the image metadata. It also **synchronizes the filesystem modification time** to match the photo's actual capture date—perfect for organizing WhatsApp media in your gallery.

### Key Features

- 📸 **Detects WhatsApp images** across multiple directories
- 🕵️ **Extracts dates** from various WhatsApp filename patterns
- ✏️ **Adds EXIF metadata** (DateTime, DateTimeOriginal, DateTimeDigitized)
- 🕒 **Syncs filesystem timestamps** to match the capture date
- 💾 **Creates automatic backups** before making changes
- ✅ **Verifies fixes** with detailed reporting
- 🚀 **Optimized for Termux** on Android

## 📱 Supported Filename Patterns

| Pattern | Example | Description |
|---------|---------|-------------|
| `IMG-YYYYMMDD-WA*.jpg` | `IMG-20240601-WA0001.jpg` | Standard WhatsApp images |
| `IMG_YYYYMMDD_HHMMSS*.jpg` | `IMG_20240601_230513_000.jpg` | WhatsApp status images |
| `PTT-YYYYMMDD-WA*.jpg` | `PTT-20240601-WA0001.jpg` | WhatsApp PTT media |
| `IMG-YYYYMMDD-WA*.jpeg` | `IMG-20240601-WA0001.jpeg` | JPEG format images |

## 🚀 Quick Start

### Prerequisites

1. **Install Termux** from [F-Droid](https://f-droid.org/en/packages/com.termux/) or [Google Play](https://play.google.com/store/apps/details?id=com.termux)
2. **Grant storage permissions**:
   ```bash
   termux-setup-storage
   ```

### Installation

```bash
# Update packages
pkg update && pkg upgrade

# Install Python
pkg install python

# Download the script
curl -O https://raw.githubusercontent.com/arifnurrohim/whatsapp-exif-fixer/main/fix_whatsapp_date_create_and_modification.py

# Or use wget
wget https://raw.githubusercontent.com/arifnurrohim/whatsapp-exif-fixer/main/fix_whatsapp_date_create_and_modification.py

# Run the script
python fix_whatsapp_date_create_and_modification.py
```

The script will automatically install required dependencies (Pillow library).

## 📖 Usage Guide

### Interactive Mode

Run the script and follow the prompts:

```bash
python fix_whatsapp_date_create_and_modification.py
```

```
======================================================================
 WhatsApp EXIF Date Fixer + Filesystem Timestamp Sync for Termux
======================================================================

📸 Total WhatsApp images found: 1542
⚠️  Found 342 images without EXIF dates
Do you want to create a backup before proceeding? (yes/no): yes

🔧 Starting to fix 342 images...

📊 SUMMARY
======================================================================
✅ Fixed (EXIF + filesystem time): 342
❌ Errors: 0
⏭ Skipped (could not extract date): 0
📁 Total processed: 342
```

### What Happens

1. **Scan**: Finds all JPEG images in WhatsApp directories
2. **Analyze**: Checks which images lack EXIF date metadata
3. **Backup**: Creates a backup (optional but recommended)
4. **Fix**: For each image:
   - Extracts date from filename
   - Adds EXIF date tags
   - Updates filesystem modification time
5. **Verify**: Confirms the fixes were applied

## 📂 Backup Location

Backups are stored at:
```
/storage/emulated/0/whatsapp_backup_exif/
├── YYYYMMDD_HHMMSS/
│   ├── [preserved directory structure]
│   ├── backup_info.txt
│   └── [all backed up images]
```

### Restoring from Backup

```bash
# Copy all files back
cp -r /storage/emulated/0/whatsapp_backup_exif/YYYYMMDD_HHMMSS/* /storage/emulated/0/Android/media/com.whatsapp/WhatsApp/

# Or restore specific files
cp /storage/emulated/0/whatsapp_backup_exif/YYYYMMDD_HHMMSS/image.jpg /storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp\ Images/
```

## 🛠️ Technical Details

### What the Script Does

1. **Detects WhatsApp Images**
   - Scans directories: `WhatsApp Images`, `WhatsApp Statuses`, `WhatsApp Animated Gifs`
   - Handles both `.jpg` and `.jpeg` extensions

2. **Extracts EXIF Data**
   - Uses `Pillow` library with caching for performance
   - Caches EXIF data in `~/.cache/whatsapp-exif-fixer/`

3. **Identifies Missing Dates**
   - Checks for `DateTime`, `DateTimeOriginal`, `DateTimeDigitized` tags

4. **Extracts Date from Filename**
   - Uses regex patterns to parse WhatsApp filename formats
   - Defaults to 12:00:00 when time not present in filename

5. **Adds EXIF Metadata**
   - Updates all three datetime tags
   - Saves with quality=95 to preserve image quality

6. **Syncs Filesystem Timestamp**
   - Uses `os.utime()` to set modification time
   - Ensures gallery apps sort by correct date

## ❗ Troubleshooting

### "WhatsApp path not found"

```
ERROR: WhatsApp path not found: /storage/emulated/0/Android/media/com.whatsapp/WhatsApp
```

**Solutions:**
1. Grant storage permissions: `termux-setup-storage`
2. Check if WhatsApp is installed
3. Verify the path exists: `ls /storage/emulated/0/Android/media/com.whatsapp/WhatsApp/`

### "Permission denied"

```
Error scanning /storage/emulated/0/Android/media/com.whatsapp/WhatsApp: Permission denied
```

**Solutions:**
1. Run `termux-setup-storage` again
2. Ensure Termux has storage permissions in Android Settings
3. Try restarting Termux

### "No WhatsApp images found"

**Solutions:**
1. Make sure WhatsApp has downloaded/sent images
2. Check the alternative paths the script tries:
   - `/sdcard/Android/media/com.whatsapp/WhatsApp`
   - `/storage/emulated/0/WhatsApp`
   - `/sdcard/WhatsApp`

## 🔧 Advanced Usage

### Run Non-Interactively (For Automation)

```bash
# With automatic backup
echo "yes\nyes" | python fix_whatsapp_date_create_and_modification.py

# Without backup (not recommended)
echo "no\nyes\nyes" | python fix_whatsapp_date_create_and_modification.py
```

### Clear Cache

```bash
rm -rf ~/.cache/whatsapp-exif-fixer/
```

### Process Only Specific Directory

You can modify the script by changing `WHATSAPP_BASE_PATH`:

```python
# In the script, change this line:
WHATSAPP_BASE_PATH = Path("/storage/emulated/0/Android/media/com.whatsapp/WhatsApp")

# To process a different location:
WHATSAPP_BASE_PATH = Path("/sdcard/WhatsApp")
```

## 📊 Performance

The script includes:
- **Caching**: EXIF data is cached to avoid re-processing
- **Progress Indicators**: Shows progress every 100 files
- **Benchmarking**: Displays execution time for each step
- **Error Handling**: Continues even if individual files fail

## 👨‍💻 Developer

**Created and developed by:**

```
★ ARIF NURROHIM ★
```

- **GitHub**: [arifnurrohim](https://github.com/arifnurrohim)
- **Email**: jobs.arifnurrohim@gmail.com

### Special Thanks

- Termux Community for the amazing Android terminal
- Pillow Library Developers for EXIF handling
- WhatsApp Users Worldwide for testing and feedback

## 📝 License

This project is open source and available under the MIT License.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

### Feature Ideas

- [ ] Support for video files
- [ ] GUI version for Android
- [ ] Cloud backup support
- [ ] Bulk rename based on EXIF dates

---

## ❓ FAQ

**Q: Does this work on non-rooted Android devices?**  
A: Yes! This works perfectly on non-rooted devices through Termux.

**Q: Will this reduce image quality?**  
A: No, the script preserves image quality by using quality=95 when saving.

**Q: Can I process images on external SD card?**  
A: Yes, modify the `WHATSAPP_BASE_PATH` to point to your SD card location.

**Q: What if the script fails halfway?**  
A: Restart the script—it will skip already fixed images.

**Q: How long does it take?**  
A: Approximately 100-200 images per minute on modern devices.

---

## 📸 Screenshots

### Before
```
IMG-20240601-WA0001.jpg
- EXIF DateTime: None
- File modified: 2024-06-15 14:30:22
```

### After
```
IMG-20240601-WA0001.jpg
- EXIF DateTime: 2024:06:01 12:00:00
- File modified: 2024-06-01 12:00:00
```

---

## 🌟 Star History

If you find this tool useful, please give it a star ⭐ on GitHub!

[![Star History Chart](https://api.star-history.com/svg?repos=arifnurrohim/whatsapp-exif-fixer&type=Date)](https://star-history.com/#arifnurrohim/whatsapp-exif-fixer&Date)

---

**Made with ❤️ for the WhatsApp and Termux community**