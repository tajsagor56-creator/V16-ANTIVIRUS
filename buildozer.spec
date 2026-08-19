[app]

title = V16 ANTIVIRUS
package.name = v16antivirus
package.domain = org.kingtaj

source.dir = .
source.include_exts = py,json,png,jpg,jpeg,kv,atlas

version = 16.3

requirements = python3,kivy,plyer

orientation = portrait
fullscreen = 0

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,POST_NOTIFICATIONS

android.api = 35
android.minapi = 23

android.archs = arm64-v8a

android.allow_backup = True
android.private_storage = True

[buildozer]

log_level = 2
warn_on_root = 0
