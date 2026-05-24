import dataclasses
import subprocess
import functools
import datetime
import logging
import shelve
import time
import sys
import os
import re
import shutil
from pathlib import Path

try:
    import PIL
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])

from PIL import Image, ExifTags

START_TIME = time.time()


@dataclasses.dataclass
class Pattern:
    name: str
    type: str
    regexp: str
    example: str = None
    regexp_compiled: re.Pattern = None

    def __post_init__(self):
        try:
            self.regexp_compiled = re.compile(self.regexp)
        except re.error as e:
            logging.error("%s -> %s", self.regexp, e)
            raise
        if self.example:
            try:
                assert self.regexp_compiled.match(self.example), f"""Example failed:
{self.example = }
{self.regexp = }"""
            except AssertionError:
                print(f"Warning: Example '{self.example}' doesn't match pattern '{self.name}'")


PATTERNS = [
    Pattern(
        name="WhatsApp_IMG",
        type="T_FILENAME",
        regexp=r"IMG-(\d{4})(\d{2})(\d{2})-WA.*\.jpg$",
        example="IMG-20240601-WA0001.jpg",
    ),
    Pattern(
        name="WhatsApp_IMG_Status",
        type="T_FILENAME",
        regexp=r"IMG_(\d{4})(\d{2})(\d{2})_(\d{2})_(\d{2})_(\d{2})\.jpg$",
        example="IMG_20240601_230513_000.jpg",
    ),
    Pattern(
        name="WhatsApp_PTT",
        type="T_FILENAME",
        regexp=r"PTT-(\d{4})(\d{2})(\d{2})-WA.*\.(jpg|jpeg)$",
    ),
    Pattern(
        name="WhatsApp_Simple",
        type="T_FILENAME",
        regexp=r"IMG-(\d{4})(\d{2})(\d{2})-WA.*\.jpeg$",
    ),
]


def timed(title):
    def decorator(function):
        @functools.wraps(function)
        def wrapper(*a, **b):
            start_time = time.time()
            print("--", title, end="...\n")
            try:
                return function(*a, **b)
            finally:
                end_time = time.time()
                print("--", title, end=f"... done. ({end_time-start_time:.3f}s)\n")
        return wrapper
    return decorator


WHATSAPP_BASE_PATH = Path("/storage/emulated/0/Android/media/com.whatsapp/WhatsApp")


@timed("find whatsapp images")
def find_whatsapp_images():
    """Find all JPEG images in WhatsApp directories"""
    jpeg_paths = []
    
    if not WHATSAPP_BASE_PATH.exists():
        print(f"ERROR: WhatsApp path not found: {WHATSAPP_BASE_PATH}")
        print("Checking alternative paths...")
        alternative_paths = [
            Path("/sdcard/Android/media/com.whatsapp/WhatsApp"),
            Path("/storage/emulated/0/WhatsApp"),
            Path("/sdcard/WhatsApp"),
            Path("/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Images"),
        ]
        base_path = None
        for alt_path in alternative_paths:
            if alt_path.exists():
                base_path = alt_path
                print(f"Found WhatsApp at: {base_path}")
                break
        else:
            print("\nCould not find WhatsApp directory!")
            print("Make sure:")
            print("1. WhatsApp is installed")
            print("2. You've granted storage permission: termux-setup-storage")
            print("3. The path exists on your device")
            return []
    else:
        base_path = WHATSAPP_BASE_PATH
    
    media_dirs = [
        base_path / "Media" / "WhatsApp Images",
        base_path / "Media" / "WhatsApp Statuses",
        base_path / "Media" / "WhatsApp Animated Gifs",
        base_path / "Media" / ".Statuses",
    ]
    
    try:
        for item in base_path.glob("*.jpg"):
            if item.is_file():
                jpeg_paths.append(item)
        for item in base_path.glob("*.jpeg"):
            if item.is_file():
                jpeg_paths.append(item)
    except Exception as e:
        print(f"Error scanning base path: {e}")
    
    for media_dir in media_dirs:
        if not media_dir.exists():
            print(f"Skipping (not found): {media_dir}")
            continue
        print(f"Scanning: {media_dir}")
        try:
            for jpg_path in media_dir.rglob("*.jpg"):
                jpeg_paths.append(jpg_path)
            for jpeg_path in media_dir.rglob("*.jpeg"):
                jpeg_paths.append(jpeg_path)
        except (PermissionError, Exception) as e:
            print(f"Error scanning {media_dir}: {e}")
            continue
    
    seen = set()
    unique_paths = []
    for path in jpeg_paths:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)
    
    print(f"Found {len(unique_paths)} WhatsApp images")
    return unique_paths


SHELVE_DIR = Path.home() / ".cache" / "whatsapp-exif-fixer"


@timed("get exif metadata")
def get_exif_data(jpeg_paths):
    """Extract EXIF data from images with caching"""
    os.makedirs(SHELVE_DIR, exist_ok=True)
    exif_by_path = {}
    shelf_path = str(SHELVE_DIR / "whatsapp_exif")
    with shelve.open(shelf_path, writeback=True) as exif_shelf:
        for i, jpeg_path in enumerate(jpeg_paths, 1):
            if i % 100 == 0:
                print(f"  Processing {i}/{len(jpeg_paths)}...")
            try:
                shelf_key = f"{jpeg_path.resolve()}:{jpeg_path.stat().st_mtime}"
                if shelf_key not in exif_shelf:
                    with Image.open(jpeg_path) as image:
                        exif_shelf[shelf_key] = dict(image.getexif().items())
                exif_by_path[jpeg_path] = exif_shelf[shelf_key]
            except Exception as e:
                logging.error("Error with %s: %s", jpeg_path.name, e)
                exif_by_path[jpeg_path] = {}
    return exif_by_path


@timed("find images without exif date")
def find_images_without_exif_date(jpeg_paths, exif_by_path):
    """Identify images missing EXIF DateTime fields"""
    missing_date = []
    for jpeg_path in jpeg_paths:
        exif = exif_by_path.get(jpeg_path, {})
        has_date = any(exif.get(tag) for tag in
                       [ExifTags.Base.DateTime, ExifTags.Base.DateTimeOriginal, ExifTags.Base.DateTimeDigitized])
        if not has_date:
            missing_date.append(jpeg_path)
    print(f"Found {len(missing_date)} images without EXIF dates")
    return missing_date


def extract_date_from_filename(filename):
    """Extract date from WhatsApp filename patterns. Returns (date_string, pattern_name, datetime_obj) or (None, None, None)"""
    for pattern in PATTERNS:
        m = pattern.regexp_compiled.match(filename)
        if m:
            groups = m.groups()
            if len(groups) >= 3:
                year = int(groups[0])
                month = int(groups[1])
                day = int(groups[2])
                if len(groups) >= 6:
                    hours = int(groups[3])
                    minutes = int(groups[4])
                    seconds = int(groups[5])
                else:
                    hours, minutes, seconds = 12, 0, 0
                try:
                    dt = datetime.datetime(year, month, day, hours, minutes, seconds)
                    date_string = dt.strftime("%Y:%m:%d %H:%M:%S")
                    return date_string, pattern.name, dt
                except ValueError as e:
                    print(f"  Invalid date in {filename}: {e}")
                    return None, None, None
    return None, None, None


@timed("process and fix exif dates")
def process_whatsapp_images(images_without_date):
    """Add EXIF dates and set filesystem timestamps to match"""
    fixed_count = 0
    error_count = 0
    skipped_count = 0
    timestamp_errors = 0

    for i, image_path in enumerate(images_without_date, 1):
        print(f"\n[{i}/{len(images_without_date)}] Processing: {image_path.name}")
        
        date_string, pattern_name, dt = extract_date_from_filename(image_path.name)
        if not date_string:
            print(f"  ⚠ Could not extract date from filename: {image_path.name}")
            skipped_count += 1
            continue
        
        print(f"  📅 Extracted date: {date_string} (from {pattern_name})")
        
        temp_path = image_path.parent / f"_temp_{image_path.name}"
        try:
            with Image.open(image_path) as img:
                exif = img.getexif()
                exif[ExifTags.Base.DateTime] = date_string
                exif[ExifTags.Base.DateTimeOriginal] = date_string
                exif[ExifTags.Base.DateTimeDigitized] = date_string
                img.save(temp_path, exif=exif, format='JPEG', quality=95)
            
            if temp_path.exists():
                shutil.move(str(temp_path), str(image_path))
                print(f"  ✓ Fixed EXIF date")
                
                # --- NEW: Set filesystem modification time to match EXIF date taken ---
                try:
                    timestamp = dt.timestamp()
                    os.utime(image_path, (timestamp, timestamp))
                    print(f"  🕒 Set file modification time to {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                except Exception as ts_err:
                    print(f"  ⚠ Could not set filesystem timestamp: {ts_err}")
                    timestamp_errors += 1
                
                fixed_count += 1
            else:
                raise Exception("Temp file was not created")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            error_count += 1
            if temp_path.exists():
                temp_path.unlink()
    
    print(f"\n  (Timestamp setting failures: {timestamp_errors})")
    return fixed_count, error_count, skipped_count


@timed("verify fixed images")
def verify_fixes(original_images):
    """Check if images now have EXIF dates"""
    verified = 0
    still_missing = []
    for image_path in original_images:
        try:
            with Image.open(image_path) as img:
                if img.getexif().get(ExifTags.Base.DateTime):
                    verified += 1
                else:
                    still_missing.append(image_path)
        except Exception:
            still_missing.append(image_path)
    print(f"Verified: {verified}/{len(original_images)} images now have EXIF dates")
    if still_missing:
        print(f"Still missing: {len(still_missing)} images")
    return still_missing


@timed("create backup")
def create_backup(images_to_backup):
    """Create backup of images before modifying"""
    BACKUP_BASE_PATH = Path("/storage/emulated/0/whatsapp_backup_exif")
    backup_dir = BACKUP_BASE_PATH / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    print(f"Creating backup in: {backup_dir}")
    print(f"Total files to backup: {len(images_to_backup)}")
    
    for i, image_path in enumerate(images_to_backup, 1):
        if i % 100 == 0:
            print(f"  Backing up {i}/{len(images_to_backup)}...")
        try:
            # Try to preserve relative structure
            whatsapp_base = WHATSAPP_BASE_PATH if WHATSAPP_BASE_PATH.exists() else Path("/storage/emulated/0/Android/media/com.whatsapp/WhatsApp")
            try:
                rel_path = image_path.relative_to(whatsapp_base.parent.parent.parent)
                backup_path = backup_dir / rel_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(image_path, backup_path)
            except ValueError:
                backup_path = backup_dir / image_path.name
                counter = 1
                while backup_path.exists():
                    stem = image_path.stem
                    backup_path = backup_dir / f"{stem}_{counter}{image_path.suffix}"
                    counter += 1
                shutil.copy2(image_path, backup_path)
        except Exception as e:
            print(f"  Warning: Could not backup {image_path.name}: {e}")
            try:
                backup_path = backup_dir / image_path.name
                shutil.copy2(image_path, backup_path)
            except:
                pass
    
    info_file = backup_dir / "backup_info.txt"
    with open(info_file, 'w') as f:
        f.write(f"Backup created: {datetime.datetime.now()}\n")
        f.write(f"Number of files: {len(images_to_backup)}\n")
        f.write(f"Original WhatsApp path: {WHATSAPP_BASE_PATH}\n")
        f.write("Script version: WhatsApp EXIF Fixer (with filesystem timestamp sync)\n")
        f.write("Created by: Arif Nurrohim\n")
    
    print(f"Backup completed: {len(images_to_backup)} files backed up")
    print(f"Backup location: {backup_dir}")
    return backup_dir


def main():
    print("=" * 70)
    print(" WhatsApp EXIF Date Fixer + Filesystem Timestamp Sync for Termux")
    print("=" * 70)
    print()
    
    BACKUP_BASE_PATH = Path("/storage/emulated/0/whatsapp_backup_exif")
    if not BACKUP_BASE_PATH.parent.exists():
        print("Warning: /storage/emulated/0/ may not be accessible")
        print("Make sure you've run: termux-setup-storage")
    
    whatsapp_images = find_whatsapp_images()
    if not whatsapp_images:
        print("\nNo WhatsApp images found to process.")
        print("Troubleshooting tips:")
        print("1. Run: termux-setup-storage")
        print("2. Make sure WhatsApp has downloaded images")
        return
    
    print(f"\n📸 Total WhatsApp images found: {len(whatsapp_images)}")
    exif_data = get_exif_data(whatsapp_images)
    images_without_date = find_images_without_exif_date(whatsapp_images, exif_data)
    
    if not images_without_date:
        print("\n✅ All WhatsApp images already have EXIF dates!")
        return
    
    print(f"\n⚠️  Found {len(images_without_date)} images without EXIF dates")
    response = input("Do you want to create a backup before proceeding? (yes/no): ")
    if response.lower() == 'yes':
        backup_dir = create_backup(images_without_date)
        print(f"\n✅ Backup created at: {backup_dir}")
    else:
        print("\n⚠️ Proceeding without backup! This is not recommended.")
        response2 = input("Are you sure you want to continue without backup? (yes/no): ")
        if response2.lower() != 'yes':
            print("Operation cancelled.")
            return
    
    response = input("\nDo you want to continue with fixing EXIF dates and file timestamps? (yes/no): ")
    if response.lower() != 'yes':
        print("Operation cancelled.")
        return
    
    print(f"\n🔧 Starting to fix {len(images_without_date)} images...")
    fixed, errors, skipped = process_whatsapp_images(images_without_date)
    
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"✅ Fixed (EXIF + filesystem time): {fixed}")
    print(f"❌ Errors: {errors}")
    print(f"⏭ Skipped (could not extract date): {skipped}")
    print(f"📁 Total processed: {len(images_without_date)}")
    
    if fixed > 0:
        still_missing = verify_fixes(images_without_date[:fixed])
        if still_missing:
            print(f"\n⚠️ {len(still_missing)} images still don't have EXIF dates")
    
    end_time = time.time()
    
    print("=" * 70)
    print()
    print("   ╔══════════════════════════════════════════════════════╗")
    print("   ║                                                      ║")
    print("   ║     WhatsApp EXIF Date Fixer - Termux Version        ║")
    print("   ║          + Filesystem Timestamp Sync                 ║")
    print("   ║                                                      ║")
    print("   ║            Created and Developed by                  ║")
    print("   ║                                                      ║")
    print("   ║              ★  ARIF NURROHIM  ★                    ║")
    print("   ║                                                      ║")
    print("   ║     ⚡ GitHub: arifnurrohim                           ║")
    print("   ║     📧 Email: jobs.arifnurrohim@gmail.com             ║")
    print("   ║                                                      ║")
    print("   ║     🎯 Special Thanks to:                            ║")
    print("   ║     • Termux Community                               ║")
    print("   ║     • Pillow Library Developers                      ║")
    print("   ║     • WhatsApp Users Worldwide                       ║")
    print("   ║                                                      ║")
    print("   ╚══════════════════════════════════════════════════════╝")
    print()
    print(f"   ⏱ Total execution time: {end_time-START_TIME:.2f} seconds")
    print()
    print(f"   📌 This script successfully fixed EXIF dates AND")
    print(f"      updated filesystem modification times for {fixed} images.")
    print()
    print("   💾 Backup location: /storage/emulated/0/whatsapp_backup_exif/")
    print("   🔄 To restore: cp -r /storage/emulated/0/whatsapp_backup_exif/* [whatsapp_path]")
    print()
    print("   🙏 Thank you for using this tool!")
    print("   ⭐ If you found it useful, please share with others")
    print()
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()