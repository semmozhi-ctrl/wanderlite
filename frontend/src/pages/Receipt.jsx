import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { CheckCircle, Ticket, FileText } from 'lucide-react';

const Receipt = () => {
  const navigate = useNavigate();
  const { state } = useLocation();
  const receiptUrl = state?.receiptUrl || null;
  const ticketUrl = state?.ticketUrl || null;
  const booking = state?.booking || null;
  const bookingRef = state?.bookingRef || booking?.booking_ref || 'WL';
  const payer = state?.payer || {};
  const serviceType = state?.serviceType || 'Flight';
  const serviceDetails = state?.serviceDetails || null;

  // Resolve backend base for document links
  const docBase = (process.env.REACT_APP_BACKEND_URL || 'http://127.0.0.1:8001').replace(/\/$/, '');
  const toAbs = (u) => {
    if (!u) return null;
    if (/^https?:\/\//i.test(u)) return u;
    return `${docBase}${u.startsWith('/') ? u : '/' + u}`;
  };
  const ticketBtnLabel = serviceType === 'Hotel' ? 'Download Hotel Voucher' : 'Download Ticket / Voucher';

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div className="mb-6 flex justify-center">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center">
            <CheckCircle className="w-12 h-12 text-green-600" />
          </div>
        </div>
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Payment Successful!</h1>
        <p className="text-gray-600 mb-6">Your booking is confirmed. Download your documents below.</p>

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
                <span className="font-semibold">₹{Number(booking.total_price || 0).toLocaleString()}</span>
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
          {/* View Ticket in-app */}
          {serviceType === 'Flight' && (
            <Button className="w-full max-w-sm h-12 bg-gradient-to-r from-blue-600 to-indigo-600 text-white" onClick={() => navigate('/ticket', { state: { bookingRef, serviceType, serviceDetails, payer, ticketUrl } })}>
              <Ticket className="w-5 h-5 mr-2" /> View E‑Ticket
            </Button>
          )}
          {ticketUrl && (
            <Button asChild className="w-full max-w-sm h-12 bg-gradient-to-r from-blue-600 to-indigo-600 text-white">
              <a href={toAbs(ticketUrl)} target="_blank" rel="noreferrer" className="flex items-center justify-center gap-2">
                <Ticket className="w-5 h-5" />
                {ticketBtnLabel}
              </a>
            </Button>
          )}
          {receiptUrl && (
            <Button asChild variant="outline" className="w-full max-w-sm h-12 border-green-600 text-green-600 hover:bg-green-50">
              <a href={toAbs(receiptUrl)} target="_blank" rel="noreferrer" className="flex items-center justify-center gap-2">
                <FileText className="w-5 h-5" />
                Download Payment Receipt
              </a>
            </Button>
          )}
          {!receiptUrl && !ticketUrl && (
            <p className="text-sm text-gray-600">Documents were downloaded locally. If not, please go back and retry.</p>
          )}
          <div className="flex gap-3 mt-4">
            <Button variant="outline" onClick={() => navigate('/explore')}>Back to Explore</Button>
            <Button onClick={() => navigate('/trip-history')}>View Trip History</Button>
            <Button onClick={() => navigate('/')}>Go Home</Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Receipt;
