# 在本机准备 AppleHDA 540.3 输出兼容层

本机输出使用 Lilu、AppleALC layout 101、嵌入 AppleHDA 540.3 的 SimpleHDA540PreProbe，以及同版本 AppleHDA HAL。此目录提供增量补丁、两个新增文件和本地构建工具。

固定上游：[laobamac/SimpleHDA](https://github.com/laobamac/SimpleHDA/tree/7517b04bb3e59306550f3c678e809e6494e5dd4b)，commit `7517b04bb3e59306550f3c678e809e6494e5dd4b`。该版本 NOTICE 保留作者版权，AppleHDA 为 Apple 专有组件。按下面步骤在本机取得输入并构建。

## 1. 准备完整 AppleHDA 540.3

需要 macOS、Python 3、Xcode Command Line Tools。以下命令从本仓库根目录执行，构建目录使用系统临时目录：

```sh
REPO_ROOT="$(pwd)"
HELPERS="$REPO_ROOT/tahoe26/audio/simplehda"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/audio540.XXXXXX")"
```

如果正在 Sonoma 上且 `/System/Library/Extensions/AppleHDA.kext` 是包含完整 Mach-O 的 540.3，可以直接验证并复制：

```sh
python3 "$HELPERS/prepare-applehda.py" copy \
  --source /System/Library/Extensions/AppleHDA.kext \
  --destination "$WORK/AppleHDA-540.3.kext"
```

如果源文件不完整或版本不符，可改用 **KDK 14.8.9 build 23J631**。这是本机成功构建使用的输入。可从 [Apple Developer Downloads](https://developer.apple.com/download/all/?q=Kernel%20Debug%20Kit) 获取，需要账户登录；本机历史下载来源为 Dortania KdkSupportPkg 镜像，已核对文件哈希和 Apple 签名。

预期文件 `Kernel_Debug_Kit_14.8.9_build_23J631.dmg`，909,962,391 字节，SHA256 `68f1d8fc168c56b60327e16db254f09c7502d39eaedda04ee6f26daa02e4f5d7`。将路径改为自己文件的位置后执行：

```sh
python3 "$HELPERS/prepare-applehda.py" extract \
  --dmg "$HOME/Downloads/Kernel_Debug_Kit_14.8.9_build_23J631.dmg" \
  --destination "$WORK/AppleHDA-540.3.kext"
```

两种方式二选一；脚本拒绝覆盖已有输出。提取脚本只读挂载 DMG，用 `pkgutil --expand-full` 展开到临时目录，并不安装 KDK。原包中的来源是 `KDK.pkg/Payload/System/Library/Extensions/AppleHDA.kext`。

脚本要求 Apple 签名有效、五个模块均为 540.3 且具已知 SHA256 的 x86_64 执行文件，并检查资源和 HAL。单独复核：

```sh
python3 "$HELPERS/prepare-applehda.py" verify --source "$WORK/AppleHDA-540.3.kext"
```

HAL 在原 bundle 的 `Contents/PlugIns/AppleHDAHALPlugIn.bundle`，版本 540.3，主二进制 SHA256 `f0995484b411b6d795c56c91ae3ee5c77c39c23f5096513f9cc99f088c312b45`。后续 HAL 安装目标是 `/Library/Audio/Plug-Ins/SimpleHDA/AppleHDAHALPlugIn.bundle`。

## 2. 获取固定上游并应用增量

```sh
git clone https://github.com/laobamac/SimpleHDA.git "$WORK/SimpleHDA"
git -C "$WORK/SimpleHDA" checkout --detach 7517b04bb3e59306550f3c678e809e6494e5dd4b
git -C "$WORK/SimpleHDA" apply --check --unidiff-zero "$HELPERS/preprobe.patch"
git -C "$WORK/SimpleHDA" apply --unidiff-zero "$HELPERS/preprobe.patch"
cp "$HELPERS/Sources/SHDAHDAUIdentity.hpp" "$WORK/SimpleHDA/Sources/"
cp "$HELPERS/Tools/test_hdau_identity.cpp" "$WORK/SimpleHDA/Tools/"
```

补丁只对 `Sources/kern_start.cpp` 增加可选的 HDAUniversal probe 隔离分支。原版权行保持不变；另外两个文件是新增的身份保护和测试。`source-pin.json` 保存固定上游与改动结果的哈希。

## 3. 使用 CLT 构建

```sh
python3 "$HELPERS/build-simplehda-clt.py" \
  --repo "$WORK/SimpleHDA" \
  --payload "$WORK/AppleHDA-540.3.kext" \
  --configuration Debug --hal-package
```

如果系统选择的开发工具目录不对，可再传 `--developer-dir "$(xcode-select -p)"` 或实际 CLT 目录。wrapper 调用上游固定依赖准备工具、payload 生成工具、clang 和静态验证工具；编译约定参考固定版本的 `Tools/generate_project.py`，保留来源说明，不依赖 xcodebuild。构建用普通用户，不需要 sudo。

2026-11-01 已使用 Python 3.9.6 和 Apple clang 16 完成本脚本的 CLT 构建、静态检查和 HAL 打包。

产生两个本地结果：

- `$WORK/SimpleHDA/Build/Debug/SimpleHDA.kext`：部署到 EFI 时使用目录名 `SimpleHDA540PreProbe.kext`，内部 ExecutablePath 仍为 `Contents/MacOS/SimpleHDA`。
- `$WORK/SimpleHDA/Build/SimpleHDA-HAL-1.0.0.pkg`：由原签名的 540.3 HAL 构建；不是把 HAL 改成版本 1.0.0，1.0.0 是 installer 的 SimpleHDA 版本。

构建完成后，按操作手册部署这两个本地产物。编译器、路径和签名差异会改变构建哈希。

## HDAUniversal 的适用边界

**新安装不需要安装 HDAUniversal。** 原机器的辅助内核集合遗留了 HDAUniversal 1.0.46，因此使用 `-shdaskiphdau` 在其 probe 前拦截。该分支固定校验这一版本的软件 UUID、探针指令和映像边界。

没有 `-shdaskiphdau` 时跳过隔离分支；启用参数但没有 HDAUniversal 时，注册可选 callback 后继续 SimpleHDA 原启动流程。

历史的 18 项 guard 测试使用指定版本的本地原执行文件，未将其放进此目录。wrapper 默认编译该测试但不运行；若使用者已经保有相同旧文件，可用 `--hdau-reference` 指定它，wrapper 先校验固定 SHA256 后才运行只读测试。它不会加载该驱动。

部署顺序、EFI 条目、系统批准和回退路径见仓库操作手册。
