#!/usr/bin/env node
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const { parse } = require('csv-parse/sync');
const mysql = require('mysql2/promise');

async function createTableFromHeader(conn, tableName, headers) {
  // simple heuristic: all columns TEXT except numeric-looking
  const cols = headers.map(h => `\`${h}\` TEXT`);
  const q = `CREATE TABLE IF NOT EXISTS \`${tableName}\` (${cols.join(',')}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`;
  await conn.query(q);
}

function toSqlValues(row, headers) {
  return headers.map(h => row[h] != null ? String(row[h]) : null);
}

async function migrateFile(pool, filePath, tableName) {
  const content = fs.readFileSync(filePath, 'utf8');
  const records = parse(content, { columns: true, skip_empty_lines: true });
  if (!records || records.length === 0) {
    console.log(`No rows in ${filePath}`);
    return;
  }
  const headers = Object.keys(records[0]);
  const conn = await pool.getConnection();
  try {
    await createTableFromHeader(conn, tableName, headers);
    // insert rows in batches
    const placeholders = '(' + headers.map(()=>'?').join(',') + ')';
    const insertQ = `INSERT INTO \`${tableName}\` (${headers.map(h=>`\`${h}\``).join(',')}) VALUES ${placeholders}`;
    for (const row of records) {
      const vals = toSqlValues(row, headers);
      await conn.query(insertQ, vals);
    }
    console.log(`Inserted ${records.length} rows into ${tableName}`);
  } finally {
    conn.release();
  }
}

async function main(){
  const { MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASS, MYSQL_DB } = process.env;
  if (!MYSQL_DB) { console.error('Please set MYSQL_DB in .env'); process.exit(1); }
  const pool = mysql.createPool({
    host: MYSQL_HOST || '127.0.0.1',
    port: MYSQL_PORT ? Number(MYSQL_PORT) : 3306,
    user: MYSQL_USER || 'root',
    password: MYSQL_PASS || '',
    database: MYSQL_DB,
    waitForConnections: true,
    connectionLimit: 10
  });

  const repoRoot = path.join(__dirname, '..');
  const backendDir = path.join(repoRoot, '..', 'backend');

  const files = [
    { src: path.join(backendDir, 'hotels_dataset.csv'), table: 'hotels_dataset' },
    { src: path.join(backendDir, 'restaurants_dataset.csv'), table: 'restaurants_dataset' }
  ];

  for (const f of files) {
    if (!fs.existsSync(f.src)) {
      console.warn(`CSV file not found: ${f.src}, skipping`);
      continue;
    }
    await migrateFile(pool, f.src, f.table);
  }

  await pool.end();
  console.log('CSV migration complete');
}

main().catch(e=>{ console.error('Migration failed', e && e.message); process.exit(1); });
