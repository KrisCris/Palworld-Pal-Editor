import traceback
from typing import Any, Optional
from palworld_save_tools.archive import UUID

from .utils import Logger

LOGGER = Logger()

def toUUID(uuid_str):
    if isinstance(uuid_str, UUID):
        return uuid_str
    return UUID.from_str(str(uuid_str))

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
        if attr and nested_keys:
            for key in nested_keys:
                attr = attr.get(key, None)
                if attr is None:
                    raise KeyError(f"key {key} not found in dict {data_container}.")
        
        if attr and "value" in attr:
            return attr["value"]
        
        raise IndexError(f"Unable to index {attr} with key `value`")
    
    except Exception as e:
        LOGGER.warning((e, traceback.format_exc()))
        return None


class PalObjects:
    EMPTY_UUID = toUUID("00000000-0000-0000-0000-000000000000")

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
    def StrProperty(value: str):
        return {"id": None, "type": "StrProperty", "value": value}
    
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
    def IntProperty(value: int):
        return {"id": None, "type": "IntProperty", "value": value}
    
    @staticmethod
    def Int64Property(value: int):
        return {"id": None, "type": "Int64Property", "value": value}
    
    # @staticmethod
    # def GetInt64PropertyValue(data: dict) -> int:

    
    @staticmethod
    def FixedPoint64(value: int):
        return {
            "struct_type": "FixedPoint64",
            "struct_id": PalObjects.EMPTY_UUID,
            "id": None,
            "value": {
                "Value": PalObjects.Int64Property(value)
            },
            "type": "StructProperty"
        }