# ============================================================
# V16.3 ANTIVIRUS PRO — APK READY
# PART 1/4
# Android + Kivy + Buildozer
# ============================================================

import os
import json
import time
import hashlib
import shutil
import threading

from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp

from kivy.graphics import (
    Color,
    Line,
    Ellipse,
    RoundedRectangle
)

from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup


# ============================================================
# 1. ANDROID SUPPORT
# ============================================================

ANDROID = False

try:
    from android.permissions import (
        request_permissions,
        Permission
    )

    ANDROID = True

except Exception:
    ANDROID = False


# ============================================================
# 2. OPTIONAL NOTIFICATION
# ============================================================

try:
    from plyer import notification
except Exception:
    notification = None


# ============================================================
# 3. APPLICATION CONFIGURATION
# ============================================================

APP_NAME = "V16 ANTIVIRUS"
VERSION = "V16.3"

BRAND = "King"
BRAND_NAME = "Taj"

HASH_CHUNK = 1024 * 1024

MONITOR_SECONDS = 8

MAX_HISTORY = 250

MAX_MONITOR_NEW_FILES_PER_CYCLE = 20


# ============================================================
# 4. VERIFIED MALWARE DATABASE
# ============================================================

# এখানে শুধুমাত্র সত্যিকারভাবে যাচাই করা
# SHA-256 IOC hash রাখতে হবে।
#
# উদাহরণ:
#
# VERIFIED_MALWARE_SHA256 = {
#     "0123456789abcdef..."
# }

VERIFIED_MALWARE_SHA256 = set()


# ============================================================
# 5. APPLICATION DATA DIRECTORY
# ============================================================

BASE_DIR = Path.home() / ".v16_antivirus"

HISTORY_FILE = (
    BASE_DIR / "scan_history.json"
)

CACHE_FILE = (
    BASE_DIR / "file_cache.json"
)

QUARANTINE_DIR = (
    BASE_DIR / "quarantine"
)


# ============================================================
# 6. CREATE DIRECTORIES
# ============================================================

try:
    BASE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    QUARANTINE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

except Exception:
    pass


# ============================================================
# 7. SYSTEM PATHS TO SKIP
# ============================================================

SKIP_PREFIXES = (
    "/proc",
    "/sys",
    "/dev",
)


# ============================================================
# 8. PROFESSIONAL COLORS
# ============================================================

BG = (
    0.008,
    0.025,
    0.045,
    1
)

PANEL = (
    0.018,
    0.055,
    0.085,
    1
)

PANEL_2 = (
    0.025,
    0.070,
    0.105,
    1
)

GREEN = (
    0.10,
    1.00,
    0.28,
    1
)

CYAN = (
    0.00,
    0.82,
    1.00,
    1
)

PURPLE = (
    0.55,
    0.30,
    1.00,
    1
)

YELLOW = (
    1.00,
    0.72,
    0.05,
    1
)

RED = (
    1.00,
    0.12,
    0.15,
    1
)

WHITE = (
    0.94,
    0.97,
    1.00,
    1
)

MUTED = (
    0.55,
    0.65,
    0.72,
    1
)

BORDER = (
    0.08,
    0.24,
    0.34,
    1
)


# ============================================================
# 9. SAFE JSON FUNCTIONS
# ============================================================

def load_json(path, default):

    try:

        if path.exists():

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

                return data

    except Exception:
        pass

    return default


def save_json(path, data):

    temp_path = Path(
        str(path) + ".tmp"
    )

    try:

        with open(
            temp_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            temp_path,
            path
        )

        return True

    except Exception:

        try:

            if temp_path.exists():
                temp_path.unlink()

        except Exception:
            pass

        return False


# ============================================================
# 10. TIME
# ============================================================

def now_text():

    return time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# 11. ANDROID NOTIFICATION
# ============================================================

def notify_user(
    title,
    message
):

    if notification is None:
        return

    try:

        notification.notify(
            title=title,
            message=message,
            app_name=APP_NAME,
            timeout=5
        )

    except Exception:
        pass


# ============================================================
# 12. ANDROID PERMISSIONS
# ============================================================

def request_android_permissions():

    if not ANDROID:
        return

    try:

        permissions = []

        for name in (
            "READ_EXTERNAL_STORAGE",
            "WRITE_EXTERNAL_STORAGE"
        ):

            value = getattr(
                Permission,
                name,
                None
            )

            if value:
                permissions.append(value)

        if permissions:

            request_permissions(
                permissions
            )

    except Exception:
        pass


# ============================================================
# 13. SCAN ROOTS
# ============================================================

def scan_roots():

    candidates = [

        "/storage/emulated/0",

        "/sdcard",

        str(Path.home())

    ]

    result = []

    for path in candidates:

        try:

            if (
                os.path.isdir(path)
                and os.access(path, os.R_OK)
            ):

                path = os.path.abspath(path)

                if path not in result:
                    result.append(path)

        except Exception:
            pass

    return result


# ============================================================
# 14. SKIP PROTECTED PATH
# ============================================================

def should_skip(path):

    try:

        path = os.path.abspath(path)

    except Exception:

        return True

    try:

        quarantine_path = os.path.abspath(
            str(QUARANTINE_DIR)
        )

        if (
            path == quarantine_path
            or path.startswith(
                quarantine_path + os.sep
            )
        ):

            return True

    except Exception:
        pass

    for prefix in SKIP_PREFIXES:

        if (
            path == prefix
            or path.startswith(
                prefix + os.sep
            )
        ):

            return True

    return False


# ============================================================
# 15. SAFE FILE ITERATOR
# ============================================================

def iter_files(root):

    try:

        for current, dirs, names in os.walk(
            root,
            topdown=True,
            onerror=lambda _error: None,
            followlinks=False
        ):

            if should_skip(current):

                dirs[:] = []

                continue

            safe_dirs = []

            for directory in dirs:

                full_path = os.path.join(
                    current,
                    directory
                )

                if not should_skip(full_path):

                    safe_dirs.append(
                        directory
                    )

            dirs[:] = safe_dirs

            for name in names:

                path = os.path.join(
                    current,
                    name
                )

                try:

                    if (
                        os.path.isfile(path)
                        and os.access(
                            path,
                            os.R_OK
                        )
                        and not should_skip(path)
                    ):

                        yield path

                except (
                    OSError,
                    PermissionError
                ):

                    continue

    except (
        OSError,
        PermissionError
    ):

        return
# ============================================================
# V16.3 PART 1 শেষ
# =========================================================
# ============================================================
# V16.3 ANTIVIRUS PRO — APK READY
# PART 2/4
# SHA-256 + IOC + QUARANTINE + HISTORY
# ============================================================


# ============================================================
# 16. SHA-256 FILE HASH
# ============================================================

def sha256_file(path):

    digest = hashlib.sha256()

    with open(
        path,
        "rb"
    ) as file:

        while True:

            chunk = file.read(
                HASH_CHUNK
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


# ============================================================
# 17. EXACT IOC MATCH
# ============================================================

def exact_ioc_match(file_hash):

    if not file_hash:
        return False

    return (
        file_hash.lower()
        in VERIFIED_MALWARE_SHA256
    )


# ============================================================
# 18. SINGLE FILE SCANNER
# ============================================================

def scan_one_file(path):

    result = {

        "time": now_text(),

        "path": path,

        "name": os.path.basename(path),

        "size": 0,

        "sha256": "",

        "verdict": "ERROR",

        "quarantined": False

    }

    try:

        result["size"] = os.path.getsize(
            path
        )

        result["sha256"] = sha256_file(
            path
        )

        if exact_ioc_match(
            result["sha256"]
        ):

            result["verdict"] = (
                "CONFIRMED_MALWARE"
            )

        else:

            result["verdict"] = (
                "NO_VERIFIED_MALWARE"
            )

    except (
        OSError,
        PermissionError
    ) as error:

        result["error"] = str(error)

    except Exception as error:

        result["error"] = str(error)

    return result


# ============================================================
# 19. QUARANTINE
# ============================================================

def quarantine(result):

    # শুধুমাত্র exact verified SHA-256 match
    # হলে quarantine করা যাবে।

    if (
        result.get("verdict")
        != "CONFIRMED_MALWARE"
    ):

        return False

    source = result.get("path")

    try:

        if (
            not source
            or not os.path.isfile(source)
        ):

            return False

        timestamp = time.strftime(
            "%Y%m%d_%H%M%S"
        )

        original_name = os.path.basename(
            source
        )

        target = (
            QUARANTINE_DIR
            / f"{timestamp}_{original_name}.quarantined"
        )

        shutil.move(
            source,
            str(target)
        )

        result["quarantined"] = True

        result["quarantine_path"] = (
            str(target)
        )

        return True

    except Exception as error:

        result["quarantine_error"] = (
            str(error)
        )

        return False


# ============================================================
# 20. HISTORY ADD
# ============================================================

def add_history(result):

    history = load_json(
        HISTORY_FILE,
        []
    )

    if not isinstance(
        history,
        list
    ):

        history = []

    history.insert(
        0,
        result
    )

    save_json(
        HISTORY_FILE,
        history[:MAX_HISTORY]
    )


# ============================================================
# 21. GET HISTORY
# ============================================================

def get_history():

    history = load_json(
        HISTORY_FILE,
        []
    )

    if isinstance(
        history,
        list
    ):

        return history

    return []


# ============================================================
# 22. FILE SIGNATURE
# ============================================================

def file_signature(path):

    try:

        stat = os.stat(path)

        return [
            stat.st_size,
            stat.st_mtime_ns
        ]

    except (
        OSError,
        PermissionError
    ):

        return None


# ============================================================
# 23. MONITOR CACHE
# ============================================================

def load_cache():

    cache = load_json(
        CACHE_FILE,
        {}
    )

    if isinstance(
        cache,
        dict
    ):

        return cache

    return {}


# ============================================================
# 24. SAVE MONITOR CACHE
# ============================================================

def save_cache(cache):

    # Cache সীমিত রাখা হচ্ছে,
    # যাতে দীর্ঘদিন ব্যবহারে storage
    # অযথা বড় না হয়।

    if len(cache) > 15000:

        items = list(
            cache.items()
        )[-10000:]

        cache = dict(items)

    save_json(
        CACHE_FILE,
        cache
    )


# ============================================================
# 25. SECURITY GAUGE
# ============================================================

class SecurityGauge(Widget):

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.value = 0

        self.status = "Safe"

        self.bind(
            pos=self.redraw,
            size=self.redraw
        )

    # --------------------------------------------------------
    # Set Gauge Value
    # --------------------------------------------------------

    def set_value(
        self,
        value,
        status=None
    ):

        self.value = max(
            0,
            min(
                100,
                int(value)
            )
        )

        if status is not None:

            self.status = status

        self.redraw()

    # --------------------------------------------------------
    # Draw Gauge
    # --------------------------------------------------------

    def redraw(self, *_):

        self.canvas.clear()

        width, height = self.size

        center_x = (
            self.x + width / 2
        )

        center_y = (
            self.y + height * 0.42
        )

        radius = min(
            width * 0.43,
            height * 0.78
        )

        if radius <= 1:
            return

        # Background ring
        Color(
            0.02,
            0.15,
            0.19,
            1
        )

        Line(
            circle=(
                center_x,
                center_y,
                radius
            ),
            width=dp(16),
            segments=64,
            angle_start=200,
            angle_end=340
        )

        # Main security arc
        if self.value >= 80:

            Color(*GREEN)

        elif self.value >= 50:

            Color(*YELLOW)

        else:

            Color(*RED)

        end_angle = (
            200
            + (
                140
                * self.value
                / 100.0
            )
        )

        Line(
            circle=(
                center_x,
                center_y,
                radius
            ),
            width=dp(7),
            segments=64,
            angle_start=200,
            angle_end=end_angle
        )

        # Tick marks
        import math

        for i in range(21):

            angle = (
                200
                + (
                    140
                    * i
                    / 20.0
                )
            )

            radians = math.radians(
                angle
            )

            r1 = (
                radius
                - dp(8)
            )

            r2 = (
                radius
                - dp(22)
            )

            x1 = (
                center_x
                + r1
                * math.cos(radians)
            )

            y1 = (
                center_y
                + r1
                * math.sin(radians)
            )

            x2 = (
                center_x
                + r2
                * math.cos(radians)
            )

            y2 = (
                center_y
                + r2
                * math.sin(radians)
            )

            if i < 16:

                Color(*GREEN)

            elif i < 19:

                Color(*YELLOW)

            else:

                Color(*RED)

            Line(
                points=[
                    x1,
                    y1,
                    x2,
                    y2
                ],
                width=dp(1.3)
            )

        # Needle
        angle = (
            200
            + (
                140
                * self.value
                / 100.0
            )
        )

        radians = math.radians(
            angle
        )

        needle_x = (
            center_x
            + (
                radius
                - dp(35)
            )
            * math.cos(radians)
        )

        needle_y = (
            center_y
            + (
                radius
                - dp(35)
            )
            * math.sin(radians)
        )

        if self.value >= 80:

            Color(*GREEN)

        elif self.value >= 50:

            Color(*YELLOW)

        else:

            Color(*RED)

        Line(
            points=[
                center_x,
                center_y,
                needle_x,
                needle_y
            ],
            width=dp(4)
        )

        # Center dot
        Color(*WHITE)

        Ellipse(
            pos=(
                center_x - dp(5),
                center_y - dp(5)
            ),
            size=(
                dp(10),
                dp(10)
            )
        )


# ============================================================
# 26. PART 2 শেষ
# ============================================================
# ============================================================
# V16.3 ANTIVIRUS PRO — APK READY
# PART 3/4
# PROFESSIONAL UI + FULL SCANNER
# ============================================================


# ============================================================
# 27. PROFESSIONAL PANEL
# ============================================================

class Panel(BoxLayout):

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        with self.canvas.before:

            Color(*PANEL)

            self.background = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(16)]
            )

        self.bind(
            pos=self.update_background,
            size=self.update_background
        )

    def update_background(self, *_):

        self.background.pos = self.pos

        self.background.size = self.size


# ============================================================
# 28. ACTION BUTTON
# ============================================================

class ActionButton(Button):

    def __init__(
        self,
        accent=GREEN,
        **kwargs
    ):

        super().__init__(**kwargs)

        self.accent = accent

        self.background_normal = ""

        self.background_down = ""

        self.background_color = (
            0,
            0,
            0,
            0
        )

        self.color = WHITE

        self.font_size = dp(18)

        with self.canvas.before:

            Color(*accent)

            self.background = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(15)]
            )

        self.bind(
            pos=self.update_button,
            size=self.update_button
        )

    def update_button(self, *_):

        self.background.pos = self.pos

        self.background.size = self.size


# ============================================================
# 29. STATUS CARD
# ============================================================

class StatusCard(Panel):

    def __init__(
        self,
        title,
        value="ON",
        accent=GREEN,
        **kwargs
    ):

        super().__init__(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(2),
            **kwargs
        )

        self.title_label = Label(
            text=title,
            color=WHITE,
            font_size=dp(12),
            halign="center",
            valign="middle"
        )

        self.value_label = Label(
            text=value,
            color=accent,
            font_size=dp(13),
            halign="center",
            valign="middle"
        )

        self.add_widget(
            self.title_label
        )

        self.add_widget(
            self.value_label
        )

    def set_value(
        self,
        value,
        accent=GREEN
    ):

        self.value_label.text = value

        self.value_label.color = accent


# ============================================================
# 30. MAIN ANTIVIRUS SCREEN
# ============================================================

class AntivirusScreen(BoxLayout):

    def __init__(self, **kwargs):

        super().__init__(
            orientation="vertical",
            spacing=dp(8),
            padding=(
                dp(12),
                dp(8),
                dp(12),
                dp(8)
            ),
            **kwargs
        )

        self.scanning = False

        self.monitor_busy = False

        self.scan_start = 0

        self.scanned_files = 0

        self.threats = 0

        self.last_scan_seconds = 0

        self.monitor_cache = load_cache()

        self.build_ui()

        Clock.schedule_interval(
            self.monitor_tick,
            MONITOR_SECONDS
        )

    # ========================================================
    # 31. LABEL HELPER
    # ========================================================

    def label(
        self,
        text="",
        size=14,
        color=WHITE,
        **kwargs
    ):

        return Label(
            text=text,
            color=color,
            font_size=dp(size),
            **kwargs
        )

    # ========================================================
    # 32. BUILD UI
    # ========================================================

    def build_ui(self):

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(58)
        )

        menu = self.label(
            "☰",
            28,
            WHITE,
            size_hint_x=None,
            width=dp(42)
        )

        brand = self.label(
            "King  ♛  Taj",
            27,
            WHITE
        )

        status_dot = self.label(
            "●",
            22,
            GREEN,
            size_hint_x=None,
            width=dp(42)
        )

        header.add_widget(menu)

        header.add_widget(brand)

        header.add_widget(status_dot)

        self.add_widget(header)

        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        title_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(70)
        )

        title_box = BoxLayout(
            orientation="vertical"
        )

        title_box.add_widget(
            self.label(
                "V16 ANTIVIRUS",
                25,
                WHITE
            )
        )

        title_box.add_widget(
            self.label(
                "Adaptive Security Intelligence",
                13,
                MUTED
            )
        )

        device_panel = Panel(
            orientation="vertical",
            padding=dp(6),
            spacing=dp(1),
            size_hint_x=None,
            width=dp(150)
        )

        self.device_status = self.label(
            "SECURE",
            16,
            GREEN
        )

        self.device_threat = self.label(
            "No Threats Found",
            11,
            MUTED
        )

        device_panel.add_widget(
            self.device_status
        )

        device_panel.add_widget(
            self.device_threat
        )

        title_row.add_widget(
            title_box
        )

        title_row.add_widget(
            device_panel
        )

        self.add_widget(
            title_row
        )

        # ----------------------------------------------------
        # SECURITY GAUGE
        # ----------------------------------------------------

        gauge_area = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(300)
        )

        gauge_box = BoxLayout(
            orientation="vertical"
        )

        self.gauge = SecurityGauge(
            size_hint_y=None,
            height=dp(230)
        )

        gauge_box.add_widget(
            self.gauge
        )

        self.percent_label = self.label(
            "0%",
            46,
            WHITE,
            size_hint_y=None,
            height=dp(58)
        )

        self.health_label = self.label(
            "SYSTEM HEALTH",
            14,
            GREEN,
            size_hint_y=None,
            height=dp(25)
        )

        self.safe_label = self.label(
            "Safe",
            16,
            GREEN,
            size_hint_y=None,
            height=dp(32)
        )

        gauge_box.add_widget(
            self.percent_label
        )

        gauge_box.add_widget(
            self.health_label
        )

        gauge_box.add_widget(
            self.safe_label
        )

        gauge_area.add_widget(
            gauge_box
        )

        self.add_widget(
            gauge_area
        )

        # ----------------------------------------------------
        # SCAN BUTTON
        # ----------------------------------------------------

        self.scan_button = ActionButton(
            text=(
                "SCAN DEVICE\n"
                "Full System Scan"
            ),
            accent=GREEN,
            size_hint_y=None,
            height=dp(68)
        )

        self.scan_button.bind(
            on_press=self.start_full_scan
        )

        self.add_widget(
            self.scan_button
        )

        # ----------------------------------------------------
        # STATUS CARDS
        # ----------------------------------------------------

        cards = GridLayout(
            cols=4,
            spacing=dp(6),
            size_hint_y=None,
            height=dp(92)
        )

        self.rt_card = StatusCard(
            "Real-time\nProtection",
            "ON",
            GREEN
        )

        self.auto_card = StatusCard(
            "Auto Scan\nNew Files",
            "ON",
            GREEN
        )

        self.intel_card = StatusCard(
            "Threat\nIntelligence",
            "READY",
            CYAN
        )

        self.privacy_card = StatusCard(
            "Privacy\nProtected",
            "ON",
            GREEN
        )

        for card in (
            self.rt_card,
            self.auto_card,
            self.intel_card,
            self.privacy_card
        ):

            cards.add_widget(card)

        self.add_widget(
            cards
        )

        # ----------------------------------------------------
        # LAST SCAN RESULT
        # ----------------------------------------------------

        last_panel = Panel(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(88),
            padding=dp(10),
            spacing=dp(6)
        )

        last_panel.add_widget(
            self.label(
                "LAST SCAN\nRESULT",
                13,
                MUTED
            )
        )

        self.last_result = self.label(
            "No Scan Yet",
            13,
            GREEN
        )

        self.files_label = self.label(
            "Files Scanned\n0",
            13,
            CYAN
        )

        self.time_label = self.label(
            "Scan Time\n--:--",
            13,
            YELLOW
        )

        last_panel.add_widget(
            self.last_result
        )

        last_panel.add_widget(
            self.files_label
        )

        last_panel.add_widget(
            self.time_label
        )

        self.add_widget(
            last_panel
        )

        # ----------------------------------------------------
        # HISTORY BUTTON
        # ----------------------------------------------------

        self.history_button = ActionButton(
            text="▣  VIEW HISTORY   ›",
            accent=PURPLE,
            size_hint_y=None,
            height=dp(58)
        )

        self.history_button.bind(
            on_press=self.show_history
        )

        self.add_widget(
            self.history_button
        )

        # ----------------------------------------------------
        # LIVE PROTECTION
        # ----------------------------------------------------

        live_panel = Panel(
            orientation="vertical",
            padding=dp(10),
            size_hint_y=None,
            height=dp(112)
        )

        self.live_title = self.label(
            "REAL-TIME PROTECTION",
            13,
            GREEN,
            size_hint_y=None,
            height=dp(26)
        )

        self.live_event = self.label(
            "✓ Protection active\n"
            "Waiting for new or changed files...",
            13,
            WHITE
        )

        live_panel.add_widget(
            self.live_title
        )

        live_panel.add_widget(
            self.live_event
        )

        self.add_widget(
            live_panel
        )

        # ----------------------------------------------------
        # NAVIGATION
        # ----------------------------------------------------

        nav = BoxLayout(
            spacing=dp(4),
            size_hint_y=None,
            height=dp(58)
        )

        navigation = (
            ("HOME", self.home),
            ("SCAN", self.start_full_scan),
            (
                "HISTORY",
                self.show_history
            ),
            (
                "QUARANTINE",
                self.show_quarantine
            ),
            (
                "SETTINGS",
                self.show_info
            )
        )

        for name, callback in navigation:

            button = Button(
                text=name,
                font_size=dp(11),
                color=WHITE,
                background_normal="",
                background_color=(
                    0.02,
                    0.06,
                    0.09,
                    1
                )
            )

            button.bind(
                on_press=callback
            )

            nav.add_widget(
                button
            )

        self.add_widget(
            nav
        )

    # ========================================================
    # 33. START FULL SCAN
    # ========================================================

    def start_full_scan(self, *_):

        if self.scanning:
            return

        request_android_permissions()

        roots = scan_roots()

        if not roots:

            self.show_scan_error(
                "No readable storage location was found."
            )

            return

        self.scanning = True

        self.scan_start = time.time()

        self.scanned_files = 0

        self.threats = 0

        self.scan_button.disabled = True

        self.scan_button.text = (
            "SCANNING...\n"
            "Please wait"
        )

        self.gauge.set_value(
            0,
            "Scanning"
        )

        self.percent_label.text = "0%"

        self.health_label.text = (
            "SYSTEM HEALTH"
        )

        self.safe_label.text = (
            "Scanning..."
        )

        self.safe_label.color = YELLOW

        self.device_status.text = (
            "SCANNING"
        )

        self.device_status.color = YELLOW

        self.device_threat.text = (
            "Security scan running"
        )

        self.last_result.text = (
            "Scanning..."
        )

        self.last_result.color = YELLOW

        self.files_label.text = (
            "Files Scanned\n0"
        )

        self.time_label.text = (
            "Scan Time\n00:00"
        )

        self.live_event.text = (
            "Scanning accessible storage..."
        )

        self.live_event.color = YELLOW

        thread = threading.Thread(
            target=self.scan_worker,
            args=(roots,),
            daemon=True
        )

        thread.start()

    # ========================================================
    # 34. SCAN WORKER
    # ========================================================

    def scan_worker(self, roots):

        try:

            files = []

            for root in roots:

                for path in iter_files(root):

                    files.append(path)

            total = max(
                1,
                len(files)
            )

            for index, path in enumerate(
                files,
                1
            ):

                if not self.scanning:
                    break

                result = scan_one_file(
                    path
                )

                self.scanned_files = index

                if (
                    result["verdict"]
                    == "CONFIRMED_MALWARE"
                ):

                    self.threats += 1

                    quarantine(
                        result
                    )

                add_history(
                    result
                )

                progress = int(
                    index
                    * 100
                    / total
                )

                Clock.schedule_once(
                    lambda dt,
                    r=result,
                    p=progress:
                    self.scan_ui_update(
                        r,
                        p
                    )
                )

            elapsed = (
                time.time()
                - self.scan_start
            )

            Clock.schedule_once(
                lambda dt,
                e=elapsed:
                self.finish_scan(e)
            )

        except Exception as error:

            Clock.schedule_once(
                lambda dt,
                message=str(error):
                self.show_scan_error(
                    message
                )
            )

    # ========================================================
    # 35. SCAN UI UPDATE
    # ========================================================

    def scan_ui_update(
        self,
        result,
        progress
    ):

        threat = (
            result.get("verdict")
            == "CONFIRMED_MALWARE"
        )

        self.gauge.set_value(
            progress,
            "Threat Found"
            if threat
            else "Scanning"
        )

        self.percent_label.text = (
            f"{progress}%"
        )

        self.files_label.text = (
            "Files Scanned\n"
            f"{self.scanned_files:,}"
        )

        if threat:

            self.safe_label.text = (
                "Threat Found"
            )

            self.safe_label.color = RED

            self.device_status.text = (
                "THREAT"
            )

            self.device_status.color = RED

            self.device_threat.text = (
                f"{self.threats} confirmed"
            )

            self.last_result.text = (
                "CONFIRMED MALWARE\n"
                + result.get(
                    "name",
                    "Unknown"
                )
            )

            self.last_result.color = RED

            self.live_event.text = (
                "⚠ CONFIRMED MALWARE DETECTED\n"
                + result.get(
                    "name",
                    "Unknown"
                )
                + "\nFile quarantined"
            )

            self.live_event.color = RED

            notify_user(
                APP_NAME,
                "Confirmed malware detected and quarantined."
            )

        else:

            self.last_result.text = (
                "Scanning\n"
                + result.get(
                    "name",
                    "Unknown"
                )
            )

            self.last_result.color = GREEN

    # ========================================================
    # 36. FINISH SCAN
    # ========================================================

    def finish_scan(
        self,
        elapsed
    ):

        if not self.scanning:
            return

        self.scanning = False

        self.last_scan_seconds = int(
            elapsed
        )

        self.scan_button.disabled = False

        self.scan_button.text = (
            "SCAN DEVICE\n"
            "Full System Scan"
        )

        self.gauge.set_value(
            100,
            "Threat Found"
            if self.threats
            else "Safe"
        )

        self.percent_label.text = (
            "100%"
        )

        self.files_label.text = (
            "Files Scanned\n"
            f"{self.scanned_files:,}"
        )

        minutes = (
            self.last_scan_seconds
            // 60
        )

        seconds = (
            self.last_scan_seconds
            % 60
        )

        self.time_label.text = (
            "Scan Time\n"
            f"{minutes:02d}:{seconds:02d}"
        )

        if self.threats:

            self.safe_label.text = (
                "Threat Found"
            )

            self.safe_label.color = RED

            self.device_status.text = (
                "THREAT"
            )

            self.device_status.color = RED

            self.device_threat.text = (
                f"{self.threats} confirmed"
            )

            self.last_result.text = (
                f"{self.threats} "
                "CONFIRMED MALWARE\n"
                "Quarantine completed where possible"
            )

            self.last_result.color = RED

        else:

            self.safe_label.text = (
                "Safe"
            )

            self.safe_label.color = GREEN

            self.device_status.text = (
                "SECURE"
            )

            self.device_status.color = GREEN

            self.device_threat.text = (
                "No Threats Found"
            )

            self.last_result.text = (
                "✓ No Threat Found\n"
                "Your accessible storage is safe"
            )

            self.last_result.color = GREEN

            self.live_event.text = (
                "✓ Scan completed\n"
                "No verified malware found"
            )

            self.live_event.color = GREEN


# ============================================================
# 37. PART 3 শেষ
# ============================================================
# ============================================================
# V16.3 ANTIVIRUS PRO — APK READY
# PART 4/4
# MONITOR + HISTORY + QUARANTINE + INFO + APP
# ============================================================


# ============================================================
# 38. SCAN ERROR
# ============================================================

    def show_scan_error(
        self,
        message
    ):

        self.scanning = False

        self.scan_button.disabled = False

        self.scan_button.text = (
            "SCAN DEVICE\n"
            "Full System Scan"
        )

        self.device_status.text = (
            "SCAN ERROR"
        )

        self.device_status.color = RED

        self.device_threat.text = (
            "See details"
        )

        self.safe_label.text = (
            "Scan Error"
        )

        self.safe_label.color = RED

        self.live_event.text = (
            "Scan stopped safely\n"
            + str(message)[:200]
        )

        self.live_event.color = RED


# ============================================================
# 39. REAL-TIME FILE MONITOR
# ============================================================

    def monitor_tick(
        self,
        *_args
    ):

        if self.scanning:
            return

        if self.monitor_busy:
            return

        roots = scan_roots()

        if not roots:
            return

        self.monitor_busy = True

        thread = threading.Thread(
            target=self.monitor_worker,
            args=(roots,),
            daemon=True
        )

        thread.start()


# ============================================================
# 40. MONITOR WORKER
# ============================================================

    def monitor_worker(
        self,
        roots
    ):

        try:

            new_files = []

            for root in roots:

                for path in iter_files(root):

                    if (
                        len(new_files)
                        >= MAX_MONITOR_NEW_FILES_PER_CYCLE
                    ):

                        break

                    signature = file_signature(
                        path
                    )

                    if not signature:
                        continue

                    key = os.path.abspath(
                        path
                    )

                    old_signature = (
                        self.monitor_cache.get(
                            key
                        )
                    )

                    if (
                        old_signature is not None
                        and old_signature
                        != signature
                    ):

                        new_files.append(
                            path
                        )

                    self.monitor_cache[
                        key
                    ] = signature

                if (
                    len(new_files)
                    >= MAX_MONITOR_NEW_FILES_PER_CYCLE
                ):

                    break

            save_cache(
                self.monitor_cache
            )

            for path in new_files:

                result = scan_one_file(
                    path
                )

                if (
                    result.get("verdict")
                    == "CONFIRMED_MALWARE"
                ):

                    quarantine(
                        result
                    )

                add_history(
                    result
                )

                Clock.schedule_once(
                    lambda dt,
                    r=result:
                    self.live_scan_result(r)
                )

        except Exception:

            pass

        finally:

            Clock.schedule_once(
                lambda dt:
                self.clear_monitor_busy()
            )


# ============================================================
# 41. CLEAR MONITOR STATE
# ============================================================

    def clear_monitor_busy(
        self
    ):

        self.monitor_busy = False


# ============================================================
# 42. LIVE SCAN RESULT
# ============================================================

    def live_scan_result(
        self,
        result
    ):

        verdict = result.get(
            "verdict"
        )

        if verdict == "CONFIRMED_MALWARE":

            self.threats += 1

            self.device_status.text = (
                "THREAT"
            )

            self.device_status.color = RED

            self.device_threat.text = (
                "New confirmed threat"
            )

            self.safe_label.text = (
                "Threat Found"
            )

            self.safe_label.color = RED

            self.live_event.text = (
                "⚠ THREAT DETECTED\n"
                + result.get(
                    "name",
                    "Unknown"
                )
                + "\nFile quarantined"
            )

            self.live_event.color = RED

            notify_user(
                APP_NAME,
                "New confirmed malware detected and quarantined."
            )

        elif verdict == "NO_VERIFIED_MALWARE":

            self.live_event.text = (
                "✓ New File Detected & Scanned\n"
                + result.get(
                    "name",
                    "Unknown"
                )
                + "\nNo verified malware found"
            )

            self.live_event.color = GREEN


# ============================================================
# 43. HISTORY POPUP
# ============================================================

    def show_history(
        self,
        *_args
    ):

        history = get_history()

        box = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(10)
        )

        scroll = ScrollView()

        rows = []

        if not history:

            rows.append(
                "No scan history yet."
            )

        for index, item in enumerate(
            history[:120],
            1
        ):

            verdict = item.get(
                "verdict",
                "UNKNOWN"
            )

            filename = item.get(
                "name",
                "-"
            )

            scan_time = item.get(
                "time",
                "-"
            )

            sha256 = item.get(
                "sha256",
                "-"
            )

            quarantined = item.get(
                "quarantined",
                False
            )

            rows.append(
                f"{index}. {scan_time}\n"
                f"   File: {filename}\n"
                f"   Verdict: {verdict}\n"
                f"   SHA-256: {sha256}\n"
                f"   Quarantine: {quarantined}\n"
            )

        history_text = Label(
            text="\n".join(rows),
            color=WHITE,
            font_size=dp(12),
            halign="left",
            valign="top",
            size_hint_y=None
        )

        history_text.bind(
            texture_size=lambda obj, size:
            setattr(
                obj,
                "height",
                size[1] + dp(20)
            )
        )

        scroll.add_widget(
            history_text
        )

        box.add_widget(
            scroll
        )

        close_button = Button(
            text="CLOSE",
            size_hint_y=None,
            height=dp(50)
        )

        box.add_widget(
            close_button
        )

        popup = Popup(
            title="SCAN HISTORY",
            content=box,
            size_hint=(0.94, 0.90)
        )

        close_button.bind(
            on_press=popup.dismiss
        )

        popup.open()


# ============================================================
# 44. QUARANTINE POPUP
# ============================================================

    def show_quarantine(
        self,
        *_args
    ):

        try:

            files = sorted(
                QUARANTINE_DIR.iterdir(),
                key=lambda item:
                item.stat().st_mtime,
                reverse=True
            )

        except Exception:

            files = []

        names = [
            item.name
            for item in files[:100]
        ]

        if not names:

            names = [
                "Quarantine is empty."
            ]

        box = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )

        scroll = ScrollView()

        quarantine_text = Label(
            text="\n\n".join(names),
            color=WHITE,
            font_size=dp(13),
            halign="left",
            valign="top",
            size_hint_y=None
        )

        quarantine_text.bind(
            texture_size=lambda obj, size:
            setattr(
                obj,
                "height",
                size[1] + dp(20)
            )
        )

        scroll.add_widget(
            quarantine_text
        )

        box.add_widget(
            scroll
        )

        close_button = Button(
            text="CLOSE",
            size_hint_y=None,
            height=dp(50)
        )

        box.add_widget(
            close_button
        )

        popup = Popup(
            title="QUARANTINE",
            content=box,
            size_hint=(0.94, 0.90)
        )

        close_button.bind(
            on_press=popup.dismiss
        )

        popup.open()


# ============================================================
# 45. HOME
# ============================================================

    def home(
        self,
        *_args
    ):

        self.live_event.text = (
            "✓ Protection active\n"
            "Waiting for new or changed files..."
        )

        self.live_event.color = GREEN


# ============================================================
# 46. SECURITY INFORMATION
# ============================================================

    def show_info(
        self,
        *_args
    ):

        information = (
            f"{APP_NAME} {VERSION}\n\n"
            "Security baseline:\n"
            "• SHA-256 exact IOC matching\n"
            "• Confirmed-malware quarantine\n"
            "• Scan history\n"
            "• New/changed file monitoring\n"
            "• Permission-safe file traversal\n\n"
            "Important:\n"
            "Android protected/private app data "
            "may not be accessible to a normal "
            "Python/Kivy application."
        )

        box = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(10)
        )

        information_label = Label(
            text=information,
            color=WHITE,
            font_size=dp(13),
            halign="left",
            valign="top"
        )

        box.add_widget(
            information_label
        )

        close_button = Button(
            text="CLOSE",
            size_hint_y=None,
            height=dp(50)
        )

        box.add_widget(
            close_button
        )

        popup = Popup(
            title="V16 SECURITY",
            content=box,
            size_hint=(0.92, 0.70)
        )

        close_button.bind(
            on_press=popup.dismiss
        )

        popup.open()


# ============================================================
# 47. V16.3 APPLICATION
# ============================================================

class V16AntivirusApp(App):

    def build(self):

        self.title = (
            f"{APP_NAME} {VERSION}"
        )

        return AntivirusScreen()


# ============================================================
# 48. APPLICATION LAUNCHER
# ============================================================

if __name__ == "__main__":

    V16AntivirusApp().run()


# ============================================================
# V16.3 main.py — PART 4 শেষ
# ============================================================
