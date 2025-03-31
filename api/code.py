import sqlite3
import subprocess

# Install necessary libraries
subprocess.run(['pip', 'install', 'sqlite3'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Connect to the SQLite database
conn = sqlite3.connect('tickets.db')
cursor = conn.cursor()

# SQL query to calculate total sales for "Gold" ticket type
query = '''
SELECT SUM(units * price) FROM tickets WHERE type = 'Gold';
'''

# Execute the query and fetch the result
cursor.execute(query)
total_sales = cursor.fetchone()[0]

# Close the connection
conn.close()

# Print the total sales
print("Total sales of 'Gold' ticket type:", total_sales)