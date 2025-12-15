import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { MapPin, Calendar, Users, IndianRupee, Trash2 } from 'lucide-react';

const MyBookings = () => {
  const navigate = useNavigate();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(null);

  useEffect(() => {
    const fetchBookings = async () => {
      try {
        const response = await api.get('/api/bookings');
        setBookings(response.data || []);
      } catch (error) {
        console.error('Failed to fetch bookings:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchBookings();
  }, []);

  const handleDelete = async (bookingId) => {
    if (!window.confirm('Are you sure you want to cancel this booking?')) return;
    setDeleting(bookingId);
    try {
      await api.delete(`/api/bookings/${bookingId}`);
      setBookings((prev) => prev.filter((b) => b.id !== bookingId));
    } catch (error) {
      console.error('Failed to cancel booking:', error);
      alert('Failed to cancel booking. Please try again.');
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-[#0077b6] to-[#48cae4] bg-clip-text text-transparent mb-2">
            My Bookings
          </h1>
          <p className="text-gray-600">View and manage your travel bookings</p>
        </div>

        {loading && (
          <div className="flex justify-center items-center py-20">
            <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-[#0077b6]"></div>
          </div>
        )}

        {!loading && bookings.length === 0 && (
          <Card className="p-12 text-center">
            <p className="text-gray-600 text-lg mb-4">No bookings found</p>
            <Button onClick={() => navigate('/explore')} className="bg-gradient-to-r from-[#0077b6] to-[#48cae4]">
              Explore Destinations
            </Button>
          </Card>
        )}

        {!loading && bookings.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {bookings.map((booking) => (
              <Card key={booking.id} className="p-6 hover:shadow-lg transition-shadow">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-xl font-bold text-gray-900">{booking.destination}</h3>
                    <Badge className="mt-2 bg-green-100 text-green-700 border-green-200">
                      {booking.booking_ref}
                    </Badge>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(booking.id)}
                    disabled={deleting === booking.id}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-gray-700">
                    <Calendar className="w-4 h-4 text-[#0077b6]" />
                    <span className="text-sm">
                      {booking.start_date ? new Date(booking.start_date).toLocaleDateString() : '-'} to{' '}
                      {booking.end_date ? new Date(booking.end_date).toLocaleDateString() : '-'}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-gray-700">
                    <Users className="w-4 h-4 text-[#0077b6]" />
                    <span className="text-sm">{booking.travelers} {booking.travelers === 1 ? 'Traveler' : 'Travelers'}</span>
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
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MyBookings;
