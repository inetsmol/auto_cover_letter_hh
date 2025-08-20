## Настройка Aerich

1. **Инициализация Aerich:**

    В корне проекта выполните:

    ```bash
    aerich init -t src.db.config.TORTOISE_ORM
    ```

    - Создаст папку `migrations/` и файл `.aerich.ini`.

2. **Инициализация миграций и базы:**

    ```bash
    aerich init-db
    ```

    - Создаст все таблицы и первую миграцию.

3. **Работа с миграциями:**

    После каждого изменения моделей выполняйте:

    ```bash
    aerich migrate      # Создать новую миграцию
    aerich upgrade      # Применить миграцию к базе
    ```

    Если нужно откатить последнюю миграцию:

    ```bash
    aerich downgrade
    ```
   
### Запуск Celery
#### Запускать отдельных терминалах

#### Запустить воркер
```bash
celery -A src.celery_app.celery_app worker -l info --queues=celery,free,notifications --pool=solo
```
#### Запустить планировщик
```bash
celery -A src.celery_app.celery_app beat -l info
```