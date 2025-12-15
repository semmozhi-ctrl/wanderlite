import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import api from '../services/api';
import { detectAndStoreIP } from '../services/publicUrl';
import FlightTicket from '../components/tickets/FlightTicket';
import HotelVoucher from '../components/tickets/HotelVoucher';
import RestaurantBooking from '../components/tickets/RestaurantBooking';

const TicketVerify = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const pnr = searchParams.get('pnr');
  
  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState(null);
  const [payment, setPayment] = useState(null);
  const [passenger, setPassenger] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchTicketData = async () => {
      // Detect and store IP address for future QR code generation
      await detectAndStoreIP();

      if (!pnr) {
        setError('No booking reference provided');
        setLoading(false);
        return;
      }

      try {
        // Fetch booking details
        const bookingResponse = await api.get(`/api/bookings`);
        const bookings = bookingResponse.data;
        const foundBooking = Array.isArray(bookings) 
          ? bookings.find(b => b.booking_ref === pnr)
          : null;

        if (!foundBooking) {
          setError('Booking not found');
          setLoading(false);
          return;
        }

        setBooking(foundBooking);

        // Fetch payment details
        try {
          const paymentResponse = await api.get(`/api/payment/receipt/${pnr}`);
          setPayment(paymentResponse.data);
          
          // Create passenger object from payment data
          setPassenger({
            fullName: paymentResponse.data?.full_name || 'Traveler',
            email: paymentResponse.data?.email || 'traveler@wanderlite.com',
            phone: paymentResponse.data?.phone || '+91 XXXXX-XXXXX',
            idType: 'Aadhaar',
            idNumber: '1234567890',
          });
        } catch (err) {
          // Payment data might not exist, use defaults
          setPassenger({
            fullName: 'Traveler',
            email: 'traveler@wanderlite.com',
            phone: '+91 XXXXX-XXXXX',
            idType: 'Aadhaar',
            idNumber: '1234567890',
          });
        }

        setLoading(false);
      } catch (err) {
        console.error('Error fetching ticket data:', err);
        setError('Failed to load ticket details');
        setLoading(false);
      }
    };

    fetchTicketData();
  }, [pnr]);

  const renderTicket = () => {
    if (!booking) return null;
    
    const serviceType = (booking.service_type || 'flight').toLowerCase();
    
    switch (serviceType) {
      case 'flight':
        return <FlightTicket booking={booking} passenger={passenger} payment={payment} />;
      case 'hotel':
        return <HotelVoucher booking={booking} passenger={passenger} payment={payment} />;
      case 'restaurant':
        return <RestaurantBooking booking={booking} passenger={passenger} payment={payment} />;
      default:
        return <FlightTicket booking={booking} passenger={passenger} payment={payment} />;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600 text-lg">Verifying your ticket...</p>
          <p className="text-gray-400 text-sm mt-2">PNR: {pnr}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
        <div className="max-w-2xl mx-auto px-4">
          <div className="bg-white rounded-lg shadow-lg p-8 text-center">
            <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Verification Failed</h1>
            <p className="text-gray-600 mb-6">{error}</p>
            {pnr && <p className="text-sm text-gray-400 mb-6">PNR: {pnr}</p>}
            <button
              onClick={() => navigate('/')}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              Go to Home
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-20 pb-16 bg-gradient-to-b from-gray-50 to-white">
      {/* Verification Status */}
      <div className="max-w-4xl mx-auto px-4 mb-6">
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
          <CheckCircle2 className="w-6 h-6 text-green-600" />
          <div>
            <p className="text-green-800 font-semibold">Ticket Verified Successfully</p>
            <p className="text-green-600 text-sm">PNR: {pnr} | Status: {booking?.status || 'Confirmed'}</p>
          </div>
        </div>
      </div>

      {/* Render the appropriate ticket */}
      {renderTicket()}

      {/* Actions */}
      <div className="max-w-4xl mx-auto px-4 mt-6 flex gap-3 justify-center">
        <button
          onClick={() => navigate('/trip-history')}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          View Trip History
        </button>
        <button
          onClick={() => navigate('/explore')}
          className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
        >
          Explore More
        </button>
      </div>
    </div>
  );
};

export default TicketVerify;

