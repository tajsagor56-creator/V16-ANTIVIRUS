[app]

title = V16 ANTIVIRUS

package.name = v16antivirus

package.domain = org.kingtaj

version = 16.3

source.dir = .

source.include_exts = py,json,png,jpg,jpeg,kv,atlas

requirements = python3,kivy,plyer

orientation = portrait

fullscreen = 0

android.api = 35

android.minapi = 24

android.archs = arm64-v8a

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,POST_NOTIFICATIONS

android.allow_backup = True

android.private_storage = True

android.accept_sdk_license = True


[buildozer]

log_level = 2

warn_on_root = 0
