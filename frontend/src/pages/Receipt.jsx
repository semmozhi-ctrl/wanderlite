import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { CheckCircle, Ticket } from 'lucide-react';
import { detectAndStoreIP } from '../services/publicUrl';

const Receipt = () => {
  const navigate = useNavigate();
  const { state } = useLocation();
  const [ipAddress, setIpAddress] = useState(null);
  
  const receiptUrl = state?.receiptUrl || null;
  const ticketUrl = state?.ticketUrl || null;
  const booking = state?.booking || null;
  const bookingRef = state?.bookingRef || booking?.booking_ref || 'WL';
  const payer = state?.payer || {};
  const serviceType = state?.serviceType || 'Flight';
  const payment = state?.payment || null;
  const serviceDetails = state?.serviceDetails || booking?.service_details || {};

  useEffect(() => {
    // Get IP address for QR code sharing
    const getIP = async () => {
      const ip = await detectAndStoreIP();
      setIpAddress(ip);
    };
    getIP();
  }, []);

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div className="mb-6 flex justify-center">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center">
            <CheckCircle className="w-12 h-12 text-green-600" />
          </div>
        </div>
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Payment Successful!</h1>
        <p className="text-gray-600 mb-6">Your booking is confirmed.</p>

        <Card className="p-6 text-left space-y-3 bg-gradient-to-br from-blue-50 to-cyan-50 border-0">
          <div className="flex justify-between">
            <span className="text-gray-600">Booking Ref</span>
            <span className="font-semibold text-[#0077b6]">{bookingRef}</span>
          </div>
          {booking && (
            <>
              <div className="flex justify-between">
                <span className="text-gray-600">Destination</span>
                <span className="font-semibold">{booking.destination}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Travel Dates</span>
                <span className="font-semibold">{booking.start_date ? new Date(booking.start_date).toLocaleDateString() : '-'} to {booking.end_date ? new Date(booking.end_date).toLocaleDateString() : '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Amount</span>
                <span className="font-semibold">₹{Number(booking.amount || booking.total_price || 0).toLocaleString()}</span>
              </div>
            </>
          )}
          {payer?.fullName && (
            <div className="flex justify-between">
              <span className="text-gray-600">Name</span>
              <span className="font-semibold">{payer.fullName}</span>
            </div>
          )}
        </Card>

        <div className="mt-6 flex flex-col gap-3 items-center">
          {/* View Ticket in-app - Updated to pass full data */}
          <Button 
            className="w-full max-w-sm h-12 bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700" 
            onClick={() => navigate('/ticket', { 
              state: { 
                booking: {
                  ...booking,
                  service_details: serviceDetails || booking?.service_details,
                  service_type: serviceType
                },
                passenger: payer,
                payment: payment,
                serviceType: serviceType
              } 
            })}
          >
            <Ticket className="w-5 h-5 mr-2" /> View E‑Ticket
          </Button>

          {ipAddress && (
            <div className="w-full max-w-sm p-3 bg-purple-50 rounded-lg text-xs text-purple-700 border border-purple-200">
              <p className="font-semibold mb-1">📱 Share QR Code:</p>
              <p className="break-all">http://{ipAddress}:3001/ticket/verify?pnr={bookingRef}</p>
            </div>
          )}

          <div className="flex gap-3 mt-4 flex-wrap justify-center">
            <Button variant="outline" onClick={() => navigate('/explore')}>Back to Explore</Button>
            <Button onClick={() => navigate('/my-bookings')}>View My Bookings</Button>
            <Button onClick={() => navigate('/')}>Go Home</Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Receipt;
