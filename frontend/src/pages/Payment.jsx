import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { CheckCircle, IndianRupee, Mail, Phone, User } from 'lucide-react';

const Payment = () => {
  const navigate = useNavigate();
  const location = useLocation();
  let booking = location.state?.booking;
  const bookingId = location.state?.bookingId;
  const bookingRef = location.state?.bookingRef;
  const amount = location.state?.amount;
  const serviceType = location.state?.serviceType;
  const serviceDetails = location.state?.serviceDetails;

  const [form, setForm] = useState({
    fullName: '',
    email: '',
    phone: '',
    method: 'Card',
    credential: '', // Card Number or UPI ID or Wallet ID
  });
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [fullBooking, setFullBooking] = useState(booking);

  const paymentAmount = useMemo(() => {
    if (amount) return amount; // Service booking amount
    if (fullBooking) return fullBooking.amount || fullBooking.total_price || 0; // Old trip booking amount
    return 0;
  }, [amount, fullBooking]);

  useEffect(() => {
    if (!booking && !bookingId) {
      // If user navigates directly without booking, redirect to Explore
      navigate('/explore');
      return;
    }

    // Fetch complete booking details if we only have bookingId
    if (bookingId && !booking) {
      const fetchBooking = async () => {
        try {
          const { data } = await api.get(`/api/bookings/${bookingId}`);
          setFullBooking(data);
        } catch (err) {
          console.error('Failed to fetch booking details:', err);
        }
      };
      fetchBooking();
    }
  }, [booking, bookingId, navigate]);

  const handleChange = (field) => (e) => {
    const value = e?.target ? e.target.value : e; // handles Select
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const validate = () => {
    if (!form.fullName.trim()) return 'Please enter full name';
    if (!form.email.trim() || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)) return 'Please enter a valid email';
    if (!form.phone.trim() || form.phone.length < 10) return 'Please enter a valid phone number';
    if (!form.credential.trim()) return `Please enter ${form.method === 'Card' ? 'Card Number' : form.method === 'UPI' ? 'UPI ID' : 'Wallet ID'}`;
    return null;
  };

  const maskCredential = (value) => {
    if (form.method === 'Card') {
      const digits = value.replace(/\D/g, '');
      if (digits.length <= 4) return digits;
      return `${'*'.repeat(Math.max(0, digits.length - 4))}${digits.slice(-4)}`;
    }
    // For UPI/Wallet just partially mask username part
    const [id, domain] = value.split('@');
    if (!domain) return value.length <= 2 ? value : `${value.slice(0, 2)}***`;
    return `${id.slice(0, 2)}***@${domain}`;
  };

  const handlePayNow = async (e) => {
    e.preventDefault();
    const err = validate();
    if (err) {
      alert(err);
      return;
    }
    setSubmitting(true);

    // Try backend receipt generation first
    try {
      // Helpers to safely serialize optional dates to ISO 8601 (omit if invalid)
      const toIso = (val) => {
        if (!val) return undefined;
        const d = new Date(val);
        return Number.isNaN(d.getTime()) ? undefined : d.toISOString();
      };

      const prune = (obj) => Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== undefined && v !== ''));

      // Prepare payload for service bookings or trip bookings
      const payload = bookingRef ? prune({
        // Service booking (flight/hotel/restaurant)
        booking_ref: bookingRef,
        destination: serviceDetails?.destination || '',
        start_date: toIso(serviceDetails?.checkIn || serviceDetails?.travelDate || serviceDetails?.reservationDate),
        end_date: toIso(serviceDetails?.checkOut),
        travelers: serviceDetails?.travelers || serviceDetails?.guests || 1,
        full_name: form.fullName,
        email: form.email,
        phone: form.phone,
        method: form.method,
        credential: form.credential,
        amount: Number(paymentAmount) || 0,
      }) : prune({
        // Old trip booking format
        booking_ref: fullBooking?.booking_ref || booking?.booking_ref,
        destination: fullBooking?.destination || booking?.destination,
        start_date: toIso(fullBooking?.start_date || booking?.start_date),
        end_date: toIso(fullBooking?.end_date || booking?.end_date),
        travelers: fullBooking?.travelers || booking?.travelers,
        full_name: form.fullName,
        email: form.email,
        phone: form.phone,
        method: form.method,
        credential: form.credential,
        amount: Number(paymentAmount) || 0,
      });

  const res = await api.post('/api/payment/confirm', payload);
      setSuccess(true);
      setSubmitting(false);
      navigate('/receipt', { 
        state: { 
          receiptUrl: res.data.receipt_url, 
          ticketUrl: res.data.ticket_url,
          bookingRef: res.data.booking_ref, 
          booking: {
            ...fullBooking,
            ...booking,
            booking_ref: res.data.booking_ref,
            service_details: serviceDetails, // Ensure full service details are passed
            service_type: serviceType
          },
          payer: { ...form },
          payment: res.data,
          serviceType,
          serviceDetails
        } 
      });
      return;
    } catch (err) {
      console.error('Payment confirm failed:', err?.response?.status, err?.response?.data || err?.message);
      setSubmitting(false);
      alert(`Payment failed to confirm on server. ${err?.response?.data?.detail || ''}`.trim());
      return;
    }
  };

  const methodLabel = form.method === 'Card' ? 'Card Number' : form.method === 'UPI' ? 'UPI ID' : 'Wallet ID';
  const methodPlaceholder = form.method === 'Card' ? '1234-5678-9012-3456' : form.method === 'UPI' ? 'name@upi' : 'Paytm / PhonePe ID';

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8 text-center space-y-2">
          <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-[#0077b6] to-[#48cae4] bg-clip-text text-transparent">Payment</h1>
          <p className="text-gray-600">Securely complete your booking payment</p>
        </div>

        {/* Summary Card */}
        {(booking || bookingRef) && (
          <Card className="mb-8 p-6 bg-gradient-to-br from-blue-50 to-cyan-50 border-0">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {serviceType && (
                <div>
                  <p className="text-sm text-gray-600">Service Type</p>
                  <p className="text-lg font-bold text-[#0077b6]">{serviceType}</p>
                </div>
              )}
              <div>
                <p className="text-sm text-gray-600">Booking Ref</p>
                <p className="text-lg font-bold text-[#0077b6]">{bookingRef || booking?.booking_ref}</p>
              </div>
              {(serviceDetails?.destination || booking?.destination) && (
                <div>
                  <p className="text-sm text-gray-600">Destination</p>
                  <p className="font-semibold">{serviceDetails?.destination || booking?.destination}</p>
                </div>
              )}
              {(serviceDetails?.checkIn || booking?.start_date) && (
                <div>
                  <p className="text-sm text-gray-600">
                    {serviceType === 'Hotel' ? 'Check-in / Check-out' : 
                     serviceType === 'Restaurant' ? 'Reservation Date' : 
                     'Travel Date'}
                  </p>
                  <p className="font-semibold">
                    {serviceType === 'Hotel' 
                      ? `${serviceDetails?.checkIn} to ${serviceDetails?.checkOut}`
                      : serviceType === 'Restaurant'
                      ? `${serviceDetails?.reservationDate} at ${serviceDetails?.timeSlot}`
                      : serviceType === 'Flight'
                      ? serviceDetails?.travelDate
                      : `${booking?.start_date ? new Date(booking.start_date).toLocaleDateString() : '-'} to ${booking?.end_date ? new Date(booking.end_date).toLocaleDateString() : '-'}`
                    }
                  </p>
                </div>
              )}
              <div>
                <p className="text-sm text-gray-600">Amount</p>
                <p className="text-[#0077b6] font-bold text-lg">₹{Number(paymentAmount).toLocaleString()}</p>
              </div>
            </div>
          </Card>
        )}

        {/* Payment Form */}
        <Card className="p-6 space-y-5">
          <form onSubmit={handlePayNow} className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="space-y-2">
                <Label className="flex items-center gap-2"><User className="w-4 h-4 text-[#0077b6]" /> Full Name</Label>
                <Input value={form.fullName} onChange={handleChange('fullName')} placeholder="John Doe" />
              </div>
              <div className="space-y-2">
                <Label className="flex items-center gap-2"><Mail className="w-4 h-4 text-[#0077b6]" /> Email</Label>
                <Input value={form.email} onChange={handleChange('email')} placeholder="john@gmail.com" />
              </div>
              <div className="space-y-2">
                <Label className="flex items-center gap-2"><Phone className="w-4 h-4 text-[#0077b6]" /> Phone Number</Label>
                <Input type="tel" value={form.phone} onChange={handleChange('phone')} placeholder="9876543210" />
              </div>
              <div className="space-y-2">
                <Label>Payment Method</Label>
                <Select value={form.method} onValueChange={handleChange('method')}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Card">Card</SelectItem>
                    <SelectItem value="UPI">UPI</SelectItem>
                    <SelectItem value="Wallet">Wallet</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>{methodLabel}</Label>
              <Input value={form.credential} onChange={handleChange('credential')} placeholder={methodPlaceholder} />
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2"><IndianRupee className="w-4 h-4 text-[#0077b6]" /> Amount</Label>
              <Input readOnly value={`₹${Number(amount).toLocaleString()}`} />
            </div>

            <div className="pt-2">
              <Button type="submit" disabled={submitting} className="w-full h-12 bg-gradient-to-r from-[#0077b6] to-[#48cae4] text-white text-lg font-semibold rounded-lg">
                {submitting ? 'Processing…' : 'Pay Now'}
              </Button>
            </div>
          </form>

          {success && (
            <div className="mt-6 p-4 rounded-lg border border-green-200 bg-green-50 flex items-start gap-3">
              <CheckCircle className="w-6 h-6 text-green-600 mt-0.5" />
              <div>
                <p className="font-semibold text-green-700">Payment Successful</p>
                <p className="text-sm text-green-700/80">Your payment has been confirmed. A PDF receipt has been downloaded.</p>
              </div>
            </div>
          )}
        </Card>

        <div className="mt-6 flex gap-3">
          <Button variant="outline" onClick={() => navigate('/explore')}>Back to Explore</Button>
          <Button onClick={() => navigate('/')}>Go Home</Button>
        </div>
      </div>
    </div>
  );
};

export default Payment;
