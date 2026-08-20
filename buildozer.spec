[app]

# ==================================================
# V16 ANTIVIRUS PRO
# ==================================================

title = V16 Antivirus Pro

package.name = v16antivirus
package.domain = org.kingtaj

source.dir = .
source.include_exts = py,json,png,jpg,jpeg,kv,atlas

version = 16.2

orientation = portrait
fullscreen = 0

# ==================================================
# Python / Kivy
# ==================================================

requirements = python3,kivy,plyer

# ==================================================
# Android permissions
# ==================================================

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,POST_NOTIFICATIONS

# ==================================================
# Android SDK
# ==================================================

android.api = 35
android.minapi = 23

# প্রথম build-এর জন্য ARM64
android.archs = arm64-v8a

# ==================================================
# Android settings
# ==================================================

android.private_storage = True
android.allow_backup = False
android.uses_cleartext_connection = False

# ==================================================
# Icon / Presplash
# ==================================================

presplash.filename = %(source.dir)s/presplash.png
icon.filename = %(source.dir)s/icon.png


[buildozer]

log_level = 2
warn_on_root = 1
