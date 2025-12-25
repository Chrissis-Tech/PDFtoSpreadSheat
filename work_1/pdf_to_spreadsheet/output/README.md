# Output Directory

Generated CSV, JSON, and Google Sheets backup files are stored here.

## Generated Files:

Output files follow this naming pattern:
- `result_YYYYMMDD_HHMMSS.csv` - CSV export
- `result_YYYYMMDD_HHMMSS.json` - JSON export
- `*_backup.csv` - Local backup of Google Sheets exports

## Cleanup:

To clean generated files:
```bash
rm output/*.csv output/*.json
```

Or on Windows:
```powershell
Remove-Item output/*.csv, output/*.json
```
