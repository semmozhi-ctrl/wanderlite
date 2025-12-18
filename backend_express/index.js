require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');
const { WebSocketServer } = require('ws');
const jwt = require('jsonwebtoken');

const app = express();
const PORT = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || 'change_this_secret';

app.use(bodyParser.json({ limit: '5mb' }));
app.use(bodyParser.urlencoded({ extended: true }));

// Static uploads mount
app.use('/uploads', express.static(path.join(__dirname, '..', 'uploads')));

// Routes
const authRoutes = require('./routes/auth');
const flightRoutes = require('./routes/flight');
const hotelRoutes = require('./routes/hotel');
const restaurantRoutes = require('./routes/restaurant');
const destinationsRoutes = require('./routes/destinations');
const bookingsRoutes = require('./routes/bookings');
const paymentsRoutes = require('./routes/payments');
const receiptsRoutes = require('./routes/receipts');
const kycRoutes = require('./routes/kyc');
const adminKycRoutes = require('./routes/admin_kyc');
const aiRoutes = require('./routes/ai');
const parityStubs = require('./routes/parity_stubs');

app.use('/api/auth', authRoutes);
app.use('/api', flightRoutes);
app.use('/api', hotelRoutes);
app.use('/api', restaurantRoutes);
app.use('/api/destinations', destinationsRoutes);
app.use('/api', parityStubs);
app.use('/api/bookings', bookingsRoutes);
app.use('/api/payments', paymentsRoutes);
app.use('/api/receipts', receiptsRoutes);
app.use('/api/kyc', kycRoutes);
app.use('/api/ai', aiRoutes);
app.use('/api/admin', adminKycRoutes);

// Simple health-check — match Python service shape (returns an empty array in Python)
app.get('/api/status', (req, res) => res.json([]));

// Create HTTP server and attach WS to it
const server = app.listen(PORT, () => {
  console.log(`Wanderlite Express scaffold listening on http://localhost:${PORT}`);
});

// WebSocket notifications endpoint: /ws/notifications/{token}
const wss = new WebSocketServer({ noServer: true });

server.on('upgrade', (request, socket, head) => {
  const url = new URL(request.url, `http://${request.headers.host}`);
  if (url.pathname.startsWith('/ws/notifications/')) {
    wss.handleUpgrade(request, socket, head, (ws) => {
      const token = url.pathname.split('/').pop();
      try {
        const payload = jwt.verify(token, JWT_SECRET);
        ws.user = payload;
        ws.send(JSON.stringify({ type: 'init', unread_count: 0 }));
        ws.on('message', (msg) => {
          if (msg.toString() === 'ping') ws.send('pong');
        });
        ws.on('close', () => {});
      } catch (e) {
        ws.close(4001, 'Invalid token');
      }
    });
  } else {
    socket.destroy();
  }
});

module.exports = app;
