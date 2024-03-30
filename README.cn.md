# Palworld Pal Editor

<p align="center">
   <a href="/README.md">English</a> | <strong>简体中文</strong>
</p>

<p align='center'>
<a href="https://github.com/KrisCris/Palworld-Pal-Editor"><img alt="GitHub Repo Stars" src="https://img.shields.io/github/stars/KrisCris/Palworld-Pal-Editor?style=for-the-badge"></a>&nbsp;&nbsp;
<a href="https://github.com/KrisCris/Palworld-Pal-Editor/releases/latest"><img alt="GitHub Repo Downloads" src="https://img.shields.io/github/downloads/KrisCris/Palworld-Pal-Editor/total?style=for-the-badge"></a>&nbsp;&nbsp;
<a href="https://discord.gg/Dg5CcDem"><img alt="Discord Server" src="https://dcbadge.vercel.app/api/server/Dg5CcDem"></a>&nbsp;&nbsp;
<img alt="Python" src="https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue">&nbsp;&nbsp;
<img alt="Vue.js" src="https://img.shields.io/badge/Vue%20js-35495E?style=for-the-badge&logo=vuedotjs&logoColor=4FC08D">&nbsp;&nbsp;
</p>

## 这是什么？

#### 幻兽帕鲁 帕鲁 编辑器

https://www.bilibili.com/video/av1402092377

**为了防止数据丢失，请注意备份存档 (这个工具会自动帮你备份)**

***如果遇到BUG欢迎提交issue***

<img width="720" alt="Screenshot" src="https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/51a9c262-a71a-4008-b2a3-f4a68e78046a">

---

- [Palworld Pal Editor](#palworld-pal-editor)
  - [这是什么？](#这是什么)
      - [幻兽帕鲁 帕鲁 编辑器](#幻兽帕鲁-帕鲁-编辑器)
  - [这个工具能干啥](#这个工具能干啥)
  - [使用](#使用)
    - [A. 使用打包的可执行文件](#a-使用打包的可执行文件)
    - [B. 通过 pip 安装](#b-通过-pip-安装)
    - [C. 使用 Docker Container](#c-使用-docker-container)
    - [D. 直接运行代码](#d-直接运行代码)
    - [可选命令行参数](#可选命令行参数)
    - [配置文件](#配置文件)
      - [命令行参数会覆盖并写入配置文件](#命令行参数会覆盖并写入配置文件)
  - [视频](#视频)
  - [未来开发计划？ (无ETA)](#未来开发计划-无eta)
  - [Star History](#star-history)
  - [贡献](#贡献)
  - [赞助](#赞助)
  - [感谢](#感谢)
  - [原因?](#原因)

---

## 这个工具能干啥

- [x] 生成帕鲁
- [x] 复制帕鲁
- [x] 删除帕鲁
- [x] 显示 / 隐藏 不在玩家帕鲁栏位中的帕鲁
- [x] 显示 / 隐藏 无用的帕鲁数据
- [x] 列出玩家和帕鲁
- [x] 查看帕鲁数据
- [x] 改变帕鲁性别
- [x] 切换 BOSS / 稀有 / 塔主
- [x] 修改 / 删除帕鲁昵称
- [x] 增删 帕鲁学会的主动技能
- [x] 增删 帕鲁装备的主动技能
- [x] 增删 帕鲁被动技能
- [x] 修改 帕鲁等级
- [x] 修改 帕鲁浓缩机等级
- [x] 修改 帕鲁魂强化等级
- [x] 修改 帕鲁种族
- [x] 修改 帕鲁个体值
- [x] 计算并展示 最大生命值，攻击力，防御力，工作速度 （除了最大生命值其他可能不准）
- [x] 移除 帕鲁工作疾病
- [x] 复活帕鲁
- [x] 修改 食物BUFF 的时间 （目前只支持CLI）

## 使用

### A. 使用打包的可执行文件

1. 下载Release页面的最新程序，或者你也可以去Actions里下载最近commits的打包（后者是最新的，但你很可能会遇到bug）。
2. （命令行参数可用。）

### B. 通过 pip 安装

1. 请确保你使用了 Python 3.11+
2. `pip install --upgrade palworld-pal-editor`
3. `python -m palworld_pal_editor`

### C. 使用 Docker Container

1. 克隆项目.
2. 复制 `./docker/sample-docker-compose.yml` 到 `./docker/docker-compose.yml`, 并根据需求做适当修改（网络不佳的用户建议传入代理环境变量）。
3. 运行 `./build_and_run_docker.sh` 以构建容器并运行容器。（Windows的话你把里面的命令复制出来手动跑就行了）。

### D. 直接运行代码

1. 安装 Python 3.11+ 和 node.js
2. 克隆 / 下载项目代码
3. 在项目文件夹里运行，Windows：`setup_and_run.ps1`， Unix-like系统：`setup_and_run.sh`.

### 可选命令行参数

```text
options:
  -h, --help           show this help message and exit
  --lang LANG          Language for the application. options: en, zh-CN, ja
  --path PATH          Path to the save folder.
  --mode MODE          Running Mode, options: cli, gui, web
  --port PORT          Port used for WebUI mode.
  --password PASSWORD  Password for WebUI.
```

### 配置文件

#### 命令行参数会覆盖并写入配置文件

默认:

```json
// config.json
{
    "i18n": "en",
    "mode": "web",
    "port": 58080,
    "path": null,
    "password": null,
    "JWT_SECRET_KEY": "X2Nvbm5sb3N0"
}
```

自定义:

```json
// config.json
{
    "i18n": "zh-CN",
    "mode": "gui",
    "port": 12345,
    "path": "/path/to/save/folder",
    "password": "YOUR PASSWORD",
    "JWT_SECRET_KEY": "YOUR SECRETS"
}
```

## 视频

- DOCKER

https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/d7008b22-a2ff-4a2c-8903-32bab0922b32

- GUI / WEB
  

https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/66f3cb1e-f1fc-401e-b8a1-987ac3e6b02d

- CLI: (old, but you get the idea)

https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/02284dda-f1d7-40af-b12d-6b4ae11d4113

## 未来开发计划？ (无ETA)

- [ ] 改进网页端（一开始是打算做桌面端程序的，但想着dockerfile都写了，就临时改主意搓了一个。我这坨屎山vue实在是写的太乱了qwq）。
- [ ] 桌面端, 或者干脆用 [Textual](https://textualize.io/) 做一个控制台UI， XD。
- [ ] 移动帕鲁存储栏位？或者修改主人？ idk
- [ ] More Stuff...

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=KrisCris/Palworld-Pal-Editor&type=Date)](https://star-history.com/#KrisCris/Palworld-Pal-Editor&Date)

## 贡献

1. 如果你遇到任何问题，或者需要新功能，请先搜索 [Issues](https://github.com/KrisCris/Palworld-Pal-Editor/issues) 板块。
2. 先看一看最新的分支
3. 如果你真的想贡献的话，建议先开PR让大家知道。

## 赞助

[ko-fi ❤️](https://ko-fi.com/connlost)

<img width="256" alt="AliPay" src="https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/78d85efd-3a3f-4007-a8a3-4c7ada0cfc5b">

## 感谢

- 感谢 [Take-Me1010](https://github.com/Take-Me1010) 的日语翻译。

---

- 感谢 [MagicBear](https://github.com/magicbear) 大大的超快速存档载入方法。
- 感谢 [palworld-save-tools](https://github.com/cheahjs/palworld-save-tools) 提供的存档解包工具。
- 感谢 [MagicBear](https://github.com/magicbear) 大佬的 [Palworld-Server-Toolkit](https://github.com/magicbear/palworld-server-toolkit) 的启发。
- 感谢 [EternalWraith](https://github.com/EternalWraith) 的 [PalEdit](https://github.com/EternalWraith/PalEdit) 的启发。

## 原因?

1. 感谢各位能和我一起玩游戏的朋友 ❤。
2. 复健一下两三年没用的Python。
3. 这个人实在是太无聊了。
4. 这个人已经被另外一个工具的BUG折磨坏了。
