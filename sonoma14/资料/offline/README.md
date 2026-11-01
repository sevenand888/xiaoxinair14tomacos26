# Sonoma 离线安装辅助工具

此目录补充原 Sonoma 安装 U 盘上的 `Start-Offline.command` 入口。它在同一目录找到 InstallAssistant.pkg 和 UnPlugged.command 后，启动 UnPlugged 的交互式离线安装流程。

## 准备

从仓库根目录运行：

```sh
python3 tools/fetch-resources.py sonoma14/资源来源.json --id unplugged
```

脚本下载固定提交 `4f8e9135c1de051adf96f4d5b3045a383f7aaa01` 的 UnPlugged.command，与原 U 盘文件一致。上游文件保存在本地，来源和 SHA256 见资源清单。

将 `Start-Offline.command`、下载的 `UnPlugged.command` 和自己取得的 Sonoma InstallAssistant.pkg 放入安装 U 盘的 `MACOS_DATA` 分区根目录。

## 使用

在恢复环境中挂载 MACOS_DATA，再运行：

```sh
bash /Volumes/MACOS_DATA/Start-Offline.command
```

按界面选择 `Fully expand InstallAssistant.pkg`，再选择已经准备好的 APFS 目标卷。安装期间保持 U 盘、电源和终端连接，后续重启从 OpenCore 选择相应安装项。

完整的本机安装步骤见[操作手册第 5—7 步](../../操作手册.md)。UnPlugged 为交互式辅助入口。

## 来源

[corpnewt/UnPlugged 固定提交](https://github.com/corpnewt/UnPlugged/tree/4f8e9135c1de051adf96f4d5b3045a383f7aaa01)。该提交没有独立许可证文件，本仓库保留下载入口和自行编写的启动脚本。
