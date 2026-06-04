# Changelog — масштабируемость, UX и инфраструктура (после Stage 1–6)

**Проект:** Antifraud.SYS • **Дата:** 2026-06-04
Сравнительная таблица «До → После» для пакета изменений, сделанных после
security-этапов (Stage 1–6, см. `CHANGELOG_SECURITY.md`). Для каждого пункта —
**где проверить**.

---

## Масштабируемость / производительность (§14 архитектурного аудита)

| # | Что | До | После | Где проверить |
|---|---|---|---|---|
| 1 | Rate limiting | In-memory (ломался при нескольких инстансах) | Конфигурируемое хранилище; в Docker → Redis (общий лимит) | `RATE_LIMIT_STORAGE_URI`, `app/core/rate_limit.py`, docker-compose |
| 2 | Миграции БД | Только `create_all` при старте | Alembic-scaffolding (env.py, alembic.ini) — контролируемые миграции | `backend/alembic.ini`, `backend/migrations/`, `migrations/README.md` |
| 3 | Хранилище документов | Локальный диск (не делится между инстансами) | Pluggable `local`/`s3`; MinIO в Docker; шифрование Fernet сохранено | `app/services/storage.py`, MinIO http://localhost:9001 |
| 4 | Фоновые задачи | Redis/Celery объявлены, но не использовались | Celery + Redis: `recalculate_risk_score`, `send_notification`; worker-сервис | `POST /clients/{id}/risk-score/async`, `GET /tasks/{id}`, `docker-compose logs worker` |
| 5 | Индексы БД | Описаны в schema.sql, но в рантайме не создавались | Индексы объявлены в моделях (реально создаются `create_all`) | `transactions`, `audit_logs`, `login_history`, `user_activity_logs`, `security_events` |
| 6 | Пагинация | Только OFFSET (медленно на больших таблицах) | Keyset-курсор `before_id` в `/monitoring/audit` (OFFSET сохранён по умолчанию) | `GET /api/v1/monitoring/audit?before_id=...` |
| 7 | Пул соединений БД | Нет | PgBouncer-сервис (опционально, профиль `pooler`) | `docker-compose --profile pooler up` |

## Аудит и активность клиента

| Что | До | После | Где проверить |
|---|---|---|---|
| Действия клиента | Не логировались | `PROFILE_CREATED/UPDATED`, `DOCUMENT_UPLOADED`, `TRANSACTION_CREATED` в `user_activity_logs` | Audit Dashboard → «Действия» |
| Захват устройства клиента | Только при входе | + при создании/правке профиля, загрузке документа, транзакции | Audit Dashboard → «Устройства»; My Activity |
| PII_VIEWED | USERNAME/ROLE/DEVICE_ID пустые | Заполняются (кто/роль/устройство) | Audit Dashboard → «Аудит» |

## UX / интерфейс

| Что | До | После | Где проверить |
|---|---|---|---|
| Фавикон вкладки | Стандартный глобус (файл отсутствовал) | Синий «щит» как в сайдбаре | вкладка браузера; `frontend/public/shield.svg` |
| Регистрация: пароль | Только точки, без индикатора | «Глазок» (показать/скрыть) для пароля и подтверждения | страница Register |
| Сложность пароля | Не оценивалась | Индикатор слабый/средний/надёжный; слабый **не принимается** | страница Register |
| Телефон при регистрации | Не было; nationality в KYC | Обязательный уникальный телефон (E.164); nationality убрана | Register, KYC Form |

## Инфраструктура / репозиторий

| Что | До | После | Где проверить |
|---|---|---|---|
| Переносы строк | Предупреждения `LF will be replaced by CRLF` | `.gitattributes` фиксирует LF | `.gitattributes` |
| docker-compose | Устаревший атрибут `version` | Удалён (нет предупреждения Compose v2) | `docker-compose.yml` |
| Сервисы Docker | db, redis, backend, frontend | + **minio** (хранилище), **worker** (Celery), pgbouncer (опц.) | `docker-compose ps` |

---

## Как проверить «после» вживую

```cmd
cd /d C:\Users\User\Desktop\Dissertation\kyc-aml-platform
docker-compose up -d --build
docker-compose exec backend python seed_data.py
docker-compose ps        # db, redis, minio, backend, worker, frontend = Up
```

1. **Фоновые задачи (Celery):** `POST /api/v1/clients/1/risk-score/async` → вернёт `task_id`;
   `GET /api/v1/tasks/{task_id}` → `state: SUCCESS`. Логи: `docker-compose logs worker`.
2. **S3/MinIO:** загрузи документ клиентом → в MinIO (http://localhost:9001) в бакете
   `kyc-documents` появятся (зашифрованные) объекты.
3. **Rate-limit:** >10 быстрых POST `/auth/login` → `429 Too Many Requests`.
4. **Аудит/устройства:** действия клиента видны админом в **Audit Dashboard** (вкладки
   «Действия»/«Устройства»), пользователь — только свои в **My Activity**.
5. **Keyset:** `GET /api/v1/monitoring/audit?before_id=<id>` возвращает записи с меньшим id.
6. **Фавикон/Register:** открой вкладку (синий щит) и страницу регистрации (глазок + индикатор пароля).

## Связанные документы
- `docs/SCALABILITY_ARCHITECTURE_AUDIT.md` — полный архитектурный аудит и план до 30M+
- `docs/CHANGELOG_SECURITY.md` — before/after по Stage 1–6 (безопасность/GDPR)
- `docs/ACCESS_MATRIX.md` — матрица доступа ролей
