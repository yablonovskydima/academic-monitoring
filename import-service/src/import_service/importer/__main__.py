from import_service.importer.import_runner import run_import
from import_service.importer.sources.csv_source import CsvSource
from import_service.generator import config

if __name__ == "__main__":
    source = CsvSource(data_dir=config.DATA_DIR)
    run_import(source)