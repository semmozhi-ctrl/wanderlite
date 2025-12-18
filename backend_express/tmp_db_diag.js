require(dotenv).config({path: ./.env});
(async ()=>{
  const mysql = require(mysql2/promise);
  try {
    const pool = mysql.createPool({
      host: process.env.MYSQL_HOST || 127.0.0.1,
      port: process.env.MYSQL_PORT ? Number(process.env.MYSQL_PORT) : 3306,
      user: process.env.MYSQL_USER || root,
      password: process.env.MYSQL_PASS || ,
      database: process.env.MYSQL_DB || wanderlite,
      connectTimeout: 10000,
      waitForConnections: true,
      connectionLimit: 1
    });
    const conn = await pool.getConnection();
    console.log(CONNECTED_OK);
    conn.release();
    await pool.end();
  } catch (e) {
    console.error(DIAGNOSTIC_ERROR:, e && e.message ? e.message : e);
    if (e && e.code) console.error(DIAGNOSTIC_CODE:, e.code);
    process.exit(2);
  }
})();
