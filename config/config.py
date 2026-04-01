'''
    congig.py -- configuration files for postgres database
'''

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "flipkart_sales", 
    "user": "postgres",          
    "password": "Irfan@123", 
}

SCHEMAS = {
    "raw":     "raw_layer",       
    "staging": "staging_layer",
    "core":    "core_layer",
    "feature": "feature_layer",
}

RAW_TABLES = {
    "sales":    "sales",
    "products": "products",
}