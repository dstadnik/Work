insert into ft_pa_prod.delivery_magnit_d1_agg
with base_info as (
    select created_dt                as event_date,
           magnit_id,
           lower(os_name)            as os_name,
           whs_city                  as city,
           multiIf(
                   order_type = 'Доставка', 'Доставка',
                   order_type = 'Самовывоз', 'Самовывоз',
                   whs_frmt = 'МА', 'Самовывоз',
                   whs_frmt IS NULL, 'Доставка',
                   ''
           )                     as order_type,
           --order_source_version,
           multiIf(
                   store_format in ('Sellers/BH'), 'Зоотовары',
                   order_source in ('Аптеки Собственные'), 'Аптека',
                   whs_frmt = 'БФ', 'Гипермаркет',
                   whs_frmt = 'МА', 'Аптека',
                   whs_frmt = 'МК', 'Косметик',
                   whs_frmt = 'МД', 'Экспресс',
                   'Экспресс'
           )                     as format,
           app_version,
           created_date,
           coalesce(
                   qr_code_s,
                   final_price,
                   initial_price
           )                     as order_price,
           toString(loyalty_card_id) as loyalty_card_id,
           order_id                  as order_num,
           list_sku

    from ft_ops_prod.dm_operations
    where 1 = 1
      and created_dt = '{execution_date}'
      and is_cancelled = 0
      and order_source IN ('Own wl2', 'Аптеки Собственные')
      and magnit_id not in (null, '', 'unknown')
),
     money_data_agg as (
         select event_date,
                magnit_id,
                os_name,
                city,
                order_type,
                --order_source_version,
                format,

                argMax(app_version, created_date) as app_version_name,
                sum(order_price)                  as money_paid,
                sum(margin_paid)                  as margin_paid,
                sum(dct_promo_amt)                as dct_promo_amt,
                sum(dct_amt)                      as dct_amt,
                sum(net_revenue)                  as net_revenue,
                sum(cm2_amt)                      as cm2_amt,
                groupUniqArray(loyalty_card_id)   as loyalty_card_id_arr,
                groupUniqArray(order_num)         as order_arr,
                groupArray(coupon_name)                as coupon_arr,
                groupUniqArrayArray(list_sku)     as product_arr

         from base_info
                  left join
              (select create_date as event_date,
                      order_id as order_num,
                      cm_net_amt as margin_paid,
                      dct_promo_amt,
                      dct_amt,
                      net_revenue,
                      cm2_amt,
                      coupon_name
               from dm.ft_order_unit_economics_v where event_date = '{execution_date}') as margin

              USING (event_date, order_num)

         group by event_date,
                  magnit_id,
                  os_name,
                  city,
                  order_type,
                  --order_source_version,
                  format
     ),

     app_launch_flg_tbl as (
         select toString(magnit_id) as magnit_id
         from dm_nrt.loyalty_events__nrt
         where 1 = 1
           and event_date = '{execution_date}'
           and event_name in (
             'app_launch'
             )
           and magnit_id not in (null, '', 'unknown')
     ),


     delivery_tab_stat as (
         select event_date,
                os_name,
                magnit_id,
                groupUniqArray(
                        appmetrica_device_id
                )     as appmetrica_device_id_arr,
                groupUniqArray(
                        loyalty_card_id
                )     as loyalty_card_id_arr,
                toString(multiIf(
                        lower(service_name) = 'cosmetic', 'Косметик',
                        lower(service_name) = 'dostavka', 'Гипермаркет',
                        lower(service_name) = 'express', 'Экспресс',
                        lower(service_name) = 'apteka', 'Аптека',
                        'Не удалось аттрибуцировать'
                ) )    as service_name,
                multiIf(
                        lower(delivery_type) = 'delivery', 'Доставка',
                        lower(delivery_type) = 'pickup', 'Самовывоз',
                        'Не удалось аттрибуцировать'
                )     as delivery_type,
                anyIf(
                        city,
                        city not in ('', 'unknown')
                )     as city,
                anyIf(
                        appsflyer_id,
                        appsflyer_id not in ('', 'unknown')
                )     as appsflyer_id,
                anyLastIf(
                        app_version_name,
                        app_version_name not in ('', 'unknown')
                )     as app_version,
                arrayDistinct(
                        array_concat_agg(ab)
                )     as ab_arr,

                if(
                        magnit_id in app_launch_flg_tbl,
                        1,
                        NULL
                )     as app_launch_flg,

                countIf(
                        event_name in (
                                       'delivery_catalogScreen_view',
                                       'delivery_catalogScreen_categoryLvl2Snippet_snippetCard_visible',
                                       'delivery_catalogScreen_categoryLvl2Snippet_snippetCard_view'
                            )
                ) > 0 as catalog_main_flg,
                countIf(
                        event_name in (
                                       'delivery_itemScreen_view',
                                       'delivery_itemScreen_productListing_view',
                                       'delivery_itemScreen_item_visible',
                                       'delivery_itemScreen_item_view',
                                       'delivery_itemScreen_productListing_item_view'
                            )
                ) > 0 as catalog_listing_flg,


                countIf(
                        event_name in (
                                       'delivery_searchScreen_view',
                                       'delivery_searchScreen_searchInput_visible',
                                       'delivery_searchScreen_searchInput_view'
                            )
                ) > 0 as search_main_flg,
                countIf(
                        event_name in (
                                       'delivery_searchScreen_searchResult_item_visible',
                                       'delivery_searchScreen_productListing_item_view',
                                       'delivery_searchScreen_searchResult_item_view'
                            )
                ) > 0 as search_result_flg,

                countIf(
                        event_name in (
                            'delivery_productScreen_view'
                            )
                ) > 0 as product_screen_flg,
                countIf(
                        event_name in (
                            'delivery_productScreen_toCart_click'
                            )
                ) > 0 as product_screen_to_cart_flg,
                countIf(
                        event_name in (
                                       'delivery_itemScreen_toCart_click',
                                       'delivery_itemScreen_productListing_toCart_click'
                            )
                ) > 0 as listing_to_cart_flg,
                countIf(
                        event_name in (
                                       'delivery_itemScreen_item_click',
                                       'delivery_itemScreen_productListing_item_click'
                            )
                ) > 0 as listing_to_item_flg,
                countIf(
                        event_name in (
                                       'delivery_searchScreen_toCart_click',
                                       'delivery_searchScreen_productListing_toCart_click'
                            )
                ) > 0 as search_screen_to_cart_flg,
                countIf(
                        event_name in (
                            'delivery_purchase_verified'
                            )
                ) > 0 as purchase_flg,

                groupUniqArrayIf(
                        order_id,
                        event_name = 'delivery_purchase_verified'
                )     as order_id_arr,

                countIf(
                        event_name in (
                            'cart_cartScreen_view'
                            )
                ) > 0 as cart_visit_flg,

                countIf(
                        event_name in (
                            'cart_cartScreen_checkoutButton_click'
                            )
                ) > 0 as cart_2_checkout_flg,

                countIf(
                        event_name in (
                            'checkout_checkoutScreen_view'
                            )
                ) > 0 as checkout_visit_flg,

                countIf(
                        event_name in (
                            'checkout_checkoutScreen_checkoutButton_click'
                            )
                ) > 0 as pay_button_pushed_flg

         from (WITH lowerUTF8(toString(service_name)) AS service_name_lc 
                  select event_date,
                         os_name,
                         toString(magnit_id)  as magnit_id,
                         appmetrica_device_id,
                         card_number as loyalty_card_id,
                         service_name,
                         delivery_type,
                         city,
                         appsflyer_id,
                         app_version_name,
                         ab,
                         order_id,
                         event_name


                  from dm_nrt.loyalty_events__nrt

                  where 1 = 1
                    and event_date = '{execution_date}'
                    and event_name in (
                                       'app_launch',
                                       'delivery_catalogScreen_view',
                                       'delivery_catalogScreen_categoryLvl2Snippet_snippetCard_visible',
                                       'delivery_catalogScreen_categoryLvl2Snippet_snippetCard_view',
                                       'delivery_itemScreen_view',
                                       'delivery_itemScreen_productListing_view',
                                       'delivery_itemScreen_item_visible',
                                       'delivery_itemScreen_item_view',
                                       'delivery_itemScreen_productListing_item_view',
                                       'delivery_itemScreen_item_click',
                                       'delivery_itemScreen_productListing_item_click',
                                       'delivery_searchScreen_view',
                                       'delivery_searchScreen_searchInput_visible',
                                       'delivery_searchScreen_searchInput_view',
                                       'delivery_searchScreen_searchResult_item_visible',
                                       'delivery_searchScreen_productListing_item_view',
                                       'delivery_searchScreen_searchResult_item_view',
                                       'delivery_productScreen_view',
                                       'delivery_productScreen_toCart_click',
                                       'delivery_itemScreen_toCart_click',
                                       'delivery_itemScreen_productListing_toCart_click',
                                       'delivery_searchScreen_toCart_click',
                                       'delivery_searchScreen_productListing_toCart_click',
                                       'delivery_purchase_verified',
                                       'cart_cartScreen_view',
                                       'cart_cartScreen_checkoutButton_click',
                                       'checkout_checkoutScreen_view',
                                       'checkout_checkoutScreen_checkoutButton_click'
                      )
                    and toString(magnit_id) not in (null, '', 'unknown')
                    and service_name_lc != 'market' 
                     

              ) dd

         group by event_date,
                  os_name,
                  service_name,
                  delivery_type,
                  magnit_id
         having toInt8OrDefault(service_name, -8) = -8 -- отсекаем цифры сервисов оффлайн каталога 
     ),


     final_data as (
         select COALESCE(
                        money_data_agg.event_date,
                        delivery_tab_stat.event_date
                )        as event_date,
                COALESCE(
                        money_data_agg.magnit_id,
                        delivery_tab_stat.magnit_id
                )        as magnit_id,
                COALESCE(
                        money_data_agg.os_name,
                        delivery_tab_stat.os_name
                )        as os_name,
                COALESCE(
                        money_data_agg.city,
                        delivery_tab_stat.city
                )        as city,
                COALESCE(
                        money_data_agg.order_type,
                        delivery_tab_stat.delivery_type
                )        as delivery_type,
                --order_source_version,
                COALESCE(
                        toString(money_data_agg.format),
                        toString(delivery_tab_stat.service_name)
                )        as service_name,
                COALESCE(
                        money_data_agg.app_version_name,
                        delivery_tab_stat.app_version
                )        as app_version_name,
                appsflyer_id,
                appmetrica_device_id_arr,
                ab_arr,
                arrayDistinct(
                        arrayConcat(
                                money_data_agg.loyalty_card_id_arr,
                                delivery_tab_stat.loyalty_card_id_arr
                        )
                )        as loyalty_card_id_arr,
                money_paid,
                margin_paid,
                dct_amt,
                dct_promo_amt,
                net_revenue,
                cm2_amt,
                order_arr,
                coupon_arr,
                product_arr,
                app_launch_flg,
                catalog_main_flg,
                catalog_listing_flg,
                search_main_flg,
                search_result_flg,
                product_screen_flg,
                product_screen_to_cart_flg,
                listing_to_cart_flg,
                listing_to_item_flg,
                search_screen_to_cart_flg,
                cart_visit_flg,
                cart_2_checkout_flg,
                checkout_visit_flg,
                pay_button_pushed_flg,
                purchase_flg,
                order_id_arr as order_id_app_arr

         from delivery_tab_stat
                  full outer join money_data_agg
                                  ON
                                      money_data_agg.event_date = delivery_tab_stat.event_date
                                          and money_data_agg.os_name = delivery_tab_stat.os_name
                                          and money_data_agg.magnit_id = delivery_tab_stat.magnit_id
                                          and toString(money_data_agg.format) = toString(delivery_tab_stat.service_name)
                                          and money_data_agg.order_type = delivery_tab_stat.delivery_type
     ),


     reg_data_info as (
         select magnit_id,
                service_name,
                delivery_type,
                --order_source_version,
                first_order_dt     as                             first_order_dt_temp,
                first_order_id_arr as                             first_order_id_arr_temp
         from ft_pa_prod.delivery_magnit_reg_data
         where 1 = 1
           and toString(magnit_id) in (select magnit_id from final_data)
     ),
     first_order_date as (


         select magnit_id,
                first_date
         from ft_growth_prod.di_newbies_costs dnc
         where 1 = 1
           and magnit_id in (select magnit_id from final_data)



     )


select '{execution_date}' as dt,
       final_data.magnit_id,
       appmetrica_device_id_arr,
       final_data.service_name,
       final_data.delivery_type,
       --COALESCE(
       --    previous_data_activity.order_source_version,
       --    final_data.order_source_version
       --) as order_source_version,
       os_name,
       city,
       app_version_name,
       appsflyer_id,
       ab_arr,
       loyalty_card_id_arr,
       money_paid,
       margin_paid,
       cm2_amt,
       dct_amt,
       dct_promo_amt,
       net_revenue,
       order_arr,
       coupon_arr,
       product_arr,
       app_launch_flg,
       catalog_main_flg,
       catalog_listing_flg,
       search_main_flg,
       search_result_flg,
       product_screen_flg,
       product_screen_to_cart_flg,
       listing_to_cart_flg,
       listing_to_item_flg,
       search_screen_to_cart_flg,
       cart_visit_flg,
       cart_2_checkout_flg,
       checkout_visit_flg,
       pay_button_pushed_flg,
       purchase_flg,
       order_id_app_arr,
-- убрать order_source_version


       ------------------------------
       If(
               length(order_arr) > 0
                   and empty(reg_data_info.first_order_id_arr_temp),
               final_data.order_arr,
               reg_data_info.first_order_id_arr_temp
       )        as first_order_id_arr, -- массив с первыми заказами (все заказы в первый день заказа)
       If(
               length(order_arr) > 0
                   and empty(reg_data_info.first_order_id_arr_temp),
               final_data.event_date,
               reg_data_info.first_order_dt_temp
       )        as first_order_dt ,
       first_date as min_date_overall-- дата первого заказа в омни приложения


from final_data
         left join reg_data_info
                   ON
                       toString(reg_data_info.service_name) = toString(final_data.service_name)
                           and reg_data_info.magnit_id = final_data.magnit_id
                           and reg_data_info.delivery_type = final_data.delivery_type
    --and reg_data_info.order_source_version = final_data.order_source_version
         left join
     first_order_date
     on first_order_date.magnit_id = final_data.magnit_id
where final_data.magnit_id not in (select toString(magnit_id) as magnit_id
FROM ft_pa_prod.fraud_users) --Фродовые юзеры (временная история)
    SETTINGS connect_timeout = 20000
   , send_timeout = 20000
   , receive_timeout = 20000
   ,max_threads = 20
   ,max_bytes_before_external_group_by=20000000000
