# Antifraud.SYS — Аудит безопасности, приватности и соответствия

**Версия документа:** 1.0
**Дата:** 2026-06-04
**Объект аудита:** платформа Antifraud.SYS (FastAPI + React + PostgreSQL)
**Стандарты:** GDPR, ISO/IEC 27001:2022, ISO/IEC 27701, OWASP ASVS 4.0, OWASP Top 10 (2021), NIST CSF 2.0, PCI DSS 4.0 (частично), SOC 2, AML/KYC best practices.

> Документ описывает выявленные несоответствия и план их устранения. Каждый
> пункт оформлен по единому формату: проблема → риск → нарушаемый стандарт →
> объяснение → решение (БД / API / Backend / Frontend) → пример кода →
> приоритет → ожидаемый эффект.

## Сводка приоритетов

| # | Проблема | Риск | Стандарт | Статус |
|---|----------|------|----------|--------|
| 1 | Блокировка аккаунта не применялась | Высокий | ISO A.9.4.2 / ASVS V2 | ✅ Исправлено (Stage 1) |
| 2 | `SECRET_KEY` по умолчанию генерируется в рантайме | Высокий | ASVS V6 / A.9.2.4 | ✅ Исправлено (Stage 1) |
| 3 | `refresh_token` принимался как query-параметр | Средний | ASVS V3.5 / A.12.4 | ✅ Исправлено (Stage 1) |
| 4 | Нет проверки типа JWT (access/refresh) | Средний | ASVS V3.5 | ✅ Исправлено (Stage 1) |
| 5 | Нет security-заголовков и Trusted Host | Средний | A.13.1 / OWASP Headers | ✅ Исправлено (Stage 1) |
| 6 | Слабая парольная политика | Средний | A.9.4.3 / ASVS V2.1 | ✅ Исправлено (Stage 1) |
| 7 | PII хранится без шифрования | Высокий | GDPR Art.32 / A.10.1 | ⏳ Stage 3 |
| 8 | Нет прав субъекта данных (DSAR) | Высокий | GDPR Art.15–20 | ✅ Исправлено (Stage 2) |
| 9 | Учёт согласий без версии/времени/отзыва | Средний | GDPR Art.7 | ✅ Исправлено (Stage 2) |
| 10 | Нет политики хранения/ретеншена | Средний | GDPR Art.5(1)(e) | ✅ Исправлено (Stage 2) |
| 11 | Нет аудита просмотра PII | Высокий | GDPR Art.30 / A.12.4 | ✅ Исправлено (Stage 2) |
| 12 | Документы клиентов не шифруются на диске | Высокий | GDPR Art.32 | ⏳ Stage 3 |
| 13 | MFA-поля есть, логики нет | Средний | A.9.4 / ASVS V2.8 | ⏳ Stage 4 |
| 14 | Логи аудита изменяемы | Средний | A.12.4.2 | ✅ Исправлено (Stage 2) |
| 15 | Нет управления уязвимостями / CI security | Средний | A.12.6 / NIST PR.IP | ⏳ Stage 5 |
| 16 | Нет процессов RoPA / breach notification | Средний | GDPR Art.30/33-34 | ⏳ Stage 5 |

---

## 1. Authentication Security

### 1.1 Account Lockout не применялся — ✅ ИСПРАВЛЕНО
1. **Проблема.** В модели `users` были поля `login_attempts` и `locked_until`, но эндпоинт `login()` только инкрементировал счётчик и никогда не блокировал вход. Brute-force ничем не ограничивался.
2. **Риск.** Высокий.
3. **Стандарт.** ISO 27001 A.9.4.2 (secure log-on), OWASP ASVS V2.2, OWASP Top 10 A07:2021.
4. **Объяснение.** Без блокировки атакующий мог перебирать пароли неограниченно.
5. **Решение.** После `MAX_LOGIN_ATTEMPTS` неудач аккаунт блокируется на `ACCOUNT_LOCKOUT_MINUTES`. Каждая неудача и блокировка пишутся в аудит.
6. **Изменения БД.** Без изменений (поля уже были).
7. **Изменения API.** `POST /auth/login` теперь возвращает `423 Locked` при активной блокировке.
8. **Backend.** `app/api/v1/endpoints/auth.py`, конфиг `MAX_LOGIN_ATTEMPTS`, `ACCOUNT_LOCKOUT_MINUTES`.
9. **Frontend.** Обработать код 423 (показать «аккаунт временно заблокирован»).
10. **Пример кода.**
    ```python
    if user and user.locked_until and _as_aware(user.locked_until) > _utcnow():
        raise HTTPException(status_code=423, detail="Account temporarily locked")
    ...
    if user.login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
        user.locked_until = _utcnow() + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
    ```
11. **Приоритет.** Critical (Stage 1).
12. **Эффект.** Brute-force и password-spraying существенно затруднены; попытки фиксируются.

### 1.2 SECRET_KEY и секреты — ✅ ИСПРАВЛЕНО
- `SECRET_KEY` больше не должен полагаться на рантайм-генерацию: в `ENVIRONMENT=production` приложение **падает при старте**, если `SECRET_KEY` не задан в окружении, а также если используются дефолтные пароли БД/суперпользователя или `ALLOWED_HOSTS=["*"]`. ISO A.9.2.4, ASVS V6.
- Пример: `Settings._enforce_production_secrets()` в `app/core/config.py`.

### 1.3 JWT type confusion и refresh в URL — ✅ ИСПРАВЛЕНО
- `verify_token(token, expected_type=...)` проверяет claim `type`. `get_current_user` теперь принимает только `access`-токены; `/auth/refresh` — только `refresh`-токены и **из тела запроса** (а не query-string). ASVS V3.5.

### 1.4 Что ещё запланировано (Stage 4)
- **MFA (TOTP)** для админ/комплаенс-ролей (`pyotp`), QR-провижининг, backup-коды.
- **Token revocation / logout:** таблица `revoked_tokens` (jti, expires_at) или Redis-denylist; добавить `jti` в payload.
- **Password reset flow:** одноразовый токен в таблице `password_reset_tokens` (hash, expires_at, used_at), без раскрытия существования e-mail.
- **Device trust:** таблица `trusted_devices` (user_id, device_fingerprint, last_seen), уведомление о новом устройстве.

**Новые таблицы (DDL, план):**
```sql
CREATE TABLE password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE revoked_tokens (
    jti VARCHAR(64) PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 2. Authorization Security

1. **Проблема.** RBAC реализован через `Depends()` (4 роли), но: нет ABAC (ownership-проверок на уровне записи), нет разделения полномочий (SoD), отсутствует явная матрица доступа.
2. **Риск.** Средний.
3. **Стандарт.** ISO A.9.1/A.9.2, OWASP Top 10 A01:2021 (Broken Access Control), ASVS V4.
4. **Объяснение.** Комплаенс-офицер может открыть данные **любого** клиента; нет проверки «этот аналитик владеет этим тикетом». Один админ может и заводить пользователя, и менять роли, и читать аудит (нарушение SoD).
5. **Решение.**
   - Ввести **матрицу доступа** (ниже) и зафиксировать её в коде/тестах.
   - Добавить **ABAC-проверки владения** (например, аналитик правит только назначенные ему тикеты).
   - Рассмотреть роль **DPO/Privacy Officer** (доступ к DSAR и журналам приватности) и **Auditor** (только чтение аудита) для SoD.
6–9. **БД/API/Backend/Frontend.** Новая роль(и) в enum `user_role`; декоратор `require_owner_or_role`; скрытие действий в UI по правам.
10. **Пример кода (ABAC).**
    ```python
    def require_ticket_owner(current_user, ticket):
        if current_user.role == UserRole.RISK_ANALYST and ticket.assigned_analyst_id != current_user.id:
            raise HTTPException(403, "Not the assigned analyst")
    ```
11. **Приоритет.** High (Stage 4).
12. **Эффект.** Принцип наименьших привилегий, защита от горизонтальной эскалации.

**Матрица доступа (целевая):**

| Ресурс / действие | Client | Risk Analyst | Compliance | Admin | Auditor* | DPO* |
|---|---|---|---|---|---|---|
| Свой профиль (R/W) | ✅ | — | — | — | — | — |
| Любой профиль (R) | — | назначенные | ✅ | ✅ | ✅ (R) | ✅ (R) |
| Документы клиента | свои | назначенные | ✅ | ✅ | R | R |
| Инциденты | — | назначенные | ✅ | ✅ | R | — |
| Тюнинг правил | — | — | — | ✅ | R | — |
| Управление пользователями | — | — | — | ✅ | — | — |
| Аудит-логи | — | — | — | ✅ | ✅ (R) | приватность |
| DSAR (экспорт/удаление) | свои запросы | — | — | ✅ | — | ✅ |

\* — предлагаемые новые роли (Stage 4).

---

## 3. Personal Data Protection (GDPR)

### 3.1 Реестр PII (по таблицам)

| Таблица.Поле | Категория | Чувствительность | Мера защиты (план) |
|---|---|---|---|
| `users.email` | контакт/идентификатор | Средняя | хеш-индекс, маскирование в UI |
| `users.hashed_password` | креденшл | — (bcrypt) | OK |
| `users.mfa_secret` | креденшл | **Высокая** | **шифрование (Stage 3)** |
| `client_profiles.first/last/middle_name` | идентификатор | Средняя | маскирование в списках |
| `client_profiles.date_of_birth` | спец. | **Высокая** | шифрование |
| `client_profiles.id_number` | документ | **Очень высокая** | **шифрование + токенизация** |
| `client_profiles.id_*` (тип/срок/страна) | документ | Высокая | шифрование |
| `client_profiles.address_*`, `postal_code` | контакт | Средняя | шифрование/маскирование |
| `client_profiles.phone_number` | контакт | Средняя | маскирование |
| `client_profiles.source_of_funds/wealth`, `annual_income_range`, `occupation`, `employer_name` | финансовая | Высокая | шифрование |
| `client_profiles.is_pep`, `pep_details` | спец. | **Высокая** | шифрование `pep_details` |
| `client_profiles.ip_address`, `device_fingerprint` | поведенческая | Средняя | ретеншен/анонимизация |
| `documents.*` (файл, OCR, extracted_*) | документ | **Очень высокая** | **шифрование файлов at-rest** |
| `transactions.counterparty_*`, `amount`, `ip_address`, `device_id` | финансовая | Высокая | ретеншен, маскирование |

**Подход к защите по уровням:**
- **Маскирование** (в ответах API/спискам): `+•••••1234`, `••••@gmail.com`, последние 4 цифры ID.
- **Field-level encryption** (at-rest): AES-256-GCM через application-level шифрование (envelope encryption с data-key из KMS), прозрачные `EncryptedString`-типы SQLAlchemy.
- **Токенизация** для `id_number`: хранить токен + значение в отдельном защищённом хранилище.

### 3.2 Права субъекта данных (DSAR) — план Stage 2
Создаётся новый модуль `privacy`:

- **Право доступа / переносимости (Art.15/20):** `GET /privacy/my-data/export` → JSON-архив всех данных субъекта.
- **Право на удаление (Art.17):** `POST /privacy/my-data/erasure` → запрос; обработка с учётом AML-ретеншена (анонимизация вместо удаления, если запись под legal hold).
- **Право на ограничение (Art.18):** флаг `processing_restricted` в профиле.
- **Право на исправление (Art.16):** уже частично (`PUT /auth/me`), расширить на профиль.
- **Отзыв согласия (Art.7):** см. §3.3.

**Новые таблицы (DDL, план):**
```sql
CREATE TYPE dsar_type AS ENUM ('access','export','erasure','restriction','rectification');
CREATE TYPE dsar_status AS ENUM ('received','in_progress','completed','rejected');
CREATE TABLE data_subject_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    request_type dsar_type NOT NULL,
    status dsar_status NOT NULL DEFAULT 'received',
    details TEXT,
    handled_by INTEGER REFERENCES users(id),
    legal_hold BOOLEAN DEFAULT FALSE,    -- блокировка удаления из-за AML
    due_at TIMESTAMPTZ,                  -- срок ответа (30 дней)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

### 3.3 Управление согласиями (Art.7) — план Stage 2
Сейчас `kyc_forms.agrees_to_data_processing` — только bool. Нужен полноценный журнал согласий с версией политики, временем и возможностью отзыва.
```sql
CREATE TABLE consents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    purpose VARCHAR(100) NOT NULL,       -- 'kyc_processing','marketing',...
    policy_version VARCHAR(20) NOT NULL,
    granted BOOLEAN NOT NULL,
    granted_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
API: `POST /privacy/consents`, `DELETE /privacy/consents/{purpose}` (отзыв), `GET /privacy/consents`.

### 3.4 Политика хранения (Art.5(1)(e)) — план Stage 2
- Документированный срок (например, **5 лет** после завершения отношений — AML), затем анонимизация/удаление.
- Поле `client_profiles.retention_until` + периодическая задача (Celery beat) `purge_expired_data`.
- `ip_address`/`device_*` — более короткий срок (например, 90 дней).

---

## 4. Audit & Accountability

### 4.1 Аудит просмотра PII (план Stage 2)
1. **Проблема.** Аудит фиксирует только login/register/review. Просмотр профиля/документов клиента **не логируется**.
2. **Стандарт.** GDPR Art.30, ISO A.12.4.1, SOC 2 CC7.
3. **Решение.** Зависимость `audit_access(resource_type, resource_id)` на чтениях PII-эндпоинтов; запись `action="PII_VIEWED"`.
   ```python
   async def log_pii_access(db, user, resource_type, resource_id):
       db.add(AuditLog(user_id=user.id, action="PII_VIEWED",
                       resource_type=resource_type, resource_id=resource_id))
   ```

### 4.2 Неизменяемость и целостность логов (план Stage 2)
1. **Проблема.** Логи лежат в той же БД и удаляемы админом/DBA.
2. **Стандарт.** ISO A.12.4.2 (защита журналов), NIST PR.PT-1.
3. **Решение — hash-chain (tamper-evidence):** в каждую запись добавить `prev_hash` и `entry_hash = SHA256(prev_hash + payload)`. Любая модификация рвёт цепочку.
   ```sql
   ALTER TABLE audit_logs ADD COLUMN prev_hash VARCHAR(64);
   ALTER TABLE audit_logs ADD COLUMN entry_hash VARCHAR(64);
   ```
   ```python
   entry_hash = sha256(f"{prev_hash}|{user_id}|{action}|{created_at}|{details}".encode()).hexdigest()
   ```
   Дополнительно: экспорт в WORM-хранилище / внешний SIEM, периодическая верификация цепочки.

---

## 5. Encryption

- **At-rest БД:** field-level encryption для PII (см. §3.1) + шифрование диска БД (инфраструктура).
- **Envelope encryption:** мастер-ключ в KMS, data-key шифрует поля; ротация ключей.
- **Секреты:** вынести из кода в Vault / AWS Secrets Manager / Azure Key Vault (см. §7).
- **In-transit:** TLS терминируется на reverse-proxy (nginx); HSTS включается флагом `ENABLE_HSTS`.
- **Пример типа SQLAlchemy:**
  ```python
  class EncryptedString(TypeDecorator):
      impl = String
      def process_bind_param(self, value, dialect):
          return aes_gcm_encrypt(value) if value is not None else None
      def process_result_value(self, value, dialect):
          return aes_gcm_decrypt(value) if value is not None else None
  ```

---

## 6. File Security

1. **Проблема.** Документы (`uploads/documents`) хранятся в открытом виде; нет антивирус-проверки; нет защищённой выдачи (download-эндпоинта с контролем доступа и временными ссылками).
2. **Стандарт.** GDPR Art.32, ISO A.8.2/A.13.2.
3. **Решение.**
   - Шифровать файл при сохранении (AES-256-GCM), хранить только зашифрованный blob.
   - Антивирус-скан (ClamAV) перед принятием.
   - Перенести в объектное хранилище (S3/MinIO) с серверным шифрованием.
   - Выдача через **pre-signed URL** с TTL и проверкой прав (`require_compliance`/владелец).
   - Валидация контента, а не только `content_type` (magic bytes — `python-magic` уже в зависимостях).
4. **Пример (временная ссылка):** `GET /documents/{id}/download` → 302 на pre-signed URL (TTL 60s), запись в аудит.

---

## 7. Secrets Management

1. **Проблема.** В `config.py`/`.env.example` присутствуют дефолтные `POSTGRES_PASSWORD`, `FIRST_SUPERUSER_PASSWORD`.
2. **Стандарт.** ISO A.9.2.4, ASVS V6, PCI DSS 8.
3. **Решение.**
   - Production-валидатор уже блокирует дефолты (Stage 1).
   - Интеграция с **HashiCorp Vault** / **AWS Secrets Manager** / **Azure Key Vault**; загрузка секретов при старте.
   - **Secret scanning** в CI (gitleaks/trufflehog) — Stage 5.
   - Ротация ключей и паролей по расписанию.

---

## 8. Infrastructure Security — ✅ частично ИСПРАВЛЕНО (Stage 1)

- **CORS:** сужены `allow_methods`/`allow_headers` (вместо `*`).
- **Security headers:** `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy`, опциональный `HSTS`.
- **Trusted Host:** `TrustedHostMiddleware` включается при заданном `ALLOWED_HOSTS`.
- **Осталось (инфраструктура):** TLS/redirect на уровне nginx, rate-limiting (`slowapi` уже в зависимостях — подключить глобально и на `/auth/*`).
- **Пример rate-limit (план):**
  ```python
  from slowapi import Limiter
  limiter = Limiter(key_func=lambda r: r.client.host)
  @router.post("/login")
  @limiter.limit("10/minute")
  async def login(...): ...
  ```

---

## 9. Monitoring & Incident Response

- В продукте уже есть **Incident Management** (тикеты, классификация, false-positive analysis). Предлагается расширить на **security-инциденты**:
  - События безопасности (`security_events`): неудачные входы, блокировки, аномальный доступ к PII, отказы авторизации.
  - **SIEM-интеграция:** экспорт аудита/событий в формате CEF/JSON в Elastic/Splunk/Wazuh.
  - **Alerting:** пороги (N блокировок за период, всплеск 403/401), уведомления (`notifications` уже есть).
  - **Workflow реагирования:** detect → triage → contain → eradicate → recover → lessons-learned (привязать к уже существующему модулю инцидентов).
```sql
CREATE TABLE security_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,   -- 'login_failed','account_locked','pii_access_anomaly'
    severity VARCHAR(20) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    ip_address VARCHAR(45),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 10. AML/KYC Improvements

Текущая система: 7 правил, поведенческий скоринг, инциденты. Предлагается развитие:
- **Санкционные списки/PEP:** интеграция с реальными источниками (OFAC, EU, UN, локальные), периодический rescreening, fuzzy-matching имён.
- **Adverse media screening:** проверка по новостям/негативным упоминаниям.
- **Risk-profiling:** динамический риск-профиль клиента во времени, пороги по сегментам.
- **Transaction monitoring:** скользящие окна, сезонность, peer-group аномалии.
- **Fraud scoring:** ML-модель поверх правил (с сохранением интерпретируемости — SHAP).
- **Graph analytics:** граф связей клиент↔контрагент↔устройство↔IP, выявление колец/layering.
- **Behavioral analytics / биометрия:** паттерны устройства, времени, геолокации.

---

## 11. ISO 27001 Controls — карта несоответствий

| Контроль | Несоответствие | Риск | Устранение |
|---|---|---|---|
| A.9.4.2 | нет lockout | Высокий | ✅ Stage 1 |
| A.9.2.4 | секреты-дефолты | Высокий | ✅ Stage 1 (валидатор) + Vault (Stage 5) |
| A.13.1 | нет security headers/host check | Средний | ✅ Stage 1 |
| A.9.4.3 | слабая парольная политика | Средний | ✅ Stage 1 |
| A.10.1 | нет шифрования PII | Высокий | Stage 3 |
| A.12.4.1 | нет аудита доступа к PII | Высокий | Stage 2 |
| A.12.4.2 | логи изменяемы | Средний | Stage 2 (hash-chain) |
| A.8.2 | нет классификации данных | Средний | Stage 2 (реестр PII) |
| A.12.6.1 | нет управления уязвимостями | Средний | Stage 5 (CI) |
| A.16.1 | нет процесса реагирования на инциденты ИБ | Средний | Stage 4 |
| A.18.1 | нет RoPA/учёта согласий | Средний | Stage 2/5 |

---

## 12. Privacy by Design

- **Минимизация данных:** собирать только необходимое; убрать избыточные поля из ответов API (DTO с маскированием).
- **Псевдонимизация:** разделить идентификаторы и атрибуты; аналитика на псевдонимизированных данных.
- **Анонимизация:** при удалении под legal hold — анонимизировать (хеш/обнуление PII), сохраняя агрегаты для AML.
- **Разделение данных:** чувствительные поля/документы — в отдельном защищённом хранилище.
- **Жизненный цикл:** `retention_until` + автоматический purge; журнал жизненного цикла.

---

## 13. Secure SDLC (CI/CD security pipeline) — план Stage 5

| Этап | Инструмент | Где |
|---|---|---|
| SAST | Bandit (Python), ESLint security, Semgrep | CI на PR |
| Dependency scanning | `pip-audit`, `npm audit`, Dependabot | CI + еженедельно |
| Secret scanning | gitleaks / trufflehog | pre-commit + CI |
| DAST | OWASP ZAP (baseline) | staging |
| Container scan | Trivy | сборка образов |
| Tests | pytest + покрытие безопасности | CI |

Пример GitHub Actions (фрагмент):
```yaml
- run: pip install pip-audit bandit && pip-audit -r backend/requirements.txt && bandit -r backend/app
- run: cd frontend && npm audit --audit-level=high
```

---

## 14. Enterprise Roadmap

### Этап 1 — Critical Fixes ✅ (выполнено)
- Account lockout, SECRET_KEY/секреты в production, JWT type-check, refresh в теле, security headers, парольная политика.
- Приоритет: Critical • Сложность: низкая • Эффект: закрыты основные дыры аутентификации/инфраструктуры.

### Этап 2 — GDPR Compliance ✅ (выполнено)
- DSAR (доступ/экспорт/удаление/ограничение/исправление), журнал согласий с версией и отзывом, политика хранения + purge, аудит доступа к PII (`PII_VIEWED`), tamper-evident hash-chain аудита + проверка целостности.
- Реализация: модели `DataSubjectRequest`/`Consent`, сервисы `privacy_service`/`audit_service`, эндпоинты `/privacy/*`, фронт-страницы `PrivacyPage` (self-service) и `PrivacyAdminPage` (DSAR/ретеншен/целостность).
- Приоритет: High • Сложность: средняя • Эффект: соответствие GDPR, подотчётность.

### Этап 3 — ISO 27001 (техническая защита)
- Field-level encryption PII, шифрование файлов + защищённая выдача (pre-signed URL, антивирус), маскирование в ответах.
- Приоритет: High • Сложность: средне-высокая • Эффект: защита данных at-rest, A.10/A.8.

### Этап 4 — Enterprise Security
- MFA (TOTP) + backup-коды, token revocation/logout, password reset flow, device trust, ABAC + новые роли (Auditor/DPO), security-инциденты + SIEM, rate limiting.
- Приоритет: Medium-High • Сложность: средняя • Эффект: зрелая модель доступа и реагирования.

### Этап 5 — AI-Powered Fraud Detection & Governance
- ML fraud scoring (интерпретируемый), graph analytics, adverse media, реальные санкционные фиды; CI security pipeline, Vault/KMS, RoPA и процессы breach notification.
- Приоритет: Medium • Сложность: высокая • Эффект: продвинутое выявление мошенничества + операционная зрелость.

---

*Документ поддерживается вместе с кодом. Изменения статуса фиксируются в таблице «Сводка приоритетов».*
