# HeliPort 无线管理工具

原 Sonoma U 盘保存了 HeliPort 1.5.0。HeliPort 用于管理 `itlwm.kext` 提供的无线连接；本仓库当前默认使用 AirportItlwm 和 macOS 系统 Wi-Fi 菜单。

需要使用 itlwm 路线时，可从仓库根目录获取原 U 盘对应版本：

```sh
python3 tools/fetch-resources.py sonoma14/资源来源.json --id heliport-1.5.0
```

下载后位于 `sonoma14/downloads/HeliPort-1.5.0.dmg`，大小 8,601,948 字节。打开 DMG，将 HeliPort.app 放入“应用程序”。无线驱动和 EFI 开关按所选路线配置。

[OpenIntelWireless/HeliPort 1.5.0 官方发布页](https://github.com/OpenIntelWireless/HeliPort/releases/tag/v1.5.0)。下载 SHA256：

```text
49cbe7abea742a3c662a836f14c05b79b3e6e6577c897b57101f5bd0a086eec8
```
