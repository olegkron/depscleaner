# depscleaner/logger.py

def log_error(error_message):
    print(f"Error: {error_message}")
    with open('error.log', 'a') as log_file:
        log_file.write(f"{error_message}\n")
