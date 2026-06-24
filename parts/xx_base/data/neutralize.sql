-- account_peppol_edi_mode -> Test
UPDATE ir_config_parameter
   SET value = 'test'
 WHERE key = 'account_peppol.edi.mode';
