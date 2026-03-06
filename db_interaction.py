import sqlite3
import sys

def connect_db():
    """Connect to the SQLite database."""
    conn = sqlite3.connect('lockinfo.db')  # Change the database name if necessary
    return conn

def execute_query(conn, query):
    """Execute a single query and return the results."""
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    return results

def main():
    conn = connect_db()
    print("Connected to the database. Type your SQL queries below:")
    
    while True:
        try:
            query = input("SQL> ")
            if query.lower() in ['exit', 'quit']:
                print("Exiting...")
                break
            
            results = execute_query(conn, query)
            for row in results:
                print(row)
        
        except Exception as e:
            print(f"An error occurred: {e}")

    conn.close()

if __name__ == "__main__":
    main()