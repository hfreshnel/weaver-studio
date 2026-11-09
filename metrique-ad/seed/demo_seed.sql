-- Demo data for the launch-ad screenshots (LOCAL stack only, fictional people, no reviews).
-- Usage: docker compose exec -T postgres psql -U superadmin -d metrique < seed/demo_seed.sql
\set ON_ERROR_STOP on

-- Client: onboarding finished as a client.
UPDATE accounts SET city = 'Cotonou' WHERE email = 'demo.cliente@metrique.local';
INSERT INTO account_onboarding (account_id, step, payload)
SELECT id, 'role_client', '{"role": "client", "completed": true}'::jsonb FROM accounts WHERE email = 'demo.cliente@metrique.local'
ON CONFLICT (account_id) DO UPDATE SET step = EXCLUDED.step, payload = EXCLUDED.payload;

-- Provider: plumber in Cotonou, identity approved (KYC), onboarding complete.
UPDATE accounts SET
  city = 'Cotonou',
  service_cities = ARRAY['Cotonou', 'Abomey-Calavi'],
  domain = 'Bâtiment',
  profession = 'Plombier',
  description = 'Plombier à Cotonou : fuites, robinetterie, sanitaires et installation.',
  identity_status = 'approved',
  identity_reviewed_at = now()
WHERE email = 'demo.plombier@metrique.local';
INSERT INTO account_onboarding (account_id, step, payload)
SELECT id, 'provider_complete', '{"role": "provider", "completed": true, "domain": "Bâtiment", "profession": "Plombier"}'::jsonb
FROM accounts WHERE email = 'demo.plombier@metrique.local'
ON CONFLICT (account_id) DO UPDATE SET step = EXCLUDED.step, payload = EXCLUDED.payload;

-- Service + three packs (DB names Basic/Standard/Premium = UI Essentiel/Confort/Prestige; illustrative demo prices, shown with an on-screen "données de démonstration" note).
INSERT INTO services (account_id, name, description, is_active)
SELECT id, 'Plomberie : dépannage et réparation de fuites',
       'Recherche et réparation de fuites, remplacement de robinetterie et de siphons, débouchage. Intervention à Cotonou et Abomey-Calavi.',
       true
FROM accounts WHERE email = 'demo.plombier@metrique.local'
ON CONFLICT (account_id) DO NOTHING;

INSERT INTO service_packs (service_id, name, price, currency, delivery_days, max_delivery, description, is_active)
SELECT s.id, p.name, p.price, 'XOF', p.days, 0, p.descr, true
FROM services s
JOIN accounts a ON a.id = s.account_id AND a.email = 'demo.plombier@metrique.local'
CROSS JOIN (VALUES
  ('Basic', 10000, 1, 'Diagnostic et réparation d''une fuite simple.'),
  ('Standard', 20000, 1, 'Réparation de fuite et remplacement d''un siphon ou d''un robinet.'),
  ('Premium', 35000, 2, 'Révision complète de la plomberie de la cuisine et de la salle de bain.')
) AS p(name, price, days, descr)
WHERE NOT EXISTS (SELECT 1 FROM service_packs sp WHERE sp.service_id = s.id);

SELECT s.id AS service_id, s.name, count(sp.id) AS packs
FROM services s JOIN accounts a ON a.id = s.account_id
LEFT JOIN service_packs sp ON sp.service_id = s.id
WHERE a.email = 'demo.plombier@metrique.local' GROUP BY s.id, s.name;

-- Portfolio photo: the site's own plumbing illustration (frontend/public/home/services/service-plumbing.png),
-- uploaded through POST /api/upload/portfolio as the provider; set the returned key here, e.g.:
-- UPDATE services SET portfolio_photos = ARRAY['portfolio/<key>.png'] WHERE id = '<service_id>';
