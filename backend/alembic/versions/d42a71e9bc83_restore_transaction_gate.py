"""Coordinate clinic business writes with exclusive restore transactions.

Revision ID: d42a71e9bc83
Revises: c38f91a2d47b
"""
from alembic import op

revision = 'd42a71e9bc83'
down_revision = 'c38f91a2d47b'
branch_labels = None
depends_on = None

# Explicitly scoped tables only. Child rows without tenant_id use their parent.
TENANT_TABLES = (
    'users', 'appointments', 'attachments', 'batches', 'care_observations',
    'care_session_steps', 'care_sessions', 'clinical_attachment_links',
    'clinical_charges', 'clinical_event_targets', 'clinical_events',
    'clinical_projection_coverages', 'clinical_treatment_plan_items',
    'clinical_treatment_plan_phases', 'clinical_treatment_plans',
    'clinical_work_item_targets', 'clinical_work_items', 'expenses',
    'insurance_providers', 'lab_orders', 'lab_payments', 'laboratories',
    'material_learning_logs', 'material_sessions', 'materials', 'next_visit_requests',
    'patients', 'payments', 'prescriptions', 'price_lists', 'procedure_chart_styles',
    'procedure_material_weights', 'procedures', 'salary_payments', 'saved_medications',
    'stock_items', 'stock_movements', 'tooth_status', 'treatment_material_usages',
    'treatment_sessions', 'treatments', 'warehouses', 'workflow_templates',
)
NAMESPACE = 1146377304


def upgrade():
    if op.get_bind().dialect.name != 'postgresql':
        return
    op.execute(f'''
        CREATE FUNCTION dentix_clinic_write_gate() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE old_tenant integer; new_tenant integer;
        BEGIN
            IF TG_OP <> 'INSERT' THEN old_tenant := OLD.tenant_id; END IF;
            IF TG_OP <> 'DELETE' THEN new_tenant := NEW.tenant_id; END IF;
            IF old_tenant IS NOT NULL AND new_tenant IS NOT NULL AND old_tenant <> new_tenant THEN
                PERFORM pg_advisory_xact_lock_shared({NAMESPACE}, LEAST(old_tenant, new_tenant));
                PERFORM pg_advisory_xact_lock_shared({NAMESPACE}, GREATEST(old_tenant, new_tenant));
            ELSIF COALESCE(old_tenant, new_tenant) IS NOT NULL THEN
                PERFORM pg_advisory_xact_lock_shared({NAMESPACE}, COALESCE(old_tenant, new_tenant));
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
        END $$
    ''')
    for table in TENANT_TABLES:
        op.execute(f'CREATE TRIGGER clinic_write_gate BEFORE INSERT OR UPDATE OR DELETE ON "{table}" FOR EACH ROW EXECUTE FUNCTION dentix_clinic_write_gate()')
    op.execute(f'''
        CREATE FUNCTION dentix_price_item_write_gate() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE old_tenant integer; new_tenant integer;
        BEGIN
            IF TG_OP <> 'INSERT' THEN SELECT tenant_id INTO old_tenant FROM price_lists WHERE id = OLD.price_list_id; END IF;
            IF TG_OP <> 'DELETE' THEN SELECT tenant_id INTO new_tenant FROM price_lists WHERE id = NEW.price_list_id; END IF;
            IF old_tenant IS NOT NULL AND new_tenant IS NOT NULL AND old_tenant <> new_tenant THEN
                PERFORM pg_advisory_xact_lock_shared({NAMESPACE}, LEAST(old_tenant, new_tenant));
                PERFORM pg_advisory_xact_lock_shared({NAMESPACE}, GREATEST(old_tenant, new_tenant));
            ELSIF COALESCE(old_tenant, new_tenant) IS NOT NULL THEN
                PERFORM pg_advisory_xact_lock_shared({NAMESPACE}, COALESCE(old_tenant, new_tenant));
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
        END $$
    ''')
    op.execute('CREATE TRIGGER clinic_write_gate BEFORE INSERT OR UPDATE OR DELETE ON price_list_items FOR EACH ROW EXECUTE FUNCTION dentix_price_item_write_gate()')


def downgrade():
    if op.get_bind().dialect.name != 'postgresql':
        return
    op.execute('DROP TRIGGER clinic_write_gate ON price_list_items')
    op.execute('DROP FUNCTION dentix_price_item_write_gate()')
    for table in TENANT_TABLES:
        op.execute(f'DROP TRIGGER clinic_write_gate ON "{table}"')
    op.execute('DROP FUNCTION dentix_clinic_write_gate()')
