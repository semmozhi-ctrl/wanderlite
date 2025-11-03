import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, MapPin, Calendar, Shield, Sparkles, MessageCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { heroImages, destinations } from '../data/mock';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';

const Home = () => {
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentImageIndex((prev) => (prev + 1) % heroImages.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const features = [
    {
      icon: MapPin,
      title: 'Explore Destinations',
      description: 'Discover amazing places around the world with detailed guides and insider tips'
    },
    {
      icon: Calendar,
      title: 'Smart Trip Planning',
      description: 'Create personalized itineraries based on your budget and preferences'
    },
    {
      icon: Shield,
      title: 'Travel Checklist',
      description: 'Never forget essentials with our comprehensive packing and preparation lists'
    },
    {
      icon: Sparkles,
      title: 'Expert Recommendations',
      description: 'Get real-time weather updates and currency conversion for seamless travel'
    }
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section with Carousel */}
      <section className="relative h-screen overflow-hidden">
        {/* Background Images */}
        {heroImages.map((image, index) => (
          <div
            key={image.id}
            className={`absolute inset-0 transition-opacity duration-1000 ${
              index === currentImageIndex ? 'opacity-100' : 'opacity-0'
            }`}
          >
            <img
              src={image.url}
              alt={image.title}
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-b from-black/50 via-black/30 to-black/60" />
          </div>
        ))}

        {/* Hero Content */}
        <div className="relative z-10 h-full flex items-center justify-center">
          <div className="text-center px-4 space-y-6 animate-fade-in">
            <h1 className="text-5xl md:text-7xl font-bold text-white leading-tight">
              {heroImages[currentImageIndex].title}
            </h1>
            <p className="text-xl md:text-2xl text-gray-200 max-w-2xl mx-auto">
              {heroImages[currentImageIndex].subtitle}
            </p>
            <div className="pt-4">
              <Link to="/planner">
                <Button
                  size="lg"
                  className="bg-gradient-to-r from-[#0077b6] to-[#48cae4] hover:from-[#005f8f] hover:to-[#3ab5d9] text-white px-8 py-6 text-lg font-semibold rounded-full shadow-2xl transform transition-all duration-300 hover:scale-105"
                >
                  Start Planning
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {/* Carousel Indicators */}
        <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 flex space-x-2 z-20">
          {heroImages.map((_, index) => (
            <button
              key={index}
              onClick={() => setCurrentImageIndex(index)}
              className={`w-3 h-3 rounded-full transition-all duration-300 ${
                index === currentImageIndex
                  ? 'bg-white w-8'
                  : 'bg-white/50 hover:bg-white/75'
              }`}
              aria-label={`Go to slide ${index + 1}`}
            />
          ))}
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-gradient-to-b from-white to-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 space-y-4">
            <h2 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-[#0077b6] to-[#48cae4] bg-clip-text text-transparent">
              Why Choose WanderLite?
            </h2>
            <p className="text-gray-600 text-lg max-w-2xl mx-auto">
              Everything you need to plan your perfect journey in one place
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <Card
                key={index}
                className="p-6 hover:shadow-xl transition-all duration-300 transform hover:-translate-y-2 border-0 bg-white"
              >
                <div className="space-y-4">
                  <div className="w-14 h-14 bg-gradient-to-br from-[#0077b6] to-[#48cae4] rounded-xl flex items-center justify-center">
                    <feature.icon className="w-7 h-7 text-white" />
                  </div>
                  <h3 className="text-xl font-semibold text-gray-800">
                    {feature.title}
                  </h3>
                  <p className="text-gray-600 leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Popular Destinations Preview */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 space-y-4">
            <h2 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-[#0077b6] to-[#48cae4] bg-clip-text text-transparent">
              Popular Destinations
            </h2>
            <p className="text-gray-600 text-lg">
              Start exploring our curated collection of breathtaking places
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {destinations.slice(0, 4).map((destination) => (
              <Card
                key={destination.id}
                className="overflow-hidden group cursor-pointer border-0 shadow-lg hover:shadow-2xl transition-all duration-300"
              >
                <div className="relative h-64 overflow-hidden">
                  <img
                    src={destination.image}
                    alt={destination.name}
                    className="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-500"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent" />
                  <div className="absolute bottom-0 left-0 right-0 p-4 text-white">
                    <h3 className="text-xl font-bold mb-1">{destination.name}</h3>
                    <p className="text-sm text-gray-200">{destination.shortDescription}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>

          <div className="text-center mt-12">
            <Link to="/explore">
              <Button
                size="lg"
                variant="outline"
                className="border-2 border-[#0077b6] text-[#0077b6] hover:bg-[#0077b6] hover:text-white px-8 py-6 text-lg font-semibold rounded-full transition-all duration-300"
              >
                Explore All Destinations
                <ArrowRight className="ml-2 w-5 h-5" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-br from-[#0077b6] to-[#48cae4] text-white">
        <div className="max-w-4xl mx-auto text-center px-4 space-y-8">
          <h2 className="text-4xl md:text-5xl font-bold">
            Ready to Start Your Adventure?
          </h2>
          <p className="text-xl text-white/90 leading-relaxed">
            Join thousands of travelers who trust WanderLite to plan their perfect trips.
            Create your personalized itinerary in minutes!
          </p>
          <Link to="/planner">
            <Button
              size="lg"
              className="bg-white text-[#0077b6] hover:bg-gray-100 px-8 py-6 text-lg font-semibold rounded-full shadow-2xl transform transition-all duration-300 hover:scale-105"
            >
              Get Started Now
              <ArrowRight className="ml-2 w-5 h-5" />
            </Button>
          </Link>
        </div>
      </section>
      {/* Floating AI Assistant Button */}
      <button
        onClick={() => navigate('/assistant')}
        aria-label="Open assistant"
        className="fixed bottom-6 right-6 z-50 rounded-full bg-sky-500 hover:bg-sky-600 text-white shadow-xl p-4"
      >
        <MessageCircle className="w-6 h-6" />
      </button>
    </div>
  );
};

export default Home;