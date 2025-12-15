import React from "react";
import "./App.css";
import 'leaflet/dist/leaflet.css'; // Import Leaflet CSS for maps
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { AIProvider } from "./contexts/AIContext";
import { NotificationProvider } from "./contexts/NotificationContext";
import { ToastProvider } from "./components/Toast";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import ChatBot from "./components/ChatBot";
import Home from "./pages/Home";
import Explore from "./pages/Explore";
import TripPlanner from "./pages/TripPlanner";
import Contact from "./pages/Contact";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Profile from "./pages/Profile";
import Dashboard from "./pages/Dashboard";
import Gallery from "./pages/Gallery";
import { Toaster } from "./components/ui/sonner";
import Payment from "./pages/Payment";
import Receipt from "./pages/Receipt";
import Ticket from "./pages/Ticket";
import TicketVerify from "./pages/TicketVerify";
import MyBookings from "./pages/MyBookings";
import MyReceipts from "./pages/MyReceipts";
import Flights from "./pages/Flights";
import Buses from "./pages/Buses";
import BusResults from "./pages/BusResults";
import BusBooking from "./pages/BusBooking";
import BusTicket from "./pages/BusTicket";
import Assistant from "./pages/Assistant";
import Hotels from "./pages/Hotels";
import Restaurants from "./pages/Restaurants";
import DestinationDetails from "./pages/DestinationDetails";
import FlightDetail from "./pages/FlightDetail";
import HotelDetail from "./pages/HotelDetail";
import RestaurantDetail from "./pages/RestaurantDetail";

// Admin imports
import AdminLogin from "./pages/AdminLogin";
import AdminLayout from "./components/admin/AdminLayout";
import AdminDashboard from "./pages/admin/AdminDashboard";
import UserManagement from "./pages/admin/UserManagement";
import KYCVerification from "./pages/admin/KYCVerification";
import Bookings from "./pages/admin/Bookings";
import Transactions from "./pages/admin/Transactions";
import Destinations from "./pages/admin/Destinations";
import Notifications from "./pages/admin/Notifications";
import Receipts from "./pages/admin/Receipts";
import Reports from "./pages/admin/Reports";
import Settings from "./pages/admin/Settings";
import AdminProtectedRoute from "./components/admin/AdminProtectedRoute";

// Protected Route component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0077b6]"></div>
      </div>
    );
  }

  return isAuthenticated ? children : <Navigate to="/login" />;
};

// Public Route component (redirects to dashboard if authenticated)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0077b6]"></div>
      </div>
    );
  }

  return isAuthenticated ? <Navigate to="/profile" /> : children;
};

// AppContent component to conditionally render Navbar and Footer
const AppContent = () => {
  const location = useLocation();
  const isAdminRoute = location.pathname.startsWith('/admin');

  return (
    <>
      {!isAdminRoute && <Navbar />}
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/explore" element={<Explore />} />
        <Route path="/destination/:destinationName" element={<DestinationDetails />} />
        <Route path="/destination/:destinationName/flights/:flightId" element={<FlightDetail />} />
        <Route path="/destination/:destinationName/hotels/:hotelId" element={<HotelDetail />} />
        <Route path="/destination/:destinationName/restaurants/:restaurantId" element={<RestaurantDetail />} />
        <Route path="/planner" element={<TripPlanner />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/flights" element={<Flights />} />
        <Route path="/buses" element={<Buses />} />
        <Route path="/bus-results" element={<BusResults />} />
        <Route path="/bus-booking" element={<ProtectedRoute><BusBooking /></ProtectedRoute>} />
        <Route path="/bus-ticket" element={<ProtectedRoute><BusTicket /></ProtectedRoute>} />
        <Route path="/hotels" element={<Hotels />} />
        <Route path="/restaurants" element={<Restaurants />} />
        <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
        <Route path="/signup" element={<PublicRoute><Signup /></PublicRoute>} />
        <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/gallery" element={<ProtectedRoute><Gallery /></ProtectedRoute>} />
        <Route path="/payment" element={<Payment />} />
        <Route path="/receipt" element={<Receipt />} />
        <Route path="/ticket" element={<Ticket />} />
        <Route path="/ticket/verify" element={<TicketVerify />} />
        <Route path="/my-bookings" element={<ProtectedRoute><MyBookings /></ProtectedRoute>} />
        <Route path="/my-receipts" element={<ProtectedRoute><MyReceipts /></ProtectedRoute>} />
        <Route path="/assistant" element={<Assistant />} />

        {/* Admin Routes */}
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin" element={<AdminProtectedRoute><AdminLayout /></AdminProtectedRoute>}>
          <Route index element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="dashboard" element={<AdminDashboard />} />
          <Route path="users" element={<UserManagement />} />
          <Route path="kyc" element={<KYCVerification />} />
          <Route path="bookings" element={<Bookings />} />
          <Route path="transactions" element={<Transactions />} />
          <Route path="receipts" element={<Receipts />} />
          <Route path="destinations" element={<Destinations />} />
          <Route path="notifications" element={<Notifications />} />
          <Route path="reports" element={<Reports />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
      {!isAdminRoute && <Footer />}
      {!isAdminRoute && <ChatBot />}
      <Toaster />
    </>
  );
};

function App() {
  return (
    <AuthProvider>
      <NotificationProvider>
        <AIProvider>
          <ToastProvider>
            <div className="App">
              <BrowserRouter>
                <AppContent />
              </BrowserRouter>
            </div>
          </ToastProvider>
        </AIProvider>
      </NotificationProvider>
    </AuthProvider>
  );
}

export default App;
