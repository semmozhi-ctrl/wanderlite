import React, { useState, useEffect } from 'react';
import { destinations as mockDestinations, mockWeather } from '../data/mock';
import axios from 'axios';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { MapPin, Cloud, Droplets, Calendar, Activity, X, Search } from 'lucide-react';

const Explore = () => {
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedDestination, setSelectedDestination] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [destinations, setDestinations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const categories = ['All', 'Beach', 'Heritage'];

  useEffect(() => {
    const fetchDestinations = async () => {
      try {
        const response = await axios.get('/api/destinations');
        setDestinations(response.data);
      } catch (error) {
        console.error('Error fetching destinations:', error);
        // Fallback to mock data
        setDestinations(mockDestinations);
      } finally {
        setLoading(false);
      }
    };

    fetchDestinations();
  }, []);

  const filteredDestinations = destinations.filter((dest) => {
    const matchesCategory = selectedCategory === 'All' || dest.category === selectedCategory;
    const matchesSearch = dest.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         dest.shortDescription.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         dest.attractions.some(attr => attr.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  const openModal = (destination) => {
    setSelectedDestination(destination);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setTimeout(() => setSelectedDestination(null), 300);
  };

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12 space-y-4">
          <h1 className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-[#0077b6] to-[#48cae4] bg-clip-text text-transparent">
            Explore Destinations
          </h1>
          <p className="text-gray-600 text-lg max-w-2xl mx-auto">
            Discover your next adventure from our handpicked collection of stunning destinations
          </p>
        </div>

        {/* Search and Filter Bar */}
        <div className="mb-12 space-y-6">
          {/* Search Bar */}
          <div className="flex justify-center">
            <div className="relative w-full max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <Input
                type="text"
                placeholder="Search destinations, attractions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-4 py-3 rounded-full border-2 border-[#0077b6]/20 focus:border-[#0077b6] focus:ring-0"
              />
            </div>
          </div>

          {/* Filter Buttons */}
          <div className="flex flex-wrap justify-center gap-3">
            {categories.map((category) => (
              <Button
                key={category}
                onClick={() => setSelectedCategory(category)}
                variant={selectedCategory === category ? 'default' : 'outline'}
                className={`px-6 py-2 rounded-full font-medium transition-all duration-300 ${
                  selectedCategory === category
                    ? 'bg-gradient-to-r from-[#0077b6] to-[#48cae4] text-white shadow-lg scale-105'
                    : 'border-2 border-[#0077b6] text-[#0077b6] hover:bg-[#0077b6] hover:text-white'
                }`}
              >
                {category}
              </Button>
            ))}
          </div>
        </div>

        {/* Destination Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {filteredDestinations.map((destination) => {
            const weather = mockWeather[destination.name];
            return (
              <Card
                key={destination.id}
                className="overflow-hidden group cursor-pointer border-0 shadow-lg hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-2"
                onClick={() => openModal(destination)}
              >
                <div className="relative h-64 overflow-hidden">
                  <img
                    src={destination.image}
                    alt={destination.name}
                    className="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-500"
                  />
                  <div className="absolute top-4 right-4">
                    <Badge className="bg-white/95 text-[#0077b6] font-semibold px-3 py-1">
                      {destination.category}
                    </Badge>
                  </div>
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
                </div>
                <div className="p-6 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-2xl font-bold text-gray-800 mb-1">
                        {destination.name}
                      </h3>
                      <p className="text-gray-600">{destination.shortDescription}</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between pt-2">
                    <div className="flex items-center space-x-2 text-sm text-gray-500">
                      <Cloud className="w-4 h-4" />
                      <span>
                        {weather.temp}°C · {weather.condition}
                      </span>
                    </div>
                    <Button
                      size="sm"
                      className="bg-gradient-to-r from-[#0077b6] to-[#48cae4] hover:from-[#005f8f] hover:to-[#3ab5d9] text-white rounded-full"
                    >
                      View Details
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Destination Details Modal */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {selectedDestination && (
            <div className="space-y-6">
              {/* Header Image */}
              <div className="relative -m-6 mb-0 h-64 overflow-hidden rounded-t-lg">
                <img
                  src={selectedDestination.image}
                  alt={selectedDestination.name}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                <DialogTitle className="absolute bottom-4 left-6 text-3xl font-bold text-white">
                  {selectedDestination.name}
                </DialogTitle>
              </div>

              <DialogDescription className="text-gray-700 text-base leading-relaxed">
                {selectedDestination.description}
              </DialogDescription>

              {/* Weather & Best Time */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="p-4 bg-gradient-to-br from-blue-50 to-cyan-50 border-0">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-white rounded-lg">
                      <Cloud className="w-5 h-5 text-[#0077b6]" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 font-medium">Current Weather</p>
                      <p className="text-lg font-bold text-gray-800">
                        {mockWeather[selectedDestination.name]?.temp}°C ·{' '}
                        {mockWeather[selectedDestination.name]?.condition}
                      </p>
                    </div>
                  </div>
                </Card>
                <Card className="p-4 bg-gradient-to-br from-green-50 to-emerald-50 border-0">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-white rounded-lg">
                      <Calendar className="w-5 h-5 text-[#0077b6]" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 font-medium">Best Time to Visit</p>
                      <p className="text-lg font-bold text-gray-800">
                        {selectedDestination.bestTime}
                      </p>
                    </div>
                  </div>
                </Card>
              </div>

              {/* Top Attractions */}
              <div>
                <div className="flex items-center space-x-2 mb-3">
                  <MapPin className="w-5 h-5 text-[#0077b6]" />
                  <h3 className="text-xl font-bold text-gray-800">Top Attractions</h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  {selectedDestination.attractions.map((attraction, index) => (
                    <Badge
                      key={index}
                      variant="secondary"
                      className="px-3 py-1 bg-gradient-to-r from-[#0077b6]/10 to-[#48cae4]/10 text-[#0077b6] border border-[#0077b6]/20"
                    >
                      {attraction}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Activities */}
              <div>
                <div className="flex items-center space-x-2 mb-3">
                  <Activity className="w-5 h-5 text-[#0077b6]" />
                  <h3 className="text-xl font-bold text-gray-800">Popular Activities</h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  {selectedDestination.activities.map((activity, index) => (
                    <Badge
                      key={index}
                      variant="outline"
                      className="px-3 py-1 border-[#48cae4] text-[#0077b6]"
                    >
                      {activity}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Explore;