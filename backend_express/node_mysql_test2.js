const mysql = require('mysql2/promise');
(async ()=>{
  try {
    const pool = mysql.createPool({
      host: '127.0.0.1',
      port: 3306,
      user: 'wanderlite',
      password: 'node_test_2025',
      database: 'wanderlite',
      connectionLimit: 1
    });
    const conn = await pool.getConnection();
    console.log('NODE_FILE_TCP_OK_SIMPLE');
    conn.release();
    await pool.end();
  } catch (e) {
    console.error('NODE_FILE_TCP_ERROR_SIMPLE', e && e.message ? e.message : e);
    if (e && e.code) console.error('CODE', e.code);
    process.exit(2);
  }
})();
