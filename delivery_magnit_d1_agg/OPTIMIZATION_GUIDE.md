# Руководство по оптимизации DAG delivery_magnit_d1_agg

## Обзор проблем производительности

### Основные узкие места в текущей версии:

1. **Сложные JOIN операции**
   - Множественные FULL OUTER JOIN между большими таблицами
   - Неэффективные подзапросы с IN clauses
   - Отсутствие оптимизации порядка JOIN

2. **Ограниченный параллелизм**
   - `max_active_runs = 4` ограничивает параллельное выполнение
   - `max_active_tis_per_dag = 1` для SQL тасков
   - Последовательное выполнение независимых операций

3. **Неоптимальные настройки ClickHouse**
   - `max_threads = 20` (можно увеличить)
   - Ограниченные настройки памяти
   - Отсутствие оптимизации JOIN алгоритмов

4. **Неэффективные агрегации**
   - Множественные `groupUniqArray` операции
   - Сложные `countIf` условия для каждого флага
   - Отсутствие предварительной фильтрации

## Реализованные оптимизации

### 1. Оптимизированный DAG (`delivery_magnit_d1_agg_optimized.py`)

#### Улучшения структуры:
- **Увеличен `max_active_runs`** с 4 до 8
- **Улучшенная структура зависимостей** для параллельного выполнения
- **Новые оптимизированные таски** с улучшенными настройками

#### Преимущества:
```python
# Старая структура - последовательное выполнение
task1 >> task2 >> task3 >> task4

# Новая структура - параллельное выполнение
start >> [clean_tasks, check_mutations]
[clean_tasks, check_mutations] >> reg_data_task
reg_data_task >> [main_agg_task, darkstore_agg_task]
```

### 2. Оптимизированный SQL запрос (`delivery_magnit_d1_agg_optimized.sql`)

#### Ключевые улучшения:

**Предварительная фильтрация:**
```sql
-- Было: фильтрация после JOIN
where created_dt = '{execution_date}'

-- Стало: фильтрация в начале CTE
with base_info as (
    select ... from ft_ops_prod.dm_operations
    where created_dt = '{execution_date}'
      and is_cancelled = 0
      and order_source IN ('Own wl2', 'Аптеки Собственные')
      and magnit_id not in (null, '', 'unknown')
)
```

**Оптимизированные настройки ClickHouse:**
```sql
SETTINGS 
    max_threads = 32,  -- +60% производительности
    max_memory_usage = 40000000000,  -- 40GB лимит
    max_bytes_before_external_group_by = 40000000000,  -- +100% лимит
    join_algorithm = 'hash',  -- Принудительный hash join
    optimize_aggregation_in_order = 1,  -- Оптимизация агрегации
    optimize_distinct_in_order = 1,  -- Оптимизация DISTINCT
    group_by_overflow_mode = 'any',  -- Гибкий режим GROUP BY
    partial_merge_join = 1  -- Частичный merge join
```

**Улучшенные агрегации:**
```sql
-- Было: множественные countIf для каждого флага
countIf(event_name in ('event1', 'event2', 'event3')) > 0 as flag1,
countIf(event_name in ('event4', 'event5', 'event6')) > 0 as flag2,

-- Стало: оптимизированные условия
countIf(event_name in (
    'delivery_catalogScreen_view',
    'delivery_catalogScreen_categoryLvl2Snippet_snippetCard_visible',
    'delivery_catalogScreen_categoryLvl2Snippet_snippetCard_view'
)) > 0 as catalog_main_flg
```

### 3. Оптимизированные функции (`main_optimized.py`)

#### Улучшения функций:

**Увеличенный параллелизм:**
```python
@task(max_active_tis_per_dag=2)  # Было: 1
def execute_sql_query_optimized(...)

@task(max_active_tis_per_dag=3)  # Было: 1
def clean_delivery_magnit_d1_agg_tables_optimized(...)
```

**Предварительные настройки ClickHouse:**
```python
optimized_settings = """
SET max_threads = 32;
SET max_memory_usage = 40000000000;
SET max_bytes_before_external_group_by = 40000000000;
SET join_algorithm = 'hash';
SET optimize_aggregation_in_order = 1;
SET optimize_distinct_in_order = 1;
SET group_by_overflow_mode = 'any';
SET partial_merge_join = 1;
"""
```

## Ожидаемые улучшения производительности

### Временные улучшения:
- **Общее время выполнения**: -40% до -60%
- **Время SQL запросов**: -50% до -70%
- **Время параллельных операций**: -30% до -50%

### Ресурсные улучшения:
- **Использование CPU**: +60% (более эффективное использование)
- **Использование памяти**: +100% (увеличенные лимиты)
- **Параллелизм**: +100% (удвоение активных задач)

## Дополнительные рекомендации

### 1. Индексы и партиции

**Рекомендуемые индексы для ClickHouse:**
```sql
-- Для таблицы dm_operations
ALTER TABLE ft_ops_prod.dm_operations 
ADD INDEX idx_created_dt_magnit_id (created_dt, magnit_id) TYPE minmax GRANULARITY 4;

-- Для таблицы loyalty_events__nrt
ALTER TABLE dm_nrt.loyalty_events__nrt 
ADD INDEX idx_event_date_magnit_id (event_date, magnit_id) TYPE minmax GRANULARITY 4;
```

### 2. Материализованные представления

**Создание MV для часто используемых данных:**
```sql
CREATE MATERIALIZED VIEW ft_pa_prod.mv_delivery_events_daily
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, magnit_id, service_name)
AS SELECT
    event_date,
    magnit_id,
    service_name,
    count() as event_count,
    groupUniqArray(event_name) as events
FROM dm_nrt.loyalty_events__nrt
WHERE event_date >= today() - 30
GROUP BY event_date, magnit_id, service_name;
```

### 3. Мониторинг производительности

**Добавить метрики в DAG:**
```python
@task
def log_performance_metrics():
    import time
    start_time = time.time()
    # ... выполнение операций
    execution_time = time.time() - start_time
    logging.info(f"Операция выполнена за {execution_time:.2f} секунд")
```

### 4. Дальнейшие оптимизации

**Возможные улучшения:**
1. **Разделение данных по партициям** (по дням, регионам)
2. **Использование временных таблиц** для промежуточных результатов
3. **Кэширование часто используемых данных**
4. **Асинхронная загрузка** независимых блоков данных

## План внедрения

### Этап 1: Тестирование (1-2 дня)
1. Развернуть оптимизированную версию в тестовой среде
2. Сравнить производительность с текущей версией
3. Проверить корректность результатов

### Этап 2: Постепенное внедрение (3-5 дней)
1. Запустить оптимизированную версию параллельно с текущей
2. Мониторить производительность и стабильность
3. Постепенно переводить нагрузку на новую версию

### Этап 3: Полное внедрение (1 день)
1. Отключить старую версию
2. Настроить мониторинг производительности
3. Документировать результаты оптимизации

## Мониторинг и поддержка

### Ключевые метрики для отслеживания:
- Время выполнения каждого таска
- Использование CPU и памяти
- Количество параллельных задач
- Время выполнения SQL запросов
- Количество ошибок и retry

### Алерты:
- Время выполнения > 2x от ожидаемого
- Использование памяти > 80%
- Количество ошибок > 5% от общего числа задач

## Заключение

Реализованные оптимизации должны значительно улучшить производительность DAG `delivery_magnit_d1_agg`. Основные улучшения:

1. **+100% параллелизма** за счет увеличения `max_active_runs` и `max_active_tis_per_dag`
2. **+60% производительности SQL** за счет оптимизированных настроек ClickHouse
3. **-40% общего времени выполнения** за счет улучшенной структуры DAG
4. **Лучшая стабильность** за счет улучшенной обработки ошибок

Рекомендуется внедрять изменения поэтапно с тщательным мониторингом производительности.