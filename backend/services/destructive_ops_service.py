"""
Destructive Operations Service

Implements Two-Man Rule for critical operations that require
approval from two different users before execution.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import secrets
import hashlib
from backend import models
from backend.utils.audit_logger import log_admin_action


class DestructiveOperationRequest:
    """Represents a pending destructive operation awaiting approval."""
    
    def __init__(
        self,
        operation: str,
        target_type: str,
        target_id: int,
        requestor_id: int,
        reason: str,
        expires_in_hours: int = 24
    ):
        self.operation = operation
        self.target_type = target_type
        self.target_id = target_id
        self.requestor_id = requestor_id
        self.reason = reason
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(hours=expires_in_hours)
        self.confirmation_token = secrets.token_urlsafe(32)
        self.status = "pending"
        self.approver_id = None
        self.approved_at = None


class DestructiveOpsService:
    """
    Service for managing destructive operations with Two-Man Rule.
    
    Two-Man Rule: Critical operations require approval from a different
    admin user before they can be executed.
    """
    
    # Operations requiring Two-Man Rule
    PROTECTED_OPERATIONS = [
        "permanent_delete_tenant",
        "permanent_delete_patient",
        "modify_super_admin_permissions",
        "rotate_encryption_keys",
        "bulk_data_export",
        "database_migration_destructive",
    ]
    
    def __init__(self, db: Session):
        self.db = db
        # In-memory store for pending requests (use Redis in production)
        self._pending_requests: dict = {}
    
    def requires_two_man_rule(self, operation: str) -> bool:
        """Check if operation requires Two-Man Rule."""
        return operation in self.PROTECTED_OPERATIONS
    
    def request_operation(
        self,
        operation: str,
        target_type: str,
        target_id: int,
        requestor: models.User,
        reason: str
    ) -> dict:
        """
        Request a destructive operation.
        
        Returns:
            dict with confirmation_token to share with approver
        """
        if not self.requires_two_man_rule(operation):
            return {
                "success": False,
                "error": "Operation does not require Two-Man Rule",
                "can_execute_directly": True
            }
        
        # Validate requestor is admin
        if requestor.role not in ["super_admin", "admin"]:
            return {
                "success": False,
                "error": "Only admins can request destructive operations"
            }
        
        # Create request
        request = DestructiveOperationRequest(
            operation=operation,
            target_type=target_type,
            target_id=target_id,
            requestor_id=requestor.id,
            reason=reason
        )
        
        # Store with hashed token as key
        token_hash = hashlib.sha256(request.confirmation_token.encode()).hexdigest()
        self._pending_requests[token_hash] = request
        
        # Log the request
        log_admin_action(
            self.db, requestor, "request_destructive_op", target_type, target_id,
            details=f"Requested {operation}: {reason}"
        )
        
        return {
            "success": True,
            "confirmation_token": request.confirmation_token,
            "expires_at": request.expires_at.isoformat(),
            "message": "تم إنشاء طلب العملية. يرجى مشاركة الرمز مع مدير آخر للموافقة."
        }
    
    def approve_operation(
        self,
        confirmation_token: str,
        approver: models.User
    ) -> dict:
        """
        Approve a pending destructive operation.
        
        The approver must be different from the requestor.
        """
        # Find request by token
        token_hash = hashlib.sha256(confirmation_token.encode()).hexdigest()
        request = self._pending_requests.get(token_hash)
        
        if not request:
            return {
                "success": False,
                "error": "طلب غير موجود أو منتهي الصلاحية"
            }
        
        # Check expiry
        if datetime.utcnow() > request.expires_at:
            del self._pending_requests[token_hash]
            return {
                "success": False,
                "error": "انتهت صلاحية الطلب"
            }
        
        # Two-Man Rule: approver must be different from requestor
        if approver.id == request.requestor_id:
            return {
                "success": False,
                "error": "لا يمكنك الموافقة على طلبك الخاص (Two-Man Rule)"
            }
        
        # Validate approver is admin
        if approver.role not in ["super_admin", "admin"]:
            return {
                "success": False,
                "error": "Only admins can approve destructive operations"
            }
        
        # Mark as approved
        request.status = "approved"
        request.approver_id = approver.id
        request.approved_at = datetime.utcnow()
        
        # Log the approval
        log_admin_action(
            self.db, approver, "approve_destructive_op", 
            request.target_type, request.target_id,
            details=f"Approved {request.operation} requested by user {request.requestor_id}"
        )
        
        return {
            "success": True,
            "operation": request.operation,
            "target_type": request.target_type,
            "target_id": request.target_id,
            "can_execute": True,
            "message": "تمت الموافقة. يمكن تنفيذ العملية الآن."
        }
    
    def execute_if_approved(
        self,
        confirmation_token: str,
        executor: models.User
    ) -> dict:
        """
        Execute operation if it has been approved.
        
        The executor must be the original requestor.
        """
        token_hash = hashlib.sha256(confirmation_token.encode()).hexdigest()
        request = self._pending_requests.get(token_hash)
        
        if not request:
            return {
                "success": False,
                "error": "طلب غير موجود"
            }
        
        if request.status != "approved":
            return {
                "success": False,
                "error": "الطلب لم تتم الموافقة عليه بعد"
            }
        
        # Only original requestor can execute
        if executor.id != request.requestor_id:
            return {
                "success": False,
                "error": "فقط صاحب الطلب الأصلي يمكنه التنفيذ"
            }
        
        # Mark as executed and remove
        request.status = "executed"
        del self._pending_requests[token_hash]
        
        # Log execution
        log_admin_action(
            self.db, executor, "execute_destructive_op",
            request.target_type, request.target_id,
            details=f"Executed {request.operation} (approved by user {request.approver_id})"
        )
        
        return {
            "success": True,
            "operation": request.operation,
            "target_type": request.target_type,
            "target_id": request.target_id,
            "executed": True,
            "approved_by": request.approver_id
        }
    
    def cancel_request(
        self,
        confirmation_token: str,
        canceller: models.User
    ) -> dict:
        """Cancel a pending request."""
        token_hash = hashlib.sha256(confirmation_token.encode()).hexdigest()
        request = self._pending_requests.get(token_hash)
        
        if not request:
            return {"success": False, "error": "طلب غير موجود"}
        
        # Only requestor or super_admin can cancel
        if canceller.id != request.requestor_id and canceller.role != "super_admin":
            return {
                "success": False,
                "error": "لا يمكنك إلغاء هذا الطلب"
            }
        
        del self._pending_requests[token_hash]
        
        log_admin_action(
            self.db, canceller, "cancel_destructive_op",
            request.target_type, request.target_id,
            details=f"Cancelled {request.operation}"
        )
        
        return {"success": True, "message": "تم إلغاء الطلب"}
    
    def get_pending_requests(self, user: models.User) -> list:
        """Get all pending requests visible to this user."""
        result = []
        
        for token_hash, request in self._pending_requests.items():
            # Super admins see all, others see only their requests
            if user.role == "super_admin" or user.id == request.requestor_id:
                result.append({
                    "operation": request.operation,
                    "target_type": request.target_type,
                    "target_id": request.target_id,
                    "status": request.status,
                    "created_at": request.created_at.isoformat(),
                    "expires_at": request.expires_at.isoformat(),
                    "is_mine": user.id == request.requestor_id
                })
        
        return result
