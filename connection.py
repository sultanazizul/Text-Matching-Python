import pandas as pd
import mysql.connector

# Fungsi untuk melakukan koneksi ke database MySQL dan mengambil informasi tabel dan kolom
def sql_connection(database_name):
    # Konfigurasi koneksi database
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'database': database_name,
    }

    # Membuat koneksi dan cursor
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    # Query untuk mengambil informasi tabel
    query_tables = "SELECT table_name, table_comment FROM information_schema.tables WHERE table_schema = %s"
    cursor.execute(query_tables, (database_name,))
    tables_info = cursor.fetchall()

    # DataFrame untuk menyimpan hasil query
    result_df = pd.DataFrame()

    # Loop melalui setiap tabel dan kolom dalam database
    for table_info in tables_info:
        table_name = table_info[0]
        table_description = table_info[1]

        # Query untuk mengambil informasi kolom (columns) dari sebuah tabel
        query_columns = f"SHOW FULL COLUMNS FROM {table_name}"
        cursor.execute(query_columns)
        columns_info = cursor.fetchall()

        # Loop melalui setiap kolom dalam sebuah tabel
        for column_info in columns_info:
            column_name = column_info[0]
            # Indeks 8 adalah indeks kolom deskripsi
            column_description = column_info[8]

            # Query untuk mengambil data dari tabel dengan menambahkan informasi sumber database, tabel, dan deskripsi
            query_data = f"SELECT *, '{database_name}' as source_database, '{table_name}' as source_table, '{table_description}' as source_description FROM {table_name}"
            
            # Membaca data hasil query ke DataFrame sementara
            temp_df = pd.read_sql(query_data, con=connection)
            
            # Menggabungkan hasil query sementara ke dalam DataFrame utama
            result_df = pd.concat([result_df, temp_df], ignore_index=True)

    # Menutup koneksi ke database
    connection.close()
    
    # Mengembalikan DataFrame hasil query
    return result_df
