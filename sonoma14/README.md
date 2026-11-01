# Sonoma 14.8.9 资料

这里保留联想小新 Air14 ITL 2021 / 82FF 的 Sonoma 配置、驱动和原 18 步操作路径。

- [操作手册](操作手册.md)：从制作安装 U 盘到图形、电池、亮度、睡眠和 Wi-Fi 配置。
- `资料/EFI-VESA-BT`：安装阶段的基础 EFI。
- `资料/graphics`、`资料/power`：图形与电源相关配置和组件。
- [资源来源](资源来源.json)：文件 SHA256、官方下载地址及放置位置。

使用前按来源清单获取 HfsPlus、USBToolBox 1.2.0、AMFIPass 1.4.1 Mod 和图形卸载脚本，并放回清单指定位置。图形安装包从 WhateverXe Graphics 0.3.1 发行页获取。随后按操作手册填写自己的 SMBIOS 并检查 EFI 配置。

第三方组件的许可证与对应源代码入口见 [licenses/sonoma14](../licenses/sonoma14/README.md)。
