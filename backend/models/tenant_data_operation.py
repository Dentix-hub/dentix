"""Durable, tenant-scoped tracking for destructive clinic-data operations."""
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, column
from rls.schemas import Command, ConditionArg, Permissive

from .base import Base


class TenantDataOperation(Base):
    __tablename__ = 'tenant_data_operations'
    __rls_policies__ = [Permissive(
        condition_args=[ConditionArg(comparator_name='tenant_id', type=Integer)],
        cmd=[Command.select, Command.update, Command.delete, Command.insert],
        custom_expr=lambda tenant: column('tenant_id') == tenant,
    )]
    id = Column(String(36), primary_key=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    kind = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False)
    archive_digest = Column(String(64), nullable=False)
    confirmation_digest = Column(String(64), nullable=False)
    encrypted_payload = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_code = Column(String(64), nullable=True)
    request_key = Column(String(128), nullable=True)
    remote_file_id = Column(String(255), nullable=True)
    connection_generation = Column(Integer, nullable=True)
    attempts = Column(Integer, nullable=False, default=0, server_default='0')
    updated_at = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        Index('ix_tenant_data_operations_tenant_status', 'tenant_id', 'status'),
        Index('uq_tenant_data_operation_request', 'tenant_id', 'kind', 'request_key', unique=True),
    )
