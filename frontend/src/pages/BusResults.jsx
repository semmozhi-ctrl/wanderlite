import React, { useState, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Bus,
  Star,
  Clock,
  MapPin,
  Filter,
  ChevronDown,
  ChevronUp,
  Moon,
  Sun,
  Wifi,
  Zap,
  Droplets,
  X,
  ArrowLeft,
  SlidersHorizontal
} from 'lucide-react';

const BusResults = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { results, fromCity, toCity, journeyDate } = location.state || {};

  const [sortBy, setSortBy] = useState('departure');
  const [filters, setFilters] = useState({
    busType: [],
    priceRange: [0, 2000],
    departureTime: [],
    rating: 0,
    amenities: []
  });
  const [showFilters, setShowFilters] = useState(false);
  const [expandedBus, setExpandedBus] = useState(null);

  // Format date for display
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  };

  // Format duration
  const formatDuration = (mins) => {
    const hours = Math.floor(mins / 60);
    const minutes = mins % 60;
    return `${hours}h ${minutes}m`;
  };

  // Get unique bus types
  const busTypes = useMemo(() => {
    if (!results?.buses) return [];
    return [...new Set(results.buses.map(b => b.bus_type))];
  }, [results]);

  // Filter and sort buses
  const filteredBuses = useMemo(() => {
    if (!results?.buses) return [];
    
    let buses = [...results.buses];

    // Apply filters
    if (filters.busType.length > 0) {
      buses = buses.filter(b => filters.busType.includes(b.bus_type));
    }

    if (filters.priceRange) {
      buses = buses.filter(b => 
        b.base_price >= filters.priceRange[0] && 
        b.base_price <= filters.priceRange[1]
      );
    }

    if (filters.departureTime.length > 0) {
      buses = buses.filter(b => {
        const hour = parseInt(b.departure_time.split(':')[0]);
        return filters.departureTime.some(slot => {
          if (slot === 'morning') return hour >= 6 && hour < 12;
          if (slot === 'afternoon') return hour >= 12 && hour < 17;
          if (slot === 'evening') return hour >= 17 && hour < 21;
          if (slot === 'night') return hour >= 21 || hour < 6;
          return false;
        });
      });
    }

    if (filters.rating > 0) {
      buses = buses.filter(b => b.operator_rating >= filters.rating);
    }

    // Apply sorting
    switch (sortBy) {
      case 'price-low':
        buses.sort((a, b) => a.base_price - b.base_price);
        break;
      case 'price-high':
        buses.sort((a, b) => b.base_price - a.base_price);
        break;
      case 'departure':
        buses.sort((a, b) => a.departure_time.localeCompare(b.departure_time));
        break;
      case 'duration':
        buses.sort((a, b) => a.duration_mins - b.duration_mins);
        break;
      case 'rating':
        buses.sort((a, b) => b.operator_rating - a.operator_rating);
        break;
      default:
        break;
    }

    return buses;
  }, [results, filters, sortBy]);

  // Toggle filter
  const toggleFilter = (type, value) => {
    setFilters(prev => {
      const current = prev[type];
      if (Array.isArray(current)) {
        return {
          ...prev,
          [type]: current.includes(value)
            ? current.filter(v => v !== value)
            : [...current, value]
        };
      }
      return { ...prev, [type]: value };
    });
  };

  // Handle bus selection
  const handleSelectBus = (bus) => {
    navigate('/bus-booking', {
      state: {
        bus,
        fromCity,
        toCity,
        journeyDate
      }
    });
  };

  if (!results) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="container mx-auto px-4 py-20 text-center">
          <Bus className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-600 mb-2">No Search Results</h2>
          <p className="text-gray-500 mb-6">Please search for buses first</p>
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-orange-600 to-red-600 text-white py-6">
        <div className="container mx-auto px-4">
          <button
            onClick={() => navigate('/buses')}
            className="flex items-center gap-2 text-orange-100 hover:text-white mb-4 transition"
          >
            <ArrowLeft className="w-4 h-4" />
            Modify Search
          </button>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-3">
              <MapPin className="w-5 h-5" />
              <span className="font-semibold text-lg">{fromCity?.name}</span>
              <span className="text-orange-200">→</span>
              <span className="font-semibold text-lg">{toCity?.name}</span>
            </div>
            <div className="flex items-center gap-2 bg-white/20 px-3 py-1 rounded-full">
              <Clock className="w-4 h-4" />
              <span>{formatDate(journeyDate)}</span>
            </div>
            <div className="ml-auto bg-white/20 px-3 py-1 rounded-full">
              {filteredBuses.length} buses found
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-6">
        <div className="flex flex-col lg:flex-row gap-6">
          
          {/* Filters Sidebar */}
          <div className={`lg:w-72 ${showFilters ? 'block' : 'hidden lg:block'}`}>
            <div className="bg-white rounded-xl shadow-sm p-6 sticky top-4">
              <div className="flex items-center justify-between mb-6">
                <h3 className="font-bold text-gray-800 flex items-center gap-2">
                  <Filter className="w-5 h-5" />
                  Filters
                </h3>
                <button
                  onClick={() => setFilters({
                    busType: [],
                    priceRange: [0, 2000],
                    departureTime: [],
                    rating: 0,
                    amenities: []
                  })}
                  className="text-orange-500 text-sm hover:underline"
                >
                  Clear All
                </button>
              </div>

              {/* Bus Type */}
              <div className="mb-6">
                <h4 className="font-medium text-gray-700 mb-3">Bus Type</h4>
                <div className="space-y-2">
                  {busTypes.map(type => (
                    <label key={type} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.busType.includes(type)}
                        onChange={() => toggleFilter('busType', type)}
                        className="w-4 h-4 text-orange-500 rounded border-gray-300 focus:ring-orange-500"
                      />
                      <span className="text-gray-600 text-sm">{type}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Departure Time */}
              <div className="mb-6">
                <h4 className="font-medium text-gray-700 mb-3">Departure Time</h4>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'morning', label: 'Morning', icon: Sun, sub: '6AM-12PM' },
                    { id: 'afternoon', label: 'Afternoon', icon: Sun, sub: '12PM-5PM' },
                    { id: 'evening', label: 'Evening', icon: Moon, sub: '5PM-9PM' },
                    { id: 'night', label: 'Night', icon: Moon, sub: '9PM-6AM' }
                  ].map(slot => (
                    <button
                      key={slot.id}
                      onClick={() => toggleFilter('departureTime', slot.id)}
                      className={`p-3 rounded-lg border text-center transition ${
                        filters.departureTime.includes(slot.id)
                          ? 'border-orange-500 bg-orange-50 text-orange-600'
                          : 'border-gray-200 hover:border-orange-300'
                      }`}
                    >
                      <slot.icon className="w-4 h-4 mx-auto mb-1" />
                      <p className="text-xs font-medium">{slot.label}</p>
                      <p className="text-xs text-gray-400">{slot.sub}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Rating */}
              <div className="mb-6">
                <h4 className="font-medium text-gray-700 mb-3">Rating</h4>
                <div className="space-y-2">
                  {[4, 3.5, 3].map(rating => (
                    <label key={rating} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="rating"
                        checked={filters.rating === rating}
                        onChange={() => setFilters(prev => ({ ...prev, rating }))}
                        className="w-4 h-4 text-orange-500 border-gray-300 focus:ring-orange-500"
                      />
                      <div className="flex items-center gap-1">
                        <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                        <span className="text-gray-600 text-sm">{rating}+ & above</span>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Price Range */}
              <div>
                <h4 className="font-medium text-gray-700 mb-3">Price Range</h4>
                <div className="flex items-center gap-2">
                  <span className="text-gray-500 text-sm">₹{filters.priceRange[0]}</span>
                  <input
                    type="range"
                    min="0"
                    max="2000"
                    step="100"
                    value={filters.priceRange[1]}
                    onChange={(e) => setFilters(prev => ({
                      ...prev,
                      priceRange: [prev.priceRange[0], parseInt(e.target.value)]
                    }))}
                    className="flex-1 accent-orange-500"
                  />
                  <span className="text-gray-500 text-sm">₹{filters.priceRange[1]}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Results */}
          <div className="flex-1">
            {/* Sort Bar */}
            <div className="bg-white rounded-xl shadow-sm p-4 mb-4 flex flex-wrap items-center gap-4">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="lg:hidden flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg"
              >
                <SlidersHorizontal className="w-4 h-4" />
                Filters
              </button>
              
              <span className="text-gray-600 text-sm">Sort by:</span>
              {[
                { id: 'departure', label: 'Departure' },
                { id: 'duration', label: 'Duration' },
                { id: 'price-low', label: 'Price: Low to High' },
                { id: 'price-high', label: 'Price: High to Low' },
                { id: 'rating', label: 'Rating' }
              ].map(option => (
                <button
                  key={option.id}
                  onClick={() => setSortBy(option.id)}
                  className={`px-3 py-1.5 rounded-full text-sm transition ${
                    sortBy === option.id
                      ? 'bg-orange-500 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-orange-100'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>

            {/* Bus Cards */}
            {filteredBuses.length === 0 ? (
              <div className="bg-white rounded-xl shadow-sm p-12 text-center">
                <Bus className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-600 mb-2">No buses found</h3>
                <p className="text-gray-500">Try adjusting your filters</p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredBuses.map((bus) => (
                  <div key={bus.schedule_id} className="bg-white rounded-xl shadow-sm overflow-hidden hover:shadow-md transition">
                    <div className="p-6">
                      <div className="flex flex-col md:flex-row md:items-center gap-4">
                        {/* Operator Info */}
                        <div className="md:w-1/4">
                          <h3 className="font-bold text-gray-800">{bus.operator_name}</h3>
                          <p className="text-gray-500 text-sm">{bus.bus_type}</p>
                          <div className="flex items-center gap-1 mt-1">
                            <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                            <span className="text-sm font-medium">{bus.operator_rating}</span>
                          </div>
                        </div>

                        {/* Time & Duration */}
                        <div className="md:w-2/5 flex items-center justify-between md:justify-around">
                          <div className="text-center">
                            <p className="text-2xl font-bold text-gray-800">{bus.departure_time}</p>
                            <p className="text-sm text-gray-500">{fromCity?.name}</p>
                          </div>
                          <div className="flex flex-col items-center px-4">
                            <p className="text-sm text-gray-500">{formatDuration(bus.duration_mins)}</p>
                            <div className="w-24 h-0.5 bg-gray-200 relative my-2">
                              <Bus className="w-4 h-4 text-orange-500 absolute -top-1.5 left-1/2 -translate-x-1/2" />
                            </div>
                            {bus.is_night_bus === 1 && (
                              <span className="text-xs text-purple-600 flex items-center gap-1">
                                <Moon className="w-3 h-3" />
                                Night Bus
                              </span>
                            )}
                          </div>
                          <div className="text-center">
                            <p className="text-2xl font-bold text-gray-800">{bus.arrival_time}</p>
                            <p className="text-sm text-gray-500">
                              {toCity?.name}
                              {bus.next_day_arrival === 1 && (
                                <span className="text-orange-500 text-xs ml-1">+1</span>
                              )}
                            </p>
                          </div>
                        </div>

                        {/* Price & Availability */}
                        <div className="md:w-1/4 text-right">
                          <p className="text-sm text-gray-500">Starting from</p>
                          <p className="text-2xl font-bold text-orange-600">₹{bus.base_price}</p>
                          <p className="text-sm text-green-600">{bus.available_seats} seats available</p>
                        </div>
                      </div>

                      {/* Amenities & Actions */}
                      <div className="mt-4 pt-4 border-t border-gray-100 flex flex-wrap items-center justify-between gap-4">
                        <div className="flex items-center gap-3">
                          {bus.bus_type.toLowerCase().includes('ac') && (
                            <span className="flex items-center gap-1 text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                              <Droplets className="w-3 h-3" />
                              AC
                            </span>
                          )}
                          {bus.seat_layout && (
                            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                              {bus.seat_layout} Layout
                            </span>
                          )}
                          {bus.has_upper_deck === 1 && (
                            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                              Upper Deck
                            </span>
                          )}
                          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                            <Zap className="w-3 h-3 inline mr-1" />
                            Charging
                          </span>
                        </div>

                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => setExpandedBus(expandedBus === bus.schedule_id ? null : bus.schedule_id)}
                            className="text-orange-500 text-sm hover:underline flex items-center gap-1"
                          >
                            {expandedBus === bus.schedule_id ? (
                              <>Hide Details <ChevronUp className="w-4 h-4" /></>
                            ) : (
                              <>View Details <ChevronDown className="w-4 h-4" /></>
                            )}
                          </button>
                          <button
                            onClick={() => handleSelectBus(bus)}
                            className="px-6 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition font-medium"
                          >
                            Select Seats
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Expanded Details */}
                    {expandedBus === bus.schedule_id && (
                      <div className="bg-gray-50 p-6 border-t border-gray-100">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          {/* Boarding Points */}
                          <div>
                            <h4 className="font-medium text-gray-800 mb-3 flex items-center gap-2">
                              <MapPin className="w-4 h-4 text-green-500" />
                              Boarding Points
                            </h4>
                            <div className="space-y-2">
                              {bus.boarding_points?.map(point => (
                                <div key={point.id} className="flex items-start gap-2 text-sm">
                                  <span className="font-medium text-gray-700 w-14">{point.time}</span>
                                  <div>
                                    <p className="text-gray-800">{point.name}</p>
                                    <p className="text-gray-500 text-xs">{point.address}</p>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Dropping Points */}
                          <div>
                            <h4 className="font-medium text-gray-800 mb-3 flex items-center gap-2">
                              <MapPin className="w-4 h-4 text-red-500" />
                              Dropping Points
                            </h4>
                            <div className="space-y-2">
                              {bus.dropping_points?.map(point => (
                                <div key={point.id} className="flex items-start gap-2 text-sm">
                                  <span className="font-medium text-gray-700 w-14">{point.time}</span>
                                  <div>
                                    <p className="text-gray-800">{point.name}</p>
                                    <p className="text-gray-500 text-xs">{point.address}</p>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>

                        {/* Cancellation Policy */}
                        <div className="mt-4 pt-4 border-t border-gray-200">
                          <h4 className="font-medium text-gray-800 mb-2">Cancellation Policy</h4>
                          <p className="text-sm text-gray-600">{bus.cancellation_policy}</p>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BusResults;
