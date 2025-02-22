import EntryView from "@/views/EntryView.vue";

export default {
    AuthView_PW_Prompt_1: "你好! 似乎你在运行这个工具时设置了认证密码 🔐。",
    AuthView_PW_Prompt_2: "你现在需要输入正确的密码，以进行后续操作：",
    AuthView_BTN_Unlock: "解锁",

    EntryView_Greet_1: "你好呀！",
    EntryView_Greet_2: " > 感谢你下载并使用Palworld Pal Editor！",
    EntryView_Greet_3:
        " > 如果你正在以WebUI模式，或远程访问Docker容器的方式使用这个工具，请考虑设置密码，以防止未经授权的远程访问。",
    EntryView_Greet_4: " > 帕鲁编辑器的下载地址为：",
    EntryView_Greet_4_1: "或",
    EntryView_Greet_5: " 页面。",
    EntryView_Greet_6: " > 如果你喜欢这个工具，可以考虑赞助我，以帮助我继续开发和维护这个工具。访问我的",
    EntryView_Greet_7: " > 遇到问题？加入",
    EntryView_Greet_7_1: "或访问",
    EntryView_Greet_8: " > 我的BiliBili频道：",
    EntryView_Note_1:
        " > 如果你是第一次使用这个工具，你需要手动输入或选择 (仅限GUI模式) 正确的存档路径，即包含 Level.sav 文件的那个文件夹的目录。",
    EntryView_Note_2:
        " > 在成功载入存档后，存档的路径将会被保存，并在下次使用时自动为您输入。",
    EntryView_Note_3:
        " > 如果你在通过Docker容器的方式使用这个工具，请确保已经正确的映射了存档的路径，并且容器具有合适的文件访问权限。这里你只需要输入映射的路径。",
    EntryView_BTN_Path_Picker: "选择路径",
    EntryView_BTN_Load: "载入存档",
    EntryView_Period: "。",
    EntryView_Version_Warning: "此版本不是由官方 CI/CD 管道构建。请谨慎使用并验证来源。",


    Editor_Note_Ghost_Pal: "这只帕鲁很可能不存在于游戏中",
    Editor_Basic_Info: "基础信息",
    Editor_Species: "种族: ",
    Editor_Nickname: "昵称: ",
    Editor_Gender: "性别: ",
    Editor_Variant: "特殊种: ", // 不知道用什么词
    Editor_Pal_ID: "帕鲁对象 ID: ",
    Editor_Pal_Guild_ID: "帕鲁工会 ID: ",
    Editor_Pal_Slot: "帕鲁容器位置: ",
    Editor_Pal_Owner: "所有者: ",
    Editor_Pal_No_Owner: "无 (基地打工人)",
    Editor_Estimated_HP: "估算的最大生命值: ",
    Editor_Estimated_ATK: "估算的攻击力: ",
    Editor_Estimated_DEF: "估算的防御力: ",
    Editor_Estimated_WorkSpeed: "估算的制作速度: ",
    Editor_IV: "个体值",
    Editor_IV_HP: "生命值: ",
    Editor_IV_DEF: "防御力: ",
    Editor_IV_ATK: "攻击力: ",
    Editor_IV_MELEE: "近战 (未使用): ",
    Editor_Souls_Upgrade: "帕鲁强化 (力量雕像)",
    Editor_Souls_HP: "生命值: ",
    Editor_Souls_ATK: "攻击力: ",
    Editor_Souls_DEF: "防御力: ",
    Editor_Souls_CraftSpeed: "制作速度: ",
    Editor_Condenser: "帕鲁浓缩机",
    Editor_Condenser_Rank: "浓缩等级: ",
    Editor_Passive_Skills: "被动技能",
    Editor_Select_Skill: "选择添加的技能",
    Editor_Equipped_Skills: "装备的主动技能",
    Editor_Skill_ATK: "攻击力: ",
    Editor_Skill_CD: "冷却时间: ",
    Editor_Skill_EL: "元素: ",
    Editor_Mastered_Skills: "学会的主动技能 (升级帕鲁时对应的技能会被自动添加)",

    Editor_Suitabilities: "工作适应性",

    Editor_Btn_Export_Data: "导出数据",
    Editor_Btn_Dupe_Pal: "复制帕鲁",
    Editor_Btn_Delete_Pal: "删除帕鲁",
    Editor_Btn_Retrieve_Pal: "取回帕鲁",
    Editor_Btn_Heal_Pal: "消除工作疾病",
    Editor_Btn_Revive_Pal: "复活帕鲁",

    PalList_Text: "帕鲁列表",

    PlayerList_Text: "玩家列表",
    PlayerList_Viewing_Cage: "为选中的玩家解锁观赏笼。注：解锁后你可以直接建造它，但科技解锁菜单并不会显示。",

    PlayerList_Base_Pal: "基地",

    TopBar_Btn_Save: "保存更改",
    TopBar_Btn_Reload: "重新载入存档",
    TopBar_Btn_Main_Page: "返回主页",
    TopBar_Btn_HealAllPals: "治愈所有帕鲁",
    TopBar_Btn_Pal_OOB: "显示不在身边的帕鲁",
    TopBar_Btn_Pal_Ghost: "显示不存在的帕鲁",
    TopBar_Btn_Invalid_Options: "隐藏作弊选项",
    TopBar_Btn_Invalid_Options_ADs: "我不想把这个功能做成单独的付费版来赚钱，所以如果你喜欢这个工具，请考虑赞助我，以帮助我继续开发和维护这个工具。\n更多信息将会在弹出的页面展示。",

    TopBar_Btn_HealAllPals_Tooltips: "治愈帕鲁的所有负面状态，回复血量，饱食度。",
    TopBar_Pal_OOB_Tooltips: "显示不在玩家的帕鲁容器中的帕鲁，即，观赏笼中的帕鲁，或被其他人拿走的帕鲁。",
    TopBar_Pal_Ghost_Tooltips: "显示不存在的帕鲁，即游戏中找不到的帕鲁，比如，你已将其出售，丢弃，宰杀。",
    TopBar_Invalid_Options_Tooltips: "隐藏游戏中通常不可用的一些选项和下拉菜单，使用时请注意。",

    Alert_Successful_Save: "更改已成功保存到 {{path}}。",
};