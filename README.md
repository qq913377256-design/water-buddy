# Water Buddy

Windows 喝水小助手。轻提醒、托盘常驻、可爱简约界面，使用 Python 和 PySide6 实现。

## 功能

- 今日喝水进度
- 一键记录一杯水
- 4 个单次喝水量选项：100 ml、150 ml、250 ml、300 ml
- 自定义提醒间隔
- 暂停提醒 30 分钟
- 系统托盘常驻
- 开机自动启动
- 新的一天自动切换到当天记录，今日进度从 0 开始
- Qt 原生轻通知
- 水位、呼吸、按钮回弹等非线性动效
- 本地 JSON 保存配置和今日记录

## 运行

安装 Python 3.10+ 后，在项目目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
water-buddy
```

如果 Python 没有加入 `PATH`，把第一行的 `python` 换成你的 `python.exe` 完整路径。

如果只想临时从源码目录启动：

```powershell
$env:PYTHONPATH = "src"
python -m water_buddy.main
```

## 数据位置

运行后配置保存在：

```text
%APPDATA%\WaterBuddy\state.json
```

开机启动使用当前用户注册表启动项：

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run\WaterBuddy
```

## 打包方向

使用内置脚本打包为 Windows `.exe`：

```powershell
.\scripts\build_exe.ps1
```

如果 Python 没有加入 `PATH`：

```powershell
.\scripts\build_exe.ps1 -Python C:\Path\To\python.exe
```

打包产物：

```text
dist\WaterBuddy\WaterBuddy.exe
```
