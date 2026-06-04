# Antifraud.SYS — Аудит архитектуры, масштабируемости и план перехода к Enterprise

**Версия:** 1.0 • **Дата:** 2026-06-04
**Цель:** оценить текущую систему и спроектировать переход к платформе на 30M+
пользователей и 100k+ одновременных сессий (микросервисы, event-driven,
multi-region) с соответствием GDPR / ISO 27001 / PCI DSS / SOC 2 / AMLD6 / FATF.

> Документ описывает **текущее состояние (as-is)**, **разрывы (gaps)**, **целевую
> архитектуру (to-be)** и **поэтапный план миграции**. Часть пунктов уже
> реализована (Stages 1–6, см. `SECURITY_COMPLIANCE_AUDIT.md`); остальное —
> проектные рекомендации, требующие инфраструктурной программы работ.

---

## 0. Краткое резюме (Executive Summary)

Текущая система — **монолит** (FastAPI + один PostgreSQL + nginx-фронтенд),
функционально зрелый (KYC, AML, риск-скоринг, инциденты, аудит, device
intelligence, шифрование PII, MFA). Для целевой нагрузки он **не масштабируется
горизонтально без изменений** из-за нескольких SPOF и stateful-зависимостей.

**Ключевые блокеры масштабирования (нужно устранить в первую очередь):**
1. In-memory rate limiter (`slowapi`) — не работает на нескольких инстансах.
2. Хранение документов на локальном диске контейнера — не разделяется между подами.
3. `Base.metadata.create_all` вместо миграций — небезопасно для прод/много-инстансов.
4. Один PostgreSQL без реплик/шардинга — SPOF и предел записи/чтения.
5. Redis и Celery объявлены, но **не используются** (нет кэша/очередей/фоновых задач).
6. Один процесс backend в `docker-compose` — нет автоскейла и отказоустойчивости.

---

## 1. Текущее состояние (As-Is)

| Слой | Сейчас |
|---|---|
| Backend | FastAPI (монолит), async SQLAlchemy 2.0, asyncpg |
| БД | один PostgreSQL 15, схема через `create_all` (Alembic в зависимостях, но не используется) |
| Кэш/очереди | Redis 7 и Celery **объявлены**, но в коде не задействованы |
| Frontend | React 18 + Vite → статика в nginx |
| Аутентификация | JWT (access+refresh, jti, отзыв), MFA TOTP, bcrypt |
| Безопасность | RBAC, шифрование PII (Fernet), hash-chain аудит, lockout, security-заголовки (Stages 1–6) |
| Файлы | локальный диск `uploads/` (зашифрованы) |
| Инфраструктура | Docker Compose: db, redis, backend, frontend; по одному инстансу |
| Наблюдаемость | loguru-логи + `X-Process-Time`; нет метрик/трейсинга |
| Интеграции | внутренние; внешних коннекторов (банки/SWIFT/санкции) нет |

**Сильные стороны:** чистая модульная кодовая база (services/endpoints/models),
async-стек, зрелый домен (KYC/AML/инциденты), сильная безопасность данных.

---

## 2. Масштабируемость (30M+ пользователей, 100k+ сессий)

### Разрывы
- Stateful rate limiter и локальные файлы мешают горизонтальному масштабированию.
- Один PostgreSQL — предел по записи, отсутствие географической репликации.
- Нет автоскейла, health/readiness разнесены слабо, один воркер.

### Целевое решение
- **Stateless-сервисы** за балансировщиком; вынести всё состояние в Redis/БД/объектное хранилище.
- **PostgreSQL: read replicas** (чтение скейлится горизонтально) + **шардинг** по `user_id`/`tenant_id` (Citus/Vitess-подход) либо распределённая БД (**CockroachDB**/YugabyteDB) для multi-region.
- **Redis Cluster** для кэша, сессий, rate-limit, идемпотентности.
- **Партиционирование** «горячих» таблиц по времени: `transactions`, `audit_logs`, `login_history`, `security_events` (partition by month).
- **Multi-region active-active**: гео-маршрутизация (GeoDNS/anycast), репликация БД между регионами, привязка данных к региону (data residency для GDPR).
- **No SPOF:** ≥3 реплики каждого сервиса, ≥3 узла Postgres (1 primary + N replicas + автоматический failover Patroni), Redis Cluster ≥6 узлов, Kafka ≥3 брокера.

---

## 3. Целевая архитектура (To-Be)

### 3.1 Декомпозиция на микросервисы (по bounded contexts)
| Сервис | Ответственность | Текущий код-источник |
|---|---|---|
| **identity-service** | регистрация, логин, MFA, токены, сессии | `auth`, `deps`, `security`, `monitoring`(сессии) |
| **kyc-service** | профили, документы, верификация, OCR/liveness | `clients`, `documents`, `kyc` |
| **aml-service** | мониторинг транзакций, правила, скрининг | `aml_monitor`, `transactions`, `aml` |
| **risk-service** | риск-скоринг, поведенческая аналитика | `risk_engine` |
| **case-service** | инциденты, false-positive, тюнинг правил | `incidents`, `detection_rules` |
| **audit-service** | неизменяемый аудит, активность, security events | `audit_service`, `monitoring` |
| **privacy-service** | DSAR, согласия, ретеншен | `privacy` |
| **notification-service** | уведомления, вебхуки, e-mail | `audit.Notification` |
| **analytics-service** | дашборды, отчётность (CQRS read-side) | `analytics` |

### 3.2 Event-Driven (Kafka)
- Доменные события: `UserRegistered`, `KycSubmitted`, `TransactionCreated`,
  `AlertRaised`, `IncidentClassified`, `SecurityEventDetected`, `ConsentChanged`.
- **Outbox pattern** в каждом сервисе (атомарность БД-запись + событие).
- Потребители: risk-service (скоринг), aml-service (мониторинг), audit-service
  (журнал), analytics-service (проекции), notification-service (вебхуки).
- Брокер: **Apache Kafka** (≥3 брокера, реплика-фактор 3); схемы — Schema Registry (Avro/Protobuf).

### 3.3 API Gateway + Service Discovery
- **API Gateway** (Kong/APISIX/Envoy): маршрутизация, authN/Z (JWT/OAuth2.1/OIDC),
  rate-limit, квоты, mTLS к сервисам, WAF.
- **Service discovery**: Kubernetes DNS + Service mesh (**Istio/Linkerd**) для mTLS,
  retry/timeout/circuit-breaker, трафик-сплит (canary).

### 3.4 CQRS
- Запись (команды) — нормализованные БД сервисов; чтение (запросы) —
  материализованные проекции в analytics-service (например, дашборды
  инцидентов/FP-rate, аудит-витрины) из Kafka-событий. Снимает нагрузку чтения с OLTP.

### 3.5 Кэширование (Redis Cluster)
- Кэш справочников (санкционные списки, страны риска), результатов скрининга,
  сессий, идемпотент* ключей вебхуков; rate-limit storage (заменить in-memory).

### 3.6 Диаграммы (создать)
- C4 (Context/Container/Component), Deployment (multi-region), обновлённый **ER**
  (текущий — в `database/schema.sql`), sequence-диаграммы ключевых потоков.

---

## 4. Интеграции

### 4.1 API-поверхности
- **REST** (уже есть, OpenAPI на `/docs`) — стабилизировать версионирование (`/api/v1`).
- **GraphQL** (Strawberry/Ariadne) — агрегирующий слой для партнёров.
- **Webhook Framework**: подписки, подпись HMAC, ретраи с backoff, dead-letter, идемпотентность.
- **SDK**: генерировать из OpenAPI (openapi-generator) для **Java / Python / Node.js / .NET**.

### 4.2 Внешние коннекторы (anti-corruption layer на каждый)
- Банки / Open Banking (PSD2), **SWIFT** (gpi/MT/MX ISO 20022), **Visa Direct**,
  **Mastercard Send**, ERP/CRM (SAP, Salesforce), госреестры.
- AML/KYC-провайдеры: санкции (OFAC/EU/UN), PEP, adverse media, document/liveness
  (Onfido/Sumsub/Jumio-класс). Каждый — отдельный адаптер с кэшем и rate-limit.

---

## 5. Безопасность (соответствие)

Базовое уже реализовано (Stages 1–6): RBAC, ABAC (частично), MFA, JWT, шифрование
at-rest/in-transit, hash-chain аудит, lockout, rate-limit, device/IP intelligence.

### Дельта до enterprise
- **OAuth 2.1 / OpenID Connect** через внешний IdP (Keycloak/Auth0) + федерация.
- **ABAC** полноценно (атрибутные политики, OPA/Rego) поверх RBAC.
- **HSM / KMS** для мастер-ключей (AWS KMS/CloudHSM, Vault Transit) вместо ключа из env.
- **Secrets Management**: HashiCorp Vault (динамические креды БД, ротация).
- **Zero Trust**: mTLS между сервисами (mesh), per-request authZ, отказ от «доверенной сети».
- **PCI DSS**: при работе с PAN — токенизация, изоляция CDE, скоуп-сегментация.
- **AMLD6 / FATF**: travel rule, расширенный KYC/EDD, SAR-воркфлоу (есть основа в case-service).

---

## 6. Аудит и логирование

Реализовано: неизменяемый hash-chain аудит, device/IP tracking, login/session
history, security events, доступ к системным логам — только админ.

### Дельта
- **SIEM**: экспорт аудита/событий (CEF/JSON) в Splunk/Elastic/Wazuh; корреляция.
- **Geo tracking**: GeoIP-обогащение `login_history`/`security_events`.
- **Risk/Suspicious activity logging**: вынести в поток Kafka + долговременное WORM-хранилище.
- Централизованные логи: **OpenTelemetry logs** → Loki/Elastic.

---

## 7. KYC (расширение)

| Возможность | Статус | План |
|---|---|---|
| Phone verification | телефон обязателен/валиден (E.164) | + OTP-подтверждение (SMS-провайдер) |
| Device fingerprinting | базовое (device id + UA + screen) | + продвинутый fingerprint (FingerprintJS) |
| IP intelligence | IP-история, new-IP события | + репутация IP/VPN/Tor (MaxMind/IPQS) |
| Geolocation verification | — | GeoIP + сверка с заявленной страной |
| Liveness / Face match / OCR | поля под OCR есть | интеграция провайдера (Sumsub/Onfido) |
| Fraud / Duplicate detection | риск-движок | + графовая дедупликация (см. §8) |

## 8. AML (расширение)

Есть: transaction monitoring (7 правил), risk scoring, PEP/sanctions флаги,
поведенческие факторы, инциденты/кейсы, false-positive tuning.

Дельта: реальные **санкционные/PEP/adverse-media** фиды с rescreening; **графовый
анализ связей** (Neo4j/AuraDB) для колец/layering; ML-скоринг (интерпретируемый,
SHAP); полноценный **SAR** (формирование/подача), enhanced case management/SLA.

---

## 9. Производительность (API < 200ms, 99.99% uptime)

### Квик-вины (реализуемо на текущем стеке)
- **Индексы**: добавить под частые выборки (`transactions(client_id, transaction_date)`,
  `audit_logs(created_at)`, `login_history(user_id, created_at)`, `aml_alerts(status, created_at)`).
- **Пагинация курсором** (keyset) вместо OFFSET на больших таблицах.
- **Redis-кэш** справочников и тяжёлых агрегатов; **Celery** для фоновой обработки
  (скоринг, скрининг, экспорты, отправка вебхуков/SMS).
- **Connection pooling**: PgBouncer перед PostgreSQL.
- **Несколько воркеров**: gunicorn/uvicorn workers + горизонтальный автоскейл.
- Партиционирование больших таблиц по времени; архивация холодных данных.

### Целевые SLO
- p99 API < 200ms (на read-проекциях и кэше), 99.99% uptime (multi-AZ/region,
  health-checks, авто-failover), нагрузочные тесты (k6/Locust) в CI.

---

## 10. DevOps / Платформа

| Область | План |
|---|---|
| Контейнеры | многоступенчатые образы (есть для фронта); non-root, минимальные базовые образы |
| Оркестрация | **Kubernetes** (HPA по CPU/lag Kafka), PodDisruptionBudget, anti-affinity |
| Пакеты | **Helm-charts** на сервис; values per-env |
| CI/CD | есть базовый CI (tests/build/SAST/scan); добавить build→scan→deploy, **blue-green** и **canary** (Argo Rollouts/Flagger) |
| Конфиг/секреты | Vault + External Secrets Operator |
| Наблюдаемость | **Prometheus** (метрики) + **Grafana** (дашборды) + **OpenTelemetry** (трейсинг) + Loki (логи) |
| Надёжность | мультизональные ноды, бэкапы БД (PITR), DR-регион |

---

## 11. Документация (создать)

OpenAPI/Swagger (есть `/docs` — дополнить примерами и версионированием),
Architecture Diagram (C4), ER Diagram, Deployment Guide, Integration Guide,
Security Guide (есть основа в `SECURITY_COMPLIANCE_AUDIT.md`), **Disaster Recovery Plan**
(RTO/RPO, бэкапы, failover-процедуры, runbooks).

---

## 12. План миграции (Strangler Fig, поэтапно)

**Фаза 0 — Подготовка платформы (квик-вины, низкий риск)**
- Alembic-миграции вместо `create_all`; Redis-backed rate-limit; вынос файлов в
  S3/MinIO; PgBouncer; индексы; Celery+Redis для фоновых задач; gunicorn workers.
- *Эффект:* монолит становится горизонтально масштабируемым и stateless.

**Фаза 1 — Платформа наблюдаемости и K8s**
- Контейнеризация под K8s, Helm, Prometheus/Grafana/OTel, CI/CD blue-green/canary,
  Vault. Нагрузочное тестирование, базовые SLO.

**Фаза 2 — API Gateway + события**
- Kong/Envoy gateway, внешний IdP (OAuth2.1/OIDC), Kafka + outbox; первые события
  (audit, notifications) как отдельные потребители.

**Фаза 3 — Выделение сервисов**
- Отделять по контекстам: audit-service и analytics-service (CQRS read-side) →
  identity → kyc → aml/risk → case/privacy. По одному, со strangler-маршрутизацией через gateway.

**Фаза 4 — Данные в масштабе**
- Read replicas → шардинг/распределённая БД (CockroachDB) → multi-region active-active,
  data residency, гео-маршрутизация.

**Фаза 5 — Интеграции и интеллект**
- Внешние коннекторы (SWIFT/card rails/Open Banking), реальные AML/KYC-фиды,
  графовый анализ, ML-скоринг, SDK (Java/Python/Node/.NET), GraphQL, Webhooks.

---

## 13. Что уже сделано в репозитории (база для перехода)
- Stages 1–6: аутентификация/MFA/токены, GDPR-движок (DSAR/согласия/ретеншен),
  шифрование PII/файлов, hash-chain аудит, device/IP intelligence, security events,
  rate-limit, CI с SAST/деп-сканами/секрет-сканом, RoPA, IR-runbook, access matrix.
- Это покрывает значительную часть требований «Безопасность», «Аудит», «KYC/AML
  (базовый)» и «Документация (security)». Остальное — инфраструктурная программа выше.

---

## 14. Приоритетные «реализуемо сейчас» улучшения (можно внедрить в текущий монолит)
1. **Alembic-миграции** (заменить `create_all`). ✅ Scaffolding готов (`backend/alembic.ini`, `backend/migrations/`); см. `backend/migrations/README.md` для генерации baseline.
2. **Rate-limit в Redis** (slowapi storage) — снимает SPOF для multi-instance. ✅ Реализовано (`RATE_LIMIT_STORAGE_URI`, в Docker → `redis://redis:6379`).
3. **Документы в S3/MinIO** (вместо локального диска) + pre-signed URL. ✅ Реализовано: pluggable хранилище (`STORAGE_BACKEND=local|s3`), MinIO в docker-compose, Fernet-шифрование сохранено, выдача потоком через API; `presigned_get()` доступен в S3-бэкенде.
4. **Celery + Redis** для фоновых задач (скоринг/скрининг/экспорт/вебхуки).
5. **PgBouncer + индексы + keyset-пагинация**.
6. **Prometheus-метрики + OpenTelemetry** (FastAPI instrumentation).
7. **gunicorn-воркеры + K8s-манифесты/Helm-skeleton**.

> Любой из пунктов §14 можно реализовать и закоммитить отдельно — это реальные,
> низкорисковые шаги к enterprise-готовности без полного переписывания.
