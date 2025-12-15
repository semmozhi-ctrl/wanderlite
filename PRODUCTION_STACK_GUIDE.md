# Wanderlite Production Stack Guide

## 🎯 Stack Overview

**Complete Production-Ready Local Stack for Wanderlite Travel & Tourism Application**

### Technology Stack
- **OS:** Ubuntu 24.04 LTS
- **Backend:** Node.js v18.19.1 LTS with Express.js
- **Database:** MySQL 8.0.44 standalone
- **Web Server:** Nginx 1.24.0 (reverse proxy)
- **Package Manager:** npm 9.2.0

---

## 📋 Component Details

### 1. MySQL Database Configuration

**Database Name:** `wanderlite`
**Character Set:** utf8mb4_unicode_ci
**Port:** 3306
**Host:** 127.0.0.1 (TCP connection)

**User Credentials:**
- Username: `wanderuser@localhost`
- Password: `StrongPass@123`
- Authentication: `mysql_native_password`
- Privileges: ALL on wanderlite.*

**Connection String:**
```bash
mysql -u wanderuser -pStrongPass@123 -h 127.0.0.1 --protocol=tcp -D wanderlite
```

---

### 2. Node.js Backend Configuration

**Location:** `~/wanderlite-backend`
**Port:** 3000
**Environment:** Production

**Directory Structure:**
```
~/wanderlite-backend/
├── .env                 # Environment configuration
├── package.json         # Node.js dependencies
├── server.js           # Express application entry point
└── config/
    └── db.js           # MySQL connection pool
```

**Environment Variables (.env):**
```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=wanderuser
DB_PASSWORD=StrongPass@123
DB_NAME=wanderlite
PORT=3000
NODE_ENV=production
```

**API Endpoints:**
- `GET /api/health` - Database health check
- `GET /api/` - API information and endpoint list

**Connection Pool Settings:**
- Max Connections: 10
- Wait for connections: true
- Connection limit: 10
- Queue limit: 0
- Keep alive enabled

---

### 3. Nginx Reverse Proxy Configuration

**Configuration File:** `/etc/nginx/sites-available/wanderlite`
**Enabled Via:** `/etc/nginx/sites-enabled/wanderlite`
**Port:** 80
**Document Root:** `/var/www/wanderlite`

**Key Configuration:**
```nginx
# Frontend serving
location / {
    root /var/www/wanderlite;
    try_files $uri $uri/ /index.html;
}

# API reverse proxy
location /api/ {
    proxy_pass http://127.0.0.1:3000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_cache_bypass $http_upgrade;
}
```

**Security Headers:**
- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block

**Logs:**
- Access: `/var/log/nginx/wanderlite-access.log`
- Error: `/var/log/nginx/wanderlite-error.log`

---

## 🚀 Quick Start Commands

### Start All Services
```bash
# 1. Start MySQL (if not running)
sudo systemctl start mysql

# 2. Start Node.js backend
cd ~/wanderlite-backend
npm start

# 3. Start/Reload Nginx
sudo systemctl start nginx
# or
sudo systemctl reload nginx
```

### Stop All Services
```bash
# Stop backend (find PID first)
ps aux | grep "[n]ode.*server.js"
kill <PID>

# Stop Nginx
sudo systemctl stop nginx

# Stop MySQL (if needed)
sudo systemctl stop mysql
```

### Check Service Status
```bash
# MySQL status
sudo systemctl status mysql

# Nginx status
sudo systemctl status nginx

# Backend process
ps aux | grep "[n]ode.*server.js"

# Test endpoints
curl http://localhost
curl http://localhost/api/health
```

---

## 🔧 Troubleshooting Guide

### Common MySQL Issues

#### Issue 1: Authentication Plugin Error
**Error:** `Authentication plugin 'caching_sha2_password' cannot be loaded`

**Solution:**
```sql
-- Recreate user with mysql_native_password
DROP USER 'wanderuser'@'localhost';
CREATE USER 'wanderuser'@'localhost' IDENTIFIED WITH mysql_native_password BY 'StrongPass@123';
GRANT ALL PRIVILEGES ON wanderlite.* TO 'wanderuser'@'localhost';
FLUSH PRIVILEGES;
```

#### Issue 2: Socket vs TCP Connection Error
**Error:** `Can't connect to local MySQL server through socket`

**Solution:**
Always use `-h 127.0.0.1 --protocol=tcp` to force TCP connection:
```bash
mysql -u wanderuser -p -h 127.0.0.1 --protocol=tcp -D wanderlite
```

In Node.js, ensure `.env` uses:
```env
DB_HOST=127.0.0.1  # NOT 'localhost'
```

#### Issue 3: Access Denied for User
**Error:** `Access denied for user 'wanderuser'@'localhost'`

**Verify privileges:**
```sql
SHOW GRANTS FOR 'wanderuser'@'localhost';
```

**If missing, re-grant:**
```sql
GRANT ALL PRIVILEGES ON wanderlite.* TO 'wanderuser'@'localhost';
FLUSH PRIVILEGES;
```

---

### Common Node.js Backend Issues

#### Issue 1: Port Already in Use
**Error:** `EADDRINUSE: address already in use :::3000`

**Find and kill process:**
```bash
sudo lsof -i :3000
kill -9 <PID>
```

**Or change port in .env:**
```env
PORT=3001
```

#### Issue 2: MySQL Connection Refused
**Error:** `ECONNREFUSED 127.0.0.1:3306`

**Check MySQL running:**
```bash
sudo systemctl status mysql
sudo systemctl start mysql
```

**Verify MySQL listening on TCP:**
```bash
sudo netstat -tlnp | grep 3306
```

#### Issue 3: Environment Variables Not Loading
**Error:** Database connection fails with undefined values

**Solution:**
1. Verify `.env` file exists in `~/wanderlite-backend/`
2. Check file has correct format (no quotes around values)
3. Ensure `require('dotenv').config()` is at top of `server.js`

**Debug:**
```bash
cd ~/wanderlite-backend
node -e "require('dotenv').config(); console.log(process.env.DB_HOST)"
```

---

### Common Nginx Issues

#### Issue 1: 502 Bad Gateway
**Error:** Nginx shows "502 Bad Gateway" for /api/* requests

**Causes:**
- Backend not running
- Backend running on wrong port
- Firewall blocking connection

**Solution:**
```bash
# Check backend running
ps aux | grep "[n]ode.*server.js"

# Test backend directly
curl http://localhost:3000/api/health

# Check Nginx error logs
sudo tail -50 /var/log/nginx/wanderlite-error.log

# Restart backend if needed
cd ~/wanderlite-backend
npm start
```

#### Issue 2: Configuration Syntax Error
**Error:** `nginx: configuration file /etc/nginx/nginx.conf test failed`

**Solution:**
```bash
# Test configuration
sudo nginx -t

# Check specific site config
sudo nginx -t -c /etc/nginx/sites-available/wanderlite

# Fix syntax errors shown in output
sudo nano /etc/nginx/sites-available/wanderlite

# After fixing, reload
sudo systemctl reload nginx
```

#### Issue 3: Port 80 Already in Use
**Error:** Nginx fails to start, port 80 in use

**Find process using port 80:**
```bash
sudo lsof -i :80
sudo netstat -tlnp | grep :80
```

**Kill process or change Nginx port:**
```nginx
# In /etc/nginx/sites-available/wanderlite
listen 8080;  # Change from 80
```

#### Issue 4: Permission Denied for /var/www/wanderlite
**Error:** 403 Forbidden or file access errors

**Fix permissions:**
```bash
sudo chown -R www-data:www-data /var/www/wanderlite
sudo chmod -R 755 /var/www/wanderlite
```

---

### Common Frontend Issues

#### Issue 1: 404 Not Found for SPA Routes
**Error:** Nginx returns 404 for React routes like `/explore`, `/login`

**Verify try_files directive:**
```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

**Reload Nginx after changes:**
```bash
sudo nginx -t && sudo systemctl reload nginx
```

#### Issue 2: Static Assets Not Loading
**Error:** CSS/JS files return 404

**Check file locations:**
```bash
ls -la /var/www/wanderlite/
```

**Verify build output copied:**
```bash
# If using React build
cd ~/wanderlite/frontend
npm run build
sudo cp -r build/* /var/www/wanderlite/
```

---

## 🔍 Verification Commands

### Complete System Health Check
```bash
# 1. Check MySQL
sudo systemctl status mysql --no-pager
mysql -u wanderuser -pStrongPass@123 -h 127.0.0.1 --protocol=tcp -D wanderlite -e "SELECT 1;"

# 2. Check Backend
ps aux | grep "[n]ode.*server.js"
curl -s http://localhost:3000/api/health | jq

# 3. Check Nginx
sudo systemctl status nginx --no-pager
curl -s http://localhost

# 4. Check Reverse Proxy
curl -s http://localhost/api/health | jq

# 5. Check Logs
sudo tail -10 /var/log/nginx/wanderlite-access.log
sudo tail -10 /var/log/nginx/wanderlite-error.log
```

### Database Connectivity Test
```bash
# From command line
mysql -u wanderuser -pStrongPass@123 -h 127.0.0.1 --protocol=tcp -D wanderlite

# From Node.js
cd ~/wanderlite-backend
node -e "require('dotenv').config(); const db = require('./config/db'); db.query('SELECT 1+1 AS result').then(([rows]) => console.log(rows)).catch(err => console.error(err)).finally(() => process.exit())"
```

### Port Availability Check
```bash
# Check if ports are in use
sudo netstat -tlnp | grep -E ':(80|3000|3306)\s'

# Or using lsof
sudo lsof -i :80
sudo lsof -i :3000
sudo lsof -i :3306
```

---

## 📝 Maintenance Tasks

### Restart Backend Service
```bash
# Find current process
ps aux | grep "[n]ode.*server.js"

# Kill process
kill <PID>

# Start new instance
cd ~/wanderlite-backend
npm start &

# Verify running
curl http://localhost:3000/api/health
```

### Update Nginx Configuration
```bash
# Edit config
sudo nano /etc/nginx/sites-available/wanderlite

# Test syntax
sudo nginx -t

# If successful, reload
sudo systemctl reload nginx

# Check logs for errors
sudo tail -20 /var/log/nginx/wanderlite-error.log
```

### View Real-Time Logs
```bash
# Nginx access log
sudo tail -f /var/log/nginx/wanderlite-access.log

# Nginx error log
sudo tail -f /var/log/nginx/wanderlite-error.log

# MySQL error log
sudo tail -f /var/log/mysql/error.log

# Backend logs (if logging to file)
tail -f ~/wanderlite-backend/app.log
```

### Database Backup
```bash
# Backup entire database
mysqldump -u wanderuser -pStrongPass@123 -h 127.0.0.1 --protocol=tcp wanderlite > wanderlite_backup_$(date +%Y%m%d).sql

# Restore from backup
mysql -u wanderuser -pStrongPass@123 -h 127.0.0.1 --protocol=tcp wanderlite < wanderlite_backup_20251215.sql
```

---

## 🔐 Security Notes

### Production Security Checklist

1. **Change Default Password**
   ```sql
   ALTER USER 'wanderuser'@'localhost' IDENTIFIED BY 'NewStrongPassword123!';
   ```

2. **Restrict Database User Privileges**
   ```sql
   -- Remove ALL, grant only needed privileges
   REVOKE ALL PRIVILEGES ON wanderlite.* FROM 'wanderuser'@'localhost';
   GRANT SELECT, INSERT, UPDATE, DELETE ON wanderlite.* TO 'wanderuser'@'localhost';
   FLUSH PRIVILEGES;
   ```

3. **Enable HTTPS (for production deployment)**
   - Install Let's Encrypt SSL certificate
   - Update Nginx to listen on 443
   - Redirect HTTP to HTTPS

4. **Firewall Configuration**
   ```bash
   # Allow only necessary ports
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

5. **Secure .env File**
   ```bash
   chmod 600 ~/wanderlite-backend/.env
   ```

6. **MySQL Security Hardening**
   ```bash
   sudo mysql_secure_installation
   ```

---

## 📊 Performance Monitoring

### Check Resource Usage
```bash
# Memory usage
free -h

# CPU usage
top -bn1 | grep "Cpu(s)"

# Disk usage
df -h

# MySQL process stats
mysqladmin -u wanderuser -pStrongPass@123 -h 127.0.0.1 --protocol=tcp status

# Nginx connections
sudo systemctl status nginx | grep "Active:"
```

### MySQL Performance
```sql
-- Show active connections
SHOW PROCESSLIST;

-- Show database size
SELECT table_schema AS "Database", 
       ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS "Size (MB)" 
FROM information_schema.TABLES 
WHERE table_schema = 'wanderlite'
GROUP BY table_schema;

-- Show query cache stats
SHOW VARIABLES LIKE 'query_cache%';
```

---

## 🎯 Next Steps

### Deploying React Frontend

1. **Build React application:**
   ```bash
   cd ~/wanderlite/frontend
   npm run build
   ```

2. **Copy build to web root:**
   ```bash
   sudo rm -rf /var/www/wanderlite/*
   sudo cp -r build/* /var/www/wanderlite/
   ```

3. **Update permissions:**
   ```bash
   sudo chown -R www-data:www-data /var/www/wanderlite
   sudo chmod -R 755 /var/www/wanderlite
   ```

4. **Test deployment:**
   ```bash
   curl http://localhost
   ```

### Adding More API Endpoints

**Example: Add booking endpoint to backend**

1. Create routes file:
   ```bash
   mkdir ~/wanderlite-backend/routes
   nano ~/wanderlite-backend/routes/bookings.js
   ```

2. Add route handler:
   ```javascript
   const express = require('express');
   const router = express.Router();
   const db = require('../config/db');

   router.post('/bookings', async (req, res) => {
       try {
           const { user_id, service_type, details } = req.body;
           const [result] = await db.query(
               'INSERT INTO bookings (user_id, service_type, details) VALUES (?, ?, ?)',
               [user_id, service_type, JSON.stringify(details)]
           );
           res.json({ success: true, booking_id: result.insertId });
       } catch (error) {
           res.status(500).json({ error: error.message });
       }
   });

   module.exports = router;
   ```

3. Register in server.js:
   ```javascript
   const bookingRoutes = require('./routes/bookings');
   app.use('/api', bookingRoutes);
   ```

---

## 📚 References

- **Nginx Documentation:** https://nginx.org/en/docs/
- **MySQL Documentation:** https://dev.mysql.com/doc/
- **Express.js Guide:** https://expressjs.com/
- **Node.js Best Practices:** https://github.com/goldbergyoni/nodebestpractices

---

## ✅ Verification Checklist

**After Setup Completion:**

- [ ] MySQL service running (`sudo systemctl status mysql`)
- [ ] Database `wanderlite` exists (`SHOW DATABASES;`)
- [ ] User `wanderuser@localhost` can login via TCP
- [ ] Node.js backend running (`ps aux | grep node`)
- [ ] Backend responds to health check (`curl localhost:3000/api/health`)
- [ ] Nginx service active (`sudo systemctl status nginx`)
- [ ] Frontend accessible (`curl localhost`)
- [ ] API proxy working (`curl localhost/api/health`)
- [ ] No errors in Nginx logs (`tail /var/log/nginx/wanderlite-error.log`)
- [ ] Environment variables loaded correctly

**Current Status: ✅ ALL CHECKS PASSED**

---

*Last Updated: December 15, 2025*
*Wanderlite Production Stack v1.0.0*
