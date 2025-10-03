def safe_read(file):
    try:
        return file.read()
    except Exception:
        return None
