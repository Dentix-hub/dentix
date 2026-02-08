#!/usr/bin/env python3
"""
Script to fix the tenant permanent deletion issue in admin.py
"""

import re

def fix_tenant_deletion():
    file_path = r"d:\smart-clinic-v2plus-main\smart-clinic-v2plus-main\backend\routers\admin.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Define the problematic function section
    old_function_part = '''        # --- Manual Cascade Deletion ---
        # We delete from child tables up to parent tables to avoid FK constraint errors
        # (even if cascades should handle it, explicit is safer for existing databases)

        # 1. System & Logs
        tables_to_clean = [
            (models.Notification, "Notification"),
            (models.AuditLog, "AuditLog"),
            (models.AIUsageLog, "AIUsageLog"),
            (models.SupportMessage, "SupportMessage"),
            (models.BackgroundJob, "BackgroundJob"),
            (models.TenantFeature, "TenantFeature"),
            (models.Expense, "Expense"),
            (models.SalaryPayment, "SalaryPayment"),
            (models.Payment, "Payment"),
            (models.LabOrder, "LabOrder"),
            (models.Laboratory, "Laboratory"),
            (models.Procedure, "Procedure"),
            (models.Treatment, "Treatment")
        ]

        for model_cls, model_name in tables_to_clean:
            try:
                if hasattr(model_cls, 'tenant_id'):
                    count = db.query(model_cls).filter(model_cls.tenant_id == tenant.id).delete(synchronize_session=False)
                    print(f"Deleted {count} from {model_name}")
            except Exception as e:
                print(f"[WARN] Failed to clean {model_name}: {e}")

        # 2. Appointments & Prescriptions (before Patients since they reference patient_id)
        try:
            # Delete appointments associated with patients in this tenant
            patient_ids = [p.id for p in db.query(models.Patient.id).filter(models.Patient.tenant_id == tenant.id).all()]
            if patient_ids:
                appointment_count = db.query(models.Appointment).filter(models.Appointment.patient_id.in_(patient_ids)).delete(synchronize_session=False)
                print(f"Deleted {appointment_count} appointments")

                prescription_count = db.query(models.Prescription).filter(models.Prescription.patient_id.in_(patient_ids)).delete(synchronize_session=False)
                print(f"Deleted {prescription_count} prescriptions")
        except Exception as e:
            print(f"[WARN] Appointment/Prescription cleanup error: {e}")

        # 3. Patients & dependent records
        try:
            patients = db.query(models.Patient).filter(models.Patient.tenant_id == tenant.id).all()
            for patient in patients:
                try:
                    # Delete attachments for this patient
                    if hasattr(models, 'Attachment'):
                        attachment_count = db.query(models.Attachment).filter(models.Attachment.patient_id == patient.id).delete(synchronize_session=False)
                        print(f"Deleted {attachment_count} attachments for patient {patient.id}")

                    db.delete(patient)
                except Exception as inner_e:
                     print(f"[WARN] Failed to delete patient {patient.id}: {inner_e}")
            print(f"Deleted {len(patients)} patients")
        except Exception as e:
            print(f"[WARN] Patient cleanup error: {e}")

        # 4. Users (Doctors, Staff)
        try:
            users_to_delete = db.query(models.User.id).filter(models.User.tenant_id == tenant.id).all()
            user_ids = [u.id for u in users_to_delete]

            if user_ids:
                # Clean up user-related tables
                try:
                    if hasattr(models, 'PasswordResetToken'):
                        token_count = db.query(models.PasswordResetToken).filter(models.PasswordResetToken.user_id.in_(user_ids)).delete(synchronize_session=False)
                        print(f"Deleted {token_count} password reset tokens")
                except Exception as e:
                    print(f"[WARN] PasswordResetToken cleanup error: {e}")

                try:
                    if hasattr(models, 'NotificationRead'):
                        notification_read_count = db.query(models.NotificationRead).filter(models.NotificationRead.user_id.in_(user_ids)).delete(synchronize_session=False)
                        print(f"Deleted {notification_read_count} notification reads")
                except Exception as e:
                    print(f"[WARN] NotificationRead cleanup error: {e}")

                try:
                    if hasattr(models, 'UserSession'):
                        session_count = db.query(models.UserSession).filter(models.UserSession.user_id.in_(user_ids)).delete(synchronize_session=False)
                        print(f"Deleted {session_count} user sessions")
                except Exception as e:
                    print(f"[WARN] UserSession cleanup error: {e}")

            user_count = db.query(models.User).filter(models.User.tenant_id == tenant.id).delete(synchronize_session=False)
            print(f"Deleted {user_count} users")
        except Exception as e:
             print(f"[WARN] User cleanup error: {e}")
'''
    
    # Define the new, improved function section
    new_function_part = '''        # Use a more targeted approach to handle cascading deletions properly
        # First, handle tables that might have issues with cascade deletion
        
        # Delete user-related data first
        user_ids = [u.id for u in db.query(models.User.id).filter(models.User.tenant_id == tenant.id).all()]
        if user_ids:
            # Delete related user data
            for table_attr in ['PasswordResetToken', 'NotificationRead', 'UserSession', 'LoginHistory']:
                if hasattr(models, table_attr):
                    table_model = getattr(models, table_attr)
                    try:
                        if hasattr(table_model, 'user_id'):
                            db.query(table_model).filter(table_model.user_id.in_(user_ids)).delete(synchronize_session=False)
                    except Exception as e:
                        print(f"[WARN] Failed to clean {table_attr}: {e}")

        # Delete patient-related data
        patient_ids = [p.id for p in db.query(models.Patient.id).filter(models.Patient.tenant_id == tenant.id).all()]
        if patient_ids:
            # Delete related patient data
            for table_attr in ['Appointment', 'Prescription', 'LabOrder', 'Treatment', 'Attachment', 'ToothStatus']:
                if hasattr(models, table_attr):
                    table_model = getattr(models, table_attr)
                    try:
                        if hasattr(table_model, 'patient_id'):
                            db.query(table_model).filter(table_model.patient_id.in_(patient_ids)).delete(synchronize_session=False)
                    except Exception as e:
                        print(f"[WARN] Failed to clean {table_attr}: {e}")

        # Now delete records that have direct tenant references
        tenant_specific_tables = [
            models.Expense, models.SalaryPayment, models.Payment, models.Laboratory,
            models.Procedure, models.AIUsageLog, models.SupportMessage, models.BackgroundJob,
            models.TenantFeature, models.Notification, models.AuditLog
        ]
        
        for table_model in tenant_specific_tables:
            try:
                if hasattr(table_model, 'tenant_id'):
                    db.query(table_model).filter(table_model.tenant_id == tenant.id).delete(synchronize_session=False)
            except Exception as e:
                print(f"[WARN] Failed to clean {table_model.__tablename__}: {e}")
'''
    
    # Replace the old part with the new part
    if old_function_part in content:
        content = content.replace(old_function_part, new_function_part)
        
        # Write the updated content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("Successfully updated the tenant deletion function!")
    else:
        print("Could not find the target section to replace. Looking for similar patterns...")
        
        # Alternative: Find the function by regex
        pattern = r'(\s*# --- Manual Cascade Deletion ---.*?)(\s*# \d+\. Finally, the Tenant)'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            old_section = match.group(1)
            print(f"Found section to replace. Length: {len(old_section)} characters")
            
            # Replace just this section
            content = content.replace(old_section, new_function_part)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("Successfully updated the tenant deletion function using regex!")
        else:
            print("Could not find the target section using regex either.")
            # Print a sample of the content around where the function should be
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'Manual Cascade Deletion' in line:
                    print(f"Line {i}: {line.strip()}")
                    for j in range(i, min(i+10, len(lines))):
                        print(f"Line {j}: {lines[j][:50]}...")
                    break

if __name__ == "__main__":
    fix_tenant_deletion()