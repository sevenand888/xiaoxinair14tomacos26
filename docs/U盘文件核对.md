# 两个 U 盘的文件核对

2026-11-01 检查了两个 U 盘、四个分区，共 **319 个文件**。文件系统索引目录另行忽略。

| U 盘 | 分区 | 检查文件数 |
| --- | --- | ---: |
| Tahoe 32 GB | TAHOE26 | 110 |
| Tahoe 32 GB | TAHOE_DATA | 18 |
| Sonoma 64 GB | OC_OFFLINE | 178 |
| Sonoma 64 GB | MACOS_DATA | 13 |

## 已有内容

124 个文件与仓库文件的 SHA256 相同，10 个文件已在下载清单中固定来源和 SHA256。另有 3 份配置或无线预设经过脱敏整理，WhateverXe 0.6.1 归档中的驱动已展开收录。

Tahoe U 盘的安装阶段配置已与仓库 `config-install.plist` 逐项比较，差异为机器身份清除。最终使用仓库中的图形、Wi-Fi 和麦克风配置。

## 本次补充

| U 盘内容 | 仓库位置 |
| --- | --- |
| Start-Offline.command | [Sonoma 离线安装目录](../sonoma14/资料/offline/) |
| UnPlugged.command | 同目录的中文说明及[固定提交下载项](../sonoma14/资源来源.json)；原 U 盘文件与上游逐字节一致 |
| HeliPort 1.5.0 | [工具说明](../sonoma14/资料/network/README.md)、官方获取入口与 SHA256 |
| Sonoma 安装包来源及校验记录 | [sonoma14/installer.json](../sonoma14/installer.json) |
| Tahoe 安装包来源 | [tahoe26/installer.json](../tahoe26/installer.json) |
| WhateverXe 0.6.1 原归档校验 | [Tahoe 资源清单](../tahoe26/resources.json) |

## 已排除的内容

- 两套系统的 InstallAssistant.pkg、恢复镜像及其附属完整性文件。
- SSH 访问凭据、OpenCore 与安装排查日志、文件系统元数据。
- 早期分析报告、诊断配置、测试配置、旧版 WhateverXe 0.5.0 和重复备份。
- 42,283,393 字节的旧 Graphics 包；采用当前已验证的 95,196,691 字节版本。
- 早期显卡启用与 VESA 回退脚本；对应操作已整理到完整手册。旧显卡脚本写入的是当时整组启动参数，现配置包含后续麦克风参数。
- 远程排查时的临时软件安装包。

逐文件去向见 [U盘文件清单.json](U盘文件清单.json)。两个 U 盘的原文件保持原样。
