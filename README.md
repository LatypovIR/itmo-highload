# HW1. Инструменты автоматизации в Grafana

Модельный CRUD-сервис заказов `orders-service` (Python + FastAPI), три его пода в двух
датацентрах, VictoriaMetrics, Grafana, генератор дашборда и нагрузочный скрипт.
Всё поднимается одним `docker compose up`.

## Состав

| Сервис | Что делает | Порт на хосте |
|---|---|---|
| `app-dc1-pod0`, `app-dc1-pod1`, `app-dc2-pod0` | CRUD-сервис, in-memory хранилище | 8081, 8082, 8083 |
| `victoriametrics` | скрейпит `/metrics` всех подов раз в 5 с | 8428 |
| `grafana` | Grafana 11.6.16, datasource VictoriaMetrics через provisioning | 3000 |
| `grafana-init` | создаёт service account `dashboard-generator` и выпускает токен | — |
| `dashboard-generator` | генерирует дашборд по списку ручек запущенного приложения | — |
| `loadgen` | k6 (`grafana/k6:2.3.0`), сценарий `loadgen/load.js` | — |

Ручки сервиса:

| Метод | Путь | Ответы |
|---|---|---|
| `POST` | `/orders` | 201, 422 (невалидное тело) |
| `GET` | `/orders?limit=N` | 200 |
| `GET` | `/orders/{order_id}` | 200, 404 |
| `PUT` | `/orders/{order_id}` | 200, 404, 422 |
| `GET` | `/health` | 200 (health probe, в метрики не входит) |
| `GET` | `/metrics` | экспозиция Prometheus |

Заказ: `customer_id`, `items` (`sku`, `quantity`), `status` (`created`, `paid`,
`shipped`, `cancelled`). `POST` создаёт заказ в статусе `created`, `PUT` заменяет его целиком.

Каждая CRUD-ручка с вероятностью `FAULT_RATE` (по умолчанию 5%) отвечает `503`,
поэтому в метриках есть 5xx. Ещё 4xx даёт нагрузка невалидными запросами.

Параметры пода приходят из environment:

| Переменная | Пример | Смысл |
|---|---|---|
| `POD_ID` | `0` | номер пода |
| `DATACENTER` | `dc1` | датацентр |
| `DEPLOYMENT_NAME` | `orders-service` | название развертывания |
| `FAULT_RATE` | `0.05` | доля искусственных 503 |

## Запуск

Нужен Docker с Compose v2: плагин `docker compose` или бинарник `docker-compose`.

```bash
./scripts/init-secrets.sh
docker compose up --build -d
```

Порядок старта задан через `depends_on`:

1. `victoriametrics` → `grafana` (ждёт healthcheck) → `grafana-init` (создаёт SA и токен).
2. `dashboard-generator` стартует, когда `grafana-init` завершился успешно и у всех
   подов приложения прошла health probe `/health`.
3. `loadgen` стартует после успешного завершения генератора.

Grafana: <http://localhost:3000>, пользователь `admin`, пароль —
`secrets/grafana_admin_password.txt`.

Остановить и удалить данные:

```bash
docker compose down -v
```

## Секреты

- Пароль администратора Grafana генерирует `scripts/init-secrets.sh` в
  `secrets/grafana_admin_password.txt` с правами `600`. Каталог `secrets/` в `.gitignore`.
- Пароль попадает в контейнеры как Docker secret (`/run/secrets/...`) через
  `GF_SECURITY_ADMIN_PASSWORD__FILE`, а не через переменную окружения, поэтому не виден
  в `docker inspect`.
- Service Account Token выпускает `grafana-init` при каждом `up`. Старые токены этого
  SA он отзывает. Токен пишется в файл на volume `grafana-sa-token` (права `600`), генератор
  монтирует volume только на чтение. В git, env и логах токена нет.
- Роль SA — `Editor`: её хватает для создания дашбордов, прав администратора у генератора нет.

## Проверка вручную

```bash
curl -s -XPOST localhost:8081/orders -H 'content-type: application/json' \
  -d '{"customer_id":"c1","items":[{"sku":"milk","quantity":2}]}'
curl -s -XPUT localhost:8081/orders/1 -H 'content-type: application/json' \
  -d '{"customer_id":"c1","items":[{"sku":"milk","quantity":3}],"status":"paid"}'
curl -s localhost:8081/orders/1
curl -s 'localhost:8428/api/v1/query?query=up'
```

VictoriaMetrics по умолчанию не отдаёт точки свежее 30 с (`-search.latencyOffset`),
поэтому сразу после старта запросы могут вернуть пустой результат.

## Версии

| Компонент | Версия |
|---|---|
| Grafana | `grafana/grafana:11.6.16` |
| Grafana Foundation SDK (Python) | `grafana-foundation-sdk==1769699379!11.6.0` — ветка SDK под Grafana 11.6 |
| VictoriaMetrics | `victoriametrics/victoria-metrics:v1.154.1` |
| k6 | `grafana/k6:2.3.0` |
| Python | 3.13 |

Под Grafana 12+ SDK для Python на PyPI нет, поэтому Grafana закреплена на 11.6.

## Что осталось реализовать (содержательная часть)

- [ ] **Библиотека метрик** поверх `prometheus_client`: лёгкая идиома навешивания на
      ручки (middleware / декоратор / ...), latency (p50/75/90/95/99), RPS, ошибки по
      HTTP-кодам; лейблы pod, datacenter, deployment, ручка, тип метрики из env.
      Подключить в `app/orders_service/main.py`.
- [ ] **Список ручек** в рантайме: библиотека должна отдавать набор ручек приложения.
- [ ] **Генератор** `generator/generate_dashboard.py`: забрать список ручек у `TARGET_URL`,
      собрать дашборд через SDK с селекторами датацентра и пода, PromQL с агрегирующими
      функциями (sum для rate, корректные перцентили), non-editable, отправить в Grafana.
- [ ] **Нагрузка** `loadgen/load.js` (k6; сейчас там только разовая проверка `/health`): плавный разгон до фоновой нагрузки по всем подам, часть
      запросов с ошибками.
- [ ] Скриншот дашборда под нагрузкой — в описание PR.
