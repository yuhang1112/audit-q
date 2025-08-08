import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
REMOTE_ADDR = "http://i-1.gpushare.com:28356/static/"
DB_CFG = {
    "host":     "8.138.3.143",
    "port":     3306,
    "user":     "root",
    "password": "123456",
    "database": "hxbank",
    "charset":  "utf8mb4",
}