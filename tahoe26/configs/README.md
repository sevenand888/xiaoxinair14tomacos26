# Tahoe 配置的用途与校验

本目录的 `config-install.plist` 用于安装阶段；`../EFI/OC/config.plist` 用于完成图形、输出兼容层和 SST 音频部署后的系统。两者都清除了原机器身份，需先填写自己的身份并补齐相应文件。

## 安装阶段配置的来源

这份配置按 2026-10-31 实际 U 盘修改记录重建。脱敏前的序列化 SHA256 与当时写入后回读值完全一致：

```text
dfc3398ba6ac6ca8e3360e45c1375407a92e344e252e5e05ba49269a22e14ac2
```

安装配置启用的各 kext 的 Info.plist/可执行文件、五份 ACPI、OpenCore、OpenRuntime 和 HfsPlus，均已核对为与本次选用文件逐字节一致。

安装配置的关键状态：

- `ScanPolicy=2621442`，允许 USB 与 NVMe；没有旧内置 NVMe 屏蔽属性，也没有 `nvme=16`。
- WhateverGreen 启用、WhateverXe 与 AMFIPass 关闭；启动参数保留 `-igfxvesa`，按无加速显示完成恢复与安装。
- `csr-active-config=03080000`、`SecureBootModel=Disabled`、`DmgLoading=Any`；菜单 `Timeout=0`，需要手选安装器或系统卷。
- 双版本 AirportItlwm 和三项 Force 是当时配置的一部分。该次恢复环境 Wi-Fi 未能联网，因此本路线采用离线安装；完整系统的 Wi-Fi 随后已修复。
- 原恢复镜像不随仓库提供；使用者需取得自己的 Apple 恢复/安装资源。

准备安装介质时，在工作副本中把 `config-install.plist` 复制为 `EFI/OC/config.plist`，填写本机身份、补齐 HfsPlus 和 USBToolBox 后校验。先核对目标磁盘分区，再备份并写入配置。

实际安装路线是在既有 Sonoma 中将 InstallAssistant.pkg 展开到外置 Tahoe 卷，再进入 Tahoe 恢复环境运行 `startosinstall --volume`。运行中的 Sonoma 直接执行该 Tahoe 安装命令曾返回 Usage/15。详细分区、安装器准备和后续重启选择见仓库操作手册。

## 最终配置与安装配置的区别

最终配置保留当前 `070a0000` SIP 值、双系统 WEX 范围、图形参数、AppleALC layout 101、SimpleHDA540PreProbe 和 `-82ffsst` 等已验收音频参数。启用项所需的外部文件和本地构建见 `../resources.json`；SimpleHDA540PreProbe 按音频目录说明准备。

图形包和音频组件准备完成后，在工作副本中换用最终配置。每次切换都填写并核对同一台机器的身份，校验后保留可启动的回退介质。

## 身份字段与验证

在 `PlatformInfo/Generic` 中填写自行生成、与目标机型相符的 `MLB`、`SystemSerialNumber`、`SystemUUID`，并将六字节零值 `ROM` 换成自己的值。

使用 **OpenCore 1.0.8 对应的 ocvalidate**：

```sh
ocvalidate /path/to/EFI/OC/config.plist
```

身份填写完成后应得到 `No issues found`。接着核对每个启用的 `Kernel/Add`、`ACPI/Add` 和 `UEFI/Drivers` 路径真实存在，验证外部文件哈希，再进行启动验收。

本次已用临时测试身份对两份脱敏配置完成 ocvalidate 1.0.8 结构校验；临时身份未写入仓库。除身份清除外，最终配置没有改变实机启动参数或驱动开关。
