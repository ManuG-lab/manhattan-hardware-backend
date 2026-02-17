# Manhattan Hardware Inventory Backend

FastAPI backend for hardware inventory management system.

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
uvicorn main:app --reload
```

3. Access API at: http://127.0.0.1:8000

## Database

The application uses SQLite for data storage. Locally, data persists between restarts. However, on Render's free tier, the file system is ephemeral.

## Database

The application stores its SQLite database in a persistent location by default. Current DB file and schema snapshot are available in the repository at `db_info.txt`.

- DB file path: `/home/emmanuel-gitau/.bussines_data/inventory.db`
- To change the DB location, set the `DB_PATH` environment variable to an absolute path (file or directory).

You can inspect the live DB yourself with:

```bash
sqlite3 /home/emmanuel-gitau/.bussines_data/inventory.db 
.tables
.schema products
PRAGMA table_info(products);
```
### Backup/Restore Database

```bash
# Backup current database
python backup_db.py

# Restore from backup
python -c "from backup_db import restore_database; restore_database('backups/inventory_backup_20260122_120000.db')"
```

## Production Deployment

### Option 1: Render with Persistent Disk (Paid Tier)
1. Upgrade to Render paid tier with persistent disk
2. Set `RENDER_DISK_PATH` environment variable
3. Deploy using the render.yaml configuration

### Option 2: Use PostgreSQL (Recommended)
For production, consider switching to PostgreSQL:

1. Create a free PostgreSQL database on:
   - Neon (neon.tech)
   - Supabase (supabase.com)
   - Railway (railway.app)

2. Update `database.py` to use PostgreSQL instead of SQLite

3. Set database URL as environment variable

## API Endpoints

- `GET /products` - List all products
- `POST /products` - Add new product
- `PUT /products/{id}` - Update product
- `DELETE /products/{id}` - Delete product
- `GET /sales` - List all sales
- `POST /sales` - Add new sale
- `PUT /sales/{id}` - Update sale
- `DELETE /sales/{id}` - Delete sale
- `PUT /products/{id}/sell` - Alternative sale endpoint

## Environment Variables

- `RENDER`: Set to 'true' when running on Render
- `RENDER_DISK_PATH`: Path to persistent disk (if available)
- `DATABASE_URL`: PostgreSQL connection string (for production)