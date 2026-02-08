# 🔒 Week 1: الأمان والبنية التحتية

## الأهداف
- رفع مستوى الأمان إلى معايير عالمية
- تحسين أداء قاعدة البيانات
- إعداد نظام Caching فعال
- تحسين Error Handling

---

## Day 1-2: Authentication & Authorization

### 1. Two-Factor Authentication (2FA)

#### Backend Implementation
```python
# File: backend/auth/two_factor.py

import pyotp
import qrcode
from io import BytesIO
import base64

class TwoFactorAuth:
    @staticmethod
    def generate_secret(user_id: int) -> str:
        """Generate TOTP secret for user"""
        secret = pyotp.random_base32()
        # Save to database
        return secret
    
    @staticmethod
    def get_provisioning_uri(user_email: str, secret: str) -> str:
        """Generate QR code URI"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=user_email,
            issuer_name="Smart Clinic"
        )
    
    @staticmethod
    def generate_qr_code(uri: str) -> str:
        """Generate QR code as base64 image"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    @staticmethod
    def verify_token(secret: str, token: str) -> bool:
        """Verify TOTP token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> list:
        """Generate backup codes for account recovery"""
        import secrets
        return [secrets.token_hex(4).upper() for _ in range(count)]
```

#### API Endpoints
```python
# File: backend/routers/auth.py

@router.post("/auth/2fa/setup")
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Setup 2FA for user"""
    # Generate secret
    secret = TwoFactorAuth.generate_secret(current_user.id)
    
    # Save to database (encrypted)
    current_user.two_factor_secret = encrypt_data(secret)
    db.commit()
    
    # Generate QR code
    uri = TwoFactorAuth.get_provisioning_uri(current_user.email, secret)
    qr_code = TwoFactorAuth.generate_qr_code(uri)
    
    # Generate backup codes
    backup_codes = TwoFactorAuth.generate_backup_codes()
    
    # Save hashed backup codes
    for code in backup_codes:
        backup = BackupCode(
            user_id=current_user.id,
            code_hash=hash_password(code),
            used=False
        )
        db.add(backup)
    db.commit()
    
    return {
        "qr_code": qr_code,
        "secret": secret,  # Show once
        "backup_codes": backup_codes
    }

@router.post("/auth/2fa/verify")
async def verify_2fa(
    token: str,
    current_user: User = Depends(get_current_user)
):
    """Verify 2FA token"""
    secret = decrypt_data(current_user.two_factor_secret)
    
    if TwoFactorAuth.verify_token(secret, token):
        # Enable 2FA
        current_user.two_factor_enabled = True
        db.commit()
        return {"success": True}
    
    raise HTTPException(status_code=400, detail="Invalid token")

@router.post("/auth/login")
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Enhanced login with 2FA support"""
    # Verify username/password
    user = authenticate_user(credentials.email, credentials.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if 2FA is enabled
    if user.two_factor_enabled:
        # Return temporary token
        temp_token = create_temp_token(user.id)
        return {
            "requires_2fa": True,
            "temp_token": temp_token
        }
    
    # Normal login
    access_token = create_access_token(user.id)
    return {"access_token": access_token}

@router.post("/auth/login/2fa")
async def login_2fa(
    temp_token: str,
    token: str,
    db: Session = Depends(get_db)
):
    """Complete login with 2FA"""
    # Verify temp token
    user_id = verify_temp_token(temp_token)
    user = db.query(User).get(user_id)
    
    # Verify 2FA token
    secret = decrypt_data(user.two_factor_secret)
    if not TwoFactorAuth.verify_token(secret, token):
        # Check backup codes
        if not verify_backup_code(user.id, token, db):
            raise HTTPException(status_code=400, detail="Invalid 2FA token")
    
    # Create session
    access_token = create_access_token(user.id)
    return {"access_token": access_token}
```

#### Frontend Implementation
```typescript
// File: src/features/auth/TwoFactorSetup.tsx

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import QRCode from 'qrcode.react';

export function TwoFactorSetup() {
  const [step, setStep] = useState<'qr' | 'verify' | 'backup'>('qr');
  const [secret, setSecret] = useState('');
  const [qrCode, setQrCode] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [token, setToken] = useState('');

  const setupMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/auth/2fa/setup');
      return res.data;
    },
    onSuccess: (data) => {
      setSecret(data.secret);
      setQrCode(data.qr_code);
      setBackupCodes(data.backup_codes);
    }
  });

  const verifyMutation = useMutation({
    mutationFn: async (token: string) => {
      await api.post('/auth/2fa/verify', { token });
    },
    onSuccess: () => {
      setStep('backup');
    }
  });

  return (
    <div className="max-w-md mx-auto p-6">
      {step === 'qr' && (
        <div className="space-y-4">
          <h2 className="text-2xl font-bold">تفعيل المصادقة الثنائية</h2>
          <p className="text-gray-600">
            امسح رمز QR باستخدام تطبيق Google Authenticator أو Authy
          </p>
          
          <div className="bg-white p-6 rounded-lg text-center">
            {qrCode ? (
              <img src={qrCode} alt="QR Code" className="mx-auto" />
            ) : (
              <Button onClick={() => setupMutation.mutate()}>
                إنشاء رمز QR
              </Button>
            )}
          </div>
          
          {secret && (
            <div className="bg-gray-100 p-4 rounded-lg">
              <p className="text-sm text-gray-600 mb-2">
                أو أدخل المفتاح يدوياً:
              </p>
              <code className="font-mono text-lg">{secret}</code>
            </div>
          )}
          
          {qrCode && (
            <Button onClick={() => setStep('verify')} className="w-full">
              التالي
            </Button>
          )}
        </div>
      )}

      {step === 'verify' && (
        <div className="space-y-4">
          <h2 className="text-2xl font-bold">تأكيد التفعيل</h2>
          <p className="text-gray-600">
            أدخل الرمز المكون من 6 أرقام من التطبيق
          </p>
          
          <Input
            type="text"
            maxLength={6}
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="000000"
            className="text-center text-2xl font-mono"
          />
          
          <Button
            onClick={() => verifyMutation.mutate(token)}
            disabled={token.length !== 6}
            className="w-full"
          >
            تأكيد
          </Button>
        </div>
      )}

      {step === 'backup' && (
        <div className="space-y-4">
          <h2 className="text-2xl font-bold">رموز الاسترجاع</h2>
          <Alert variant="warning">
            احفظ هذه الرموز في مكان آمن. يمكنك استخدامها لتسجيل الدخول
            إذا فقدت هاتفك.
          </Alert>
          
          <div className="grid grid-cols-2 gap-3 bg-gray-100 p-4 rounded-lg">
            {backupCodes.map((code, i) => (
              <code key={i} className="font-mono text-lg">
                {code}
              </code>
            ))}
          </div>
          
          <Button
            onClick={() => downloadBackupCodes(backupCodes)}
            variant="secondary"
            className="w-full"
          >
            تحميل الرموز
          </Button>
          
          <Button onClick={onComplete} className="w-full">
            إنهاء
          </Button>
        </div>
      )}
    </div>
  );
}
```

### 2. Enhanced Password Policy

```python
# File: backend/auth/password_policy.py

import re
from passlib.pwd import genword

class PasswordPolicy:
    MIN_LENGTH = 12
    MAX_LENGTH = 128
    
    # Common weak passwords to reject
    COMMON_PASSWORDS = [
        "password", "123456", "qwerty", "admin",
        "letmein", "welcome", "monkey", "dragon"
    ]
    
    @staticmethod
    def validate(password: str) -> tuple[bool, str]:
        """Validate password against policy"""
        
        # Length check
        if len(password) < PasswordPolicy.MIN_LENGTH:
            return False, f"يجب أن تكون كلمة المرور {PasswordPolicy.MIN_LENGTH} حرف على الأقل"
        
        if len(password) > PasswordPolicy.MAX_LENGTH:
            return False, f"كلمة المرور طويلة جداً (الحد الأقصى {PasswordPolicy.MAX_LENGTH})"
        
        # Complexity requirements
        if not re.search(r'[A-Z]', password):
            return False, "يجب أن تحتوي على حرف كبير واحد على الأقل"
        
        if not re.search(r'[a-z]', password):
            return False, "يجب أن تحتوي على حرف صغير واحد على الأقل"
        
        if not re.search(r'[0-9]', password):
            return False, "يجب أن تحتوي على رقم واحد على الأقل"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "يجب أن تحتوي على رمز خاص واحد على الأقل"
        
        # Check against common passwords
        if password.lower() in PasswordPolicy.COMMON_PASSWORDS:
            return False, "كلمة المرور شائعة جداً. اختر كلمة أكثر تعقيداً"
        
        # Check for sequential characters
        if PasswordPolicy._has_sequential(password):
            return False, "تجنب الأحرف أو الأرقام المتسلسلة"
        
        return True, "كلمة مرور قوية"
    
    @staticmethod
    def _has_sequential(password: str) -> bool:
        """Check for sequential characters like '123' or 'abc'"""
        for i in range(len(password) - 2):
            if (ord(password[i]) + 1 == ord(password[i+1]) and 
                ord(password[i+1]) + 1 == ord(password[i+2])):
                return True
        return False
    
    @staticmethod
    def check_password_history(
        user_id: int, 
        new_password: str, 
        db: Session,
        history_count: int = 5
    ) -> bool:
        """Check if password was used recently"""
        history = db.query(PasswordHistory).filter(
            PasswordHistory.user_id == user_id
        ).order_by(
            PasswordHistory.created_at.desc()
        ).limit(history_count).all()
        
        for old in history:
            if verify_password(new_password, old.password_hash):
                return False
        
        return True
    
    @staticmethod
    def generate_strong_password() -> str:
        """Generate a strong random password"""
        # Use passlib to generate strong password
        password = genword(length=16, charset="ascii_62")
        
        # Ensure it meets all requirements
        while not PasswordPolicy.validate(password)[0]:
            password = genword(length=16, charset="ascii_62")
        
        return password
```

```python
# File: backend/models/password_history.py

class PasswordHistory(Base):
    __tablename__ = "password_history"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")
```

```python
# Update change password endpoint
@router.post("/auth/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify old password
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="كلمة المرور الحالية غير صحيحة")
    
    # Validate new password
    is_valid, message = PasswordPolicy.validate(new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    # Check password history
    if not PasswordPolicy.check_password_history(current_user.id, new_password, db):
        raise HTTPException(
            status_code=400,
            detail="لا يمكن استخدام كلمة مرور سابقة"
        )
    
    # Save old password to history
    history = PasswordHistory(
        user_id=current_user.id,
        password_hash=current_user.password_hash
    )
    db.add(history)
    
    # Update password
    current_user.password_hash = hash_password(new_password)
    current_user.password_changed_at = datetime.utcnow()
    db.commit()
    
    return {"success": True}
```

---

## Day 3-4: Session Management & Data Encryption

### 3. Enhanced Session Management

```python
# File: backend/auth/session_manager.py

from datetime import datetime, timedelta
from typing import Optional
import hashlib
import secrets

class SessionManager:
    SESSION_TIMEOUT = 30  # minutes
    MAX_CONCURRENT_SESSIONS = 3
    
    @staticmethod
    def create_session(
        user_id: int,
        ip_address: str,
        user_agent: str,
        db: Session
    ) -> str:
        """Create new session"""
        
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        
        # Create device fingerprint
        fingerprint = hashlib.sha256(
            f"{user_agent}{ip_address}".encode()
        ).hexdigest()
        
        # Check concurrent sessions limit
        active_sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow()
        ).count()
        
        if active_sessions >= SessionManager.MAX_CONCURRENT_SESSIONS:
            # Revoke oldest session
            oldest = db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            ).order_by(UserSession.created_at.asc()).first()
            
            if oldest:
                oldest.is_active = False
                oldest.revoked_at = datetime.utcnow()
                oldest.revoke_reason = "MAX_SESSIONS_EXCEEDED"
        
        # Create session
        session = UserSession(
            user_id=user_id,
            session_token=session_token,
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint=fingerprint,
            expires_at=datetime.utcnow() + timedelta(
                minutes=SessionManager.SESSION_TIMEOUT
            ),
            is_active=True
        )
        
        db.add(session)
        db.commit()
        
        return session_token
    
    @staticmethod
    def verify_session(
        session_token: str,
        ip_address: str,
        user_agent: str,
        db: Session
    ) -> Optional[int]:
        """Verify and refresh session"""
        
        session = db.query(UserSession).filter(
            UserSession.session_token == session_token,
            UserSession.is_active == True
        ).first()
        
        if not session:
            return None
        
        # Check expiry
        if session.expires_at < datetime.utcnow():
            session.is_active = False
            session.revoke_reason = "EXPIRED"
            db.commit()
            return None
        
        # Verify device fingerprint (optional strict mode)
        fingerprint = hashlib.sha256(
            f"{user_agent}{ip_address}".encode()
        ).hexdigest()
        
        if session.device_fingerprint != fingerprint:
            # Log suspicious activity
            log_security_event(
                "DEVICE_MISMATCH",
                user_id=session.user_id,
                details=f"Original: {session.device_fingerprint}, Current: {fingerprint}"
            )
            
            # Optionally revoke session
            # session.is_active = False
            # session.revoke_reason = "DEVICE_MISMATCH"
            # db.commit()
            # return None
        
        # Refresh session
        session.last_activity = datetime.utcnow()
        session.expires_at = datetime.utcnow() + timedelta(
            minutes=SessionManager.SESSION_TIMEOUT
        )
        db.commit()
        
        return session.user_id
    
    @staticmethod
    def revoke_session(session_token: str, db: Session):
        """Revoke a session"""
        session = db.query(UserSession).filter(
            UserSession.session_token == session_token
        ).first()
        
        if session:
            session.is_active = False
            session.revoked_at = datetime.utcnow()
            session.revoke_reason = "USER_LOGOUT"
            db.commit()
    
    @staticmethod
    def revoke_all_sessions(user_id: int, db: Session):
        """Revoke all user sessions (useful for security)"""
        db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        ).update({
            "is_active": False,
            "revoked_at": datetime.utcnow(),
            "revoke_reason": "USER_REQUESTED"
        })
        db.commit()
```

```python
# File: backend/models/session.py

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_token = Column(String, unique=True, index=True)
    ip_address = Column(String)
    user_agent = Column(String)
    device_fingerprint = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime, nullable=True)
    revoke_reason = Column(String, nullable=True)
    
    user = relationship("User", back_populates="sessions")
```

---

## Day 5: Database Optimization & Caching

### 4. Database Optimization

```python
# File: backend/database/optimization.py

from sqlalchemy import Index, text

class DatabaseOptimizer:
    @staticmethod
    def create_indexes(engine):
        """Create performance indexes"""
        
        indexes = [
            # Patient indexes
            Index('idx_patient_name', 'patients', 'name'),
            Index('idx_patient_phone', 'patients', 'phone'),
            Index('idx_patient_national_id', 'patients', 'national_id'),
            Index('idx_patient_tenant', 'patients', 'tenant_id', 'deleted_at'),
            
            # Appointment indexes
            Index('idx_appointment_date', 'appointments', 'date'),
            Index('idx_appointment_doctor', 'appointments', 'doctor_id', 'date'),
            Index('idx_appointment_patient', 'appointments', 'patient_id'),
            Index('idx_appointment_status', 'appointments', 'status', 'date'),
            
            # Treatment indexes
            Index('idx_treatment_patient', 'treatments', 'patient_id', 'date'),
            Index('idx_treatment_procedure', 'treatments', 'procedure_id'),
            Index('idx_treatment_date', 'treatments', 'date'),
            
            # Inventory indexes
            Index('idx_material_tenant', 'materials', 'tenant_id', 'deleted_at'),
            Index('idx_stock_warehouse', 'stock_items', 'warehouse_id'),
            Index('idx_stock_batch', 'stock_items', 'batch_id'),
            Index('idx_batch_expiry', 'batches', 'expiry_date'),
            
            # Audit log indexes
            Index('idx_audit_user', 'audit_logs', 'user_id', 'timestamp'),
            Index('idx_audit_resource', 'audit_logs', 'resource_type', 'resource_id'),
            Index('idx_audit_timestamp', 'audit_logs', 'timestamp'),
        ]
        
        for index in indexes:
            try:
                index.create(engine, checkfirst=True)
                print(f"✅ Created index: {index.name}")
            except Exception as e:
                print(f"❌ Failed to create index {index.name}: {e}")
    
    @staticmethod
    def analyze_slow_queries(db: Session, threshold_ms: int = 500):
        """Analyze and log slow queries"""
        
        # Enable query logging (PostgreSQL)
        db.execute(text("""
            ALTER DATABASE your_db_name
            SET log_min_duration_statement = :threshold
        """), {"threshold": threshold_ms})
        
        # For SQLite, use EXPLAIN QUERY PLAN
        # For monitoring in production
```

### 5. Redis Caching Strategy

```python
# File: backend/services/cache_service.py

import redis
import json
from typing import Any, Optional
from functools import wraps
import hashlib

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

class CacheService:
    # Cache TTLs
    SHORT = 60  # 1 minute
    MEDIUM = 300  # 5 minutes
    LONG = 3600  # 1 hour
    
    @staticmethod
    def cache_key(*args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_str = f"{args}{kwargs}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    @staticmethod
    def get(key: str) -> Optional[Any]:
        """Get from cache"""
        try:
            value = redis_client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    @staticmethod
    def set(key: str, value: Any, ttl: int = MEDIUM):
        """Set cache value"""
        try:
            redis_client.setex(
                key,
                ttl,
                json.dumps(value, default=str)
            )
        except Exception as e:
            print(f"Cache set error: {e}")
    
    @staticmethod
    def delete(key: str):
        """Delete from cache"""
        try:
            redis_client.delete(key)
        except Exception as e:
            print(f"Cache delete error: {e}")
    
    @staticmethod
    def invalidate_pattern(pattern: str):
        """Invalidate all keys matching pattern"""
        try:
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        except Exception as e:
            print(f"Cache invalidate error: {e}")

def cache_result(ttl: int = CacheService.MEDIUM, key_prefix: str = ""):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{CacheService.cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached = CacheService.get(cache_key)
            if cached is not None:
                return cached
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            CacheService.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

# Usage example
@cache_result(ttl=CacheService.LONG, key_prefix="materials")
async def get_materials(tenant_id: int):
    """Get materials with caching"""
    # This will be cached for 1 hour
    return db.query(Material).filter(Material.tenant_id == tenant_id).all()
```

---

## Testing Checklist

### Security Tests
- [ ] Test 2FA setup flow
- [ ] Test 2FA login flow
- [ ] Test backup codes
- [ ] Test password policy validation
- [ ] Test password history
- [ ] Test session management
- [ ] Test concurrent sessions limit
- [ ] Test session timeout
- [ ] Test session revocation

### Performance Tests
- [ ] Benchmark database queries
- [ ] Test cache hit/miss rates
- [ ] Load test with 100 concurrent users
- [ ] Measure API response times

### Integration Tests
- [ ] Test complete authentication flow
- [ ] Test password reset with 2FA
- [ ] Test session refresh
- [ ] Test cache invalidation

---

## Deployment Checklist

- [ ] Backup database
- [ ] Run migrations
- [ ] Update environment variables
- [ ] Setup Redis
- [ ] Create database indexes
- [ ] Test in staging
- [ ] Monitor logs
- [ ] Update documentation

---

## Success Metrics

### Security
- ✅ 2FA adoption rate > 80%
- ✅ Zero password-related incidents
- ✅ All sessions properly managed

### Performance
- ✅ Database queries < 100ms (95th percentile)
- ✅ Cache hit rate > 70%
- ✅ API response time < 200ms

---

**Week 1 Status**: Ready for implementation 🚀
