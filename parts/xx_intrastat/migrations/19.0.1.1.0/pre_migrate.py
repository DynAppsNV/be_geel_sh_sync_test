import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    # Pre-migration runs before the ORM creates new columns, so we add them manually first.
    cr.execute("""
        ALTER TABLE account_intrastat_code
            ADD COLUMN IF NOT EXISTS xx_default_transport   BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS xx_default_transaction BOOLEAN DEFAULT FALSE
    """)
    cr.execute("""
        UPDATE account_intrastat_code
        SET xx_default_transport   = COALESCE(default_transport,   FALSE),
            xx_default_transaction = COALESCE(default_transaction, FALSE)
        WHERE default_transport IS NOT NULL
           OR default_transaction IS NOT NULL
    """)
    _logger.info(
        "Migrated default_transport / default_transaction → xx_ fields (%d rows)",
        cr.rowcount,
    )

    cr.execute("""
        ALTER TABLE account_move
            ADD COLUMN IF NOT EXISTS xx_ignore_intrastat_warning BOOLEAN DEFAULT FALSE
    """)
    cr.execute("""
        UPDATE account_move
        SET xx_ignore_intrastat_warning = COALESCE(ignore_intrastat_warning, FALSE)
        WHERE ignore_intrastat_warning IS NOT NULL
    """)
    _logger.info(
        "Migrated ignore_intrastat_warning → xx_ field (%d rows)",
        cr.rowcount,
    )
