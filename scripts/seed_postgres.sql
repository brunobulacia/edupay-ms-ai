-- ============================================================
-- EduPay — Seed PostgreSQL (edupay-erp + payment-school)
-- ============================================================

-- ┌─────────────────────────────────────────────────────────┐
-- │  1. Nuevas familias FAM-001 … FAM-020                   │
-- └─────────────────────────────────────────────────────────┘
INSERT INTO erp_family (external_id, tutor_name, tutor_email, active) VALUES
  ('FAM-001', 'Juan Carlos Perez',    'juan.perez@edupay.bo',    true),
  ('FAM-002', 'Maria Elena Lopez',    'maria.lopez@edupay.bo',   true),
  ('FAM-003', 'Roberto Gutierrez',    'roberto.g@edupay.bo',     true),
  ('FAM-004', 'Ana Lucia Flores',     'ana.flores@edupay.bo',    true),
  ('FAM-005', 'Carlos Mendoza',       'c.mendoza@edupay.bo',     true),
  ('FAM-006', 'Patricia Vargas',      'p.vargas@edupay.bo',      true),
  ('FAM-007', 'Luis Alberto Rojas',   'l.rojas@edupay.bo',       true),
  ('FAM-008', 'Carmen Rosa Quispe',   'c.quispe@edupay.bo',      true),
  ('FAM-009', 'Fernando Mamani',      'f.mamani@edupay.bo',      true),
  ('FAM-010', 'Silvia Condori',       's.condori@edupay.bo',     true),
  ('FAM-011', 'Marcos Antonio Rios',  'm.rios@edupay.bo',        true),
  ('FAM-012', 'Elena Beatriz Cruz',   'e.cruz@edupay.bo',        true),
  ('FAM-013', 'Diego Herrera',        'd.herrera@edupay.bo',     true),
  ('FAM-014', 'Rosa Maria Arce',      'r.arce@edupay.bo',        true),
  ('FAM-015', 'Jorge Pinto',          'j.pinto@edupay.bo',       true),
  ('FAM-016', 'Claudia Vega',         'c.vega@edupay.bo',        true),
  ('FAM-017', 'Alejandro Soria',      'a.soria@edupay.bo',       true),
  ('FAM-018', 'Monica Bustamante',    'm.bustamante@edupay.bo',  true),
  ('FAM-019', 'Hector Villanueva',    'h.villanueva@edupay.bo',  true),
  ('FAM-020', 'Gabriela Miranda',     'g.miranda@edupay.bo',     true)
ON CONFLICT (external_id) DO NOTHING;

-- ┌─────────────────────────────────────────────────────────┐
-- │  2. Estudiantes por familia                             │
-- └─────────────────────────────────────────────────────────┘
INSERT INTO erp_student_ref (family_id, external_id, full_name, active)
SELECT f.id, 'STU-' || f.external_id || '-A', split_part(f.tutor_name, ' ', 2) || ' Jr.', true
FROM erp_family f WHERE f.external_id LIKE 'FAM-%'
ON CONFLICT (external_id) DO NOTHING;

INSERT INTO erp_student_ref (family_id, external_id, full_name, active)
SELECT f.id, 'STU-' || f.external_id || '-B', split_part(f.tutor_name, ' ', 3) || ' ' || split_part(f.tutor_name, ' ', 2), true
FROM erp_family f
WHERE f.external_id IN ('FAM-001','FAM-002','FAM-005','FAM-007','FAM-011','FAM-014','FAM-018','FAM-020')
ON CONFLICT (external_id) DO NOTHING;

-- ┌─────────────────────────────────────────────────────────┐
-- │  3. erp_account_status — 18 meses × 20 familias         │
-- └─────────────────────────────────────────────────────────┘
DO $$
DECLARE
  fam_rec  RECORD;
  m        INT;
  yr       INT;
  mo       INT;
  period   VARCHAR(20);
  expected NUMERIC(12,2);
  paid     NUMERIC(12,2);
  debt     NUMERIC(12,2);
  st       VARCHAR(20);
  due      DATE;
  days_off INT;
BEGIN
  FOR fam_rec IN
    SELECT id, external_id FROM erp_family WHERE external_id LIKE 'FAM-%'
  LOOP
    FOR m IN 0..17 LOOP
      yr     := EXTRACT(YEAR  FROM (CURRENT_DATE - (m * 30)::INT))::INT;
      mo     := EXTRACT(MONTH FROM (CURRENT_DATE - (m * 30)::INT))::INT;
      period := yr || '-' || LPAD(mo::TEXT, 2, '0');
      due    := (yr || '-' || LPAD(mo::TEXT,2,'0') || '-10')::DATE;

      -- Base: 750–1400 BOB según familia
      expected := 750 + (hashtext(fam_rec.external_id) % 13) * 50;

      -- Calcular estado según cluster simulado vía hash
      days_off := ABS(hashtext(fam_rec.external_id || period) % 40);

      IF days_off <= 5 THEN
        st := 'PAID';    paid := expected; debt := 0;
      ELSIF days_off <= 15 THEN
        st := 'PAID';    paid := expected; debt := 0;
      ELSIF days_off <= 25 THEN
        st := 'OVERDUE'; paid := 0;        debt := expected;
      ELSE
        st := 'PARTIAL'; paid := expected * 0.5; debt := expected * 0.5;
      END IF;

      -- Periodo actual puede estar PENDING
      IF m = 0 AND CURRENT_DATE < due THEN
        st   := 'PENDING'; paid := 0; debt := 0;
      END IF;

      INSERT INTO erp_account_status
        (family_id, period_code, expected_amount, paid_amount, debt_amount, status, due_date)
      VALUES
        (fam_rec.id, period, expected, paid, debt, st, due)
      ON CONFLICT (family_id, period_code) DO NOTHING;
    END LOOP;
  END LOOP;
END $$;

-- ┌─────────────────────────────────────────────────────────┐
-- │  4. doc_document — documentos por familia               │
-- └─────────────────────────────────────────────────────────┘
INSERT INTO doc_document (family_id, student_id, type, original_name, s3_key, s3_bucket, mime_type, size_bytes, status, uploaded_by, uploaded_at)
SELECT
  f.id,
  NULL,
  dtype,
  dtype || '_' || f.external_id || '.pdf',
  'families/' || f.external_id || '/' || lower(dtype) || '/doc.pdf',
  'edupay-scz-docs',
  'application/pdf',
  (100000 + ABS(hashtext(f.external_id || dtype)) % 900000),
  CASE ABS(hashtext(f.external_id || dtype)) % 3
    WHEN 0 THEN 'APPROVED'
    WHEN 1 THEN 'APPROVED'
    ELSE       'PENDING'
  END,
  lower(replace(f.external_id, '-', '')) || '@edupay.bo',
  NOW() - (ABS(hashtext(f.external_id || dtype)) % 60 || ' days')::INTERVAL
FROM erp_family f
CROSS JOIN (VALUES ('CI_TUTOR'),('CI_ALUMNO'),('CERT_NACIMIENTO')) AS t(dtype)
WHERE f.external_id LIKE 'FAM-%'
ON CONFLICT DO NOTHING;
