import React from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { Plane, Calendar, Clock, User, CreditCard, Luggage, MapPin } from 'lucide-react';
import { Card } from '../ui/card';
import { getPublicBaseUrl } from '../../services/publicUrl';

const FlightTicket = ({ booking, passenger, payment }) => {
  // Parse service_details if it's a string
  const serviceDetails = typeof booking?.service_details === 'string'
    ? (() => { try { return JSON.parse(booking.service_details); } catch { return {}; } })()
    : booking?.service_details || {};
  
  const flight = serviceDetails.flight || serviceDetails;
  const pnr = booking?.booking_ref || 'N/A';
  const ticketNumber = `WL-${Date.now().toString().slice(-8)}`;
  
  // QR Code data - Simple URL that opens ticket when scanned
  // Uses IP address if available for cross-device scanning
  const baseUrl = getPublicBaseUrl();
  const qrData = `${baseUrl}/ticket/verify?pnr=${pnr}`;

  const formatTime = (dateStr) => {
    if (!dateStr) return '--:--';
    try {
      return new Date(dateStr).toLocaleTimeString('en-IN', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
      });
    } catch {
      return '--:--';
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'DD MMM YYYY';
    try {
      return new Date(dateStr).toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      });
    } catch {
      return 'DD MMM YYYY';
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
      <Card className="overflow-hidden shadow-2xl border-0">
        {/* Header with airline branding */}
        <div className="bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-700 p-6 text-white">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center">
                <Plane className="w-8 h-8 text-blue-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-wide">WanderLite Airlines</h1>
                <p className="text-blue-100 text-sm">Your Journey, Our Priority</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-blue-200">Flight Number</p>
              <p className="text-2xl font-bold">{flight.flight_number || 'WL1001'}</p>
            </div>
          </div>
        </div>

        {/* Boarding Pass Status */}
        <div className="bg-green-50 border-l-4 border-green-500 px-6 py-3">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-green-800 font-semibold text-sm">BOOKING CONFIRMED</span>
          </div>
        </div>

        <div className="p-8 bg-gradient-to-br from-gray-50 to-white">
          {/* Route Information - Large & Prominent */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <div className="flex-1">
                <p className="text-xs text-gray-500 mb-1">FROM</p>
                <p className="text-3xl font-bold text-gray-900">{flight.from || flight.origin || 'BLR'}</p>
                <p className="text-sm text-gray-600 mt-1">{booking?.destination || flight.origin || 'Bengaluru'}</p>
              </div>

              <div className="flex-1 flex flex-col items-center px-4">
                <div className="flex items-center gap-2 text-gray-400 mb-2">
                  <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                  <div className="flex-1 h-px bg-gradient-to-r from-blue-500 to-indigo-500"></div>
                  <Plane className="w-5 h-5 text-blue-600 transform rotate-90" />
                  <div className="flex-1 h-px bg-gradient-to-r from-indigo-500 to-blue-500"></div>
                  <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                </div>
                <p className="text-xs text-gray-500">{flight.duration || '2h 30m'}</p>
                <p className="text-xs text-gray-400">{flight.stops === 0 ? 'Non-stop' : `${flight.stops || 0} Stop${flight.stops > 1 ? 's' : ''}`}</p>
              </div>

              <div className="flex-1 text-right">
                <p className="text-xs text-gray-500 mb-1">TO</p>
                <p className="text-3xl font-bold text-gray-900">{flight.to || flight.destination || 'DEL'}</p>
                <p className="text-sm text-gray-600 mt-1">{booking?.destination || flight.destination || 'Delhi'}</p>
              </div>
            </div>

            {/* Time Details */}
            <div className="grid grid-cols-2 gap-6 mt-6 p-4 bg-white rounded-lg shadow-sm border border-gray-100">
              <div>
                <p className="text-xs text-gray-500 mb-1 flex items-center gap-1">
                  <Calendar className="w-3 h-3" /> DEPARTURE
                </p>
                <p className="text-xl font-bold text-gray-900">{formatTime(flight.departure_time || booking?.start_date)}</p>
                <p className="text-sm text-gray-600">{formatDate(flight.departure_time || booking?.start_date)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1 flex items-center gap-1">
                  <Calendar className="w-3 h-3" /> ARRIVAL
                </p>
                <p className="text-xl font-bold text-gray-900">{formatTime(flight.arrival_time || booking?.end_date)}</p>
                <p className="text-sm text-gray-600">{formatDate(flight.arrival_time || booking?.end_date)}</p>
              </div>
            </div>
          </div>

          {/* Passenger & Seat Information */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <Card className="p-4 border-2 border-blue-100 bg-blue-50/50">
              <p className="text-xs text-gray-600 mb-2 flex items-center gap-1">
                <User className="w-3 h-3" /> PASSENGER NAME
              </p>
              <p className="text-lg font-bold text-gray-900">{passenger?.fullName || 'John Doe'}</p>
              <p className="text-xs text-gray-500 mt-1">{passenger?.idType || 'Aadhaar'}: {passenger?.idNumber ? `****${passenger.idNumber.slice(-4)}` : '****1234'}</p>
            </Card>

            <Card className="p-4 border-2 border-indigo-100 bg-indigo-50/50">
              <p className="text-xs text-gray-600 mb-2">CLASS & SEAT</p>
              <p className="text-lg font-bold text-gray-900">{flight.class || 'Economy'}</p>
              <p className="text-2xl font-bold text-indigo-600 mt-1">{passenger?.seatNumber || '12A'}</p>
            </Card>

            <Card className="p-4 border-2 border-purple-100 bg-purple-50/50">
              <p className="text-xs text-gray-600 mb-2">BOARDING</p>
              <p className="text-sm text-gray-700">Gate: <span className="text-xl font-bold text-purple-600">{flight.gate || 'G15'}</span></p>
              <p className="text-sm text-gray-700 mt-1">Group: <span className="font-semibold">{flight.boarding_group || 'B'}</span> | Zone: <span className="font-semibold">{flight.boarding_zone || '2'}</span></p>
            </Card>
          </div>

          {/* Baggage & Aircraft */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div className="p-4 bg-white rounded-lg shadow-sm border border-gray-100">
              <p className="text-xs text-gray-600 mb-3 flex items-center gap-1">
                <Luggage className="w-4 h-4" /> BAGGAGE ALLOWANCE
              </p>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Cabin</span>
                  <span className="font-semibold text-gray-900">{flight.cabin_baggage || '7 kg'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Check-in</span>
                  <span className="font-semibold text-gray-900">{flight.checkin_baggage || '15 kg'}</span>
                </div>
              </div>
            </div>

            <div className="p-4 bg-white rounded-lg shadow-sm border border-gray-100">
              <p className="text-xs text-gray-600 mb-3">AIRCRAFT & TERMINAL</p>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Aircraft</span>
                  <span className="font-semibold text-gray-900">{flight.aircraft_type || 'Airbus A320'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Terminal</span>
                  <span className="font-semibold text-gray-900">{flight.terminal || 'T2'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Payment & Fare Breakdown */}
          <div className="mb-8 p-6 bg-gradient-to-br from-amber-50 to-yellow-50 rounded-lg border-2 border-amber-200">
            <p className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
              <CreditCard className="w-4 h-4" /> FARE BREAKDOWN
            </p>
            {(() => {
              // Extract fare data from multiple sources
              const totalAmount = parseFloat(booking?.total_price || payment?.amount || booking?.amount || serviceDetails?.total_price || 0);
              
              // Try to get individual fare components from service_details or calculate them
              const baseFare = parseFloat(serviceDetails?.baseFare || serviceDetails?.base_fare || totalAmount * 0.82 || 0);
              const taxes = parseFloat(serviceDetails?.taxes || serviceDetails?.taxes_fees || totalAmount - baseFare || totalAmount * 0.18 || 0);
              const discount = parseFloat(serviceDetails?.discount || payment?.discount || 0);
              
              return (
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Base Fare</span>
                      <span className="font-semibold">₹{baseFare.toFixed(2)}</span>
                    </div>
                    {discount > 0 && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Discount</span>
                        <span className="font-semibold text-green-600">-₹{discount.toFixed(2)}</span>
                      </div>
                    )}
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Taxes & Fees</span>
                      <span className="font-semibold">₹{taxes.toFixed(2)}</span>
                    </div>
                  <div className="flex justify-between text-sm pt-2 border-t border-amber-300">
                      <span className="text-gray-900 font-bold">Total Paid</span>
                      <span className="text-lg font-bold text-green-600">₹{totalAmount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                  </div>
                  <div className="space-y-2 pl-4 border-l border-amber-300">
                    <div className="text-sm">
                      <span className="text-gray-600">Payment Mode:</span>
                      <span className="font-semibold ml-2">{payment?.method || 'Card'}</span>
                    </div>
                    <div className="text-sm">
                      <span className="text-gray-600">Txn ID:</span>
                      <span className="font-mono text-xs ml-2">{payment?.id ? `WL${payment.id}` : 'N/A'}</span>
                    </div>
                    <div className="text-sm">
                      <span className="text-gray-600">Status:</span>
                      <span className="ml-2 px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-semibold">PAID</span>
                    </div>
                  </div>
                </div>
              );
            })()}
          </div>

          {/* QR Code & Booking Reference */}
          <div className="flex items-center justify-between p-6 bg-white rounded-lg shadow-lg border-2 border-gray-200">
            <div className="flex-1">
              <div className="mb-4">
                <p className="text-xs text-gray-500 mb-1">BOOKING REFERENCE (PNR)</p>
                <p className="text-3xl font-bold text-blue-600 tracking-wider font-mono">{pnr}</p>
              </div>
              <div className="mb-4">
                <p className="text-xs text-gray-500 mb-1">E-TICKET NUMBER</p>
                <p className="text-lg font-mono font-semibold text-gray-800">{ticketNumber}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">BOOKED ON</p>
                <p className="text-sm text-gray-700">{formatDate(booking?.created_at)}</p>
              </div>
            </div>

            <div className="flex flex-col items-center ml-8">
              <div className="p-4 bg-white rounded-lg shadow-inner">
                <QRCodeSVG 
                  value={qrData}
                  size={160}
                  level="H"
                  includeMargin={true}
                  imageSettings={{
                    src: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%232563eb'%3E%3Cpath d='M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z'/%3E%3C/svg%3E",
                    height: 24,
                    width: 24,
                    excavate: true,
                  }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-2 text-center">Scan for verification</p>
            </div>
          </div>

          {/* Important Info */}
          <div className="mt-6 p-4 bg-red-50 border-l-4 border-red-500 rounded">
            <p className="text-xs font-semibold text-red-800 mb-2">IMPORTANT INSTRUCTIONS</p>
            <ul className="text-xs text-red-700 space-y-1">
              <li>• Check-in opens 2 hours before departure</li>
              <li>• Carry a valid government-issued photo ID</li>
              <li>• Web check-in is mandatory</li>
              <li>• Reach boarding gate 25 minutes before departure</li>
            </ul>
          </div>

          {/* Footer */}
          <div className="mt-6 pt-6 border-t border-gray-200 flex justify-between items-center">
            <div className="text-xs text-gray-500">
              <p className="font-semibold mb-1">Customer Support</p>
              <p>📞 1800-123-WANDER (92633)</p>
              <p>📧 support@wanderlite.com</p>
            </div>
            <div className="text-right text-xs text-gray-400">
              <p>WanderLite Airlines Pvt. Ltd.</p>
              <p>GSTIN: 29AABCU9603R1ZX</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default FlightTicket;
