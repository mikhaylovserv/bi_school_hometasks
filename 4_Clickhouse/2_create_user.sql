- Создаем администратора
create user admin_user identified with sha256_password by 'admin1234';

--Выдаем права
grant current grants on *.* to admin_user with grant option;
