import React from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { UtensilsCrossed, Calendar, Clock, Users, MapPin, Phone, Mail, CreditCard } from 'lucide-react';
import { Card } from '../ui/card';
import { getPublicBaseUrl } from '../../services/publicUrl';

const RestaurantBooking = ({ booking, passenger, payment }) => {
  // Parse service_details if it's a string
  const serviceDetails = typeof booking?.service_details === 'string'
    ? (() => { try { return JSON.parse(booking.service_details); } catch { return {}; } })()
    : booking?.service_details || {};
  
  const restaurant = serviceDetails.restaurant || serviceDetails;
  const details = serviceDetails;
  const bookingRef = booking?.booking_ref || 'N/A';
  
  // QR Code data - Simple URL that opens booking when scanned
  // Uses IP address if available for cross-device scanning
  const baseUrl = getPublicBaseUrl();
  const qrData = `${baseUrl}/ticket/verify?pnr=${bookingRef}`;

  const formatDate = (dateStr) => {
    if (!dateStr) return 'DD MMM YYYY';
    try {
      return new Date(dateStr).toLocaleDateString('en-IN', {
        weekday: 'long',
        day: '2-digit',
        month: 'long',
        year: 'numeric'
      });
    } catch {
      return 'DD MMM YYYY';
    }
  };

  const formatTime = (timeStr) => {
    if (!timeStr) return '19:00';
    return timeStr;
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
      <Card className="overflow-hidden shadow-2xl border-0">
        {/* Header */}
        <div className="bg-gradient-to-r from-rose-600 via-red-600 to-orange-600 p-6 text-white">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <div className="w-16 h-16 bg-white rounded-lg flex items-center justify-center">
                <UtensilsCrossed className="w-8 h-8 text-rose-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Table Reservation</h1>
                <p className="text-rose-100 text-sm">Powered by WanderLite</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-rose-200">Booking ID</p>
              <p className="text-xl font-bold font-mono">{bookingRef}</p>
            </div>
          </div>
        </div>

        {/* Confirmation Status */}
        <div className="bg-green-50 border-l-4 border-green-500 px-6 py-3">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-green-800 font-semibold text-sm">TABLE CONFIRMED</span>
          </div>
        </div>

        <div className="p-8 bg-gradient-to-br from-orange-50 to-white">
          {/* Restaurant Information */}
          <div className="mb-8">
            <div className="bg-white rounded-xl shadow-lg p-6 border-2 border-rose-100">
              <h2 className="text-3xl font-bold text-gray-900 mb-3">{restaurant.name || 'Fine Dining Restaurant'}</h2>
              
              <div className="mb-4">
                <span className="px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-semibold mr-2">
                  {restaurant.cuisine || 'Multi-Cuisine'}
                </span>
                {restaurant.category && (
                  <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-xs font-semibold">
                    {restaurant.category}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div className="flex items-start gap-2">
                  <MapPin className="w-5 h-5 text-rose-600 mt-1" />
                  <div>
                    <p className="text-sm font-semibold text-gray-700">Location</p>
                    <p className="text-sm text-gray-600">{restaurant.address || `${booking?.destination || 'City Center'}, India`}</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <Phone className="w-5 h-5 text-rose-600 mt-1" />
                  <div>
                    <p className="text-sm font-semibold text-gray-700">Contact</p>
                    <p className="text-sm text-gray-600">{restaurant.phone || '+91 1800-XXX-FOOD'}</p>
                  </div>
                </div>
              </div>

              {restaurant.description && (
                <p className="text-sm text-gray-600 italic mb-3">{restaurant.description}</p>
              )}

              {restaurant.rating && (
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold">Rating:</span>
                  <div className="flex">
                    {[...Array(5)].map((_, i) => (
                      <span key={i} className={i < Math.floor(restaurant.rating) ? 'text-amber-400' : 'text-gray-300'}>★</span>
                    ))}
                  </div>
                  <span className="text-sm text-gray-600">({restaurant.rating || '4.7'}/5)</span>
                </div>
              )}
            </div>
          </div>

          {/* Reservation Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <Card className="p-6 border-2 border-orange-100 bg-gradient-to-br from-orange-50 to-amber-50">
              <div className="flex items-center gap-3 mb-3">
                <Calendar className="w-6 h-6 text-orange-600" />
                <p className="text-sm font-semibold text-gray-700">RESERVATION DATE</p>
              </div>
              <p className="text-xl font-bold text-gray-900">{formatDate(details.date || booking?.start_date)}</p>
            </Card>

            <Card className="p-6 border-2 border-rose-100 bg-gradient-to-br from-rose-50 to-pink-50">
              <div className="flex items-center gap-3 mb-3">
                <Clock className="w-6 h-6 text-rose-600" />
                <p className="text-sm font-semibold text-gray-700">DINING TIME</p>
              </div>
              <p className="text-3xl font-bold text-gray-900">{formatTime(details.time || '19:00')}</p>
              <p className="text-sm text-gray-600 mt-2">Duration: {details.duration || '2 hours'}</p>
            </Card>
          </div>

          {/* Party Details */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="p-5 bg-white rounded-lg shadow-md border-2 border-purple-100">
              <div className="flex items-center gap-2 mb-2">
                <Users className="w-5 h-5 text-purple-600" />
                <p className="text-xs text-gray-600">PARTY SIZE</p>
              </div>
              <p className="text-4xl font-bold text-purple-600">{details.partySize || booking?.travelers || 2}</p>
              <p className="text-sm text-gray-600 mt-1">Guest{(details.partySize || booking?.travelers) > 1 ? 's' : ''}</p>
            </div>

            <div className="p-5 bg-white rounded-lg shadow-md border-2 border-indigo-100">
              <div className="flex items-center gap-2 mb-2">
                <UtensilsCrossed className="w-5 h-5 text-indigo-600" />
                <p className="text-xs text-gray-600">TABLE TYPE</p>
              </div>
              <p className="text-lg font-bold text-gray-900">{details.tableType || 'Standard'}</p>
              <p className="text-sm text-gray-600 mt-1">{details.tableNumber ? `Table #${details.tableNumber}` : 'Assigned on arrival'}</p>
            </div>

            <div className="p-5 bg-white rounded-lg shadow-md border-2 border-pink-100">
              <div className="flex items-center gap-2 mb-2">
                <MapPin className="w-5 h-5 text-pink-600" />
                <p className="text-xs text-gray-600">SEATING</p>
              </div>
              <p className="text-lg font-bold text-gray-900">{details.seating || 'Indoor'}</p>
              <p className="text-sm text-gray-600 mt-1">{details.section || 'Main dining area'}</p>
            </div>
          </div>

          {/* Guest Information */}
          <div className="mb-8 p-6 bg-white rounded-lg shadow-md border-2 border-blue-100">
            <p className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
              <Mail className="w-4 h-4" /> PRIMARY CONTACT DETAILS
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">Guest Name</p>
                <p className="text-lg font-bold text-gray-900">{passenger?.fullName || 'John Doe'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Mobile Number</p>
                <p className="text-lg font-semibold text-gray-900">{passenger?.phone || '+91 XXXXX-XXXXX'}</p>
              </div>
              <div className="md:col-span-2">
                <p className="text-xs text-gray-500 mb-1">Email Address</p>
                <p className="text-sm font-semibold text-gray-900">{passenger?.email || 'guest@email.com'}</p>
              </div>
            </div>
          </div>

          {/* Special Requests */}
          {details.specialRequests && (
            <div className="mb-8 p-6 bg-gradient-to-br from-yellow-50 to-amber-50 rounded-lg border-2 border-yellow-200">
              <p className="text-sm font-semibold text-gray-700 mb-3">SPECIAL REQUESTS</p>
              <p className="text-sm text-gray-700">{details.specialRequests}</p>
            </div>
          )}

          {/* Dietary Preferences */}
          {details.dietaryPreferences && details.dietaryPreferences.length > 0 && (
            <div className="mb-8 p-6 bg-gradient-to-br from-green-50 to-teal-50 rounded-lg border-2 border-green-200">
              <p className="text-sm font-semibold text-gray-700 mb-3">DIETARY PREFERENCES</p>
              <div className="flex flex-wrap gap-2">
                {details.dietaryPreferences.map((pref, i) => (
                  <span key={i} className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-semibold">
                    {pref}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Payment Details */}
          <div className="mb-8 p-6 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg border-2 border-blue-200">
            <p className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
              <CreditCard className="w-4 h-4" /> PAYMENT DETAILS
            </p>
            {(() => {
              // Extract fare data
              const totalAmount = parseFloat(booking?.total_price || payment?.amount || booking?.amount || details?.total_price || 0);
              const subtotal = parseFloat(details?.subtotal || details?.food_amount || totalAmount * 0.85 || 0);
              const taxes = parseFloat(details?.taxes || details?.taxes_fees || totalAmount - subtotal || totalAmount * 0.15 || 0);
              const discount = parseFloat(details?.discount || payment?.discount || 0);
              
              return (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Subtotal (Food & Beverages)</span>
                    <span className="font-semibold">₹{subtotal.toFixed(2)}</span>
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
                  <div className="flex justify-between text-sm pt-2 border-t border-blue-300">
                    <span className="text-gray-900 font-bold">Advance Amount Paid</span>
                    <span className="text-xl font-bold text-green-600">₹{totalAmount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                  </div>
                  <div className="flex justify-between text-xs text-gray-600 mt-2">
                    <span>Payment Mode: {payment?.method || 'Card'}</span>
                    <span>Txn ID: {payment?.id ? `WL${payment.id}` : 'N/A'}</span>
                  </div>
                </div>
              );
            })()}
            <p className="text-xs text-gray-500 mt-3 italic">Note: This is an advance booking payment. Final bill to be settled at the restaurant.</p>
          </div>

          {/* QR Code */}
          <div className="flex flex-col md:flex-row items-center justify-between p-6 bg-white rounded-lg shadow-lg border-2 border-gray-200">
            <div className="flex-1 mb-4 md:mb-0">
              <div className="mb-3">
                <p className="text-xs text-gray-500 mb-1">CONFIRMATION CODE</p>
                <p className="text-2xl font-bold text-rose-600 tracking-wider font-mono">{bookingRef}</p>
              </div>
              <div className="mb-3">
                <p className="text-xs text-gray-500 mb-1">BOOKED ON</p>
                <p className="text-sm text-gray-700">{formatDate(booking?.created_at)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">RESERVATION STATUS</p>
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-semibold">CONFIRMED</span>
              </div>
            </div>

            <div className="flex flex-col items-center md:ml-8">
              <div className="p-4 bg-white rounded-lg shadow-inner border-2 border-gray-100">
                <QRCodeSVG 
                  value={qrData}
                  size={140}
                  level="H"
                  includeMargin={true}
                  imageSettings={{
                    src: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23f43f5e'%3E%3Cpath d='M8.1 13.34l2.83-2.83L3.91 3.5c-1.56 1.56-1.56 4.09 0 5.66l4.19 4.18zm6.78-1.81c1.53.71 3.68.21 5.27-1.38 1.91-1.91 2.28-4.65.81-6.12-1.46-1.46-4.2-1.1-6.12.81-1.59 1.59-2.09 3.74-1.38 5.27L3.7 19.87l1.41 1.41L12 14.41l6.88 6.88 1.41-1.41L13.41 13l1.47-1.47z'/%3E%3C/svg%3E",
                    height: 20,
                    width: 20,
                    excavate: true,
                  }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-2 text-center">Present at restaurant</p>
            </div>
          </div>

          {/* Important Notes */}
          <div className="mt-6 p-4 bg-red-50 border-l-4 border-red-500 rounded">
            <p className="text-xs font-semibold text-red-800 mb-2">IMPORTANT NOTES</p>
            <ul className="text-xs text-red-700 space-y-1">
              <li>• Please arrive 10 minutes before your reservation time</li>
              <li>• Table will be held for 15 minutes after reservation time</li>
              <li>• Cancellation policy: {details.cancellation_policy || 'Free cancellation up to 2 hours before reservation'}</li>
              <li>• Dress code: {restaurant.dress_code || 'Smart casual'}</li>
              <li>• Outside food and beverages are not permitted</li>
            </ul>
          </div>

          {/* Footer */}
          <div className="mt-6 pt-6 border-t border-gray-200 flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="text-xs text-gray-500 text-center md:text-left">
              <p className="font-semibold mb-1">Need Help?</p>
              <p>📞 1800-123-DINE (3463)</p>
              <p>📧 dining@wanderlite.com</p>
            </div>
            <div className="text-center md:text-right text-xs text-gray-400">
              <p>WanderLite Dining Services</p>
              <p>Making every meal memorable</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default RestaurantBooking;
