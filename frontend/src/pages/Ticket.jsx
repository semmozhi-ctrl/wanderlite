import React from 'react';
import { useLocation } from 'react-router-dom';
import FlightTicket from '../components/tickets/FlightTicket';
import HotelVoucher from '../components/tickets/HotelVoucher';
import RestaurantBooking from '../components/tickets/RestaurantBooking';

const Ticket = () => {
  const { state } = useLocation();
  
  // Extract data from state
  const booking = state?.booking || {};
  const passenger = state?.passenger || state?.payer || {};
  const payment = state?.payment || {};
  
  // Determine service type
  const serviceType = (booking?.service_type || state?.serviceType || 'flight').toLowerCase();
  
  // Render appropriate ticket component based on service type
  const renderTicket = () => {
    switch (serviceType) {
      case 'flight':
        return <FlightTicket booking={booking} passenger={passenger} payment={payment} />;
      case 'hotel':
        return <HotelVoucher booking={booking} passenger={passenger} payment={payment} />;
      case 'restaurant':
        return <RestaurantBooking booking={booking} passenger={passenger} payment={payment} />;
      default:
        return <FlightTicket booking={booking} passenger={passenger} payment={payment} />;
    }
  };

  return (
    <div className="min-h-screen pt-20 pb-16 bg-gradient-to-b from-gray-50 to-white">
      {renderTicket()}
    </div>
  );
};

export default Ticket;



