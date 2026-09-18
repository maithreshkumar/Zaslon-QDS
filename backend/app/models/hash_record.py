"""
Hash Record Entity Model.
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..db.base import Base
from ..core.datetime_utils import utc_now


class HashRecordModel(Base):
    __tablename__ = "hash_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    raw_message = Column(Text, nullable=False)
    message_bytes_len = Column(Integer, nullable=False)
    sha512_digest = Column(String(128), index=True, nullable=False)
    hash_encoding_format = Column(String(32), default="hex", nullable=False)
    # File-based signing additions
    file_name = Column(String(255), nullable=True)
    file_mime_type = Column(String(128), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    storage_path = Column(String(512), nullable=True)
    is_binary_file = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    session = relationship("SessionModel", back_populates="hash_record")

    @property
    def byte_length(self) -> int:
        return self.message_bytes_len

