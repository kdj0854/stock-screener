"""检查 MySQL 历史行情数据库结构"""
import os
import pymysql

conn = pymysql.connect(
    host=os.environ.get('MYSQL_HOST', '127.0.0.1'),
    port=int(os.environ.get('MYSQL_PORT', '3306')),
    user=os.environ.get('MYSQL_USER', 'root'),
    password=os.environ.get('MYSQL_PASSWORD', ''),
    database='vnpy',  # 历史行情数据库名（不变）
    charset='utf8mb4'
)
cursor = conn.cursor()

print("=" * 60)
print("1. dbbardata 表结构")
print("=" * 60)
cursor.execute("DESCRIBE dbbardata")
for row in cursor.fetchall():
    print(f"  {row[0]:<20} {row[1]:<20} NULL={row[2]}  Key={row[3]}")

print("\n" + "=" * 60)
print("2. 数据库表信息（通过 information_schema 快速估算行数）")
print("=" * 60)
cursor.execute("""
    SELECT table_rows, data_length, index_length
    FROM information_schema.tables
    WHERE table_schema='vnpy' AND table_name='dbbardata'
""")
row = cursor.fetchone()
if row:
    print(f"  估算行数: {row[0]:,}")
    print(f"  数据大小: {row[1]/1024/1024:.1f} MB")
    print(f"  索引大小: {row[2]/1024/1024:.1f} MB")

print("\n" + "=" * 60)
print("3. 索引信息")
print("=" * 60)
cursor.execute("SHOW INDEX FROM dbbardata")
for row in cursor.fetchall():
    print(f"  Key={row[2]:<25} Col={row[4]:<15} Unique={row[1]==0}")

print("\n" + "=" * 60)
print("4. 样本数据（前10条，只取主要字段）")
print("=" * 60)
cursor.execute("SELECT symbol, exchange, datetime, `interval`, open_price, high_price, low_price, close_price, volume FROM dbbardata LIMIT 10")
cols = [d[0] for d in cursor.description]
print("  " + " | ".join(f"{c:<14}" for c in cols))
print("  " + "-" * (16 * len(cols)))
for row in cursor.fetchall():
    print("  " + " | ".join(f"{str(v):<14}" for v in row))

print("\n" + "=" * 60)
print("5. 取 100 条样本看包含哪些 symbol/exchange/interval")
print("=" * 60)
cursor.execute("SELECT DISTINCT symbol, exchange, `interval` FROM dbbardata LIMIT 50")
rows = cursor.fetchall()
print(f"  {'symbol':<20} {'exchange':<15} interval")
print("  " + "-" * 45)
for row in rows:
    print(f"  {str(row[0]):<20} {str(row[1]):<15} {row[2]}")

conn.close()
print("\n✅ 检查完成")
