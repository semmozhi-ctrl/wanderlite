require('dotenv').config({path:'./.env'});
(async()=>{
  const mysql = require('mysql2/promise');
  try{
    const c = await mysql.createConnection({host:'127.0.0.1', user:process.env.MYSQL_USER, password:process.env.MYSQL_PASS, database:process.env.MYSQL_DB});
    console.log('NODE_TCP_OK');
    await c.end();
  } catch(e){
    console.error('NODE_TCP_ERROR', e && e.message ? e.message : e);
    if (e && e.code) console.error('CODE', e.code);
    process.exit(2);
  }
})();
