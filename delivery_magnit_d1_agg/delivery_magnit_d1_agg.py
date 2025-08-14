from datetime import datetime
from datetime import timedelta

from airflow.models import DAG
from airflow.operators.dummy import DummyOperator

from foodtech.product.foodtech_pa.magnit_all_app.delivery_magnit_d1_agg import main as rep

#v2 2025-06-02 в d1 добавлено WITH lowerUTF8(toString(service_name)) AS service_name_lc из за обновы клика

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
    "delivery_magnit_d1_agg_new",
    description="...",
    default_args=default_args,
    schedule= "@daily",
    start_date=datetime(2024, 11,30),
    tags=[
        "catalog",
        "search",
        "cart",
        "checkout",
        "ecom_pa",
        "sidorov_a_p"
    ],
    max_active_runs=4,
    catchup=True
)

task_list = []

task_list.append(
    DummyOperator(task_id="start", dag=dag)
)

task_list.append(
    rep.clean_delivery_magnit_d1_agg_tables.expand(
        shift=list(range(6))[::-1]
    )
)

task_list.append(
    rep.check_delivery_magnit_d1_agg_tables_mutations()
)

task_list.append(
    rep.execute_sql_query.override(
        task_id="delivery_magnit_reg_data",
        dag=dag
    ).partial(
        dirname="../foodtech/product/foodtech_pa/magnit_all_app/delivery_magnit_d1_agg/sql",
        filename="delivery_magnit_reg_data.sql",
        insert_table_name="delivery_magnit_reg_data",
        date_column="first_order_dt"
    ).expand(
        shift=list(range(6))[::-1]
    )
)

task_list.append(
    rep.execute_sql_query.override(
        task_id="foodtech_magnit_d1_agg",
        dag=dag
    ).partial(
        dirname="../foodtech/product/foodtech_pa/magnit_all_app/delivery_magnit_d1_agg/sql",
        filename="delivery_magnit_d1_agg.sql",
        insert_table_name="delivery_magnit_d1_agg"
    ).expand(
        shift=list(range(6))[::-1]
    )
)


task_list.append(
    rep.execute_sql_query.override(
        task_id="foodtech_magnit_d1_agg_darkstore",
        dag=dag
    ).partial(
        dirname="../foodtech/product/foodtech_pa/magnit_all_app/delivery_magnit_d1_agg/sql",
        filename="delivery_magnit_d1_agg_darkstore.sql",
        insert_table_name="delivery_magnit_d1_agg_darkstore"
    ).expand(
        shift=list(range(6))[::-1]
    )
)


task_list.append(
    DummyOperator(task_id="finish", dag=dag)
)


for position, task_operator in enumerate(task_list):
    if position>0:
        task_list[position-1] >> task_operator
