import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { MapPin, Calendar, Users, IndianRupee, Download, XCircle, CheckCircle2, Clock, ListChecks } from 'lucide-react';

const TripHistory = () => {
  const navigate = useNavigate();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('all');
  const [updatingStatus, setUpdatingStatus] = useState(null);

  useEffect(() => {
    fetchBookings();
    const interval = setInterval(fetchBookings, 15000);
    return () => clearInterval(interval);
  }, []);

  const sampleBookings = () => {
    const now = new Date();
    return [
      {
        id: 1001,
        booking_ref: 'WL-SAMPLE-ABCD',
        service_type: 'Flight',
        destination: 'Paris, France',
        travelers: 2,
        amount: 1200,
        total_price: 1200,
        status: 'Confirmed',
        created_at: new Date(now.getTime() - 1000 * 60 * 60 * 24).toISOString(),
        service_details: {
          flight: {
            airline: 'WanderLite',
            flight_number: 'WL1285',
            to: 'Paris',
            from: 'Bengaluru',
            departure_time: now.toISOString(),
          },
        },
      },
      {
        id: 1002,
        booking_ref: 'WL-SAMPLE-EFGH',
        service_type: 'Hotel',
        destination: 'Goa, India',
        travelers: 3,
        amount: 650,
        total_price: 650,
        status: 'Completed',
        created_at: new Date(now.getTime() - 1000 * 60 * 60 * 48).toISOString(),
        service_details: {
          hotel: {
            name: 'Seaside Resort',
          },
          check_in: '2025-12-20',
          check_out: '2025-12-23',
        },
      },
      {
        id: 1003,
        booking_ref: 'WL-SAMPLE-IJKL',
        service_type: 'Restaurant',
        destination: 'Tokyo, Japan',
        travelers: 1,
        amount: 90,
        total_price: 90,
        status: 'Cancelled',
        created_at: new Date(now.getTime() - 1000 * 60 * 60 * 3).toISOString(),
        service_details: {
          restaurant: { name: 'Sushi Zen' },
          date: '2025-12-22',
          time: '19:30',
        },
      },
    ];
  };

  const fetchBookings = async () => {
    try {
      const response = await api.get('/api/bookings');
      const data = response.data || [];
      if (Array.isArray(data) && data.length > 0) {
        setBookings(data);
      } else {
        setBookings(sampleBookings());
      }
    } catch (error) {
      console.error('Failed to fetch bookings:', error);
      setBookings(sampleBookings());
    } finally {
      setLoading(false);
    }
  };

  const handleStatusUpdate = async (bookingId, newStatus) => {
    if (newStatus === 'Cancelled' && !window.confirm('Are you sure you want to cancel this booking?')) return;
    
    setUpdatingStatus(bookingId);
    try {
      await api.put(`/api/bookings/${bookingId}/status`, { status: newStatus });
      setBookings((prev) =>
        prev.map((b) => (b.id === bookingId ? { ...b, status: newStatus } : b))
      );
    } catch (error) {
      console.error('Failed to update status:', error);
      alert('Failed to update booking status. Please try again.');
    } finally {
      setUpdatingStatus(null);
    }
  };

  const viewETicket = async (booking) => {
    let payment = null;
    try {
      const { data } = await api.get(`/api/payment/receipt/${booking.booking_ref}`);
      payment = data || null;
    } catch (err) {
      // Optional: payment may not exist yet; proceed without it
      console.debug('No payment info for booking', booking.booking_ref);
    }

    const details = typeof booking.service_details === 'string'
      ? (() => { try { return JSON.parse(booking.service_details); } catch { return {}; } })()
      : booking.service_details || {};

    // Create passenger object from booking data
    const passenger = {
      fullName: payment?.full_name || 'Traveler',
      email: payment?.email || 'traveler@wanderlite.com',
      phone: payment?.phone || '+91 XXXXX-XXXXX',
      idType: 'Aadhaar',
      idNumber: '1234567890',
      seatNumber: details.flight?.seat || '12A'
    };

    navigate('/ticket', {
      state: {
        booking: booking,
        passenger: passenger,
        payment: payment,
        serviceType: booking.service_type,
      },
    });
  };

  const getStatusBadge = (status) => {
    const styles = {
      Confirmed: 'bg-green-100 text-green-700 border-green-200',
      Cancelled: 'bg-red-100 text-red-700 border-red-200',
      Completed: 'bg-blue-100 text-blue-700 border-blue-200',
    };
    const icons = {
      Confirmed: CheckCircle2,
      Cancelled: XCircle,
      Completed: Clock,
    };
    const effective = status || 'Confirmed';
    const Icon = icons[effective] || CheckCircle2;
    return (
      <Badge className={`${styles[effective] || ''} flex items-center gap-1`}>
        <Icon className="w-3 h-3" />
        {effective}
      </Badge>
    );
  };

  const filterBookings = (status) => {
    if (status === 'all') return bookings;
    return bookings.filter((b) => b.status === status);
  };

  const filteredBookings = filterBookings(activeTab);

  const renderBookingCard = (booking) => {
    const status = booking.status || 'Confirmed';
    return (
    <Card key={booking.id} className="p-6 hover:shadow-xl transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-xl font-bold text-gray-900">{booking.destination}</h3>
          <p className="text-sm text-gray-500 mt-1">{booking.booking_ref}</p>
        </div>
  {getStatusBadge(status)}
      </div>

      <div className="space-y-3 mb-4">
        <div className="flex items-center gap-2 text-gray-700">
          <Calendar className="w-4 h-4 text-[#0077b6]" />
          <span className="text-sm">
            {booking.start_date ? new Date(booking.start_date).toLocaleDateString() : '-'} to{' '}
            {booking.end_date ? new Date(booking.end_date).toLocaleDateString() : '-'}
          </span>
        </div>

        <div className="flex items-center gap-2 text-gray-700">
          <Users className="w-4 h-4 text-[#0077b6]" />
          <span className="text-sm">
            {booking.travelers} {booking.travelers === 1 ? 'Traveler' : 'Travelers'}
          </span>
        </div>

        {booking.package_type && (
          <div className="flex items-center gap-2 text-gray-700">
            <MapPin className="w-4 h-4 text-[#0077b6]" />
            <span className="text-sm">{booking.package_type}</span>
          </div>
        )}

        <div className="flex items-center gap-2 text-gray-700 pt-2 border-t">
          <IndianRupee className="w-4 h-4 text-[#0077b6]" />
          <span className="text-lg font-bold text-[#0077b6]">
            ₹{Number(booking.total_price || 0).toLocaleString()}
          </span>
        </div>

        <div className="text-xs text-gray-500 pt-2">
          Booked on {new Date(booking.created_at).toLocaleDateString()}
        </div>
      </div>

      <div className="flex gap-2 pt-3 border-t">
        <Button
          size="sm"
          variant="outline"
          onClick={() => viewETicket(booking)}
          className="flex-1 border-[#0077b6] text-[#0077b6] hover:bg-[#0077b6] hover:text-white"
        >
          <Download className="w-4 h-4 mr-2" />
          View E-Ticket
        </Button>

        <Button
          size="sm"
          variant="outline"
          onClick={() => navigate(`/checklist?booking_id=${booking.id}`)}
          className="flex-1 border-purple-500 text-purple-600 hover:bg-purple-500 hover:text-white"
        >
          <ListChecks className="w-4 h-4 mr-2" />
          Checklist
        </Button>

        {status === 'Confirmed' && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleStatusUpdate(booking.id, 'Cancelled')}
            disabled={updatingStatus === booking.id}
            className="flex-1 border-red-500 text-red-500 hover:bg-red-500 hover:text-white"
          >
            <XCircle className="w-4 h-4 mr-2" />
            Cancel Trip
          </Button>
        )}

        {status === 'Confirmed' && (
          <Button
            size="sm"
            onClick={() => handleStatusUpdate(booking.id, 'Completed')}
            disabled={updatingStatus === booking.id}
            className="flex-1 bg-gradient-to-r from-green-600 to-emerald-500"
          >
            Mark Complete
          </Button>
        )}
      </div>
    </Card>
  ); };

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-[#0077b6] to-[#48cae4] bg-clip-text text-transparent mb-2">
            Trip History & E-Ticket Center
          </h1>
          <p className="text-gray-600">Manage your bookings and download e-tickets</p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="mb-8">
          <TabsList className="grid grid-cols-4 w-full max-w-2xl">
            <TabsTrigger value="all">All Trips</TabsTrigger>
            <TabsTrigger value="Confirmed">Confirmed</TabsTrigger>
            <TabsTrigger value="Completed">Completed</TabsTrigger>
            <TabsTrigger value="Cancelled">Cancelled</TabsTrigger>
          </TabsList>

          {loading ? (
            <div className="flex justify-center items-center py-20">
              <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-[#0077b6]"></div>
            </div>
          ) : (
            <>
              <TabsContent value="all" className="mt-8">
                {filteredBookings.length === 0 ? (
                  <Card className="p-12 text-center">
                    <p className="text-gray-600 text-lg mb-4">No bookings found</p>
                    <Button onClick={() => navigate('/explore')} className="bg-gradient-to-r from-[#0077b6] to-[#48cae4]">
                      Explore Destinations
                    </Button>
                  </Card>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredBookings.map(renderBookingCard)}
                  </div>
                )}
              </TabsContent>

              <TabsContent value="Confirmed" className="mt-8">
                {filteredBookings.length === 0 ? (
                  <Card className="p-12 text-center">
                    <CheckCircle2 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-600 text-lg mb-4">No confirmed bookings</p>
                  </Card>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredBookings.map(renderBookingCard)}
                  </div>
                )}
              </TabsContent>

              <TabsContent value="Completed" className="mt-8">
                {filteredBookings.length === 0 ? (
                  <Card className="p-12 text-center">
                    <Clock className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-600 text-lg mb-4">No completed trips</p>
                  </Card>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredBookings.map(renderBookingCard)}
                  </div>
                )}
              </TabsContent>

              <TabsContent value="Cancelled" className="mt-8">
                {filteredBookings.length === 0 ? (
                  <Card className="p-12 text-center">
                    <XCircle className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-600 text-lg mb-4">No cancelled bookings</p>
                  </Card>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredBookings.map(renderBookingCard)}
                  </div>
                )}
              </TabsContent>
            </>
          )}
        </Tabs>
      </div>
    </div>
  );
};

export default TripHistory;
