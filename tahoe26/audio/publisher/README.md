# SST 启动发布器

此工具在启动后发布 `local.codex.Lenovo82FFSSTMicrophone` 0.3.2 输入设备。本机已经完成安装和两次重启验证，输入会自动出现并恢复默认选择。

## 使用

需要 macOS、Python 3，并以 root 执行管理操作；从本目录执行：

```sh
sudo python3 manage.py install --activate
sudo python3 manage.py verify
sudo launchctl print system/local.codex.Lenovo82FFSSTPublish
```

省略 `--activate` 表示安装后下次启动才运行。已有目标或同名 job 时拒绝覆盖；升级前需按原安装 receipt 卸载并保留备份。驱动预先位于 `/Library/Extensions/Lenovo82FFSSTMicrophone.kext`。

只在开机时间至少 70 秒、精确且唯一的 SST 服务出现后尝试一次；最多 60 次、每次 10 秒等待。发布前验证 root 拥有且非组/其他用户可写的安装文件、驱动签名、版本、Mach-O UUID 和 SHA256。已经发布时仅验证精确引擎 UID，不重复发布。不存在 KeepAlive 或周期录音任务。

固定驱动 SHA256 为 `44070aa05b41086159730acc24021a771bda80e611f15e58de8193f37010383a`，软件加载 UUID 为 `CF5EC589-4176-3D99-9DC1-3F7C4456D0FE`。固定 publisher SHA256 为 `55e2936f6fe9caf300711d687ec1d2c39e80e2f734b1c29d6611be690c03d4bd`。

## 路径与卸载

安装路径：

- `/Library/LaunchDaemons/local.codex.Lenovo82FFSSTPublish.plist`
- `/Library/PrivilegedHelperTools/local.codex.Lenovo82FFSSTPublish/` 下的 `publish-once.sh`、`publish`、`receipt.json`
- `/private/var/log/lenovo82ff-sst-publish.log`
- `/Library/Application Support/Lenovo82FFSSTPublish/Backups/` 下的目标机本地备份

卸载命令：

```sh
sudo python3 manage.py uninstall
```

卸载先根据 receipt 核对全部安装文件哈希，再停止本 job，将其 plist/helper/log 移到本机受保护备份。未知或已改文件会使卸载停止。此操作不撤销已经发布的当前输入，不删除驱动，不修改默认设备、EFI 或 KC；下次启动不再自动发布。

`publish` 的源码在 `../../../sources/Lenovo82FFSSTMicrophone/tools/publish.c`（相对于仓库根请查 sources 目录）。管理脚本按仓库根 LICENSE；publisher 源码和二进制保持 BSD-3-Clause，许可随上一级 kext 资源及源码目录提供。
