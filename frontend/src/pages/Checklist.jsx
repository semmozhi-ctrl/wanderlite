import React, { useState, useEffect } from 'react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Checkbox } from '../components/ui/checkbox';
import { Plus, Trash2, CheckCircle2, ListTodo } from 'lucide-react';

const Checklist = () => {
  const [items, setItems] = useState([]);
  const [newItem, setNewItem] = useState('');

  // Load items from localStorage on mount
  useEffect(() => {
    const savedItems = localStorage.getItem('wanderlite-checklist');
    if (savedItems) {
      setItems(JSON.parse(savedItems));
    } else {
      // Default checklist items
      const defaultItems = [
        { id: 1, text: 'Passport', checked: false },
        { id: 2, text: 'Visa documents', checked: false },
        { id: 3, text: 'Travel insurance', checked: false },
        { id: 4, text: 'Flight tickets', checked: false },
        { id: 5, text: 'Hotel bookings', checked: false },
        { id: 6, text: 'Camera & charger', checked: false },
        { id: 7, text: 'Phone & power bank', checked: false },
        { id: 8, text: 'Medications', checked: false },
        { id: 9, text: 'Comfortable shoes', checked: false },
        { id: 10, text: 'Sunscreen & sunglasses', checked: false }
      ];
      setItems(defaultItems);
      localStorage.setItem('wanderlite-checklist', JSON.stringify(defaultItems));
    }
  }, []);

  // Save items to localStorage whenever they change
  useEffect(() => {
    if (items.length > 0) {
      localStorage.setItem('wanderlite-checklist', JSON.stringify(items));
    }
  }, [items]);

  const addItem = () => {
    if (newItem.trim() === '') return;

    const newChecklistItem = {
      id: Date.now(),
      text: newItem,
      checked: false
    };

    setItems([...items, newChecklistItem]);
    setNewItem('');
  };

  const toggleItem = (id) => {
    setItems(
      items.map((item) =>
        item.id === id ? { ...item, checked: !item.checked } : item
      )
    );
  };

  const deleteItem = (id) => {
    setItems(items.filter((item) => item.id !== id));
  };

  const clearCompleted = () => {
    setItems(items.filter((item) => !item.checked));
  };

  const completedCount = items.filter((item) => item.checked).length;
  const totalCount = items.length;
  const progressPercentage = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12 space-y-4">
          <h1 className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-[#0077b6] to-[#48cae4] bg-clip-text text-transparent">
            Travel Checklist
          </h1>
          <p className="text-gray-600 text-lg">
            Never forget the essentials - organize your packing and preparation
          </p>
        </div>

        {/* Progress Card */}
        <Card className="p-6 shadow-xl border-0 bg-gradient-to-br from-[#0077b6] to-[#48cae4] text-white mb-8">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <CheckCircle2 className="w-8 h-8" />
                <div>
                  <h2 className="text-2xl font-bold">Your Progress</h2>
                  <p className="text-white/90">
                    {completedCount} of {totalCount} items completed
                  </p>
                </div>
              </div>
              <div className="text-right">
                <div className="text-4xl font-bold">{Math.round(progressPercentage)}%</div>
              </div>
            </div>
            <div className="w-full bg-white/30 rounded-full h-3 overflow-hidden">
              <div
                className="bg-white h-full rounded-full transition-all duration-500 ease-out"
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
          </div>
        </Card>

        {/* Add Item Card */}
        <Card className="p-6 shadow-xl border-0 bg-white mb-6">
          <div className="flex space-x-3">
            <Input
              type="text"
              placeholder="Add a new item to your checklist..."
              value={newItem}
              onChange={(e) => setNewItem(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && addItem()}
              className="flex-1 h-12 border-2 border-gray-200 focus:border-[#0077b6]"
            />
            <Button
              onClick={addItem}
              className="h-12 px-6 bg-gradient-to-r from-[#0077b6] to-[#48cae4] hover:from-[#005f8f] hover:to-[#3ab5d9] text-white font-semibold rounded-lg shadow-lg"
            >
              <Plus className="w-5 h-5" />
            </Button>
          </div>
        </Card>

        {/* Checklist Items */}
        <Card className="shadow-xl border-0 bg-white">
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-2">
                <ListTodo className="w-6 h-6 text-[#0077b6]" />
                <h3 className="text-xl font-bold text-gray-800">Your Checklist</h3>
              </div>
              {completedCount > 0 && (
                <Button
                  onClick={clearCompleted}
                  variant="outline"
                  size="sm"
                  className="text-red-600 border-red-300 hover:bg-red-50 hover:border-red-400"
                >
                  Clear Completed
                </Button>
              )}
            </div>

            {items.length === 0 ? (
              <div className="text-center py-12">
                <ListTodo className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500 text-lg">Your checklist is empty</p>
                <p className="text-gray-400">Add items to get started!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {items.map((item) => (
                  <div
                    key={item.id}
                    className={`flex items-center space-x-4 p-4 rounded-lg border-2 transition-all duration-300 ${
                      item.checked
                        ? 'bg-green-50 border-green-200'
                        : 'bg-white border-gray-200 hover:border-[#0077b6]/30 hover:shadow-md'
                    }`}
                  >
                    <Checkbox
                      checked={item.checked}
                      onCheckedChange={() => toggleItem(item.id)}
                      className="w-5 h-5 border-2"
                    />
                    <span
                      className={`flex-1 text-base transition-all duration-300 ${
                        item.checked
                          ? 'line-through text-gray-400'
                          : 'text-gray-700 font-medium'
                      }`}
                    >
                      {item.text}
                    </span>
                    <Button
                      onClick={() => deleteItem(item.id)}
                      variant="ghost"
                      size="sm"
                      className="text-red-500 hover:text-red-700 hover:bg-red-50"
                    >
                      <Trash2 className="w-5 h-5" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>

        {/* Info Note */}
        <div className="mt-6 text-center text-sm text-gray-500">
          Your checklist is automatically saved in your browser
        </div>
      </div>
    </div>
  );
};

export default Checklist;