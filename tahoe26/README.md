# 小新 Air14 ITL 的 macOS Tahoe 26 文件

本目录对应 Lenovo 小新 Air14 ITL 2021（82FF）、i5-1155G7、Iris Xe、AX201 的 macOS 26.7.1（25G241）。内屏图形加速、Wi-Fi 和内置麦克风已修复。`EFI/OC/config.plist` 来自 2026-11-01 最后验收的实际 EFI，保留当前图形、双系统驱动范围和音频参数。

**使用前先补齐外部文件和本机身份。** `MLB`、`SystemSerialNumber`、`SystemUUID` 已留空，`ROM` 为六字节零值；请填写自己的值。驱动条目保持实机配置，所需文件按下面的清单补齐。

## 文件入口

| 路径 | 用途 |
| --- | --- |
| `EFI/` | 当前工作参数、OpenCore、ACPI 和可附带的驱动 |
| [configs/config-install.plist](configs/config-install.plist) | 原成功安装阶段的 VESA 配置；准备安装介质时使用 |
| [configs/README.md](configs/README.md) | 两份配置的来源、切换方式、身份填写与校验 |
| [resources.json](resources.json) | 未附带文件的上游地址、归档与目标文件哈希、提取映射和本地构建要求 |
| [audio/README.md](audio/README.md) | SST 内置麦克风、输出兼容层、发布器的部署与验收 |

## 使用前补齐

资源获取工具在本地补齐清单指定路径，并校验下载内容和目标文件的 SHA256。下载缓存、外部安装包及这些补齐的组件由 `.gitignore` 排除。也可以先将整个仓库复制到自己的工作目录再执行。

| 文件 | 当前状态 | 放置位置 |
| --- | --- | --- |
| HfsPlus | 从上游取得并校验 | `EFI/OC/Drivers/HfsPlus.efi` |
| USBToolBox 1.2.0 | 从上游取得并校验 | `EFI/OC/Kexts/USBToolBox.kext` |
| AMFIPass 1.4.1 Mod | 使用 Graphics 项目提供的指定 Mod 包 | `EFI/OC/Kexts/AMFIPass.kext` |
| SimpleHDA540PreProbe | 依照音频说明在本机准备；完整二进制未附带 | `EFI/OC/Kexts/SimpleHDA540PreProbe.kext` |
| WhateverXe Graphics 0.3.2 | 外部下载，在目标 Tahoe 内安装 | 本目录的 `downloads/` |

最终配置中的 `SimpleHDA.kext` 和 `TigerLakeDSPProbe.kext` 条目保持关闭，未附带相应二进制。SST 麦克风驱动位于 `audio/`，按该目录说明装入 `/Library/Extensions`。

## 当前关键参数

- OpenCore 1.0.8 DEBUG（与实际工作 EFI 一致）；SMBIOS 机型为 `MacBookPro16,2`，具体身份须自行生成。
- `csr-active-config=070a0000`、`SecureBootModel=Disabled`，用于当前已修复的音频与图形组合。
- 当前图形使用 WhateverXe 0.6.1；WhateverGreen 关闭。常规 `WhateverXe.kext` 对应 Darwin 23–24，`WhateverXe-Tahoe.kext` 对应 Darwin 25。
- AirportItlwm-Sonoma14.4 对应 Darwin 23–24；Tahoe 的 AirportItlwm 为 `2.4.0-alpha / 8ae5115`，对应 Darwin 25，并保留 IO80211Family、IOSkywalkFamily、corecapture 三项 Force。
- `itlwm.kext` 保持关闭，其 `WiFiConfig` 已清为空字典；没有保存无线网络名称或口令。
- IntelBluetoothFirmware 为 2.4.0；IntelBTPatcher 为 **lshbluesky 分支 2.5.2**；BlueToolFixup 为 2.7.2。
- OpenCore 菜单等待 10 秒，`LauncherOption=Full`、`LauncherPath=Default`、`ShowPicker=true`。默认 macOS 卷需要在自己的 OpenCore 菜单中选中后按 Ctrl+Enter 设置。

内屏已修复为 1920×1080、1536MB、Metal 2，窗口操作流畅。HDMI 外接显示器和系统睡眠尚未完成验收；配置保留原有 `tgl-hdmi-wiring` 参数。升级系统前请核对对应驱动支持版本。

## 图形包说明

先用正确的 WEX、Lilu、AMFIPass Mod 配置启动目标 Tahoe，再安装校验通过的 [WhateverXe Graphics 0.3.2](https://github.com/b00t0x/WhateverXe-Graphics/releases/tag/v0.3.2)，成功后重启。正确包大小为 **95,196,691 字节**，SHA256：

```text
7ac6c7149248c483efbd93555294d587a93d81392421f3af8a4f5b1b5fcc0101
```

该包将图形组件放入 `/Library/Extensions` 和 `/Library/GPUBundles`，重建 AuxKC，并设置 Tahoe 的 CoreMedia 缩放选项。EFI、启动参数和 SIP 使用本目录的配置。包的外层容器未签名，内部组件使用指定 AMFIPass Mod 签名链。[上游安装说明](https://github.com/b00t0x/WhateverXe-Graphics)

## 来源与许可

完整组件路径、版本、源码地址及文件哈希见 `resources.json`。公共组件许可位于 [licenses/sonoma14](../licenses/sonoma14/)，WEX 0.6.1、Tahoe AirportItlwm 及 IntelBTPatcher 分支许可位于 [licenses/tahoe26](../licenses/tahoe26/)。无线固件保留其单独许可。

Graphics 包的 BSD 许可只覆盖打包工具，并不覆盖其中 Apple/Intel 派生二进制。本仓库提供下载来源与哈希；Apple 安装镜像、Graphics.pkg、SimpleHDA 完整 Apple payload 需要在本机取得和准备。[Graphics 第三方说明](https://github.com/b00t0x/WhateverXe-Graphics/blob/v0.3.2/THIRD_PARTY.md)
