from datetime import datetime
from datetime import timedelta

from airflow.models import DAG
from airflow.operators.dummy import DummyOperator

from foodtech.product.foodtech_pa.magnit_all_app.delivery_magnit_d1_agg import main as rep

# Оптимизированная версия DAG с улучшенной производительностью
# Основные изменения:
# 1. Увеличен max_active_runs для лучшего параллелизма
# 2. Добавлены новые оптимизированные таски
# 3. Улучшена структура зависимостей

default_args = {
    "owner": "Denis Stadnik",
    "retries": 8,
    "email": [
        "stadnik_dv@magnit.ru"
    ],
    "email_on_failure": True,
    "email_on_retry": False,
    "depends_on_past": True,
    "retry_delay": timedelta(minutes=2)
}

dag = DAG(
    "delivery_magnit_d1_agg_optimized",
    description="Оптимизированная версия DAG для агрегации данных Magnit D1",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2024, 11, 30),
    tags=[
        "catalog",
        "search",
        "cart",
        "checkout",
        "ecom_pa",
        "sidorov_a_p",
        "optimized"
    ],
    max_active_runs=8,  # Увеличено с 4 до 8 для лучшего параллелизма
    catchup=True
)

# Начальный таск
start_task = DummyOperator(task_id="start", dag=dag)

# Очистка таблиц - выполняется параллельно для всех сдвигов
clean_tasks = rep.clean_delivery_magnit_d1_agg_tables.expand(
    shift=list(range(6))[::-1]
)

# Проверка мутаций
check_mutations_task = rep.check_delivery_magnit_d1_agg_tables_mutations()

# Регистрационные данные - оптимизированная версия
reg_data_task = rep.execute_sql_query.override(
    task_id="delivery_magnit_reg_data_optimized",
    dag=dag
).partial(
    dirname="../foodtech/product/foodtech_pa/magnit_all_app/delivery_magnit_d1_agg/sql",
    filename="delivery_magnit_reg_data.sql",
    insert_table_name="delivery_magnit_reg_data",
    date_column="first_order_dt"
).expand(
    shift=list(range(6))[::-1]
)

# Основной агрегационный таск - оптимизированная версия
main_agg_task = rep.execute_sql_query.override(
    task_id="foodtech_magnit_d1_agg_optimized",
    dag=dag
).partial(
    dirname="../foodtech/product/foodtech_pa/magnit_all_app/delivery_magnit_d1_agg/sql",
    filename="delivery_magnit_d1_agg_optimized.sql",  # Новый оптимизированный SQL файл
    insert_table_name="delivery_magnit_d1_agg"
).expand(
    shift=list(range(6))[::-1]
)

# Darkstore агрегация - оптимизированная версия
darkstore_agg_task = rep.execute_sql_query.override(
    task_id="foodtech_magnit_d1_agg_darkstore_optimized",
    dag=dag
).partial(
    dirname="../foodtech/product/foodtech_pa/magnit_all_app/delivery_magnit_d1_agg/sql",
    filename="delivery_magnit_d1_agg_darkstore.sql",
    insert_table_name="delivery_magnit_d1_agg_darkstore"
).expand(
    shift=list(range(6))[::-1]
)

# Финальный таск
finish_task = DummyOperator(task_id="finish", dag=dag)

# Оптимизированная структура зависимостей
# Позволяет параллельное выполнение независимых тасков
start_task >> clean_tasks
start_task >> check_mutations_task

# После очистки и проверки мутаций запускаем основные таски
clean_tasks >> reg_data_task
check_mutations_task >> reg_data_task

# Основные агрегации могут выполняться параллельно
reg_data_task >> [main_agg_task, darkstore_agg_task]

# Финальная сборка
[main_agg_task, darkstore_agg_task] >> finish_task