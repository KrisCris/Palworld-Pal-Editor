from flask import Blueprint, jsonify, request
from palworld_pal_editor.api.util import reply

from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.utils import DataProvider

player_blueprint = Blueprint("player", __name__)

@player_blueprint.route("/player_pals", methods=["POST"])
def get_player_pals():
    id = request.json.get("PlayerUId")
    if id == "PAL_BASE_WORKER_BTN":
        pals = SaveManager().get_working_pals()
    else:
        player_entity = SaveManager().get_player(id)
        if not player_entity:
            return reply(1, None, f"Player {id} Not Found")
        pals = player_entity.get_sorted_pals()

    # I hate this piece of shit
    return reply(0, [{
        "InstanceId": str(pal.InstanceId) if pal.InstanceId else None,
        # "OwnerPlayerUId": str(pal.OwnerPlayerUId) if pal.OwnerPlayerUId else None,
        # "OwnerName": pal.OwnerName or None,
        "IconAccessKey": pal.IconAccessKey or None,
        "DataAccessKey": pal.DataAccessKey or None,
        # "I18nName": pal.I18nName or None,
        "DisplayName": pal.DisplayName or None,
        "Gender": pal.Gender.value if pal.Gender else None,
        # "IsTower": pal.IsTower or False,
        # "IsBOSS": pal.IsBOSS or False,
        # "IsRarePal": pal.IsRarePal or False,
        # "NickName": pal.NickName or "",
        # "Level": pal.Level or 1,
        # "Rank": pal.Rank.value if pal.Rank else 1,
        # "Rank_HP": pal.Rank_HP or 0,
        # "Rank_Attack": pal.Rank_Attack or 0,
        # "Rank_Defence": pal.Rank_Defence or 0,
        # "Rank_CraftSpeed": pal.Rank_CraftSpeed or 0,
        # "MaxHP": pal.MaxHP or None,
        # "ComputedAttack": pal.ComputedAttack or None,
        # "ComputedDefense": pal.ComputedDefense or None,
        # "PassiveSkillList": pal.PassiveSkillList or [],
        # "MasteredWaza": pal.MasteredWaza or [],
        # "Talent_HP": pal.Talent_HP or 0,
        # "Talent_Melee": pal.Talent_Melee or 0,
        # "Talent_Shot": pal.Talent_Shot or 0,
        # "Talent_Defense": pal.Talent_Defense or 0,
    } for pal in pals])
