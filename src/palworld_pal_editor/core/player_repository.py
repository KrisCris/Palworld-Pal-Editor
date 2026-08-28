from typing import Iterator, Optional

from palworld_save_tools.archive import UUID

from palworld_pal_editor.core.player_entity import PlayerEntity
from palworld_pal_editor.utils import LOGGER


class PlayerRepository:
    """The session's PlayerEntity collection, keyed by PlayerUId string."""

    def __init__(self) -> None:
        self._players: dict[str, PlayerEntity] = {}

    def __len__(self) -> int:
        return len(self._players)

    def __iter__(self) -> Iterator[PlayerEntity]:
        return iter(self._players.values())

    def __contains__(self, player_uid: object) -> bool:
        return str(player_uid) in self._players

    def register(self, player: PlayerEntity) -> bool:
        """Add a player, refusing a second entity for the same PlayerUId."""
        player_uid = str(player.PlayerUId)
        existing = self._players.get(player_uid)
        if existing is not None:
            LOGGER.error(f"Duplicated player found: \n\t{existing}, skipping...")
            return False
        self._players[player_uid] = player
        return True

    def get(self, player_uid: UUID | str | None) -> Optional[PlayerEntity]:
        if player_uid is None:
            return None
        return self._players.get(str(player_uid))

    def all(self) -> list[PlayerEntity]:
        return list(self._players.values())

    def by_name(self, name: str) -> list[PlayerEntity]:
        return [player for player in self._players.values() if player.NickName == name]
