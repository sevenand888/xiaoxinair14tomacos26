#!/bin/bash
set -e
cd -- "$(dirname -- "$0")"
test -f InstallAssistant.pkg && test -f UnPlugged.command
echo "Offline installer: macOS Sonoma 14.8.9 (23J631)."
echo "The internal SSD must be visible and validated before proceeding."
echo "Select Fully expand InstallAssistant.pkg if prompted."
echo "Select only the intended APFS target; keep Terminal and USB connected."
bash ./UnPlugged.command
