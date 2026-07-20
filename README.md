# Palworld Pal Editor

<h3 align="center">
   <strong>English</strong> | <a href="/README.cn.md">简体中文</a>
</h3>

<p align='center'>
<a href="https://github.com/KrisCris/Palworld-Pal-Editor"><img alt="GitHub Repo Stars" src="https://img.shields.io/github/stars/KrisCris/Palworld-Pal-Editor?style=for-the-badge"></a>&nbsp;
<a href="https://github.com/KrisCris/Palworld-Pal-Editor/releases/latest"><img alt="GitHub Release" src="https://img.shields.io/github/v/release/kriscris/palworld-pal-editor?display_name=tag&style=for-the-badge"></a>
<a href="https://github.com/KrisCris/Palworld-Pal-Editor/releases/latest"><img alt="GitHub Repo Downloads" src="https://img.shields.io/github/downloads/KrisCris/Palworld-Pal-Editor/total?style=for-the-badge"></a>&nbsp;
</p>

<p align='center'>
<img alt="Python" src="https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue">&nbsp;
<a href="https://pypi.org/project/palworld-pal-editor/"><img alt="PyPI - Version" src="https://img.shields.io/pypi/v/palworld-pal-editor?style=for-the-badge"></a>&nbsp;
<a href="https://pypi.org/project/palworld-pal-editor/"><img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dd/palworld-pal-editor?style=for-the-badge&label=PYPI%20DOWNLOADS"></a>&nbsp;
</p>

<p align='center'>
<a href="https://ko-fi.com/connlost"><img alt="Ko-Fi" src="https://img.shields.io/badge/Ko--fi-F16061?style=for-the-badge&logo=ko-fi&logoColor=white"></a>&nbsp;
<a href="https://www.paypal.com/paypalme/c0nnlost?country.x=US&locale.x=en_US"><img alt="PayPal" src="https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white"></a>&nbsp;
<a href="https://afdian.com/a/_connlost"><img width="100" src="https://pic1.afdiancdn.com/static/img/welcome/button-sponsorme.png" alt=""></a>&nbsp;
<a href="https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/78d85efd-3a3f-4007-a8a3-4c7ada0cfc5b"><img alt="AliPay" src="https://img.shields.io/badge/alipay-00A1E9?style=for-the-badge&logo=alipay&logoColor=white"></a>&nbsp;
<a href="https://github.com/user-attachments/assets/8dcbb43f-1270-49fd-b621-db70d2833de5"><img alt="WeChat" src="https://img.shields.io/badge/WeChat-07C160?style=for-the-badge&logo=wechat&logoColor=white"></a>&nbsp;
<a href="https://github.com/KrisCris/Palworld-Pal-Editor?tab=readme-ov-file#sponsor"><img alt="PayPal" src="https://img.shields.io/badge/sponsor-30363D?style=for-the-badge&logo=GitHub-Sponsors&logoColor=#EA4AAA"></a>&nbsp;
</p>

</p>
<p align='center'>
<a href="https://discord.gg/FnuA95nMJ8"><img alt="Discord Server" src="https://dcbadge.vercel.app/api/server/FnuA95nMJ8"></a>&nbsp;
</p>

<a href="https://github.com/KrisCris/Palworld-Pal-Editor/stargazers"><img width="720" alt="Star History Chart" src="https://api.star-history.com/svg?repos=KrisCris/Palworld-Pal-Editor&type=Date"></a>&nbsp;

## Supported Language

- **English** | **日本語** | **简体中文** | **French**

## What is this?

### A Palworld Pal Editor developed by _connlost with ❤️.

 ~~(yeah i am just too lazy to change github username)~~

- [0.13.0 Demo Video on BiliBili](https://www.bilibili.com/video/BV1xV3qzbE9r/?share_source=copy_web&vd_source=fe2d6c1e59f6c8d600d221e1800972f5)
- [Slightly updated video on Youtube](https://www.youtube.com/watch?v=PhSWpr0f70g&lc=Ugx1zdLQ-jqsf-O_ht14AaABAg)
- [An old showcase video posted on youtube](https://youtu.be/v9U60jj5Ugw), the idea should be the same though.

> [!NOTE]
> Steam Palworld Local Save Dir: `%localappdata%\Pal\Saved\SaveGames`
> 
> Your Game Save Dir: `%localappdata%\Pal\Saved\SaveGames\[Your Steam ID]\[Your GameSave ID]`
>
> **This tool currently only supports the Steam version of Palworld, if you are playing the Xbox Game Pass version, you can look into these two tools for save format conversion:**
>
> - [XGP-save-extractor (XGP -> Steam)](https://github.com/windwq/XGP-save-extractor)
> - [Palworld XGP Save Importer (Steam -> XGP)](https://github.com/HarukaMa/palworld-xgp-import)
>
> There are also some pinned messages in our Discord Server that provide knowledges on this topic.
>
> Be aware that these tools can be outdated.

> [!IMPORTANT]
> ***Always backup your save in case corruption happens. (The tool does backup files for you.)***
>
> ***[LET ME KNOW](https://github.com/KrisCris/Palworld-Pal-Editor/issues) IF ANY BUG PRESENTS.***

<img width="720" alt="Screenshot" src="https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/51a9c262-a71a-4008-b2a3-f4a68e78046a">

---

- [Palworld Pal Editor](#palworld-pal-editor)
  - [Supported Language](#supported-language)
  - [What is this?](#what-is-this)
    - [A Palworld Pal Editor developed by \_connlost with ❤️.](#a-palworld-pal-editor-developed-by-_connlost-with-️)
  - [What This Tool Can Do](#what-this-tool-can-do)
  - [Future TODOs (No ETA)](#future-todos-no-eta)
  - [Usage](#usage)
    - [Option A. Use Pre-Built Binary](#option-a-use-pre-built-binary)
    - [Option B. Install via pip](#option-b-install-via-pip)
    - [Option C. Docker Container](#option-c-docker-container)
      - [If you want to manually build it](#if-you-want-to-manually-build-it)
    - [Option D. Directly Run the Code](#option-d-directly-run-the-code)
    - [Optional Command-line Args](#optional-command-line-args)
    - [Config File](#config-file)
  - [Videos](#videos)
  - [Contribution](#contribution)
  - [Sponsor](#sponsor)
  - [Thanks](#thanks)
  - [Why?](#why)

---

## What This Tool Can Do

- [x] List Players and Their Pals
- [x] Modify Player Level
- [x] Modify Player Name
- [x] Unlock Tech
- [x] Show Pal Stats
- [x] Change Pal Species
- [x] Add Pal (To your inventory)
- [x] Delete Pal
- [x] Duplicate Pal
- [x] Change Pal Gender
- [x] Toggle Boss / Rare / Tower / Raid, etc.
- [x] Change Pal NickName
- [x] Add / Remove Pal Learned Attacks
- [x] Add / Remove Pal Equipped Attacks
- [x] Modify Pal Level / Exp
- [x] Modify Pal Condenser Level
- [x] Modify Pal Soul Levels
- [x] Modify Pal Work Suitabilities
- [x] Modify Pal Passive Skills
- [x] Modify Pal IV
- [x] Heal (and Revive) all pals and remove all negative effects.
- [x] Allow you to surpass the in-game limit, e.g. IV 255, Souls Level 255, Condenser Level 254; if you have the cheat option ON.
- [x] Edit Food Buff Timer (Only if the pal has food buff, and cli only)
- [x] Show / hide pals that are not stored in the player inventory (e.g. Pals in viewing cage, ~~(or taken away by other players, prior Palworld v0.1.5)~~)
- [x] Show / hide pals that are not displayed in game (Ghost Pals), so you can properly delete them.
- [x] Unlock Viewing Cage for Selected player (multiplayer server)
- And More...

## Future TODOs (No ETA)

- [ ] User defined skill presets.
- [ ] The player group and pal container implementation overhaul, which enables me to properly label the containers (i.e. the inventory), and group the pals based on that and change pal ownerships.
- [ ] A better UI?

## Usage

### Option A. Use Pre-Built Binary

***Just run the executable, you don't need to install Python.***

- Release Version:
  - [Nexusmods](https://www.nexusmods.com/palworld/mods/995)
  - [Github Release](https://github.com/KrisCris/Palworld-Pal-Editor/releases)
- Dev Builds:
  - [Github Actions Artifacts](https://github.com/KrisCris/Palworld-Pal-Editor/actions)

> [!NOTE]
> There is no need for you to read further if your goal is simply downloading the tool and modify your game save.
> 
> You can always run the editor in a modern web browser, in case the GUI isn't working properly for you. Also there is an [issue ticket](https://github.com/KrisCris/Palworld-Pal-Editor/issues/4) that you may found useful.
>
> Alternatively you can find the version that uses Chromium [here](https://github.com/KrisCris/Palworld-Pal-Editor/actions?query=branch%3AQWebEngineView), which should hopefully fix all the GUI issues.

### Option B. Install via pip

1. Make sure you have Python 3.11+
2. `pip install --upgrade palworld-pal-editor`
3. `python -m palworld_pal_editor`

### Option C. Docker Container

1. Download the compose file: `./docker/sample-docker-compose.yml`.
2. Rename it to `docker-compose.yml`, then configure it properly.
3. Run `docker compose up -d`.

#### If you want to manually build it

1. Clone the code.
2. Copy `./docker/sample-docker-compose.yml` to `./docker/docker-compose.yml`, then do necessary modifications.
3. Run `./build_and_run_docker.sh`, or just manually run the commands if you are using Windows.

### Option D. Directly Run the Code

1. Install Python 3.11+ and node.js.
2. Clone / Download the code
3. In the project directory, run `setup_and_run.ps1` for Windows Powershell, or `setup_and_run.sh` on Unix-like OS.
4. In `cli` mode, You can change language by calling `lang($LANG_CODE)`.

### Optional Command-line Args

```text
options:
  -h, --help           show this help message and exit
  --lang LANG          Language for the application. options: en, zh-CN, ja
  --path PATH          Path to the save folder.
  --mode MODE          Running Mode, options: cli, gui, web
  --port PORT          Port used for WebUI mode.
  --password PASSWORD  Password for WebUI.
```

### Config File

> [!NOTE]
>
> 1. There is no need for you to manually modify the config file.
> 2. Command line arguments override config, and will be saved.

Default:

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

Custom:

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

## Videos

> [!NOTE]
> In case someone is running the macOS build... 

https://github.com/user-attachments/assets/852662f7-b64a-49a6-8cde-0f800d5b5de0

> [!IMPORTANT]
> These videos show you how to run the code (and they are pretty old, but you get the idea). If you are using the pre-built executable, you can skip these parts.

- DOCKER

https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/d7008b22-a2ff-4a2c-8903-32bab0922b32

- GUI / WEB
  
https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/66f3cb1e-f1fc-401e-b8a1-987ac3e6b02d

- CLI: (old, but you get the idea)

https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/02284dda-f1d7-40af-b12d-6b4ae11d4113

## Contribution

1. If you found a bug, or are looking for a feature, please check [Issues](https://github.com/KrisCris/Palworld-Pal-Editor/issues) first.
2. If you want to contribute code, please check out the latest branch.
3. Open a PR so everyone knows what you are working on.

## Sponsor

**If you like this tool, consider supporting me to help me continue developing and maintaining it.**

<p align='center'>
<a href="https://ko-fi.com/connlost"><img alt="Ko-Fi" src="https://img.shields.io/badge/Ko--fi-F16061?style=for-the-badge&logo=ko-fi&logoColor=white"></a>&nbsp;
<a href="https://www.paypal.com/paypalme/c0nnlost?country.x=US&locale.x=en_US"><img alt="PayPal" src="https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white"></a>&nbsp;
<a href="https://afdian.com/a/_connlost"><img width="100" src="https://pic1.afdiancdn.com/static/img/welcome/button-sponsorme.png" alt=""></a>&nbsp;
<a href="https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/78d85efd-3a3f-4007-a8a3-4c7ada0cfc5b"><img alt="AliPay" src="https://img.shields.io/badge/alipay-00A1E9?style=for-the-badge&logo=alipay&logoColor=white"></a>&nbsp;
<a href="https://github.com/user-attachments/assets/8dcbb43f-1270-49fd-b621-db70d2833de5"><img alt="WeChat" src="https://img.shields.io/badge/WeChat-07C160?style=for-the-badge&logo=wechat&logoColor=white"></a>&nbsp;
</p>

[ko-fi ❤️](https://ko-fi.com/connlost)

[PayPal](https://www.paypal.com/paypalme/c0nnlost?country.x=US&locale.x=en_US)

<img width="256" alt="AliPay" src="https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/78d85efd-3a3f-4007-a8a3-4c7ada0cfc5b">
<img width="256" alt="WeChat" src="https://github.com/user-attachments/assets/8dcbb43f-1270-49fd-b621-db70d2833de5">

## Thanks

- [Take-Me1010](https://github.com/Take-Me1010) for Japanese translation.

---

- Fast game save loading code by [MagicBear](https://github.com/magicbear).
- Save conversion between GVAS and `.sav` by [palworld-save-tools](https://github.com/cheahjs/palworld-save-tools).
- Inspired by [MagicBear](https://github.com/magicbear)'s awesome [Palworld-Server-Toolkit](https://github.com/magicbear/palworld-server-toolkit).
- Inspired by [EternalWraith](https://github.com/EternalWraith)'s [PalEdit](https://github.com/EternalWraith/PalEdit).

## Why?

1. I made the tool for my friends who spent time playing this game with me ❤.
2. For practicing my 2-year untouched Python skills.
3. Fun, I am just too boring these days.
4. This guy had a really bad time fixing both his corrupted game save, and bugs of a similar tool.

## Related Resources

- [Palworld Guides](https://palworldguides.xyz/) — Palworld tier lists, base builds, Pal breeding chains, and boss strategies.
