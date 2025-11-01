import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import axios from 'axios';
import { MapPin, Calendar, DollarSign, Plus, Trash2, Edit, Upload, Camera } from 'lucide-react';
import { Link } from 'react-router-dom';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedTrip, setSelectedTrip] = useState(null);

  useEffect(() => {
    fetchTrips();
  }, []);

  const fetchTrips = async () => {
    try {
      const response = await axios.get('/api/trips');
      setTrips(response.data);
    } catch (error) {
      console.error('Error fetching trips:', error);
    } finally {
      setLoading(false);
    }
  };

  const deleteTrip = async (tripId) => {
    if (window.confirm('Are you sure you want to delete this trip?')) {
      try {
        await axios.delete(`/api/trips/${tripId}`);
        setTrips(trips.filter(trip => trip.id !== tripId));
      } catch (error) {
        console.error('Error deleting trip:', error);
      }
    }
  };

  const handleImageUpload = async (event, tripId) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    setSelectedTrip(tripId);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('/api/upload/image', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      // Update the trip with the new image URL
      const imageUrl = response.data.image_url;
      await axios.put(`/api/trips/${tripId}`, {
        images: [...(trips.find(t => t.id === tripId)?.images || []), imageUrl]
      });

      // Refresh trips to show the new image
      fetchTrips();
    } catch (error) {
      console.error('Error uploading image:', error);
      alert('Failed to upload image. Please try again.');
    } finally {
      setUploading(false);
      setSelectedTrip(null);
    }
  };

  const getCurrencySymbol = (currency) => {
    const symbols = { USD: '$', EUR: '€', GBP: '£', INR: '₹', JPY: '¥', AED: 'AED' };
    return symbols[currency] || currency;
  };

  if (loading) {
    return (
      <div className="min-h-screen pt-24 pb-16 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0077b6] mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your trips...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-[#0077b6] to-[#48cae4] bg-clip-text text-transparent">
                My Dashboard
              </h1>
              <p className="text-gray-600 mt-2">Manage your travel plans and memories</p>
            </div>
            <div className="flex space-x-4">
              <Link to="/planner">
                <Button className="bg-gradient-to-r from-[#0077b6] to-[#48cae4] hover:from-[#005f8f] hover:to-[#3ab5d9] text-white">
                  <Plus className="w-4 h-4 mr-2" />
                  Plan New Trip
                </Button>
              </Link>
              <Button variant="outline" onClick={logout}>
                Logout
              </Button>
            </div>
          </div>
        </div>

        {/* Trips Grid */}
        {trips.length === 0 ? (
          <Card className="p-12 text-center border-0 shadow-lg">
            <div className="space-y-4">
              <div className="w-16 h-16 bg-gradient-to-r from-[#0077b6] to-[#48cae4] rounded-full flex items-center justify-center mx-auto">
                <MapPin className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-gray-800">No trips yet</h3>
              <p className="text-gray-600">Start planning your first adventure!</p>
              <Link to="/planner">
                <Button className="bg-gradient-to-r from-[#0077b6] to-[#48cae4] hover:from-[#005f8f] hover:to-[#3ab5d9] text-white">
                  <Plus className="w-4 h-4 mr-2" />
                  Create Your First Trip
                </Button>
              </Link>
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {trips.map((trip) => (
              <Card key={trip.id} className="overflow-hidden border-0 shadow-lg hover:shadow-xl transition-shadow duration-300">
                <div className="p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-xl font-bold text-gray-800 mb-1">{trip.destination}</h3>
                      <div className="flex items-center space-x-4 text-sm text-gray-600">
                        <div className="flex items-center space-x-1">
                          <Calendar className="w-4 h-4" />
                          <span>{trip.days} days</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <DollarSign className="w-4 h-4" />
                          <span>{getCurrencySymbol(trip.currency)}{trip.total_cost}</span>
                        </div>
                      </div>
                    </div>
                    <Badge variant="secondary" className="bg-[#0077b6]/10 text-[#0077b6]">
                      {trip.budget}
                    </Badge>
                  </div>

                  <div className="space-y-2 mb-4">
                    <h4 className="font-semibold text-gray-700">Itinerary:</h4>
                    <div className="space-y-1 max-h-32 overflow-y-auto">
                      {trip.itinerary.slice(0, 3).map((day, index) => (
                        <div key={index} className="text-sm text-gray-600">
                          <span className="font-medium">Day {day.day}:</span> {day.activities.substring(0, 50)}...
                        </div>
                      ))}
                      {trip.itinerary.length > 3 && (
                        <div className="text-sm text-gray-500">+{trip.itinerary.length - 3} more days</div>
                      )}
                    </div>
                  </div>

                  {/* Images Section */}
                  {trip.images && trip.images.length > 0 && (
                    <div className="mb-4">
                      <h4 className="font-semibold text-gray-700 mb-2">Trip Photos:</h4>
                      <div className="grid grid-cols-2 gap-2">
                        {trip.images.slice(0, 4).map((image, index) => (
                          <img
                            key={index}
                            src={image}
                            alt={`Trip photo ${index + 1}`}
                            className="w-full h-20 object-cover rounded-lg"
                          />
                        ))}
                        {trip.images.length > 4 && (
                          <div className="w-full h-20 bg-gray-200 rounded-lg flex items-center justify-center text-sm text-gray-600">
                            +{trip.images.length - 4} more
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="flex justify-between items-center pt-4 border-t border-gray-100">
                    <div className="text-xs text-gray-500">
                      Created {new Date(trip.created_at).toLocaleDateString()}
                    </div>
                    <div className="flex space-x-2">
                      <div className="relative">
                        <input
                          type="file"
                          accept="image/*"
                          onChange={(e) => handleImageUpload(e, trip.id)}
                          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                          disabled={uploading}
                        />
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-green-600 border-green-600 hover:bg-green-600 hover:text-white"
                          disabled={uploading && selectedTrip === trip.id}
                        >
                          {uploading && selectedTrip === trip.id ? (
                            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-green-600"></div>
                          ) : (
                            <Camera className="w-3 h-3" />
                          )}
                        </Button>
                      </div>
                      <Button size="sm" variant="outline" className="text-[#0077b6] border-[#0077b6] hover:bg-[#0077b6] hover:text-white">
                        <Edit className="w-3 h-3" />
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-red-600 border-red-600 hover:bg-red-600 hover:text-white"
                        onClick={() => deleteTrip(trip.id)}
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
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

export default Dashboard;
