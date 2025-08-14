insert into ft_pa_prod.delivery_magnit_reg_data


select    
    magnit_id,
    --order_source_version,
    multiIf(
        store_format in ('Sellers/BH'),'Зоотовары',
        order_source in ('Аптеки Собственные'),'Аптека',
        whs_frmt='БФ','Гипермаркет',
        whs_frmt='МА','Аптека',
        whs_frmt='МК','Косметик',
        whs_frmt='МД','Экспресс',
        'Экспресс'
    ) as service_name,
    multiIf(
        order_type='Доставка','Доставка',
        order_type='Самовывоз','Самовывоз',
        whs_frmt='МА','Самовывоз',
        whs_frmt IS NULL,'Доставка',
        ''
    ) as delivery_type,
    min(created_dt) as first_order_dt,
    groupUniqArrayArgMin(order_id, created_dt) as first_order_id_arr

from 
    ft_ops_prod.dm_operations
where 
    1 = 1
    and created_dt <= '2023-09-30'
    and is_cancelled = 0
    and order_source IN ('Own wl2','Аптеки Собственные')
    and magnit_id not in (null, '','unknown')
group by
    magnit_id,
    service_name,
    delivery_type
