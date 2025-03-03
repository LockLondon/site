import sqlite3

DATABASE = 'database.db'

conn = sqlite3.connect(DATABASE)
c = conn.cursor()
categories = [('Ігри',), ('Новини',), ('Життя',)]
c.executemany('INSERT INTO categories (name) VALUES (?)', categories)
conn.commit()
conn.close()
