import React, { useState } from 'react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Mail, Phone, MapPin, Send, CheckCircle2 } from 'lucide-react';
import { useToast } from '../hooks/use-toast';

const Contact = () => {
  const { toast } = useToast();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    message: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.name || !formData.email || !formData.message) {
      toast({
        title: 'Missing Information',
        description: 'Please fill in all fields before submitting.',
        variant: 'destructive'
      });
      return;
    }

    setIsSubmitting(true);

    // Mock EmailJS submission (will be replaced with real API)
    setTimeout(() => {
      setIsSubmitting(false);
      setSubmitted(true);
      toast({
        title: 'Message Sent!',
        description: 'Thank you for contacting us. We\'ll get back to you soon!'
      });

      // Reset form after 3 seconds
      setTimeout(() => {
        setFormData({ name: '', email: '', message: '' });
        setSubmitted(false);
      }, 3000);
    }, 1500);
  };

  const contactInfo = [
    {
      icon: Mail,
      title: 'Email',
      value: 'hello@wanderlite.com',
      link: 'mailto:hello@wanderlite.com'
    },
    {
      icon: Phone,
      title: 'Phone',
      value: '+1 (555) 123-4567',
      link: 'tel:+15551234567'
    },
    {
      icon: MapPin,
      title: 'Location',
      value: 'San Francisco, CA',
      link: '#'
    }
  ];

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12 space-y-4">
          <h1 className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-[#0077b6] to-[#48cae4] bg-clip-text text-transparent">
            Get in Touch
          </h1>
          <p className="text-gray-600 text-lg max-w-2xl mx-auto">
            Have questions or feedback? We'd love to hear from you. Send us a message and we'll
            respond as soon as possible.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Contact Info Cards */}
          <div className="space-y-6">
            {contactInfo.map((info, index) => (
              <Card
                key={index}
                className="p-6 shadow-lg border-0 hover:shadow-xl transition-shadow duration-300"
              >
                <a
                  href={info.link}
                  className="flex items-start space-x-4 group"
                >
                  <div className="p-3 bg-gradient-to-br from-[#0077b6] to-[#48cae4] rounded-lg group-hover:scale-110 transition-transform duration-300">
                    <info.icon className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-800 mb-1">{info.title}</h3>
                    <p className="text-gray-600">{info.value}</p>
                  </div>
                </a>
              </Card>
            ))}

            {/* Additional Info */}
            <Card className="p-6 bg-gradient-to-br from-[#0077b6] to-[#48cae4] text-white shadow-lg border-0">
              <h3 className="text-xl font-bold mb-3">Why Contact Us?</h3>
              <ul className="space-y-2 text-sm">
                <li className="flex items-start space-x-2">
                  <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
                  <span>Get personalized travel advice</span>
                </li>
                <li className="flex items-start space-x-2">
                  <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
                  <span>Report issues or suggest features</span>
                </li>
                <li className="flex items-start space-x-2">
                  <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
                  <span>Partnership opportunities</span>
                </li>
                <li className="flex items-start space-x-2">
                  <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
                  <span>General inquiries</span>
                </li>
              </ul>
            </Card>
          </div>

          {/* Contact Form */}
          <Card className="lg:col-span-2 p-8 shadow-xl border-0">
            {submitted ? (
              <div className="flex flex-col items-center justify-center py-12 space-y-4 animate-fade-in">
                <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center">
                  <CheckCircle2 className="w-12 h-12 text-green-600" />
                </div>
                <h3 className="text-2xl font-bold text-gray-800">Message Sent!</h3>
                <p className="text-gray-600 text-center">
                  Thank you for reaching out. We'll get back to you shortly.
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="name" className="text-base font-semibold text-gray-700">
                    Your Name
                  </Label>
                  <Input
                    id="name"
                    name="name"
                    type="text"
                    placeholder="John Doe"
                    value={formData.name}
                    onChange={handleChange}
                    className="h-12 border-2 border-gray-200 focus:border-[#0077b6]"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email" className="text-base font-semibold text-gray-700">
                    Email Address
                  </Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="john@example.com"
                    value={formData.email}
                    onChange={handleChange}
                    className="h-12 border-2 border-gray-200 focus:border-[#0077b6]"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="message" className="text-base font-semibold text-gray-700">
                    Your Message
                  </Label>
                  <Textarea
                    id="message"
                    name="message"
                    placeholder="Tell us what's on your mind..."
                    value={formData.message}
                    onChange={handleChange}
                    rows={6}
                    className="border-2 border-gray-200 focus:border-[#0077b6] resize-none"
                  />
                </div>

                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full h-12 bg-gradient-to-r from-[#0077b6] to-[#48cae4] hover:from-[#005f8f] hover:to-[#3ab5d9] text-white text-lg font-semibold rounded-lg shadow-lg transform transition-all duration-300 hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    'Sending...'
                  ) : (
                    <>
                      <Send className="w-5 h-5 mr-2" />
                      Send Message
                    </>
                  )}
                </Button>

                <p className="text-sm text-gray-500 text-center">
                  Note: EmailJS integration will be configured with your API keys later.
                </p>
              </form>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Contact;