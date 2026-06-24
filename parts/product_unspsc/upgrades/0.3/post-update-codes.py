from odoo import tools


def migrate(cr, version):
    cr.execute("""
        CREATE UNLOGGED TABLE _upgrade_product_unspsc_code (
            code varchar,
            name jsonb,
            applies_to varchar,
            active boolean
        )
    """)

    csv_path = 'product_unspsc/data/product.unspsc.code.csv'
    with tools.misc.file_open(csv_path, 'rb') as csv_file:
        csv_file.readline()  # Read the header, so we avoid copying it to the db
        cr.copy_from(csv_file, "_upgrade_product_unspsc_code", sep="|", columns=["code", "name", "applies_to", "active"])

    cr.execute("""
        WITH insert_cte AS (
            INSERT INTO product_unspsc_code (code, name, applies_to, active)
            SELECT code, name, applies_to, active
            FROM _upgrade_product_unspsc_code upc
            WHERE NOT EXISTS (
                    SELECT 1 FROM product_unspsc_code
                    WHERE code=upc.code
                    )
            RETURNING code, id
        )
        INSERT INTO ir_model_data(name, res_id, module, model, noupdate)
        SELECT 'unspsc_code_' || code, id,  'product_unspsc', 'product.unspsc.code', True
        FROM insert_cte
    """)

    cr.execute("DROP TABLE _upgrade_product_unspsc_code;")
