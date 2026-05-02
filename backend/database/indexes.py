"""
Database Index Optimization for Smart Clinic.

This migration adds optimized indexes for common query patterns
to improve performance significantly.

Usage:
    # Apply indexes
    python -c "from backend.database.indexes import apply_indexes; apply_indexes()"

    # Analyze query performance
    python -c "from backend.database.indexes import analyze_slow_queries; analyze_slow_queries()\"
"""
from sqlalchemy import text
from backend.database import engine
import logging
logger = logging.getLogger(__name__)
INDEX_DEFINITIONS = {
    'patients': [
        ('idx_patient_tenant_deleted', ['tenant_id', 'is_deleted']),
        ('idx_patient_name_search', ['name', 'tenant_id']),
        ('idx_patient_phone', ['phone', 'tenant_id']),
        ('idx_patient_created', ['tenant_id', 'created_at']),
    ],
    'appointments': [
        ('idx_appointment_tenant_status_date', ['tenant_id', 'status', 'date_time']),
    ],
    'payments': [
        ('idx_payment_tenant_date', ['tenant_id', 'date']),
        ('idx_payment_patient', ['patient_id', 'date']),
    ],
    'users': [
        ('idx_user_tenant_role', ['tenant_id', 'role', 'is_active']),
    ],
    'treatments': [
        ('idx_treatment_patient', ['patient_id', 'date']),
        ('idx_treatment_appointment', ['appointment_id']),
    ]
}


def apply_indexes():
    """Apply all defined indexes to the database."""
    with engine.connect() as conn:
        for table, indexes in INDEX_DEFINITIONS.items():
            for index_name, columns in indexes:
                try:
                    check_sql = text(
                        """
                        SELECT 1 FROM pg_indexes
                        WHERE tablename = :table AND indexname = :index
                    """
                        )
                    result = conn.execute(check_sql, {'table': table,
                        'index': index_name}).fetchone()
                    if result:
                        logger.info(f'Index {index_name} already exists')
                        continue
                    col_str = ', '.join(columns)
                    create_sql = text(
                        f'CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({col_str})'
                        )
                    conn.execute(create_sql)
                    conn.commit()
                    logger.info(
                        f'Created index: {index_name} on {table}({col_str})')
                except Exception as e:
                    logger.warning(f'Could not create index {index_name}: {e}')


def analyze_slow_queries(min_duration_ms: int=100):
    """Find slow queries using pg_stat_statements (if enabled)."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                """
                SELECT
                    substring(query, 1, 100) as query_preview,
                    calls,
                    round(total_exec_time::numeric, 2) as total_time_ms,
                    round(mean_exec_time::numeric, 2) as mean_time_ms
                FROM pg_stat_statements
                WHERE mean_exec_time > :min_duration
                ORDER BY total_exec_time DESC
                LIMIT 10
            """
                ), {'min_duration': min_duration_ms})
            queries = result.fetchall()
            logger.info('\n=== Slow Queries ===')
            for q in queries:
                logger.info(f'\nQuery: {q.query_preview}...')
                logger.info(
                    f'Calls: {q.calls}, Avg: {q.mean_time_ms}ms, Total: {q.total_time_ms}ms'
                    )
    except Exception as e:
        logger.warning(f'Could not analyze queries: {e}')
        logger.info('Note: pg_stat_statements extension may not be enabled')


def get_index_usage():
    """Get usage statistics for existing indexes."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                """
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan as scans,
                    idx_tup_read as tuples_read
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                ORDER BY idx_scan DESC
                LIMIT 20
            """
                ))
            indexes = result.fetchall()
            logger.info('\n=== Index Usage ===')
            for idx in indexes:
                logger.info(
                    f'{idx.tablename}.{idx.indexname}: {idx.scans} scans')
    except Exception as e:
        logger.warning(f'Could not get index usage: {e}')


if __name__ == '__main__':
    logger.info('Applying database indexes...')
    apply_indexes()
    logger.info('\nDone!')
