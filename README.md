# 联想小新 Air14 ITL 2021：Sonoma 14 与 Tahoe 26

联想 82FF 的 macOS 安装和修复记录，包含 Sonoma 14.8.9 原有操作步骤，以及 Tahoe 26.7.1 的安装、原生 Wi-Fi、Iris Xe 图形加速和内置麦克风方案。

**Tahoe 已成功安装并迁入内置硬盘。原生 Wi-Fi、图形加速、扬声器和内置麦克风已修复，录音人声清楚。**

## 硬件与系统

| 项目 | 配置 |
| --- | --- |
| 机型 | Lenovo 小新 Air14 ITL 2021，82FF |
| CPU / 内存 | Intel Core i5-1155G7 / 16 GB |
| 显卡 | Intel Iris Xe，PCI 8086:9A49 |
| 无线 / 蓝牙 | Intel AX201 / Intel USB Bluetooth |
| 音频 | ALC257 输出 + Intel SST/PDM0 内置数字麦克风 |
| BIOS | FKCN40WW V3.03 |
| 系统 | Sonoma 14.8.9；Tahoe 26.7.1（25G241） |
| 引导 | OpenCore 1.0.8 DEBUG，MacBookPro16,2 |

## 从这里开始

完整步骤见 **[操作手册](docs/操作手册.md)**。手册保留 Sonoma 的 1—18 步，再续写 Tahoe 的 19—28 步。

- 安装 Sonoma：第 1—18 步。
- 已有 Sonoma，安装 Tahoe：从第 19 步开始。
- 已进入 Tahoe，补齐无线、图形与音频：第 23—26 步。
- 修复合盖/开盖黑屏（显示器睡眠唤醒）：第 28 步，见[合盖黑屏与显示唤醒](docs/合盖黑屏与显示唤醒.md)。
- 查看文件版本与来源：[文件来源](docs/文件来源.md)、[验证记录](docs/验证记录.md)。
- 查看两个安装 U 盘的收录结果：[U 盘文件核对](docs/U盘文件核对.md)。

## 目录

```text
sonoma14/                  Sonoma 原有资料、配置和 18 步手册
tahoe26/EFI/               Tahoe 最终 EFI 配置与驱动
tahoe26/configs/           Tahoe 安装阶段配置
tahoe26/audio/             麦克风驱动、发布器、音频构建材料
sources/Lenovo82FFSSTMicrophone/  麦克风源码与固件许可
tools/                     资源下载、身份填写和校验工具
docs/                      完整操作手册与修复记录
licenses/                  各组件许可证
```

文件按目录展开。Apple 系统安装包、恢复镜像、KDK、Graphics 安装包，以及需要本机准备的音频组件，按手册从对应来源获取。资源清单固定版本和 SHA256；下载到本地的文件由 `.gitignore` 排除。

启动前运行 `tools/fetch-resources.py`，补齐 HfsPlus、USBToolBox 和 AMFIPass Mod；最终 EFI 还需按音频说明构建 SimpleHDA540PreProbe，并安装对应 HAL。

SMBIOS 的序列号、MLB、UUID、ROM 及无线预设已清空。先生成自己的一组 MacBookPro16,2 身份，再按手册填入所有配置。

## Tahoe 修复结果

| 功能 | 当前结果 | 实现 |
| --- | --- | --- |
| 启动与内置盘安装 | 完成 | Sonoma 展开安装器，Tahoe 恢复环境执行安装，再迁移 EFI |
| 系统原生 Wi-Fi | 已修复 | AirportItlwm Tahoe 2.4.0-alpha，固定 8ae5115 |
| Iris Xe 图形加速 | 已修复 | WhateverXe 0.6.1 + Graphics 0.3.2，Metal 2、1536 MB |
| 扬声器 | 正常 | AppleALC layout 101 + AppleHDA 540.3 输出兼容层 |
| 内置麦克风 | 已修复，录音人声清楚 | Lenovo82FFSSTMicrophone 0.3.2，PDM0 输入 |
| 合盖/开盖唤醒 | 已缓解（不再睡眠显示器） | `disablesleep=1` + caffeinate 常驻 + 电源设置维持守护 |
| 隔空投送 | 当前 AX201 驱动未支持 | [OCLP 与无线驱动说明](docs/隔空投送与互联.md) |
| iPhone 镜像 | 本机缺少 Apple 要求的 T2 / Apple silicon | 同上 |
| HDMI 外接显示 | 尚未修复 | 保留现有配置参数 |

## 许可

仓库新增文档和辅助脚本采用 [MIT License](LICENSE)。驱动、固件及其他第三方组件沿用各自许可证，见 [licenses](licenses/)、[音频源码许可](sources/Lenovo82FFSSTMicrophone/LICENSE)。
