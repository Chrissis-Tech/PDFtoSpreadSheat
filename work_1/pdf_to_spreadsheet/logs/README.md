# Logs Directory

Execution logs for each system run are stored here.

## File Format:

`run_YYYYMMDD_HHMMSS.log`

## Typical Content:

```
2024-03-15 10:30:45 | INFO     | Starting PDF to Spreadsheet Automation
2024-03-15 10:30:45 | INFO     | Processing: invoice_001.pdf
2024-03-15 10:30:46 | INFO     | Extracted 15 rows
2024-03-15 10:30:47 | WARNING  | Validation: Field 'date' is not a valid date
2024-03-15 10:30:48 | INFO     | Exported to: output/result_20240315.csv
```

## Retention:

By default, logs are retained for 7 days and rotate at 10 MB.
Configurable in `config.yaml`.
