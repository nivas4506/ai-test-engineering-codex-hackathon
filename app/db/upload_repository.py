from __future__ import annotations

from sqlalchemy import select

from app.db.models import UploadedRepository
from app.db.session import get_db_session


class UploadRepository:
    def upsert_upload(
        self,
        upload_id: str,
        original_filename: str,
        bundle_bytes: bytes,
        owner_user_id: int | None = None,
        bundle_name: str = "repository.zip",
    ) -> UploadedRepository:
        with get_db_session() as session:
            record = session.scalar(select(UploadedRepository).where(UploadedRepository.upload_id == upload_id))
            if record is None:
                record = UploadedRepository(
                    upload_id=upload_id,
                    owner_user_id=owner_user_id,
                    original_filename=original_filename,
                    bundle_name=bundle_name,
                    bundle_bytes=bundle_bytes,
                )
                session.add(record)
            else:
                record.original_filename = original_filename
                record.bundle_name = bundle_name
                record.bundle_bytes = bundle_bytes
                if owner_user_id is not None:
                    record.owner_user_id = owner_user_id

            session.commit()
            session.refresh(record)
            return record

    def get_upload(self, upload_id: str, owner_user_id: int | None = None) -> UploadedRepository | None:
        with get_db_session() as session:
            query = select(UploadedRepository).where(UploadedRepository.upload_id == upload_id)
            if owner_user_id is not None:
                query = query.where(UploadedRepository.owner_user_id == owner_user_id)
            return session.scalar(query)
