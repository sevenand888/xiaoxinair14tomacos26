#!/bin/bash
# Runs from a root-owned protected directory. Publication only; no recording/default changes.
set -euo pipefail
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
export LC_ALL=C
unset BASH_ENV ENV CDPATH || true
umask 027

BASE='/Library/PrivilegedHelperTools/local.codex.Lenovo82FFSSTPublish'
PUBLISHER="$BASE/publish"
BUNDLE='/Library/Extensions/Lenovo82FFSSTMicrophone.kext'
INFO="$BUNDLE/Contents/Info.plist"
BINARY="$BUNDLE/Contents/MacOS/Lenovo82FFSSTMicrophone"
EXPECTED_BINARY='44070aa05b41086159730acc24021a771bda80e611f15e58de8193f37010383a'
EXPECTED_PUBLISHER='55e2936f6fe9caf300711d687ec1d2c39e80e2f734b1c29d6611be690c03d4bd'
EXPECTED_UID='Lenovo82FFSSTMicrophone:8086-A0C8:17AA-381D:PDM0'

log() { /bin/date '+%Y-%m-%dT%H:%M:%S%z' | /usr/bin/tr -d '\n'; printf ' %s\n' "$*"; }
fail() { log "ERROR: $*"; exit 1; }
trap 'log "terminated; no retry scheduled"; exit 143' TERM INT HUP
protected() {
    local path="$1" mode owner
    [ -e "$path" ] && [ ! -L "$path" ] || fail "missing/symlink path: $path"
    owner=$(/usr/bin/stat -f '%u:%g' "$path")
    mode=$(/usr/bin/stat -f '%Lp' "$path")
    [ "$owner" = '0:0' ] || fail "not root:wheel: $path"
    (( (8#$mode & 0022) == 0 )) || fail "group/other writable: $path"
}
digest() { /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'; }
field() { printf '%s' "$REGISTRY" | /usr/bin/plutil -extract "0.$1" raw -o - - 2>/dev/null; }
read_service() {
    REGISTRY=$(/usr/sbin/ioreg -a -r -c Lenovo82FFSSTMicrophone -d 1)
    if ! field Version >/dev/null; then return 1; fi
    if printf '%s' "$REGISTRY" | /usr/bin/plutil -extract 1 xml1 -o - - >/dev/null 2>&1; then
        fail 'multiple matching SST services'
    fi
    [ "$(field CFBundleIdentifier)" = 'local.codex.Lenovo82FFSSTMicrophone' ] || fail 'service bundle ID differs'
    [ "$(field Version)" = '0.3.2-82FF-TGL-Experimental' ] || fail 'service version differs'
}
verify_engine() {
    ENGINE=$(/usr/sbin/ioreg -r -c Lenovo82FFMicAudioEngine -l -w0)
    printf '%s\n' "$ENGINE" | /usr/bin/grep -Fq "\"IOAudioEngineGlobalUniqueID\" = \"$EXPECTED_UID\"" || fail 'published engine UID missing'
}

[ "$(/usr/bin/id -u)" = 0 ] || fail 'root required'
for path in "$BASE" "$BASE/publish-once.sh" "$PUBLISHER" "$BUNDLE" "$BUNDLE/Contents" "$INFO" "$BUNDLE/Contents/MacOS" "$BINARY"; do
    protected "$path"
done
[ "$(digest "$PUBLISHER")" = "$EXPECTED_PUBLISHER" ] || fail 'publisher SHA256 differs'
[ "$(digest "$BINARY")" = "$EXPECTED_BINARY" ] || fail 'driver executable SHA256 differs'
[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$INFO")" = 'local.codex.Lenovo82FFSSTMicrophone' ] || fail 'bundle ID differs'
[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$INFO")" = '0.3.2' ] || fail 'bundle version differs'
/usr/bin/codesign --verify --strict "$BUNDLE" || fail 'driver bundle signature verification failed'

log 'waiting once: boot age >=70s and exact SST service; at most 60 waits of 10s; login not required'
ready=false
for ((attempt=0; attempt<60; attempt++)); do
    BOOT=$(/usr/sbin/sysctl -n kern.boottime | /usr/bin/awk -F '[=,]' '{gsub(/ /,"",$2);print $2}')
    case "$BOOT" in ''|*[!0-9]*) fail 'cannot parse boot time';; esac
    AGE=$(( $(/bin/date +%s) - BOOT ))
    if [ "$AGE" -ge 70 ] && read_service; then ready=true; break; fi
    /bin/sleep 10
done
[ "$ready" = true ] || fail 'readiness timeout; no publication attempted; no automatic retry'
LOADED=$(/usr/bin/kmutil showloaded 2>/dev/null) || fail 'cannot inspect loaded kexts'
COUNT=$(printf '%s\n' "$LOADED" | /usr/bin/grep -Ec '(^|[[:space:]])local\.codex\.Lenovo82FFSSTMicrophone \(0\.3\.2\) CF5EC589-4176-3D99-9DC1-3F7C4456D0FE([[:space:]]|$)' || true)
[ "$COUNT" = 1 ] || fail 'loaded driver UUID/version does not match approved binary'

if [ "$(field PublishesAudioInput)" = true ]; then
    verify_engine
    log "already published; no publisher call; phase=$(field Phase)"
    exit 0
fi
[ "$(field PublishesAudioInput)" = false ] || fail 'unexpected published flag'
[ "$(field Phase)" = WaitingForRootPublication ] || fail 'service is not in initial publication state'
[ "$(field CaptureActive)" = false ] || fail 'capture already active on unpublished service'
[ "$(field HardwareWritesStarted)" = false ] || fail 'unexpected previous hardware activity'
if field Failure >/dev/null; then fail 'driver already reports failure'; fi
# Revalidate files immediately before the only mutating operation.
[ "$(digest "$PUBLISHER")" = "$EXPECTED_PUBLISHER" ] && [ "$(digest "$BINARY")" = "$EXPECTED_BINARY" ] || fail 'identity changed'
log 'publishing the idle CoreAudio input exactly once'
"$PUBLISHER" || fail 'publisher returned failure; no retry'
for ((attempt=0; attempt<15; attempt++)); do
    /bin/sleep 1
    if read_service && [ "$(field PublishesAudioInput)" = true ]; then
        verify_engine
        log "publication verified; phase=$(field Phase); captureActive=$(field CaptureActive); no capture/default-input request issued"
        exit 0
    fi
    if field Failure >/dev/null; then fail 'driver reported failure after publication'; fi
done
fail 'publication acknowledgement timed out; no retry'
