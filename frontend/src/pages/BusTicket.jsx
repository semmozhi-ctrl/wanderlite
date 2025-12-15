import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Bus,
  MapPin,
  Calendar,
  Clock,
  User,
  Phone,
  Mail,
  Download,
  Share2,
  Printer,
  CheckCircle,
  AlertCircle,
  Navigation,
  RefreshCw,
  QrCode,
  ArrowLeft,
  X,
  Loader2
} from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Helper function to extract error message from API response
const getErrorMessage = (err, defaultMsg) => {
  const detail = err.response?.data?.detail;
  if (!detail) return defaultMsg;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ');
  }
  if (typeof detail === 'object' && detail.msg) return detail.msg;
  return defaultMsg;
};

const BusTicket = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { token } = useAuth();
  const { bookingId, pnr } = location.state || {};
  const ticketRef = useRef(null);

  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [showTracking, setShowTracking] = useState(false);
  const [downloading, setDownloading] = useState(false);

  // Fetch ticket details
  useEffect(() => {
    const fetchTicket = async () => {
      if (!bookingId && !pnr) {
        setError('No booking information found');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const response = await axios.get(
          `${API_URL}/api/bus/booking/${bookingId || pnr}`,
          {
            headers: { Authorization: `Bearer ${token}` }
          }
        );
        setTicket(response.data);
      } catch (err) {
        console.error('Error fetching ticket:', err);
        setError(getErrorMessage(err, 'Failed to load ticket'));
      } finally {
        setLoading(false);
      }
    };
    fetchTicket();
  }, [bookingId, pnr, token]);

  // Format date
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
  };

  // Handle cancellation
  const handleCancel = async () => {
    setCancelling(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/bus/cancel`,
        { booking_id: ticket.id },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      
      // Update ticket with cancellation info
      setTicket(prev => ({
        ...prev,
        booking_status: 'cancelled',
        refund_amount: response.data.refund_amount
      }));
      setShowCancelModal(false);
    } catch (err) {
      console.error('Cancellation error:', err);
      setError(getErrorMessage(err, 'Failed to cancel booking'));
    } finally {
      setCancelling(false);
    }
  };

  // Print ticket
  const handlePrint = () => {
    window.print();
  };

  // Download ticket as PDF
  const handleDownloadPDF = async () => {
    if (!ticketRef.current || !ticket) return;
    
    setDownloading(true);
    try {
      // Hide buttons before capture
      const buttons = ticketRef.current.querySelectorAll('.print\\:hidden');
      buttons.forEach(btn => btn.style.display = 'none');
      
      const canvas = await html2canvas(ticketRef.current, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff'
      });
      
      // Restore buttons
      buttons.forEach(btn => btn.style.display = '');
      
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4'
      });
      
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();
      const imgWidth = canvas.width;
      const imgHeight = canvas.height;
      const ratio = Math.min(pdfWidth / imgWidth, pdfHeight / imgHeight);
      const imgX = (pdfWidth - imgWidth * ratio) / 2;
      const imgY = 10;
      
      pdf.addImage(imgData, 'PNG', imgX, imgY, imgWidth * ratio, imgHeight * ratio);
      pdf.save(`BusTicket_${ticket.pnr}.pdf`);
    } catch (err) {
      console.error('PDF download error:', err);
      setError('Failed to download ticket. Please try again.');
    } finally {
      setDownloading(false);
    }
  };

  // Calculate refund (for preview)
  const calculateRefundPreview = () => {
    if (!ticket) return { percentage: 0, amount: 0 };
    
    const journeyDateTime = new Date(`${ticket.journey_date}T${ticket.departure_time}`);
    const now = new Date();
    const hoursToJourney = (journeyDateTime - now) / (1000 * 60 * 60);
    
    let percentage = 0;
    if (hoursToJourney > 24) percentage = 90;
    else if (hoursToJourney > 12) percentage = 50;
    else if (hoursToJourney > 6) percentage = 25;
    
    return {
      percentage,
      amount: (ticket.total_amount * percentage / 100).toFixed(0)
    };
  };

  // Generate QR code data URL (simple placeholder)
  const generateQRCode = () => {
    // In production, use a proper QR library like qrcode.react
    // This is a placeholder SVG
    return `data:image/svg+xml,${encodeURIComponent(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect fill="white" width="100" height="100"/>
        <text x="50" y="40" text-anchor="middle" font-size="8" fill="black">QR CODE</text>
        <text x="50" y="55" text-anchor="middle" font-size="6" fill="black">${ticket?.pnr || 'PNR'}</text>
        <rect x="20" y="60" width="60" height="30" fill="none" stroke="black" stroke-width="2"/>
        <line x1="30" y1="65" x2="30" y2="85" stroke="black" stroke-width="2"/>
        <line x1="40" y1="65" x2="40" y2="85" stroke="black" stroke-width="3"/>
        <line x1="50" y1="65" x2="50" y2="85" stroke="black" stroke-width="2"/>
        <line x1="60" y1="65" x2="60" y2="85" stroke="black" stroke-width="3"/>
        <line x1="70" y1="65" x2="70" y2="85" stroke="black" stroke-width="2"/>
      </svg>
    `)}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="container mx-auto px-4 py-20 text-center">
          <RefreshCw className="w-12 h-12 animate-spin text-orange-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading ticket...</p>
        </div>
      </div>
    );
  }

  if (error && !ticket) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="container mx-auto px-4 py-20 text-center">
          <AlertCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-600 mb-2">Error</h2>
          <p className="text-gray-500 mb-6">{error}</p>
          <button
            onClick={() => navigate('/buses')}
            className="px-6 py-3 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition"
          >
            Search Buses
          </button>
        </div>
      </div>
    );
  }

  const refundPreview = calculateRefundPreview();

  return (
    <div className="min-h-screen bg-gray-100 print:bg-white">
      <div className="container mx-auto px-4 py-8">
        {/* Back Button */}
        <button
          onClick={() => navigate('/my-bookings')}
          className="flex items-center gap-2 text-gray-600 hover:text-orange-500 mb-6 print:hidden"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to My Bookings
        </button>

        {/* Success Message */}
        {ticket?.booking_status === 'confirmed' && location.state?.bookingId && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-xl flex items-center gap-3 print:hidden">
            <CheckCircle className="w-6 h-6 text-green-500" />
            <div>
              <p className="font-medium text-green-800">Booking Confirmed!</p>
              <p className="text-sm text-green-600">Your ticket has been booked successfully. PNR: {ticket.pnr}</p>
            </div>
          </div>
        )}

        {/* Cancelled Message */}
        {ticket?.booking_status === 'cancelled' && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 print:hidden">
            <AlertCircle className="w-6 h-6 text-red-500" />
            <div>
              <p className="font-medium text-red-800">Booking Cancelled</p>
              {ticket.refund_amount > 0 && (
                <p className="text-sm text-red-600">Refund of ₹{ticket.refund_amount} will be processed within 5-7 business days.</p>
              )}
            </div>
          </div>
        )}

        {/* Ticket Card */}
        <div className="max-w-3xl mx-auto" ref={ticketRef}>
          <div className="bg-white rounded-xl shadow-lg overflow-hidden print:shadow-none print:border">
            {/* Header */}
            <div className={`p-6 text-white ${
              ticket?.booking_status === 'cancelled' 
                ? 'bg-gradient-to-r from-gray-500 to-gray-600' 
                : 'bg-gradient-to-r from-orange-500 to-red-500'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Bus className="w-10 h-10" />
                  <div>
                    <h1 className="text-2xl font-bold">Bus Ticket</h1>
                    <p className="text-orange-100">{ticket?.operator_name}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm text-orange-100">PNR Number</p>
                  <p className="text-2xl font-mono font-bold tracking-wider">{ticket?.pnr}</p>
                </div>
              </div>
            </div>

            {/* Status Badge */}
            <div className="flex justify-center -mt-4">
              <span className={`px-6 py-2 rounded-full text-sm font-medium ${
                ticket?.booking_status === 'confirmed' ? 'bg-green-100 text-green-700' :
                ticket?.booking_status === 'cancelled' ? 'bg-red-100 text-red-700' :
                'bg-yellow-100 text-yellow-700'
              }`}>
                {ticket?.booking_status?.toUpperCase()}
              </span>
            </div>

            {/* Journey Details */}
            <div className="p-6">
              <div className="flex items-center justify-between mb-8">
                <div className="text-center flex-1">
                  <p className="text-3xl font-bold text-gray-800">{ticket?.departure_time}</p>
                  <p className="text-lg font-medium text-gray-600">{ticket?.from_city}</p>
                  <p className="text-sm text-gray-400">{ticket?.boarding_point}</p>
                </div>
                
                <div className="flex-shrink-0 px-6">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <div className="w-24 h-0.5 bg-gray-300"></div>
                    <Bus className="w-5 h-5 text-orange-500" />
                    <div className="w-24 h-0.5 bg-gray-300"></div>
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                  </div>
                  <p className="text-xs text-gray-400 text-center mt-1">{ticket?.bus_type}</p>
                </div>
                
                <div className="text-center flex-1">
                  <p className="text-3xl font-bold text-gray-800">{ticket?.arrival_time}</p>
                  <p className="text-lg font-medium text-gray-600">{ticket?.to_city}</p>
                  <p className="text-sm text-gray-400">{ticket?.dropping_point}</p>
                </div>
              </div>

              {/* Date & Bus Info */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg mb-6">
                <div>
                  <p className="text-xs text-gray-500 flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    Journey Date
                  </p>
                  <p className="font-medium text-gray-800">{formatDate(ticket?.journey_date)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 flex items-center gap-1">
                    <Bus className="w-3 h-3" />
                    Bus Number
                  </p>
                  <p className="font-medium text-gray-800">{ticket?.bus_number}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Seats</p>
                  <p className="font-medium text-gray-800">{ticket?.seats?.join(', ')}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Total Amount</p>
                  <p className="font-bold text-orange-600 text-lg">₹{ticket?.total_amount}</p>
                </div>
              </div>

              {/* Passengers */}
              <div className="mb-6">
                <h3 className="font-medium text-gray-800 mb-3 flex items-center gap-2">
                  <User className="w-4 h-4" />
                  Passengers ({ticket?.passengers?.length})
                </h3>
                <div className="space-y-2">
                  {ticket?.passengers?.map((p, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className="w-8 h-8 bg-orange-100 text-orange-600 rounded-full flex items-center justify-center text-sm font-medium">
                          {p.seat}
                        </span>
                        <div>
                          <p className="font-medium text-gray-800">{p.name}</p>
                          <p className="text-sm text-gray-500">{p.age} yrs, {p.gender}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Contact Info */}
              <div className="flex items-center gap-6 text-sm text-gray-600 mb-6">
                <div className="flex items-center gap-2">
                  <Mail className="w-4 h-4" />
                  {ticket?.contact_email}
                </div>
                <div className="flex items-center gap-2">
                  <Phone className="w-4 h-4" />
                  {ticket?.contact_phone}
                </div>
              </div>

              {/* QR Code */}
              <div className="flex items-center justify-center border-t pt-6">
                <div className="text-center">
                  <img 
                    src={generateQRCode()} 
                    alt="QR Code" 
                    className="w-24 h-24 mx-auto mb-2"
                  />
                  <p className="text-xs text-gray-500">Scan for verification</p>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="p-6 bg-gray-50 border-t flex flex-wrap items-center justify-between gap-4 print:hidden">
              <div className="flex items-center gap-3">
                <button
                  onClick={handlePrint}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition flex items-center gap-2"
                >
                  <Printer className="w-4 h-4" />
                  Print
                </button>
                <button
                  onClick={handleDownloadPDF}
                  disabled={downloading}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition flex items-center gap-2 disabled:opacity-50"
                >
                  {downloading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Downloading...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4" />
                      Download PDF
                    </>
                  )}
                </button>
                <button
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition flex items-center gap-2"
                >
                  <Share2 className="w-4 h-4" />
                  Share
                </button>
              </div>

              {ticket?.booking_status === 'confirmed' && (
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setShowTracking(true)}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition flex items-center gap-2"
                  >
                    <Navigation className="w-4 h-4" />
                    Track Bus
                  </button>
                  <button
                    onClick={() => setShowCancelModal(true)}
                    className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition"
                  >
                    Cancel Booking
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Important Info */}
          <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-xl p-4 print:hidden">
            <h3 className="font-medium text-yellow-800 mb-2">Important Information</h3>
            <ul className="text-sm text-yellow-700 space-y-1">
              <li>• Please arrive at the boarding point 15 minutes before departure</li>
              <li>• Carry a valid photo ID for verification</li>
              <li>• Show this ticket (printed or digital) to the conductor</li>
              <li>• Cancellation charges apply as per operator policy</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Cancel Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-gray-800">Cancel Booking?</h3>
              <button onClick={() => setShowCancelModal(false)}>
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            
            <p className="text-gray-600 mb-4">
              Are you sure you want to cancel this booking? This action cannot be undone.
            </p>

            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <p className="text-sm text-gray-600 mb-2">Refund Details:</p>
              <div className="flex items-center justify-between">
                <span>Refund Percentage</span>
                <span className="font-medium">{refundPreview.percentage}%</span>
              </div>
              <div className="flex items-center justify-between text-lg font-bold">
                <span>Refund Amount</span>
                <span className="text-green-600">₹{refundPreview.amount}</span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowCancelModal(false)}
                className="flex-1 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
              >
                Keep Booking
              </button>
              <button
                onClick={handleCancel}
                disabled={cancelling}
                className="flex-1 py-3 bg-red-500 text-white rounded-lg hover:bg-red-600 transition disabled:opacity-50"
              >
                {cancelling ? 'Cancelling...' : 'Confirm Cancel'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tracking Modal */}
      {showTracking && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-lg w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-gray-800">Live Bus Tracking</h3>
              <button onClick={() => setShowTracking(false)}>
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            
            <div className="aspect-video bg-gray-100 rounded-lg mb-4 flex items-center justify-center">
              <div className="text-center">
                <Navigation className="w-12 h-12 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-500">Live tracking not available yet</p>
                <p className="text-sm text-gray-400">Tracking will be available on the day of journey</p>
              </div>
            </div>

            <div className="bg-blue-50 rounded-lg p-4">
              <div className="flex items-center gap-2 text-blue-700 mb-2">
                <Bus className="w-5 h-5" />
                <span className="font-medium">{ticket?.bus_number}</span>
              </div>
              <p className="text-sm text-blue-600">
                Bus tracking will be enabled 1 hour before departure. You will receive a notification when tracking is available.
              </p>
            </div>

            <button
              onClick={() => setShowTracking(false)}
              className="w-full mt-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Print Styles */}
      <style>{`
        @media print {
          body {
            print-color-adjust: exact;
            -webkit-print-color-adjust: exact;
          }
        }
      `}</style>
    </div>
  );
};

export default BusTicket;
