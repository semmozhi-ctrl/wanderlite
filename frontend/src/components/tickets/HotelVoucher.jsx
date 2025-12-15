import React from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { Hotel, Calendar, User, CreditCard, MapPin, Phone, Mail, Clock } from 'lucide-react';
import { Card } from '../ui/card';
import { getPublicBaseUrl } from '../../services/publicUrl';

const HotelVoucher = ({ booking, passenger, payment }) => {
  // Parse service_details if it's a string
  const serviceDetails = typeof booking?.service_details === 'string'
    ? (() => { try { return JSON.parse(booking.service_details); } catch { return {}; } })()
    : booking?.service_details || {};
  
  const hotel = serviceDetails.hotel || serviceDetails;
  const details = serviceDetails;
  const voucherNumber = booking?.booking_ref || 'N/A';
  
  // QR Code data - Simple URL that opens voucher when scanned
  // Uses IP address if available for cross-device scanning
  const baseUrl = getPublicBaseUrl();
  const qrData = `${baseUrl}/ticket/verify?pnr=${voucherNumber}`;

  const formatDate = (dateStr) => {
    if (!dateStr) return 'DD MMM YYYY';
    try {
      return new Date(dateStr).toLocaleDateString('en-IN', {
        weekday: 'short',
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      });
    } catch {
      return 'DD MMM YYYY';
    }
  };

  const calculateNights = () => {
    if (!details.check_in || !details.check_out) return details.nights || 1;
    const diff = new Date(details.check_out) - new Date(details.check_in);
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
      <Card className="overflow-hidden shadow-2xl border-0">
        {/* Header */}
        <div className="bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 p-6 text-white">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <div className="w-16 h-16 bg-white rounded-lg flex items-center justify-center">
                <Hotel className="w-8 h-8 text-emerald-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Hotel Booking Voucher</h1>
                <p className="text-emerald-100 text-sm">Presented by WanderLite</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-emerald-200">Voucher No.</p>
              <p className="text-xl font-bold font-mono">{voucherNumber}</p>
            </div>
          </div>
        </div>

        {/* Confirmation Status */}
        <div className="bg-green-50 border-l-4 border-green-500 px-6 py-3">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-green-800 font-semibold text-sm">RESERVATION CONFIRMED</span>
          </div>
        </div>

        <div className="p-8 bg-gradient-to-br from-gray-50 to-white">
          {/* Hotel Information */}
          <div className="mb-8">
            <div className="bg-white rounded-xl shadow-lg p-6 border-2 border-emerald-100">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">{hotel.name || 'Premium Hotel & Resort'}</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div className="flex items-start gap-2">
                  <MapPin className="w-5 h-5 text-emerald-600 mt-1" />
                  <div>
                    <p className="text-sm font-semibold text-gray-700">Address</p>
                    <p className="text-sm text-gray-600">{hotel.address || `${booking?.destination || 'City'}, India`}</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <Phone className="w-5 h-5 text-emerald-600 mt-1" />
                  <div>
                    <p className="text-sm font-semibold text-gray-700">Contact</p>
                    <p className="text-sm text-gray-600">{hotel.phone || '+91 1800-XXX-XXXX'}</p>
                  </div>
                </div>
              </div>

              {hotel.description && (
                <p className="text-sm text-gray-600 italic">{hotel.description}</p>
              )}

              {hotel.rating && (
                <div className="mt-3 flex items-center gap-2">
                  <span className="text-xs font-semibold">Rating:</span>
                  <div className="flex">
                    {[...Array(5)].map((_, i) => (
                      <span key={i} className={i < Math.floor(hotel.rating) ? 'text-amber-400' : 'text-gray-300'}>★</span>
                    ))}
                  </div>
                  <span className="text-sm text-gray-600">({hotel.rating || '4.5'}/5)</span>
                </div>
              )}
            </div>
          </div>

          {/* Check-in/Check-out */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <Card className="p-6 border-2 border-cyan-100 bg-cyan-50/50">
              <div className="flex items-center gap-3 mb-3">
                <Calendar className="w-6 h-6 text-cyan-600" />
                <p className="text-sm font-semibold text-gray-700">CHECK-IN</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">{formatDate(details.check_in || booking?.start_date)}</p>
              <p className="text-sm text-gray-600 mt-2 flex items-center gap-1">
                <Clock className="w-4 h-4" /> After {details.check_in_time || '14:00'} hrs
              </p>
            </Card>

            <Card className="p-6 border-2 border-orange-100 bg-orange-50/50">
              <div className="flex items-center gap-3 mb-3">
                <Calendar className="w-6 h-6 text-orange-600" />
                <p className="text-sm font-semibold text-gray-700">CHECK-OUT</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">{formatDate(details.check_out || booking?.end_date)}</p>
              <p className="text-sm text-gray-600 mt-2 flex items-center gap-1">
                <Clock className="w-4 h-4" /> Before {details.check_out_time || '11:00'} hrs
              </p>
            </Card>
          </div>

          {/* Booking Details */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="p-4 bg-white rounded-lg shadow-sm border border-gray-200">
              <p className="text-xs text-gray-600 mb-2">DURATION</p>
              <p className="text-3xl font-bold text-emerald-600">{calculateNights()}</p>
              <p className="text-sm text-gray-600">Night{calculateNights() > 1 ? 's' : ''}</p>
            </div>

            <div className="p-4 bg-white rounded-lg shadow-sm border border-gray-200">
              <p className="text-xs text-gray-600 mb-2">ROOM TYPE</p>
              <p className="text-lg font-bold text-gray-900">{details.roomType || 'Deluxe Room'}</p>
              <p className="text-sm text-gray-600">{details.rooms || 1} Room{(details.rooms || 1) > 1 ? 's' : ''}</p>
            </div>

            <div className="p-4 bg-white rounded-lg shadow-sm border border-gray-200">
              <p className="text-xs text-gray-600 mb-2">GUESTS</p>
              <p className="text-3xl font-bold text-gray-900">{booking?.travelers || details.guests || 2}</p>
              <p className="text-sm text-gray-600">Adult{(booking?.travelers || details.guests) > 1 ? 's' : ''}</p>
            </div>
          </div>

          {/* Guest Information */}
          <div className="mb-8 p-6 bg-white rounded-lg shadow-sm border-2 border-blue-100">
            <p className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
              <User className="w-4 h-4" /> PRIMARY GUEST DETAILS
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">Full Name</p>
                <p className="text-lg font-bold text-gray-900">{passenger?.fullName || 'John Doe'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Contact Number</p>
                <p className="text-lg font-semibold text-gray-900">{passenger?.phone || '+91 XXXXX-XXXXX'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Email Address</p>
                <p className="text-sm font-semibold text-gray-900">{passenger?.email || 'guest@email.com'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">ID Proof</p>
                <p className="text-sm text-gray-700">{passenger?.idType || 'Aadhaar'}: {passenger?.idNumber ? `****${passenger.idNumber.slice(-4)}` : '****1234'}</p>
              </div>
            </div>
          </div>

          {/* Inclusions */}
          <div className="mb-8 p-6 bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg border border-purple-200">
            <p className="text-sm font-semibold text-gray-700 mb-3">INCLUSIONS</p>
            <div className="grid grid-cols-2 gap-3">
              {(details.inclusions || ['Breakfast', 'WiFi', 'Parking', 'Swimming Pool']).map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-gray-700">
                  <span className="text-green-500">✓</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Payment Details */}
          <div className="mb-8 p-6 bg-gradient-to-br from-amber-50 to-yellow-50 rounded-lg border-2 border-amber-200">
            <p className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
              <CreditCard className="w-4 h-4" /> PAYMENT SUMMARY
            </p>
            {(() => {
              // Extract fare data
              const totalAmount = parseFloat(booking?.total_price || payment?.amount || booking?.amount || details?.total_price || 0);
              const roomCharges = parseFloat(details?.baseFare || details?.room_charges || totalAmount * 0.85 || 0);
              const taxes = parseFloat(details?.taxes || details?.taxes_fees || totalAmount - roomCharges || totalAmount * 0.15 || 0);
              const discount = parseFloat(details?.discount || payment?.discount || 0);
              
              return (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Room Charges ({calculateNights()} night{calculateNights() > 1 ? 's' : ''})</span>
                    <span className="font-semibold">₹{roomCharges.toFixed(2)}</span>
                  </div>
                  {discount > 0 && (
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Discount</span>
                      <span className="font-semibold text-green-600">-₹{discount.toFixed(2)}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Taxes & Service Charges</span>
                    <span className="font-semibold">₹{taxes.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-sm pt-2 border-t border-amber-300">
                    <span className="text-gray-900 font-bold">Total Amount Paid</span>
                    <span className="text-xl font-bold text-green-600">₹{totalAmount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                  </div>
                  <div className="flex justify-between text-xs text-gray-600 mt-2">
                    <span>Payment Mode: {payment?.method || 'Card'}</span>
                    <span>Txn ID: {payment?.id ? `WL${payment.id}` : 'N/A'}</span>
                  </div>
                </div>
              );
            })()}
          </div>

          {/* QR Code */}
          <div className="flex items-center justify-between p-6 bg-white rounded-lg shadow-lg border-2 border-gray-200">
            <div className="flex-1">
              <div className="mb-3">
                <p className="text-xs text-gray-500 mb-1">CONFIRMATION NUMBER</p>
                <p className="text-2xl font-bold text-emerald-600 tracking-wider font-mono">{voucherNumber}</p>
              </div>
              <div className="mb-3">
                <p className="text-xs text-gray-500 mb-1">BOOKING DATE</p>
                <p className="text-sm text-gray-700">{formatDate(booking?.created_at)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">PAYMENT STATUS</p>
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-semibold">CONFIRMED & PAID</span>
              </div>
            </div>

            <div className="flex flex-col items-center ml-8">
              <div className="p-4 bg-white rounded-lg shadow-inner">
                <QRCodeSVG 
                  value={qrData}
                  size={140}
                  level="H"
                  includeMargin={true}
                  imageSettings={{
                    src: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%2310b981'%3E%3Cpath d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z'/%3E%3C/svg%3E",
                    height: 20,
                    width: 20,
                    excavate: true,
                  }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-2">Show at check-in</p>
            </div>
          </div>

          {/* Important Information */}
          <div className="mt-6 p-4 bg-blue-50 border-l-4 border-blue-500 rounded">
            <p className="text-xs font-semibold text-blue-800 mb-2">IMPORTANT INFORMATION</p>
            <ul className="text-xs text-blue-700 space-y-1">
              <li>• Valid government ID is mandatory at check-in</li>
              <li>• Early check-in subject to availability</li>
              <li>• Late check-out may incur additional charges</li>
              <li>• Cancellation policy: {details.cancellation_policy || 'Free cancellation up to 24 hours before check-in'}</li>
            </ul>
          </div>

          {/* Footer */}
          <div className="mt-6 pt-6 border-t border-gray-200 flex justify-between items-center">
            <div className="text-xs text-gray-500">
              <p className="font-semibold mb-1">24/7 Support</p>
              <p>📞 1800-123-WANDER (92633)</p>
              <p>📧 hotels@wanderlite.com</p>
            </div>
            <div className="text-right text-xs text-gray-400">
              <p>WanderLite Travel Pvt. Ltd.</p>
              <p>Your trusted travel partner</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default HotelVoucher;
