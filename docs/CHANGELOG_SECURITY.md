# Security & Compliance Changelog — «До → После» (Stage 1–5)

**Проект:** Antifraud.SYS • **Дата:** 2026-06-04
Сравнительная таблица изменений по безопасности, приватности и соответствию
стандартам (GDPR, ISO/IEC 27001/27701, OWASP). Для каждого пункта указано, **где проверить**.

---

## Stage 1 — Критические фиксы безопасности

| Что | До | После | Где проверить |
|---|---|---|---|
| Блокировка аккаунта | Счётчик попыток рос, но блокировки не было | Лок после 5 попыток на 15 мин → `423` | `backend/app/api/v1/endpoints/auth.py` (login) |
| Секреты в production | Дефолтные пароли/ключ молча работали | В `ENVIRONMENT=production` приложение не стартует без `SECRET_KEY`, реальных паролей, `ALLOWED_HOSTS` | `backend/app/core/config.py` (`_enforce_production_secrets`) |
| Тип JWT | refresh-токен можно было использовать как access | Проверка claim `type`; защищённые роуты — только `access` | `backend/app/core/security.py`, `deps.py` |
| refresh-токен | Передавался в query-строке (утечка в логи) | Только в теле запроса | `auth.py` (`/auth/refresh`) |
| Security-заголовки | Не было; CORS `*` | `X-Frame-Options`, `X-Content-Type-Options`, CSP, Referrer/Permissions-Policy, опц. HSTS; CORS сужен; TrustedHost | `backend/app/main.py` |
| Парольная политика | Только заглавная + цифра | Заглавная + строчная + цифра + спецсимвол | `backend/app/schemas/user.py` |

## Stage 2 — GDPR-движок

| Что | До | После | Где проверить |
|---|---|---|---|
| Экспорт своих данных | Нет | `GET /privacy/my-data/export` → JSON | UI: **Privacy & My Data** → «Скачать JSON» |
| Удаление/права субъекта (DSAR) | Нет | Запросы access/erasure/restriction/rectification; удаление → анонимизация | UI клиента (отправка), UI админа **GDPR / Privacy** (обработка) |
| Согласия | Только `bool` без истории | Версия, время, отзыв (`consents`) | UI: переключатели согласий |
| Хранение/ретеншен | Бессрочно | `retention_until` + purge | UI админа → «Запустить purge» |
| Аудит просмотра PII | Не логировался | `PII_VIEWED` при чтении профиля/документов | `audit_logs`, эндпоинт `/admin/audit-logs` |
| Неизменяемость логов | Логи можно было править | SHA-256 hash-chain + проверка целостности | UI админа → «Проверить» (`/privacy/audit/integrity`) |

## Stage 3 — Шифрование at-rest

| Что | До | После | Где проверить |
|---|---|---|---|
| PII в БД | Открытый текст | Шифрование `id_number`, `phone_number`, `source_of_funds/wealth`, `pep_details`, `mfa_secret` | `backend/app/core/crypto.py`; в БД эти поля — нечитаемый шифртекст |
| Файлы документов | Хранились как есть | Шифруются на диске (`.enc`) | `backend/app/api/v1/endpoints/documents.py` (upload) |
| Скачивание документа | Не было защищённой выдачи | `GET /documents/{id}/download` (доступ владелец/комплаенс + лог) | тот же файл |
| Ключ шифрования | — | `ENCRYPTION_KEY` (обязателен в prod) | `backend/.env.example` |

## Stage 4 — Enterprise-аутентификация

| Что | До | После | Где проверить |
|---|---|---|---|
| MFA (2FA) | Поля были, логики не было | TOTP + одноразовые backup-коды | UI: **Security (2FA)**; `/auth/mfa/setup\|verify\|disable` |
| Logout / отзыв токена | Logout только чистил localStorage | `jti` в токене + denylist `revoked_tokens`, реальный `/auth/logout` | `backend/app/core/deps.py`, `auth.py` |
| Сброс пароля | Не было | `/auth/password-reset/request\|confirm`, хешированные одноразовые токены | `auth.py` |
| Rate limiting | Нет | login 10/мин, сброс пароля 5/мин (slowapi) | `backend/app/core/rate_limit.py`, `main.py` |
| ABAC | Аналитик мог трогать любой тикет | Только назначенные ему тикеты | `backend/app/api/v1/endpoints/incidents.py` (`_ensure_can_act`) |

## Stage 5 — Governance / Secure SDLC

| Что | До | После | Где проверить |
|---|---|---|---|
| CI-пайплайн | Не было | Тесты + сборка фронта + bandit/pip-audit/npm audit/gitleaks | `.github/workflows/ci.yml`, вкладка **Actions** на GitHub |
| RoPA (реестр обработки) | Нет | Полный документ Art.30 | `docs/RoPA.md` |
| Реагирование на инциденты/утечки | Нет | Процесс Art.33/34 + 72ч чек-лист | `docs/INCIDENT_RESPONSE.md` |
| Аудит-документ соответствия | Нет | Полный GDPR/ISO аудит + роадмап | `docs/SECURITY_COMPLIANCE_AUDIT.md` |

---

## Как проверить «после» вживую

1. **GitHub:** репозиторий `ChristianDior141/Antifraud.SYS`, вкладка **Actions** — зелёный workflow подтверждает прохождение тестов/сборки.
2. **Локально** (из папки проекта):
   ```bash
   docker-compose down -v && docker-compose up -d --build
   docker-compose exec backend python seed_data.py
   ```
   - Войти как `admin@kyc-platform.com` → появятся пункты меню **Security (2FA)** и **GDPR / Privacy**.
   - Любой пользователь → **Privacy & My Data** → «Скачать JSON».
   - Шифрование: открыть БД и посмотреть `client_profiles.id_number` — там шифртекст, а в UI/экспорте — нормальное значение.
   - Админ → **GDPR / Privacy** → «Проверить» целостность аудита → «цепочка цела».

## Связанные документы
- `docs/SECURITY_COMPLIANCE_AUDIT.md` — полный аудит и роадмап
- `docs/RoPA.md` — реестр операций обработки (GDPR Art.30)
- `docs/INCIDENT_RESPONSE.md` — реагирование на инциденты и уведомление об утечке

## Статус по дорожной карте
Stage 1 ✅ · Stage 2 ✅ · Stage 3 ✅ · Stage 4 ✅ · Stage 5 ✅
Отложено отдельными инициативами: роли Auditor/DPO, device trust, ML-fraud/graph analytics, Vault/KMS, SIEM + `security_events`.
