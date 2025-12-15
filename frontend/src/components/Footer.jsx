import React from 'react';
import { Link } from 'react-router-dom';
import { Compass, Instagram, Youtube, Twitter, Mail, Phone, MapPin } from 'lucide-react';

const Footer = () => {
  const currentYear = new Date().getFullYear();

  const footerLinks = [
    {
      title: 'Quick Links',
      links: [
        { name: 'Home', path: '/' },
        { name: 'Explore', path: '/explore' },
        { name: 'Trip Planner', path: '/planner' },
        { name: 'Gallery', path: '/gallery' }
      ]
    },
    {
      title: 'Support',
      links: [
        { name: 'Contact Us', path: '/contact' },
        { name: 'FAQs', path: '#' },
        { name: 'Travel Tips', path: '#' },
        { name: 'Privacy Policy', path: '#' }
      ]
    }
  ];

  const socialLinks = [
    { icon: Instagram, href: 'https://instagram.com', label: 'Instagram', color: 'hover:text-pink-500' },
    { icon: Youtube, href: 'https://youtube.com', label: 'YouTube', color: 'hover:text-red-500' },
    { icon: Twitter, href: 'https://twitter.com', label: 'Twitter', color: 'hover:text-blue-400' }
  ];

  const contactInfo = [
    { icon: Mail, text: 'hello@wanderlite.com' },
    { icon: Phone, text: '+1 (555) 123-4567' },
    { icon: MapPin, text: 'San Francisco, CA' }
  ];

  return (
    <footer className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {/* Brand Section */}
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <div className="p-2 bg-gradient-to-r from-[#0077b6] to-[#48cae4] rounded-lg">
                <Compass className="w-6 h-6 text-white" />
              </div>
              <span className="text-2xl font-bold">WanderLite</span>
            </div>
            <p className="text-gray-400 text-sm leading-relaxed">
              Your ultimate travel companion for planning unforgettable journeys around the world.
            </p>
            {/* Social Links */}
            <div className="flex space-x-4 pt-2">
              {socialLinks.map((social) => (
                <a
                  key={social.label}
                  href={social.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`p-2 bg-gray-800 rounded-lg transition-all duration-300 hover:bg-gray-700 ${social.color} transform hover:scale-110`}
                  aria-label={social.label}
                >
                  <social.icon className="w-5 h-5" />
                </a>
              ))}
            </div>
          </div>

          {/* Links Sections */}
          {footerLinks.map((section) => (
            <div key={section.title}>
              <h3 className="text-lg font-semibold mb-4 text-white">{section.title}</h3>
              <ul className="space-y-2">
                {section.links.map((link) => (
                  <li key={link.name}>
                    <Link
                      to={link.path}
                      className="text-gray-400 hover:text-[#48cae4] transition-colors duration-200 text-sm"
                    >
                      {link.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}

          {/* Contact Info */}
          <div>
            <h3 className="text-lg font-semibold mb-4 text-white">Get in Touch</h3>
            <ul className="space-y-3">
              {contactInfo.map((info, index) => (
                <li key={index} className="flex items-center space-x-3 text-gray-400 text-sm">
                  <info.icon className="w-4 h-4 text-[#48cae4]" />
                  <span>{info.text}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-12 pt-8 border-t border-gray-700">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            <p className="text-gray-400 text-sm">
              © {currentYear} WanderLite. All rights reserved.
            </p>
            <div className="flex space-x-6 text-sm">
              <a href="#" className="text-gray-400 hover:text-[#48cae4] transition-colors">
                Terms of Service
              </a>
              <a href="#" className="text-gray-400 hover:text-[#48cae4] transition-colors">
                Privacy Policy
              </a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;