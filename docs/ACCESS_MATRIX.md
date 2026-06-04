# Матрица доступа (RBAC) — Antifraud.SYS

**Дата:** 2026-06-04 • **Источник:** фактические зависимости доступа в коде
(`require_analyst` / `require_compliance` / `require_admin` / `get_current_user`).

## Роли и иерархия

| Роль (код) | Назначение | Включает права |
|---|---|---|
| `client` | Клиент — только свои данные | — |
| `risk_analyst` | Аналитик — расследование | + просмотр клиентов/AML/инцидентов |
| `compliance_officer` | Комплаенс — решения | + всё аналитика, ревью, AML-решения |
| `admin` | Администратор — полный контроль | + всё комплаенса, пользователи, тюнинг, GDPR-админ |

**Сопоставление зависимостей:**
`require_analyst` = analyst + compliance + admin · `require_compliance` = compliance + admin · `require_admin` = admin.

**Легенда:** ✅ доступно · — нет доступа · 🔒 только свои данные · ⚑ с ограничением ABAC.

---

## Аккаунт и безопасность (любой авторизованный)

| Действие | Эндпоинт | Client | Analyst | Compliance | Admin |
|---|---|:--:|:--:|:--:|:--:|
| Вход / выход (с отзывом токена) | `/auth/login`, `/auth/logout` | ✅ | ✅ | ✅ | ✅ |
| Свой профиль аккаунта | `/auth/me` | ✅ | ✅ | ✅ | ✅ |
| 2FA (вкл/проверка/выкл) | `/auth/mfa/*` | ✅ | ✅ | ✅ | ✅ |
| Сброс пароля | `/auth/password-reset/*` | ✅ | ✅ | ✅ | ✅ |

## Приватность / GDPR (самообслуживание — любой авторизованный)

| Действие | Эндпоинт | Client | Analyst | Compliance | Admin |
|---|---|:--:|:--:|:--:|:--:|
| Экспорт своих данных | `/privacy/my-data/export` | ✅ | ✅ | ✅ | ✅ |
| Управление согласиями | `/privacy/consents` | ✅ | ✅ | ✅ | ✅ |
| Подать запрос DSAR | `/privacy/requests` | ✅ | ✅ | ✅ | ✅ |

## Клиентский профиль

| Действие | Эндпоинт | Client | Analyst | Compliance | Admin |
|---|---|:--:|:--:|:--:|:--:|
| Создать / смотреть / править свой профиль | `/clients/profile/me` | 🔒 | — | — | — |
| Список всех клиентов | `GET /clients/` | — | — | ✅ | ✅ |
| Карточка клиента по id | `GET /clients/{id}` | — | ✅ | ✅ | ✅ |
| Пересчёт риска клиента | `POST /clients/{id}/risk-score` | — | ✅ | ✅ | ✅ |
| Риск-оценка клиента | `GET /clients/{id}/risk-assessment` | — | ✅ | ✅ | ✅ |

## Документы

| Действие | Эндпоинт | Client | Analyst | Compliance | Admin |
|---|---|:--:|:--:|:--:|:--:|
| Загрузка / просмотр / скачивание своих | `/documents/upload`, `/documents/my` | 🔒 | — | — | — |
| Список документов клиента | `GET /documents/client/{id}` | — | — | ✅ | ✅ |
| Скачать документ клиента | `GET /documents/{id}/download` | 🔒 | — | ✅ | ✅ |
| Проверка документа (одобрить/отклонить) | `PUT /documents/{id}/review` | — | — | ✅ | ✅ |

## Транзакции

| Действие | Эндпоинт | Client | Analyst | Compliance | Admin |
|---|---|:--:|:--:|:--:|:--:|
| Создать / смотреть свои | `POST /transactions/`, `/transactions/my` | 🔒 | — | — | — |
| Транзакции клиента | `GET /transactions/client/{id}` | — | ✅ | ✅ | ✅ |
| Сводная статистика | `GET /transactions/stats/summary` | — | ✅ | ✅ | ✅ |

## AML-мониторинг

| Действие | Эндпоинт | Client | Analyst | Compliance | Admin |
|---|---|:--:|:--:|:--:|:--:|
| Список / детали алертов, статистика | `GET /aml/alerts*`, `/aml/stats` | — | ✅ | ✅ | ✅ |
| Изменить алерт (расследование / SAR) | `PUT /aml/alerts/{id}` | — | — | ✅ | ✅ |

## KYC-ревью

| Действие | Эндпоинт | Client | Analyst | Compliance | Admin |
|---|---|:--:|:--:|:--:|:--:|
| Начать ревью / вынести решение / очередь | `/reviews/*` | — | — | ✅ | ✅ |

## Аналитика

| Действие | Эндпоинт | Client | Analyst | Compliance | Admin |
|---|---|:--:|:--:|:--:|:--:|
| Дашборды, тренды, инциденты, FP, риск | `/analytics/*` | — | ✅ | ✅ | ✅ |

## Управление инцидентами

| Действие | Эндпоинт | Client | Analyst | Compliance | Admin |
|---|---|:--:|:--:|:--:|:--:|
| Список / детали / список аналитиков | `GET /incidents*`, `/incidents/meta/analysts` | — | ✅ | ✅ | ✅ |
| Назначение | `POST /incidents/{id}/assign` | — | ✅ | ✅ | ✅ |
| Статус / эскалация / коммент / риск-оценка / классификация | `/incidents/{id}/*` | — | ⚑ | ✅ | ✅ |

⚑ Аналитик может действовать **только по назначенным ему тикетам** (ABAC); комплаенс и админ — без ограничений (segregation of duties).

## Тюнинг правил детекции

| Действие | Эндпоинт | Client | Analyst | Compliance | Admin |
|---|---|:--:|:--:|:--:|:--:|
| Просмотр правил / FP / история | `GET /detection-rules*` | — | ✅ | ✅ | ✅ |
| Изменить правило (tune, версия) | `POST /detection-rules/{id}/tune` | — | — | — | ✅ |

## GDPR-администрирование

| Действие | Эндпоинт | Client | Analyst | Compliance | Admin |
|---|---|:--:|:--:|:--:|:--:|
| Все DSAR-запросы | `GET /privacy/requests/all` | — | — | — | ✅ |
| Обработка DSAR (удаление→анонимизация и т.д.) | `POST /privacy/requests/{id}/process` | — | — | — | ✅ |
| Retention-purge | `POST /privacy/retention/purge` | — | — | — | ✅ |
| Проверка целостности аудита | `GET /privacy/audit/integrity` | — | — | — | ✅ |

## Администрирование системы

| Действие | Эндпоинт | Client | Analyst | Compliance | Admin |
|---|---|:--:|:--:|:--:|:--:|
| Пользователи: список/создать/изменить/деактивировать, роли | `/admin/users*` | — | — | — | ✅ |
| Журнал аудита | `GET /admin/audit-logs` | — | — | — | ✅ |
| Системная статистика | `GET /admin/stats` | — | — | — | ✅ |

---

## Сопоставление с ролями модуля инцидентов (из ТЗ)
- **Analyst** → `risk_analyst`
- **Senior Analyst** → `compliance_officer`
- **Manager + Administrator** → `admin`

> Связанные документы: `docs/SECURITY_COMPLIANCE_AUDIT.md`, `docs/RoPA.md`, `docs/CHANGELOG_SECURITY.md`.
