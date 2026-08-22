import pymysql


# Utilise le pilote MySQL pur Python sur les hébergements cPanel où les
# bibliothèques de compilation nécessaires à mysqlclient ne sont pas présentes.
pymysql.install_as_MySQLdb()
