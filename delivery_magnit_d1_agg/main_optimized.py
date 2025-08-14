from airflow.decorators import task
import logging

delivery_magnit_d1_agg_tables = [
    "delivery_magnit_d1_agg",
    "delivery_magnit_reg_data", 
    "delivery_magnit_d1_agg_darkstore"
]

clickhouse_connection = 'clickhouse_ft_pa'

def check_mutations(schema, table, cluster, context):
    import datetime
    from airflow.models import Variable
    from utils.clickhouse.check_mutation import CheckMutationSensor

    clickhouse_connection = 'clickhouse_ft_pa'
    cluster = Variable.get('foodtech_cluster')

    time_start_mutation = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    CheckMutationSensor(
        clickhouse_connection_id=clickhouse_connection,
        check_schema=schema,
        check_table=table,
        cluster=cluster,
        timeout=12000,
        task_id=f"check_{schema}.{table}_{time_start_mutation}",
        dag=context["dag"]
    ).execute(context)

@task(max_active_tis_per_dag=2)  # Увеличено с 1 до 2 для лучшего параллелизма
def execute_sql_query_optimized(
        dirname: str,
        filename: str,
        shift: int,
        insert_table_name="default",
        date_column="event_date",
        database="ft_pa_prod"
) -> None:
    """
    Оптимизированная версия функции execute_sql_query с улучшенной производительностью
    
    Основные оптимизации:
    1. Увеличен max_active_tis_per_dag для лучшего параллелизма
    2. Улучшенная обработка ошибок
    3. Оптимизированные настройки ClickHouse
    4. Предварительная проверка данных
    """

    import datetime
    from airflow.exceptions import AirflowFailException
    from airflow.models import Variable
    from airflow.operators.python import get_current_context
    from foodtech.product.foodtech_pa.magnit_all_app.tools.clickhouse_functions import drop_partitions
    from utils.clickhouse.check_mutation import CheckMutationSensor
    from utils.clickhouse.func import clickhouse_conn
    from utils.operate_files import read_from_file

    clickhouse_connection = 'clickhouse_ft_pa'
    cluster = Variable.get('foodtech_cluster')

    ch_client = clickhouse_conn(clickhouse_conn_id=clickhouse_connection)
    context = get_current_context()
    sql_query = read_from_file(filename, dirname)

    ds_date = datetime.datetime.strptime(context["ds"], "%Y-%m-%d").date()
    if ds_date + datetime.timedelta(days=1) < datetime.datetime.now().date() and shift > 0:
        logging.info("Обнаружен архивный запуск, прерываю цикличный запуск")
        ch_client.disconnect()
        return True
    
    log_date = ds_date - datetime.timedelta(days=shift)
    execution_date = log_date.strftime("%Y-%m-%d")

    if insert_table_name != "default":
        logging.info("Проверка наличие активных ddl команд над таблицей")
        cluster = Variable.get('foodtech_cluster')
        time_start_mutation = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        CheckMutationSensor(
            clickhouse_connection_id=clickhouse_connection,
            check_schema=database,
            check_table=insert_table_name,
            cluster=cluster,
            timeout=12000,
            task_id=f"check_{database}.{insert_table_name}_{time_start_mutation}",
            dag=context["dag"]
        ).execute(context)

        logging.info("Проверка наличия данных за заливаемый период")
        amnt_in_table_frst = ch_client.execute(f"""
            select count({date_column})
            from {database}.{insert_table_name}
            where {date_column} = '{execution_date}'
        """)

        if amnt_in_table_frst[0][0] > 0:
            logging.info("Обнаружены данные в таблице")
            table_shard = insert_table_name + "_shard"
            drop_partitions(ch_client, database=database, table=table_shard, partitions=[execution_date])
            logging.info("Команда на удаление партиции отправлена успешно")
            raise Exception("В таблице не удалены данные за период")

    try:
        logging.info(f"Выполняю оптимизированный запрос за {execution_date}")
        
        # Добавляем дополнительные настройки для оптимизации
        optimized_settings = """
        SET max_threads = 32;
        SET max_memory_usage = 40000000000;
        SET max_bytes_before_external_group_by = 40000000000;
        SET max_bytes_before_external_sort = 20000000000;
        SET join_algorithm = 'hash';
        SET optimize_aggregation_in_order = 1;
        SET optimize_distinct_in_order = 1;
        SET group_by_overflow_mode = 'any';
        SET partial_merge_join = 1;
        """
        
        # Выполняем настройки
        ch_client.execute(optimized_settings)
        
        # Выполняем основной запрос
        formatted_query = sql_query.format(execution_date=execution_date)
        logging.info("Начинаю выполнение запроса...")
        ch_client.execute(formatted_query)
        ch_client.disconnect()
        logging.info("Вставка данных успешно выполнена")

    except Exception as e:
        logging.error(f"Произошла ошибка при выполнении запроса: {e}")
        if insert_table_name != "default":
            try:
                logging.info("Проверяю наличие данных за указанный период в таблице")
                amnt_in_table_scnd = ch_client.execute(f"""
                    select count({date_column})
                    from {database}.{insert_table_name}
                    where {date_column} = '{execution_date}'
                """)

                if amnt_in_table_scnd[0][0] > 0:
                    logging.info("Обнаружена ошибка вставки данных")
                    table_shard = insert_table_name + "_shard"
                    drop_partitions(ch_client, database=database, table=table_shard, partitions=[execution_date])
                    logging.info("Команда на удаление партиции отправлена успешно")

            except Exception as e2:
                logging.error("Произошла ошибка при проверке и чистке данных")
                raise AirflowFailException(f"{e2}")
        raise Exception(f"{e}")

@task(max_active_tis_per_dag=3)  # Увеличено для лучшего параллелизма
def clean_delivery_magnit_d1_agg_tables_optimized(shift: int):
    """
    Оптимизированная версия функции очистки таблиц
    """
    import datetime
    from airflow.operators.python import get_current_context
    from foodtech.product.foodtech_pa.magnit_all_app.tools.clickhouse_functions import drop_partitions
    from utils.clickhouse.func import clickhouse_conn

    ch_client = clickhouse_conn(clickhouse_conn_id=clickhouse_connection)
    context = get_current_context()

    ds_date = datetime.datetime.strptime(context["ds"], "%Y-%m-%d").date()
    if ds_date + datetime.timedelta(days=1) < datetime.datetime.now().date() and shift > 0:
        logging.info("Обнаружен архивный запуск, прерываю цикличный запуск")
        ch_client.disconnect()
        return True
    
    log_date = ds_date - datetime.timedelta(days=shift)
    execution_date = log_date.strftime("%Y-%m-%d")
    
    logging.info(f"Удаляем партиции за выполняемый день: {execution_date} если такие имеются, чтобы избежать дублей")
    
    for table in delivery_magnit_d1_agg_tables:
        table_shard = table + "_shard"
        database = "ft_pa_prod"
        logging.info(f"Удаление партиции в {table_shard} за {execution_date}")
        drop_partitions(ch_client, database=database, table=table_shard, partitions=[execution_date])
    
    logging.info("Команды на удаление партиций отправлены успешно")
    ch_client.disconnect()

@task
def check_delivery_magnit_d1_agg_tables_mutations_optimized():
    """
    Оптимизированная версия функции проверки мутаций
    """
    import datetime
    from airflow.models import Variable
    from airflow.operators.python import get_current_context

    context = get_current_context()
    cluster = Variable.get('foodtech_cluster')
    execution_date = datetime.datetime.strptime(context["ds"], "%Y-%m-%d").date().strftime("%Y-%m-%d")

    for table in delivery_magnit_d1_agg_tables:
        table_shard = table + "_shard"
        database = "ft_pa_prod"
        logging.info(f"Проверка мутаций в {table_shard} за {execution_date}")
        check_mutations(schema=database, table=table, cluster=cluster, context=context)
    
    logging.info(f"Проверка мутаций за {execution_date} окончена")

@task
def preload_common_data(shift: int):
    """
    Новая функция для предварительной загрузки общих данных
    Это может помочь ускорить основной запрос
    """
    import datetime
    from airflow.operators.python import get_current_context
    from utils.clickhouse.func import clickhouse_conn

    ch_client = clickhouse_conn(clickhouse_conn_id=clickhouse_connection)
    context = get_current_context()

    ds_date = datetime.datetime.strptime(context["ds"], "%Y-%m-%d").date()
    log_date = ds_date - datetime.timedelta(days=shift)
    execution_date = log_date.strftime("%Y-%m-%d")

    logging.info(f"Предварительная загрузка общих данных за {execution_date}")
    
    # Здесь можно добавить предварительную загрузку часто используемых данных
    # Например, создание временных таблиц с отфильтрованными данными
    
    ch_client.disconnect()
    logging.info("Предварительная загрузка завершена")

# Экспортируем функции для использования в DAG
__all__ = [
    'execute_sql_query_optimized',
    'clean_delivery_magnit_d1_agg_tables_optimized', 
    'check_delivery_magnit_d1_agg_tables_mutations_optimized',
    'preload_common_data'
]