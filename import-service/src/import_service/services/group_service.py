from sqlalchemy.orm import Session

from import_service.models.group import Group
from import_service.repositories.group_repository import GroupRepository
from import_service.schemas.group import GroupCreate, GroupUpdate


class GroupService:
    def __init__(self, db: Session):
        self.repo = GroupRepository(db)

    def get_all(self) -> list[Group]:
        return self.repo.get_all()

    def get_by_id(self, group_id: int) -> Group | None:
        return self.repo.get_by_id(group_id)

    def get_full(self, group_id: int) -> Group | None:
        return self.repo.get_full_by_id(group_id)

    def create(self, data: GroupCreate) -> Group:
        group = Group(**data.model_dump())
        return self.repo.save(group)

    def bulk_create(self, items_data: list[GroupCreate]) -> None:
        groups = [Group(**data.model_dump()) for data in items_data]
        self.repo.bulk_save(groups)

    def update(self, group_id: int, data: GroupUpdate) -> Group | None:
        group = self.repo.get_by_id(group_id)
        if group is None:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(group, key, value)

        return self.repo.save(group)

    def delete(self, group_id: int) -> bool:
        return self.repo.delete(group_id)