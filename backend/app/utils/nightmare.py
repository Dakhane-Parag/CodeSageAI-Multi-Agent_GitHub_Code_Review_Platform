import sqlite3
import time

def process_data(data1, flag, input_val):
    # QUALITY ISSUE: Bad naming (data1, flag, input_val), magic numbers, no error handling
    # TESTING ISSUE: What if input_val is None? What if data1 is empty? Unhandled edge cases.
    
    # SECURITY ISSUE: SQL Injection. Unsanitized user input directly concatenated into a SQL string.
    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = '" + input_val + "'"
    cursor.execute(query)
    
    # PERFORMANCE ISSUE: Massive O(N^2) loop.
    res = []
    if flag == True:
        for i in data1:
            for j in data1:
                # QUALITY ISSUE: Deeply nested logic, blocking sleep inside a loop
                if i == j:
                    time.sleep(0.1) # Simulate slow blocking I/O
                    res.append(i)
                    
    # SECURITY ISSUE: Hardcoded secret!
    api_key = "sk_live_12345abcde67890fghij"
    
    return res
