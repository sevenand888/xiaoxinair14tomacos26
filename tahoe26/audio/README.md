# Tahoe 26 音频文件

Lenovo 82FF 内置麦克风已修复，人声录音清楚，重启后自动恢复输入。本目录提供 SST 驱动、延迟发布器和 AppleHDA 540.3 输出兼容层的本地构建材料。机型为小新 Air14 ITL 2021，PCI `8086:a0c8` / 子系统 `17aa:381d`，系统为 macOS 26.7.1（25G241）。

## 目录与验证

`Lenovo82FFSSTMicrophone.kext` 为原样保留的 0.3.2 成功产物；`publisher/` 提供启动后一次性发布空闲输入的工具；源码位于 [sources/Lenovo82FFSSTMicrophone](../../sources/Lenovo82FFSSTMicrophone/)。先在任意有 Python 3 的系统运行：

```sh
python3 verify-package.py
```

包级检查核对驱动文件、发布器清单、版本与 UID。macOS 上运行 `codesign --verify --strict Lenovo82FFSSTMicrophone.kext` 检查签名。包内保留原 NOTICE，Lenovo 适配说明见源码目录 NOTICE。

## 安装顺序

需要先有正常启动和正常输出的 EFI，保留现有 Lilu、AppleALC 及显卡等必要项。工作配置使用 AppleALC layout 101、SimpleHDA540PreProbe 的 AppleHDA 540.3 payload 和对应 HAL。SimpleHDA/Apple 原始二进制没有随此仓库分发，准备方式见 `simplehda/README.md`。

SST 驱动安装到 `/Library/Extensions/Lenovo82FFSSTMicrophone.kext`，通过 macOS 辅助内核集合加载。先备份，再复制完整 kext，设置 `root:wheel` 和 `go-w` 权限，通过 `kmutil load -p` 请求系统批准和加载。按系统界面完成批准与重启；保留 AuxKC 中已有的显卡等组件。

驱动需要启动参数 `-82ffsst`，本机输出兼容层还有 `-shdaskiphdau` 等设置，详见仓库操作手册。按实际 EFI 挂载位置修改配置并保存备份。

待驱动确认由系统加载后，安装发布器：

```sh
sudo python3 publisher/manage.py install --activate
sudo python3 publisher/manage.py verify
sudo launchctl print system/local.codex.Lenovo82FFSSTPublish
```

发布器在开机至少 70 秒、驱动和服务身份匹配后发布输入，最多等待约 10 分钟；实测约开机 84–85 秒出现输入。细节及卸载见 [publisher/README.md](publisher/README.md)。

## 选择输入与检查

新设备显示名为 `Lenovo 82FF PDM0 internal microphone capture`。精确 UID：

```text
Lenovo82FFSSTMicrophone:8086-A0C8:17AA-381D:PDM0
```

在系统声音设置选择该输入。也可在登录用户会话编译并执行精确 UID 选择工具，它只修改默认输入、不改变音量和静音：

```sh
xcrun clang -fobjc-arc select-input-uid.m -framework Foundation -framework CoreAudio -o select-input-uid
./select-input-uid 'Lenovo82FFSSTMicrophone:8086-A0C8:17AA-381D:PDM0'
```

在目标机读状态：

```sh
kmutil showloaded | grep Lenovo82FFSSTMicrophone
ioreg -r -c Lenovo82FFSSTMicrophone -l -w0
ioreg -r -c Lenovo82FFMicAudioEngine -l -w0
tail -n 30 /private/var/log/lenovo82ff-sst-publish.log
```

发布器日志为 `publication verified` 或 `already published`，`PublishesAudioInput=Yes`，引擎 UID 与上方一致。

运行 `chmod +x mic-input-check && ./mic-input-check` 可进行三轮约四秒采样并输出统计。也可打开录音应用、授予麦克风权限，录制和回放人声。

已完成人声录音、双声道测试音和两次重启自动发布验证。

## 许可

SST 源码及二进制保留 BSD-3-Clause、SOF 固件与 SDK 许可。发布器管理脚本、选择工具和新增辅助脚本采用仓库根 LICENSE；`publisher/publish` 采用 BSD-3-Clause。SimpleHDA 上游及 Apple payload 各自保留其原许可和版权。
