--создание ролей
    --чтение
create role readonly_role;
grant select on *.* to readonly_role;
create user reader identified with sha256_password by 'reader1234' default role readonly_role;
    --роль с возможность создавать и заполнять данные в БД стейджинга(stg)
create role readwrite_stg_role;
grant create, insert on stg.* to readwrite_stg_role;
create user readwriter_stg identified with sha256_password by 'readwriter_stg1234' default role readwrite_stg_role;
