from airflow.decorators import task


delivery_magnit_d1_agg_tables =[
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
    CheckMutationSensor(clickhouse_connection_id=clickhouse_connection,
                        check_schema=schema,
                        check_table=table,
                        cluster=cluster,
                        timeout=12000,
                        task_id=f"check_{schema}.{table}_{time_start_mutation}",
                        dag=context["dag"]).execute(context)


@task(max_active_tis_per_dag=1)
def execute_sql_query(
        dirname: str,
        filename: str,
        shift: int,
        insert_table_name = "default",
        date_column = "event_date",
        database = "ft_pa_prod"
) -> None:
    """
    Выполняет sql запрос из текстового файла

    Args:
        dirname (str): путь к директории, где находится файл запроса
        filename (str): название sql файла содержащего запрос
        shift (int): окно пересборки данных (за сколько дней перед нужно собрать данные)
        insert_table_name (str, optional): Таблица в которую запрос вставляет данные,
            необходима для проверки в слуае ошибки, по умолчанию отключено
        date_column (str, optional): название столбца партиции (сделано для колонки со временем),
            по умолчанию event_date
        database (str, optional): название схемы, по умолчанию ft_pa_prod
    """


    import datetime
    import logging

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
        logging.info("Проверка наличие активных ддл команд над таблицой")
        cluster = Variable.get('foodtech_cluster')
        time_start_mutation = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        CheckMutationSensor(clickhouse_connection_id=clickhouse_connection,
                            check_schema=database,
                            check_table=insert_table_name,
                            cluster=cluster,
                            timeout=12000,
                            task_id=f"check_{database}.{insert_table_name}_{time_start_mutation}",
                            dag=context["dag"]).execute(context)

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
        logging.info(f"Выполняю запрос за {execution_date}")
        print(sql_query.format(execution_date=execution_date))
        ch_client.execute(sql_query.format(execution_date=execution_date))
        ch_client.disconnect()
        logging.info("Вставка данных успешно выполнена")

    except Exception as e:
        logging.info(f"Произошла ошибка при выполнении запроса {e}")
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
                logging.info("Произошла ошибка при проверке и чистке данных")
                raise AirflowFailException(f"{e2}")
        raise Exception(f"{e}")



@task
def clean_delivery_magnit_d1_agg_tables(shift: int):
    import datetime
    import logging

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
def check_delivery_magnit_d1_agg_tables_mutations():
    import datetime
    import logging

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
