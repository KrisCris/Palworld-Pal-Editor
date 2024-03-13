It doesn't matter if you use UUID or UUID str



# PlayerUId.sav

```python
save_data = player_gvas_file.properties['SaveData']['value']

PlayerUId = save_data['PlayerUId']['value'] # a18b721d-0000-0000-0000-000000000000
IndividualId = save_data['IndividualId']['value']['InstanceId']['value'] # a98710ed-ecb5-4c9b-828e-f67bc927dded

# Party Pal Container ID
OtomoCharacterContainerId = save_data['OtomoCharacterContainerId']['value']['ID']['value'] # 9f19d10e-012c-419a-be1b-d81942db4034

# Inventory Container IDs
save_data['inventoryInfo']

# how to unlock viewing cage
save_data['UnlockedRecipeTechnologyNames'] # ArrayProperty NameProperty
'DisplayCharacter' # viewing cage

# Pal Container ID
save_data['PalStorageContainerId'] # e96b5439-4fb8-444c-9a99-f9b5a5921f46
```





# CharacterContainerSaveData

```python
container_list = self.gvas_file.properties["worldSaveData"]["value"]["CharacterContainerSaveData"]["value"]

for container in container_list:
    container_id = PalObjects.get_BaseType(container["key"]["ID"])
    container_slots = container["Value"]["Slots"]["value"]["values"]
    for slot in container_slots:
        data = slot["RawData"]
        if data["custom_type"] != ".worldSaveData.CharacterContainerSaveData.Value.Slots.Slots.RawData": return
    	pal_InstanceID = data["value"]["instance_id"]
        
       
        
        
        
# find empty slot?
def get_empty_slot(uuid):
    container = self.container_map.get(uuid)
    # todo
```



```python
for container in container_data:
    container_id = container["key"]["ID"]["value"]
    LOGGER.info(f"Container: {container_id}")
    container_slots = container["value"]["Slots"]["value"]["values"]
    for slot in container_slots:
        LOGGER.info(f"\t{str(slot["RawData"]["value"]["instance_id"])}")
        
# log all the container contents
```

