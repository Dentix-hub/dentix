"""Single-use tenant-bound browser OAuth attempts; no token is stored here."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, column
from rls.schemas import Command, ConditionArg, Permissive
from backend.core.security import EncryptedString
from .base import Base


class GoogleOAuthAttempt(Base):
    __tablename__ = 'google_oauth_attempts'
    __rls_policies__ = [Permissive(
        condition_args=[ConditionArg(comparator_name='tenant_id', type=Integer)],
        cmd=[Command.select, Command.update, Command.delete, Command.insert],
        custom_expr=lambda tenant: column('tenant_id') == tenant,
    )]
    id = Column(String(36), primary_key=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    state_digest = Column(String(64), nullable=False, unique=True)
    browser_digest = Column(String(64), nullable=False)
    nonce_digest = Column(String(64), nullable=False)
    verifier = Column(EncryptedString(1024), nullable=False)
    connection_generation = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    pending_account_sub = Column(String(255), nullable=True)
    pending_root_id = Column(String(255), nullable=True)
    pending_backup_id = Column(String(255), nullable=True)
    pending_image_id = Column(String(255), nullable=True)
