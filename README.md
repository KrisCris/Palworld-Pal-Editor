# Palworld Pal Editor

<p align="center">
   <strong>English</strong> | <a href="/README.cn.md">简体中文</a>
</p>

<p align='center'>
<a href="https://github.com/KrisCris/Palworld-Pal-Editor"><img alt="GitHub Repo Stars" src="https://img.shields.io/github/stars/KrisCris/Palworld-Pal-Editor?style=for-the-badge"></a>&nbsp;&nbsp;
<a href="https://github.com/KrisCris/Palworld-Pal-Editor/releases/latest"><img alt="GitHub Repo Downloads" src="https://img.shields.io/github/downloads/KrisCris/Palworld-Pal-Editor/total?style=for-the-badge"></a>&nbsp;&nbsp;
<a href="https://discord.gg/FnuA95nMJ8"><img alt="Discord Server" src="https://dcbadge.vercel.app/api/server/FnuA95nMJ8"></a>&nbsp;&nbsp;
<img alt="Python" src="https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue">&nbsp;&nbsp;
<img alt="Vue.js" src="https://img.shields.io/badge/Vue%20js-35495E?style=for-the-badge&logo=vuedotjs&logoColor=4FC08D">&nbsp;&nbsp;
</p>

## Supported Language

- **English** | **日本語** | **简体中文**

> [!NOTE]
> The UI is hardcoded in English, but there isn't much text, and the emojis should be very easy to understand.
>
> At the end of the day, you can always use Chrome translation, if you are running it in web mode. ***(You don't need to worry about translation messing up the data we write to the save, we are not using plain text.)***

## What is this?

### A Palworld Pal Editor developed by _connlost with ❤️

<https://youtu.be/v9U60jj5Ugw>

 ~~(yeah i am just too lazy to change github username)~~

> [!NOTE]
> **This tool currently only supports the Steam version of Palworld, if you are playing the Xbox Game Pass version, you can look into these two tools for save format conversion:**
>
> - [XGP-save-extractor (XGP -> Steam)](https://github.com/windwq/XGP-save-extractor)
> - [Palworld XGP Save Importer (Steam -> XGP)](https://github.com/HarukaMa/palworld-xgp-import)
>
> Meanwhile, you are welcomed to submit a xbox game save, so that I can look into.

> [!IMPORTANT]
> ***Always backup your save in case corruption happens. (The tool does backup files for you.)***
>
> ***[LET ME KNOW](https://github.com/KrisCris/Palworld-Pal-Editor/issues) IF ANY BUG PRESENTS.***

<img width="720" alt="Screenshot" src="https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/51a9c262-a71a-4008-b2a3-f4a68e78046a">

---

- [Palworld Pal Editor](#palworld-pal-editor)
  - [Supported Language](#supported-language)
  - [What is this?](#what-is-this)
    - [A Palworld Pal Editor developed by \_connlost with ❤️](#a-palworld-pal-editor-developed-by-_connlost-with-️)
  - [What This Tool Can Do](#what-this-tool-can-do)
  - [Usage](#usage)
    - [Option A. Use Pre-Built Binary](#option-a-use-pre-built-binary)
    - [Option B. Install via pip](#option-b-install-via-pip)
    - [Option C. Docker Container](#option-c-docker-container)
    - [Option D. Directly Run the Code](#option-d-directly-run-the-code)
    - [Optional Command-line Args](#optional-command-line-args)
    - [Config File](#config-file)
  - [Videos](#videos)
  - [Possible Roadmap? (NO ETA)](#possible-roadmap-no-eta)
  - [Star History](#star-history)
  - [Contribution](#contribution)
  - [Sponsor](#sponsor)
  - [Thanks](#thanks)
  - [Why?](#why)

---

## What This Tool Can Do

- [x] Spawn Pal
- [x] Duplicate Pal
- [x] Delete Pal
- [x] Show / Hide pals that are not in player pal containers (e.g. Pals in viewing cage, (or taken away by other players, prior Palworld v0.1.5))
- [x] Show (so you can delete them) / hide pals that are not displayed in game (Ghost Pals).
- [x] Unlock Viewing Cage for Selected player (multiplayer server)
- [x] List Players and Pals
- [x] Inspect Pal Stats
- [x] Change Pal Gender
- [x] Toggle BOSS / Rare / Tower
- [x] Change Pal NickName
- [x] Add / Remove Pal Learned Attacks
- [x] Add / Remove Pal Equipped Attacks
- [x] Change Pal Level / Exp
- [x] Change Pal Condenser Level
- [x] Change Pal Soul Levels
- [x] Change CharacterID (Pal Species)
- [x] Change Pal Passive Skills
- [x] Change Pal IV
- [x] ~~Calculate MaxHP~~ (MaxHP no longer stored in game save.)
- [x] Remove Pal Sicks
- [x] Revive Pals
- [x] Edit Food Buff Timer (Only if the pal has food buff, and cli only)

## Usage

> [!NOTE]
> You can always run the editor in a modern web browser, in case the GUI isn't working properly for you.
>
> Alternatively you can find the version that uses Chromium [here](https://github.com/KrisCris/Palworld-Pal-Editor/actions?query=branch%3AQWebEngineView), which should hopefully fix all the GUI issues.

### Option A. Use Pre-Built Binary

***Just run the executable, you don't need to install Python.***

- Stable Version:
  - [Github Release](https://github.com/KrisCris/Palworld-Pal-Editor/releases)
  - [Nexusmods](https://www.nexusmods.com/palworld/mods/995)
- Nightly Builds:
  - [Github Actions Artifacts](https://github.com/KrisCris/Palworld-Pal-Editor/actions)

### Option B. Install via pip

1. Make sure you have Python 3.11+
2. `pip install --upgrade palworld-pal-editor`
3. `python -m palworld_pal_editor`

### Option C. Docker Container

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

> [!IMPORTANT]
> These videos show you how to run the code. If you are using the pre-built executable, you can skip these part.

- DOCKER

https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/d7008b22-a2ff-4a2c-8903-32bab0922b32

- GUI / WEB
  
https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/66f3cb1e-f1fc-401e-b8a1-987ac3e6b02d

- CLI: (old, but you get the idea)

https://github.com/KrisCris/Palworld-Pal-Editor/assets/38860226/02284dda-f1d7-40af-b12d-6b4ae11d4113

## Possible Roadmap? (NO ETA)

- [ ] Improve WebUI (I am bad at frontend dev, sorry! Contribution appreciated.)
- [ ] Real GUI, or maybe just a Terminal GUI using [Textual](https://textualize.io/).
- [ ] Move Pal to Different Slots? Change owner? IDK...
- [ ] More Stuff...

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=KrisCris/Palworld-Pal-Editor&type=Date)](https://star-history.com/#KrisCris/Palworld-Pal-Editor&Date)

## Contribution

1. If you found a bug, or are looking for a feature, please check [Issues](https://github.com/KrisCris/Palworld-Pal-Editor/issues) first.
2. If you want to contribute code, please check out the latest branch.
3. Open a PR so everyone knows what you are working on.

## Sponsor

[ko-fi ❤️](https://ko-fi.com/connlost)

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
