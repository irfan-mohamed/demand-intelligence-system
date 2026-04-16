'''
Pipeline going through different stages.

stages 
- raw data -> staging (cleaned raw) -> core data -> feature data 
'''

import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname('__file__')))

from src.utils.db import run_sql_file

SQL_STAGES = [
    ("staging", "sql/01_staging/01_create_stage.sql"),
    ("core", "sql/02_core/02_create_core.sql"),
    ("features", "sql/03_features/03_create_features.sql")
]

def run_sql_pipeline():
    for step_name, file_path in SQL_STAGES :
        print(f"starting {step_name} ...")
        try :
            run_sql_file(file_path)
            print(f"step done {step_name}")
        except Exception as e :
            print(e)
            sys.exit(1)

if __name__ == '__main__':
    run_sql_pipeline()