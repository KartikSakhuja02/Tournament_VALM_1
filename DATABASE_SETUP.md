# PostgreSQL Database Setup Guide

## Step 1: Install PostgreSQL

### Windows (using Command Prompt/PowerShell):
```bash
# Download and install PostgreSQL from:
# https://www.postgresql.org/download/windows/

# Or using Chocolatey:
choco install postgresql

# Or using winget:
winget install PostgreSQL.PostgreSQL
```

### Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### macOS:
```bash
brew install postgresql
brew services start postgresql
```

---

## Step 2: Access PostgreSQL CLI

### Windows:
```bash
# Find psql in your PostgreSQL installation directory
# Usually: C:\Program Files\PostgreSQL\<version>\bin
psql -U postgres
```

### Linux/macOS:
```bash
sudo -u postgres psql
```

---

## Step 3: Create Database and User

Run these commands in the PostgreSQL CLI (psql):

```sql
-- Create database
CREATE DATABASE valorant_tournament;

-- Create user with password
CREATE USER tournament_bot WITH PASSWORD 'your_secure_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE valorant_tournament TO tournament_bot;

-- Connect to the database
\c valorant_tournament

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO tournament_bot;

-- Exit psql
\q
```

---

## Step 4: Create Tables

Connect to your database:
```bash
psql -U tournament_bot -d valorant_tournament
```

Then run the SQL from `database/schema.sql`:
```bash
# Or run directly from file:
psql -U tournament_bot -d valorant_tournament -f database/schema.sql
```

---

## Step 5: Configure Environment Variables

Add to your `.env` file:
```env
DATABASE_URL=postgresql://tournament_bot:your_secure_password_here@localhost:5432/valorant_tournament
```

**Format:**
```
postgresql://username:password@host:port/database_name
```

---

## Step 6: Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 7: Test Connection

Run the bot and check console for:
```
✓ Database connected successfully
```

---

## Common Commands

### Check if PostgreSQL is running:
```bash
# Windows
pg_ctl status

# Linux
sudo systemctl status postgresql
```

### Connect to database:
```bash
psql -U tournament_bot -d valorant_tournament
```

### List databases:
```sql
\l
```

### List tables:
```sql
\dt
```

### View table structure:
```sql
\d players
```

### Query data:
```sql
SELECT * FROM players;
```

### Exit psql:
```sql
\q
```

---

## Troubleshooting

### Connection refused:
- Make sure PostgreSQL is running
- Check if port 5432 is open
- Verify credentials in DATABASE_URL

### Permission denied:
```sql
-- Run as postgres user:
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tournament_bot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tournament_bot;
```

### Reset password:
```sql
ALTER USER tournament_bot WITH PASSWORD 'new_password';
```
