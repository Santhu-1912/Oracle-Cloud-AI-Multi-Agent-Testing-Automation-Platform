import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

try:
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    if users:
        print("👤 Registered Users:")
        for user in users:
            print(user)
    else:
        print("No users found in the database.")

except sqlite3.Error as e:
    print("Error:", e)

finally:
    conn.close()
