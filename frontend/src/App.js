import React from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import Home from "./pages/Home";
import Explore from "./pages/Explore";
import TripPlanner from "./pages/TripPlanner";
import Checklist from "./pages/ChecklistNew";
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
import TripHistory from "./pages/TripHistory";
import Flights from "./pages/Flights";
import Assistant from "./pages/Assistant";
import Hotels from "./pages/Hotels";
import Restaurants from "./pages/Restaurants";
import DestinationDetails from "./pages/DestinationDetails";
import FlightDetail from "./pages/FlightDetail";
import HotelDetail from "./pages/HotelDetail";
import RestaurantDetail from "./pages/RestaurantDetail";

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

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <BrowserRouter>
          <Navbar />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/explore" element={<Explore />} />
            <Route path="/destination/:destinationName" element={<DestinationDetails />} />
            <Route path="/destination/:destinationName/flights/:flightId" element={<FlightDetail />} />
            <Route path="/destination/:destinationName/hotels/:hotelId" element={<HotelDetail />} />
            <Route path="/destination/:destinationName/restaurants/:restaurantId" element={<RestaurantDetail />} />
            <Route path="/planner" element={<TripPlanner />} />
            <Route path="/checklist" element={<Checklist />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/flights" element={<Flights />} />
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
            <Route path="/trip-history" element={<ProtectedRoute><TripHistory /></ProtectedRoute>} />
            <Route path="/assistant" element={<Assistant />} />
          </Routes>
          <Footer />
          <Toaster />
        </BrowserRouter>
      </div>
    </AuthProvider>
  );
}

export default App;
