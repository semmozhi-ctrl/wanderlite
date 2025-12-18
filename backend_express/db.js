const mysql = require('mysql2/promise');
const { MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASS, MYSQL_DB } = process.env;

let pool;

async function createPool(options) {
  return mysql.createPool(Object.assign({
    waitForConnections: true,
    connectionLimit: 10,
    port: MYSQL_PORT ? Number(MYSQL_PORT) : 3306,
    user: MYSQL_USER || 'root',
    password: MYSQL_PASS || '',
    database: MYSQL_DB || 'wanderlite'
  }, options));
}

(async () => {
  const host = MYSQL_HOST || '127.0.0.1';
  try {
    // Try creating pool with provided host
    pool = await createPool({ host });
    const conn = await pool.getConnection();
    conn.release();
    console.log(`DB pool created using host=${host}`);
  } catch (e) {
    console.warn(`Initial DB connect failed for host=${host}:`, e.message);
    // If host was 127.0.0.1 or localhost, try Unix socket fallback
    const socketPaths = ['/var/run/mysqld/mysqld.sock', '/tmp/mysql.sock'];
    let ok = false;
    for (const sock of socketPaths) {
      try {
        pool = await createPool({ socketPath: sock });
        const conn = await pool.getConnection();
        conn.release();
        console.log(`DB pool created using socketPath=${sock}`);
        ok = true;
        break;
      } catch (err) {
        console.warn(`Socket attempt ${sock} failed:`, err.message);
      }
    }

    if (!ok) {
      console.warn('DB initialization skipped or failed:', e.message);
      // Create a pool anyway (will error on queries); keeps module export non-null
      pool = await createPool({ host });
    }
  }

  // Initialize minimal schema for scaffold (safe idempotent CREATE TABLE IF NOT EXISTS)
  try {
    const conn = await pool.getConnection();
    await conn.query(`CREATE TABLE IF NOT EXISTS users (
      id INT AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(255),
      email VARCHAR(255) UNIQUE,
      password_hash VARCHAR(255),
      phone VARCHAR(50),
      is_kyc_completed INT DEFAULT 0,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`);

    // Ensure expected user columns exist (handles older DBs without 'name' or 'phone')
    try {
      await conn.query("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255)");
      await conn.query("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(50)");
    } catch (e) {
      /* ignore if ALTER not supported */
    }

    await conn.query(`CREATE TABLE IF NOT EXISTS bookings (
      id INT AUTO_INCREMENT PRIMARY KEY,
      user_id INT,
      type VARCHAR(50),
      reference VARCHAR(255),
      data JSON,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`);

    await conn.query(`CREATE TABLE IF NOT EXISTS flights (
      id INT AUTO_INCREMENT PRIMARY KEY,
      flight_number VARCHAR(50),
      airline_code VARCHAR(10),
      airline_name VARCHAR(255),
      origin_code VARCHAR(10),
      origin_city VARCHAR(255),
      dest_code VARCHAR(10),
      dest_city VARCHAR(255),
      departure_datetime DATETIME,
      arrival_datetime DATETIME,
      duration_mins INT,
      base_price_economy INT,
      base_price_business INT,
      available_economy INT,
      available_business INT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`);

    // seed a sample flight if none exist
    const [rows] = await conn.query('SELECT COUNT(*) as c FROM flights');
    if (rows && rows[0] && rows[0].c === 0) {
      await conn.query(`INSERT INTO flights (flight_number, airline_code, airline_name, origin_code, origin_city, dest_code, dest_city, departure_datetime, arrival_datetime, duration_mins, base_price_economy, base_price_business, available_economy, available_business) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)` , [
        '6E123','6E','IndiGo','DEL','Delhi','BOM','Mumbai', new Date(Date.now()+24*3600*1000).toISOString().slice(0,19).replace('T',' '), new Date(Date.now()+24*3600*1000+2.5*3600*1000).toISOString().slice(0,19).replace('T',' '), 150, 3500, 10500, 20, 5
      ]);
      console.log('Seeded sample flight into flights table');
    }

    await conn.query(`CREATE TABLE IF NOT EXISTS hotels (
      id INT AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(255),
      city VARCHAR(255),
      state VARCHAR(255),
      country VARCHAR(255),
      rating DECIMAL(2,1),
      price_per_night INT,
      rooms_available INT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`);

    const [hotelCount] = await conn.query('SELECT COUNT(*) as c FROM hotels');
    if (hotelCount && hotelCount[0] && hotelCount[0].c === 0) {
      await conn.query('INSERT INTO hotels (name, city, state, country, rating, price_per_night, rooms_available) VALUES (?, ?, ?, ?, ?, ?, ?)', ['Demo Hotel', 'Mumbai', 'Maharashtra', 'India', 4.3, 3500, 10]);
      console.log('Seeded sample hotel into hotels table');
    }

    await conn.query(`CREATE TABLE IF NOT EXISTS restaurants (
      id INT AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(255),
      city VARCHAR(255),
      cuisine VARCHAR(255),
      rating DECIMAL(2,1),
      average_cost INT,
      available_slots INT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`);

    const [restCount] = await conn.query('SELECT COUNT(*) as c FROM restaurants');
    if (restCount && restCount[0] && restCount[0].c === 0) {
      await conn.query('INSERT INTO restaurants (name, city, cuisine, rating, average_cost, available_slots) VALUES (?, ?, ?, ?, ?, ?)', ['Demo Eatery', 'Mumbai', 'Indian', 4.2, 500, 20]);
      console.log('Seeded sample restaurant into restaurants table');
    }

    // Payments table for handling payment records
    await conn.query(`CREATE TABLE IF NOT EXISTS payments (
      id INT AUTO_INCREMENT PRIMARY KEY,
      booking_id INT,
      user_id INT,
      amount DECIMAL(10,2),
      currency VARCHAR(10) DEFAULT 'INR',
      method VARCHAR(50),
      status VARCHAR(50) DEFAULT 'pending',
      external_ref VARCHAR(255),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`);

    // Receipts table to track uploaded receipt files
    await conn.query(`CREATE TABLE IF NOT EXISTS receipts (
      id INT AUTO_INCREMENT PRIMARY KEY,
      payment_id INT,
      file_path VARCHAR(1024),
      uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`);

    // KYC uploads table
    await conn.query(`CREATE TABLE IF NOT EXISTS kyc_uploads (
      id INT AUTO_INCREMENT PRIMARY KEY,
      user_id INT,
      file_path VARCHAR(1024),
      status VARCHAR(50) DEFAULT 'uploaded',
      uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`);

    // Admin actions / audit table to record admin reviews and actions
    await conn.query(`CREATE TABLE IF NOT EXISTS admin_actions (
      id INT AUTO_INCREMENT PRIMARY KEY,
      admin_id VARCHAR(255),
      action VARCHAR(100),
      target VARCHAR(100),
      target_id INT,
      note TEXT,
      ip VARCHAR(100),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`);

    // KYC audit logs for more structured history of KYC reviews
    await conn.query(`CREATE TABLE IF NOT EXISTS kyc_audit_logs (
      id INT AUTO_INCREMENT PRIMARY KEY,
      kyc_id INT,
      admin_id VARCHAR(255),
      action VARCHAR(50),
      note TEXT,
      ip VARCHAR(100),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`);

    // Ensure `is_kyc_completed` exists on users (some DBs may be legacy)
    try {
      const [colCheck] = await conn.query("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='users' AND COLUMN_NAME='is_kyc_completed'");
      if (!colCheck || colCheck.length === 0) {
        await conn.query('ALTER TABLE users ADD COLUMN is_kyc_completed INT DEFAULT 0');
        console.log('Added missing column users.is_kyc_completed');
      }
    } catch (e) {
      // non-fatal: some MySQL versions may not support INFORMATION_SCHEMA in this context
      try {
        await conn.query('ALTER TABLE users ADD COLUMN IF NOT EXISTS is_kyc_completed INT DEFAULT 0');
      } catch (e2) {
        // last-resort ignore; admin endpoints handle absent column
        console.warn('Could not ensure is_kyc_completed column:', e2 && e2.message);
      }
    }

    // KYC details table (records submitted KYC forms)
    await conn.query(`CREATE TABLE IF NOT EXISTS kyc_details (
      id INT AUTO_INCREMENT PRIMARY KEY,
      user_id INT,
      full_name VARCHAR(255),
      dob DATE NULL,
      gender VARCHAR(20),
      nationality VARCHAR(100),
      id_type VARCHAR(100),
      address_line VARCHAR(255),
      city VARCHAR(100),
      state VARCHAR(100),
      country VARCHAR(100),
      pincode VARCHAR(50),
      id_proof_front_path VARCHAR(1024),
      id_proof_back_path VARCHAR(1024),
      selfie_path VARCHAR(1024),
      verification_status VARCHAR(50) DEFAULT 'pending',
      submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      verified_at TIMESTAMP NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`);

    conn.release();
    console.log('DB initialized (users, bookings tables)');
  } catch (e) {
    console.warn('DB initialization skipped or failed:', e.message);
  }
})();

// Ensure legacy DBs have the is_kyc_completed column on startup (idempotent)
(async () => {
  try {
    const pool = pool || module.exports.getPool && module.exports.getPool();
    if (!pool) return;
    const conn = await pool.getConnection();
    try {
      const [cols] = await conn.query("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='users'");
      const colNames = (cols || []).map(r => r.COLUMN_NAME);
      if (!colNames.includes('is_kyc_completed')) {
        try {
          await conn.query('ALTER TABLE users ADD COLUMN is_kyc_completed INT DEFAULT 0');
          console.log('Added is_kyc_completed column to users');
        } catch (err) {
          console.warn('Could not add is_kyc_completed column on startup:', err && err.message);
        }
      }
    } finally {
      if (conn && conn.release) conn.release();
    }
  } catch (e) {
    // ignore
  }
})();

module.exports = { getPool: () => pool };
