# Lenovo 82FF 内置麦克风驱动源码

联想小新 Air14 ITL 2021（82FF）的内置麦克风已修复，人声录音清楚，重启后输入自动出现并恢复默认选择。本驱动使用 Intel SST / SOF IPC3，源自 [RazerSSTMicrophone](https://github.com/MarkPLacer/RazerSSTMicrophone/tree/17cff4e3cb074235d51fa01f3f633222ea558597)。本目录提供成功版本的 7 个内核源文件、构建工具和许可。

硬件与系统：PCI `8086:a0c8`、PCI 子系统 `17aa:381d`、Tiger Lake cAVS 2.5、PDM0 A+B、48 kHz 双声道、32 位 PCM，macOS 26.7.1（25G241）。ALC257 codec 子系统为 `17aa:3894`。

2026-11-01 已完成人声录音、双声道测试音、录音结束清理和两次重启自动发布验证。

输入 UID 为 `Lenovo82FFSSTMicrophone:8086-A0C8:17AA-381D:PDM0`，显示名为 `Lenovo 82FF PDM0 internal microphone capture`。输出使用原有 AppleHDA / AppleALC 路径。

## 构建

在 macOS 上安装 Xcode Command Line Tools 与 Python 3，以普通用户执行：

```sh
python3 tools/fetch-dependencies.py
python3 tools/audit-source.py
SST_TEST_SANITIZERS=undefined bash Test.command
bash Build.command
```

下载器固定并校验 SOF TGL 固件与 MacKernelSDK 的大小和 SHA256。固件只在录音需要时进入 DSP 易失内存，不写入主板闪存。构建输出在本目录的 `build/`；以上命令不会安装驱动、改 EFI、录音或重启。

本机使用 UBSan 完成测试；ASan 16 在 Tahoe 的 libpthread/dyld 初始化阶段失败。`tests/test_82ff_dai.py` 可独立运行，检查 216 字节 PDM0 消息和时钟字段。

固件：SOF 2.2 IPC3，固定 commit `fcd5ae85ead7ecd67ff199335b61fac825843ca0`，`sof-tgl.ri` 为 525,056 字节，SHA256 `97c8d8dea6048329bfbb1dbbd56609934d388b7e3a9acffe20df0b7daf14d7d3`。MacKernelSDK 固定 commit `3f750085caa17ec3a7880f11c11bf4f48cd6a164`。详见 [dependencies.lock.json](dependencies.lock.json)。

## 已验证产物与重新构建的区别

[tahoe26/audio](../../tahoe26/audio/) 中的驱动是原样保留的成功产物，主二进制 SHA256 为 `44070aa05b41086159730acc24021a771bda80e611f15e58de8193f37010383a`。源码快照见 [evidence/working-source.json](evidence/working-source.json)。

重新构建会生成新的资源、签名和哈希；配套发布器固定验证原成功产物的版本、UUID 与哈希。使用新构建时需同步发布器清单和身份校验值。

7 个内核源文件保留成功构建时的原字节。运行状态可查看 `CaptureActive`、`Failure` 和录音结束清理字段；`MicrophoneCaptureWorking=false` 是源码中的固定初始化值。

## 许可与来源

项目与上游适配代码采用 [BSD-3-Clause](LICENSE)，保留 MarkPLacer、DexterSLamb、Shubham Banekar、Intel 等原版权信息。固件及 SDK 的独立许可见 [NOTICE](NOTICE) 和 [licenses](licenses/)。

AppleHDA 540.3 输出兼容层按 [音频说明](../../tahoe26/audio/README.md) 在本机准备。
