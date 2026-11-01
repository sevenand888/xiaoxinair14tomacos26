#!/bin/bash
# 在 Tahoe 恢复环境执行；目标卷和安装应用已经准备完成。
set -euo pipefail
if [[ $# -ne 1 ]]; then
    echo '用法：bash recovery-install-tahoe.sh /Volumes/Tahoe' >&2
    exit 2
fi
TARGET="$1"
case "$TARGET" in
    /Volumes/*) ;;
    *) echo '目标应是 /Volumes 下已挂载的 APFS 安装卷。' >&2; exit 2 ;;
esac
[[ "$(uname -s)" == Darwin && "$(uname -r)" == 25.* ]] || {
    echo '请从 Tahoe 26 恢复环境执行。' >&2; exit 2;
}
[[ "$(id -u)" == 0 ]] || { echo '需要恢复环境的 root 终端。' >&2; exit 2; }
APP="$TARGET/Applications/Install macOS Tahoe.app"
START="$APP/Contents/Resources/startosinstall"
[[ -x "$START" && -f "$APP/Contents/SharedSupport/SharedSupport.dmg" ]] || {
    echo '请先准备安装应用及 SharedSupport 链接，并挂载安装数据分区。' >&2; exit 2;
}
diskutil info "$TARGET"
exec env __OSINSTALL_ENVIRONMENT=1 "$START" --volume "$TARGET" --agreetolicense --rebootdelay 120
