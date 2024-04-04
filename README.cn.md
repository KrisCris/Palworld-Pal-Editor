# Palworld Pal Editor

<p align="center">
   <a href="/README.md">English</a> | <strong>简体中文</strong>
</p>

<p align='center'>
<a href="https://github.com/KrisCris/Palworld-Pal-Editor"><img alt="GitHub Repo Stars" src="https://img.shields.io/github/stars/KrisCris/Palworld-Pal-Editor?style=for-the-badge"></a>&nbsp;&nbsp;
<a href="https://github.com/KrisCris/Palworld-Pal-Editor/releases/latest"><img alt="GitHub Repo Downloads" src="https://img.shields.io/github/downloads/KrisCris/Palworld-Pal-Editor/total?style=for-the-badge"></a>&nbsp;&nbsp;
<a href="https://discord.gg/A9dXQPve"><img alt="Discord Server" src="https://dcbadge.vercel.app/api/server/A9dXQPve"></a>&nbsp;&nbsp;
<img alt="Python" src="https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue">&nbsp;&nbsp;
<img alt="Vue.js" src="https://img.shields.io/badge/Vue%20js-35495E?style=for-the-badge&logo=vuedotjs&logoColor=4FC08D">&nbsp;&nbsp;
</p>

## 支持的语言

- **English** | **日本語** | **简体中文**

> [!NOTE]
> 帕鲁名称，主动/被动技能等，均有翻译。
>
> 网页UI为英文，但没几个字，且 Emojis 应该非常易懂。如果还是有阅读困难，你可以使用 web 模式，并开启浏览器自带的网页翻译。

## 这是什么？

### 幻兽帕鲁 帕鲁 编辑器

<https://www.bilibili.com/video/av1001846154>

> [!NOTE]
> **本工具目前只支持Steam，如果你使用的是Xbox Game Pass版本，可以参考一下两个工具来转换存档格式：**
>
> - [XGP-save-extractor (XGP -> Steam)](https://github.com/windwq/XGP-save-extractor)
> - [Palworld XGP Save Importer (Steam -> XGP)](https://github.com/HarukaMa/palworld-xgp-import)

> [!IMPORTANT]
> **为了防止数据丢失，请注意备份存档 (这个工具会自动帮你备份)。**
>
> ***如果遇到BUG欢迎提交 [Issue](https://github.com/KrisCris/Palworld-Pal-Editor/issues) 。***

<img width="720" alt="Screenshot" src="https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/51a9c262-a71a-4008-b2a3-f4a68e78046a">

---

- [Palworld Pal Editor](#palworld-pal-editor)
  - [支持的语言](#支持的语言)
  - [这是什么？](#这是什么)
    - [幻兽帕鲁 帕鲁 编辑器](#幻兽帕鲁-帕鲁-编辑器)
  - [这个工具能干啥](#这个工具能干啥)
  - [使用](#使用)
    - [方案 A. 使用打包的可执行文件](#方案-a-使用打包的可执行文件)
    - [方案 B. 通过 pip 安装](#方案-b-通过-pip-安装)
    - [方案 C. 使用 Docker Container](#方案-c-使用-docker-container)
    - [方案 D. 直接运行代码](#方案-d-直接运行代码)
    - [可选命令行参数](#可选命令行参数)
    - [配置文件](#配置文件)
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

### 方案 A. 使用打包的可执行文件

***直接运行可执行文件，你不需要安装Python等依赖。***

- 稳定版:
  - [Github Release](https://github.com/KrisCris/Palworld-Pal-Editor/releases)
  - [Nexusmods](https://www.nexusmods.com/palworld/mods/995)
- 最新（你可能会遇到问题）:
  - [Github Actions Artifacts](https://github.com/KrisCris/Palworld-Pal-Editor/actions)

### 方案 B. 通过 pip 安装

1. 请确保你使用了 Python 3.11+
2. `pip install --upgrade palworld-pal-editor`
3. `python -m palworld_pal_editor`

### 方案 C. 使用 Docker Container

1. 克隆项目.
2. 复制 `./docker/sample-docker-compose.yml` 到 `./docker/docker-compose.yml`, 并根据需求做适当修改（网络不佳的用户建议传入代理环境变量）。
3. 运行 `./build_and_run_docker.sh` 以构建容器并运行容器。（Windows的话你把里面的命令复制出来手动跑就行了）。

### 方案 D. 直接运行代码

1. 安装 Python 3.11+ 和 node.js
2. 克隆 / 下载项目代码
3. 在项目文件夹里运行，Windows：`setup_and_run.ps1`， Unix-like系统：`setup_and_run.sh`.

### 可选命令行参数

```text
options:
  -h, --help           显示帮助
  --lang LANG          设置应用语言，可选项: en, zh-CN, ja
  --path PATH          存档文件夹的路径
  --mode MODE          运行模式，可选项: cli, gui, web
  --port PORT          WebUI监听的端口
  --password PASSWORD  WebUI的密码，默认无密码
```

### 配置文件

> [!NOTE]
>
> 1. 通常来说你不需要手动修改配置文件
> 2. 命令行参数会覆盖并写入配置文件

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
    "password": "YOUR PASSWORD FOR WEBUI AUTH",
    "JWT_SECRET_KEY": "JUST SOME RANDOM TEXTS"
}
```

## 视频

> [!IMPORTANT]
> 以下视频展示了如何从代码运行，如果你下载的可执行文件的话，你可以快进跳过那些部分。

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
