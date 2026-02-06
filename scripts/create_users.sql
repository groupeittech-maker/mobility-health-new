-- Script SQL pour créer les utilisateurs de test
-- Les mots de passe sont hashés avec bcrypt
-- Format: $2b$12$... (12 rounds)

-- Admin
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, created_at, updated_at)
VALUES (
    'admin@mobilityhealth.com',
    'admin',
    '$2b$12$Gqz5l9D7fpD6sc0AaXImsemJFOnW0Glb0VIu20AylimyT/JRlm8Bi', -- admin123
    'Administrateur Principal',
    'ADMIN'::role,
    true,
    true,
    NOW(),
    NOW()
) ON CONFLICT (email) DO NOTHING;

-- Doctor
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, created_at, updated_at)
VALUES (
    'doctor@mobilityhealth.com',
    'doctor',
    '$2b$12$M1Rvvmtj9i575PdXYrYLwebQq1oXRjpV8ZuMsEW4EE.GjZpkl4T5a', -- doctor123
    'Dr. Jean Dupont',
    'DOCTOR'::role,
    true,
    false,
    NOW(),
    NOW()
) ON CONFLICT (email) DO NOTHING;

-- Hospital Admin
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, created_at, updated_at)
VALUES (
    'hospital@mobilityhealth.com',
    'hospital_admin',
    '$2b$12$adM/HU0Wiyl/cjX0cY8gCu4ivXdT3r.P1IZgCuHyHV0ujJc/sre2C', -- hospital123
    'Admin Hôpital',
    'HOSPITAL_ADMIN'::role,
    true,
    false,
    NOW(),
    NOW()
) ON CONFLICT (email) DO NOTHING;

-- Finance Manager
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, created_at, updated_at)
VALUES (
    'finance@mobilityhealth.com',
    'finance',
    '$2b$12$CXJqaOasGgUl7bIeTV0l4uncDEz0QbgcXO3jBd4FIY6j8rkd8CkHe', -- finance123
    'Gestionnaire Financier',
    'FINANCE_MANAGER'::role,
    true,
    false,
    NOW(),
    NOW()
) ON CONFLICT (email) DO NOTHING;

-- SOS Operator
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, created_at, updated_at)
VALUES (
    'sos@mobilityhealth.com',
    'sos_operator',
    '$2b$12$5RcDqkywXTdDP1BiaSE11uR8wvfrucFgHwAGj/Od8WdQpIMZIL1pq', -- sos123
    'Opérateur SOS',
    'SOS_OPERATOR'::role,
    true,
    false,
    NOW(),
    NOW()
) ON CONFLICT (email) DO NOTHING;

-- User
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, created_at, updated_at)
VALUES (
    'user@mobilityhealth.com',
    'user',
    '$2b$12$dXAnThajWMXGDuqQZ9CqiuCqWWQpGEiJLpToU7AVFZHy8Qgx4kZiS', -- user123
    'Utilisateur Test',
    'USER'::role,
    true,
    false,
    NOW(),
    NOW()
) ON CONFLICT (email) DO NOTHING;

