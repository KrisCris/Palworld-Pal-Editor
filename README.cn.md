# Palworld Pal Editor

<p align="center">
   <a href="/README.md">English</a> | <strong>简体中文</strong>
</p>

<p align='center'>
<img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/KrisCris/Palworld-Pal-Editor?style=for-the-badge">&nbsp;&nbsp;
<img alt="Python" src="https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue">&nbsp;&nbsp;
<img alt="Vue.js" src="https://img.shields.io/badge/Vue%20js-35495E?style=for-the-badge&logo=vuedotjs&logoColor=4FC08D">&nbsp;&nbsp;
</p>

## 这是什么？

#### 幻兽帕鲁 帕鲁 编辑器


**为了防止数据丢失，请注意备份存档 (这个工具会自动帮你备份)**

***如果遇到BUG欢迎提交issue***

<img width="720" alt="Screenshot 2024-03-03 at 1 39 32 PM" src="https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/b6259622-707a-4634-abea-c280dc7060d4">

---

- [Palworld Pal Editor](#palworld-pal-editor)
  - [这是什么？](#这是什么)
      - [幻兽帕鲁 帕鲁 编辑器](#幻兽帕鲁-帕鲁-编辑器)
  - [这个工具能干啥](#这个工具能干啥)
  - [使用](#使用)
    - [1. 直接运行代码](#1-直接运行代码)
    - [2. 打包的可执行文件](#2-打包的可执行文件)
    - [3. Docker Container](#3-docker-container)
    - [配置文件](#配置文件)
  - [视频](#视频)
  - [未来开发计划？ (无ETA)](#未来开发计划-无eta)
  - [贡献](#贡献)
  - [赞助](#赞助)
  - [感谢](#感谢)
  - [原因?](#原因)

---

## 这个工具能干啥

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

### 1. 直接运行代码

1. Install Python 3.11+
2. Clone / Download the code
3. In the project directory, run `setup_and_run.ps1` for Windows Powershell, or `setup_and_run.sh` on Unix-like OS.
4. Optional Params:
   - `--password yourPW` Login Auth, you may want this if you are running web mode.
   - `--mode <gui | web | cli>` You can launch the program in either `gui`, `web` or `cli` mode.
   - `--path /path/to/save/folder` Provide the path to the folder containing Level.sav.
   - `--port 8080` Port for web mode.
   - `--lang <zh-CN | en>` Currently supporting `zh-CN` and `en`. (Currrently hardcoded UI texts are English only.)
   - `--i` for enable interactive mode, you may want to use with `cli` mode.
5. You can change language in `cli` mode by calling `lang($LANG_CODE)`.

### 2. 打包的可执行文件

1. Download from GitHub Release Page, may not be bundled with the latest code.
2. Also support command line arguments mentioned above.

### 3. Docker Container

1. Clone the code.
2. You may want to take a look at `./docker/docker-compose.yml`, and do some modification.
3. Run `./build_and_run_docker.sh`, or just manually run the commends if you are using Windows.

### 配置文件

Default:

```json
// config.json
{
    "i18n": "en",
    "mode": "web",
    "port": 58080,
    "debug": false,
    "path": null,
    "password": null,
    "JWT_SECRET_KEY": "X2Nvbm5sb3N0"
}
```

Custom:

```json
// config.json
{
    "i18n": "zh-CN",
    "mode": "gui",
    "port": 12345,
    "debug": false,
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
- [ ] 添加删除帕鲁 （目前你可以抓棉悠悠改成别的（x）。。暂时还没研究怎么加。。）
- [ ] 移动帕鲁存储栏位？或者修改主人？ idk
- [ ] More Stuff...

## 贡献

1. 如果你遇到任何问题，或者需要新功能，请先搜索 [Issues](https://github.com/KrisCris/Palworld-Pal-Editor/issues) 板块。
2. 先看一看最新的分支
3. 如果你真的想贡献的话，建议先开PR让大家知道。

## 赞助

感谢你看到这里，但是暂未决定。

## 感谢

- 感谢 [MagicBear](https://github.com/magicbear) 大大的超快速存档载入方法。
- 感谢 [palworld-save-tools](https://github.com/cheahjs/palworld-save-tools) 提供的存档解包工具。
- 感谢 [MagicBear](https://github.com/magicbear) 大佬的 [Palworld-Server-Toolkit](https://github.com/magicbear/palworld-server-toolkit) 的启发。
- 感谢 [EternalWraith](https://github.com/EternalWraith) 的 [PalEdit](https://github.com/EternalWraith/PalEdit) 的启发。

## 原因?

1. 感谢各位能和我一起玩游戏的朋友 ❤。
2. 复健一下两三年没用的Python。
3. 这个人实在是太无聊了。
4. 这个人已经被另外一个工具的BUG折磨坏了。
