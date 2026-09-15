#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
app="build/LG Monitor Recovery.app"
mkdir -p "$app/Contents/MacOS" build/support/source
make -C source
clang -fobjc-arc -Wall -Wextra -mmacosx-version-min=13.0 -framework AppKit MenuApp.m -o "$app/Contents/MacOS/LGMonitorRecovery"
cp Info.plist "$app/Contents/Info.plist"
cp recovery.py wake_display.py build/support/
cp source/m1ddc source/LICENSE build/support/source/
codesign --force --sign - "$app"
codesign --verify --strict "$app"
printf 'Built app and helper files in build/\n'
