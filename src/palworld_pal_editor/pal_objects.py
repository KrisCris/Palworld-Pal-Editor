from typing import Any, Optional
from palworld_save_tools.archive import UUID

from palworld_pal_editor.utils import Logger

LOGGER = Logger()

def isUUIDStr(uuid_str: str) -> Optional[UUID]:
        try:
            uuid = UUID.from_str(str(uuid_str))
            if str(uuid) == uuid_str.lower():
                return uuid
            raise Exception(f"{uuid_str} is not a valid UUID")
        except Exception:
            LOGGER.warning("isUUIDStr: {e}")
            return None

def toUUID(uuid_str: str) -> Optional[UUID]:
    if isinstance(uuid_str, UUID):
        return uuid_str
    return isUUIDStr(uuid_str)


def get_attr_value(data_container: dict, attr_name: str, nested_keys: list = None) -> Optional[Any]:
    """
    Generic method to retrieve the value of an attribute from the pal data.
    
    Parameters:
        attr_name (str): The name of the attribute to retrieve.
        nested_keys (list): A list of keys to navigate through nested dictionaries if necessary.
    
    Returns:
        Optional[Any]: The value of the attribute, or None if the attribute does not exist.
    """
    try:
        if data_container is None:
            raise TypeError("Expected dict, get None.")
        attr = data_container.get(attr_name)

        if attr is None:
            raise IndexError(f"Providing dict does not have `{attr_name}` attribute.")

        if nested_keys:
            for key in nested_keys:
                attr = attr.get(key, None)
                if attr is None:
                    raise KeyError(f"trying to get attr `{attr_name}`, but nested key `{key}` not found in dict {data_container}.")
        
        if attr and "value" in attr:
            return attr["value"]
        else:
            raise KeyError(f"trying to get attr `{attr_name}`, but final key `value` not found in dict {data_container}.")
    
    except Exception as e:
        # LOGGER.warning(e)
        return None


class PalObjects:
    EMPTY_UUID = toUUID("00000000-0000-0000-0000-000000000000")
    
    @staticmethod
    def StrProperty(value: str):
        return {"id": None, "type": "StrProperty", "value": value}
    
    @staticmethod
    def NameProperty(value: str):
        return {"id": None, "type": "NameProperty", "value": value}
    
    @staticmethod
    def IntProperty(value: int):
        return {"id": None, "type": "IntProperty", "value": value}
    
    @staticmethod
    def Int64Property(value: int):
        return {"id": None, "type": "Int64Property", "value": value}
    
    @staticmethod
    def FloatProperty(value: float):
        return {'id': None, 'type': 'FloatProperty', 'value': value}
    
    @staticmethod
    def BoolProperty(value: bool):
        return {"value":value, "id":"None", "type":"BoolProperty"}

    @staticmethod
    def get_BaseType(container: dict) -> str | int | float | bool | UUID:
        return container["value"]
    
    @staticmethod
    def set_BaseType(container: dict, value: str | int | float | bool | UUID):
        container["value"] = value

    @staticmethod
    def Guid(value: str | UUID):
        return {
            "struct_type":"Guid",
            "struct_id": PalObjects.EMPTY_UUID,
            "id":"None",
            "value":toUUID(value),
            "type":"StructProperty"
        }

    @staticmethod
    def EnumProperty(type: str, value: str):
        """
        Example:
        >>> "Gender":{
                "id":"None",
                "value": {
                    "type":"EPalGenderType",
                    "value":"EPalGenderType::Female"
                },
                "type":"EnumProperty"
            },
        """

        return {
            'id': None, 'type': 'EnumProperty', 'value': {
                'type': type,
                'value': value
            }}
    
    @staticmethod
    def get_EnumProperty(container: dict):
        return container["value"]["value"]
    
    @staticmethod
    def set_EnumProperty(container: dict, value: str):
        container["value"]["value"] = value

    @staticmethod
    def ArrayProperty(array_type: str, value: dict, custom_type: Optional[str]=None):
        """
        Example:
        >>> "RawData":{
                "array_type":"ByteProperty",
                "id":"None",
                "value":{...},
                "type":"ArrayProperty",
                "custom_type":".worldSaveData.CharacterSaveParameterMap.Value.RawData"
            }

        >>> "EquipWaza":{
                "array_type":"EnumProperty",
                "id":"None",
                "value":{
                    "values":[
                        "EPalWazaID::DarkBall",
                        "EPalWazaID::DarkWave",
                        "EPalWazaID::SandTornado"
                    ]
                },
                "type":"ArrayProperty"
            },

        >>> "PassiveSkillList":{
                "array_type":"NameProperty",
                "id":"None",
                "value":{
                    "values":[
                        "TrainerATK_UP_1",
                        "MoveSpeed_up_2",
                        "ElementBoost_Ice_1_PAL"
                    ]
                },
                "type":"ArrayProperty"
            },
        """

        struct = {
            "array_type": array_type,
            "id": "None",
            "value": value,
            "type": "ArrayProperty"
        }

        if custom_type:
            struct["custom_type"] = custom_type

    @staticmethod
    def get_ArrayProperty(container: dict) -> list[Any]:
        return container["value"]["values"]
    
    @staticmethod
    def add_ArrayProperty(container: dict, value: Any):
        PalObjects.get_ArrayProperty(container).append(value)

    @staticmethod
    def FixedPoint64(value: int):
        """
        Example:
        >>> "HP":{
            "struct_type":"FixedPoint64",
            "struct_id":"00000000-0000-0000-0000-000000000000",
            "id":"None",
            "value":{
                "Value":{
                    "id":"None",
                    "value":1690000,
                    "type":"Int64Property"
                }
            },
            "type":"StructProperty"
        },
        """

        return {
            "struct_type": "FixedPoint64",
            "struct_id": PalObjects.EMPTY_UUID,
            "id": None,
            "value": {
                "Value": PalObjects.Int64Property(value)
            },
            "type": "StructProperty"
        }

    @staticmethod
    def get_FixedPoint64(container: dict) -> int:
        return PalObjects.get_BaseType(container["value"]["Value"])
    
    @staticmethod
    def set_FixedPoint64(container: dict, value: int):
        PalObjects.set_BaseType(container["value"]["Value"], value)

    @staticmethod
    def get_container_value(container: dict) -> Optional[Any]:
        case_1 = {"StrProperty", "NameProperty", "IntProperty", "Int64Property", "FloatProperty", "BoolProperty"}
        match container:
            case {"type": type_str, **rest} if type_str in case_1:
                return PalObjects.get_BaseType(container)
            case {"type": "StructProperty", "struct_type": "Guid", **rest}:
                return PalObjects.get_BaseType(container)
            case {"type": "EnumProperty", **rest}:
                return PalObjects.get_EnumProperty(container)
            case {"type": "ArrayProperty", **rest}:
                return PalObjects.get_ArrayProperty(container)
            case {"type": "StructProperty", "struct_type": "FixedPoint64", **rest}:
                return PalObjects.get_FixedPoint64(container)
        return None