import { render, screen, fireEvent } from '@testing-library/react';
import { SearchResults } from '../search-results';
import { Flight } from '@/types/search';

// Mock the onSort and onFilter functions
const mockOnSort = jest.fn();
const mockOnFilter = jest.fn();

// Create mock flight data
const mockFlights: Flight[] = [
  {
    id: '1',
    airline: 'Test Airline',
    flightNumber: 'TA123',
    origin: 'JFK',
    destination: 'LHR',
    departureTime: '10:00 AM',
    arrivalTime: '10:00 PM',
    duration: 600, // 10 hours in minutes
    stops: 0,
    price: 499,
    cabinClass: 'economy',
    seatsAvailable: 10
  },
  {
    id: '2',
    airline: 'Another Airline',
    flightNumber: 'AA456',
    origin: 'JFK',
    destination: 'LHR',
    departureTime: '12:00 PM',
    arrivalTime: '12:30 AM',
    duration: 630, // 10.5 hours in minutes
    stops: 1,
    price: 399,
    cabinClass: 'economy',
    seatsAvailable: 5,
    layovers: [
      {
        airport: 'BOS',
        duration: 90
      }
    ]
  }
];

describe('SearchResults', () => {
  beforeEach(() => {
    // Clear mock calls between tests
    mockOnSort.mockClear();
    mockOnFilter.mockClear();
  });

  it('renders the results correctly', () => {
    render(
      <SearchResults 
        type='flight' 
        results={mockFlights} 
        onSort={mockOnSort}
        onFilter={mockOnFilter}
      />
    );
    
    // Check if the results count is displayed
    expect(screen.getByText('2 Results')).toBeInTheDocument();
    
    // Check if view toggle buttons are present
    expect(screen.getByText('List')).toBeInTheDocument();
    expect(screen.getByText('Grid')).toBeInTheDocument();
    expect(screen.getByText('Map')).toBeInTheDocument();
    
    // Check if sort options are present
    expect(screen.getByText('Price')).toBeInTheDocument();
    expect(screen.getByText('Duration')).toBeInTheDocument();
    expect(screen.getByText('Stops')).toBeInTheDocument();
    
    // Check if flight details are displayed
    expect(screen.getByText('Test Airline TA123')).toBeInTheDocument();
    expect(screen.getByText('Another Airline AA456')).toBeInTheDocument();
    expect(screen.getByText('Nonstop')).toBeInTheDocument();
    expect(screen.getByText('1 stop')).toBeInTheDocument();
    expect(screen.getAllByText('$499')).toHaveLength(1);
    expect(screen.getAllByText('$399')).toHaveLength(1);
  });

  it('handles sorting correctly', () => {
    render(
      <SearchResults 
        type='flight' 
        results={mockFlights} 
        onSort={mockOnSort}
        onFilter={mockOnFilter}
      />
    );
    
    // Click the price sort button
    fireEvent.click(screen.getByText('Price'));
    
    // Check if onSort was called with the correct parameters
    expect(mockOnSort).toHaveBeenCalledTimes(1);
    expect(mockOnSort).toHaveBeenCalledWith('price', 'desc');
    
    // Click again to toggle sort direction
    fireEvent.click(screen.getByText('Price'));
    
    // Check if onSort was called again with the opposite direction
    expect(mockOnSort).toHaveBeenCalledTimes(2);
    expect(mockOnSort).toHaveBeenCalledWith('price', 'asc');
  });

  it('handles view toggle correctly', () => {
    render(
      <SearchResults 
        type='flight' 
        results={mockFlights} 
        onSort={mockOnSort}
        onFilter={mockOnFilter}
      />
    );
    
    // Default view should be list
    expect(screen.getByText('List')).toHaveClass('bg-primary');
    
    // Click the grid view button
    fireEvent.click(screen.getByText('Grid'));
    
    // Grid button should now be selected
    expect(screen.getByText('Grid')).toHaveClass('bg-primary');
    expect(screen.getByText('List')).not.toHaveClass('bg-primary');
    
    // Click the map view button
    fireEvent.click(screen.getByText('Map'));
    
    // Map button should now be selected
    expect(screen.getByText('Map')).toHaveClass('bg-primary');
    expect(screen.getByText('Grid')).not.toHaveClass('bg-primary');
  });

  it('displays loading state when loading is true', () => {
    render(
      <SearchResults 
        type='flight' 
        results={[]} 
        loading={true}
        onSort={mockOnSort}
        onFilter={mockOnFilter}
      />
    );
    
    // Check if loading text is displayed
    expect(screen.getByText('Searching...')).toBeInTheDocument();
    
    // Check if loading spinner is displayed
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    
    // Results should not be displayed
    expect(screen.queryByText('Test Airline TA123')).not.toBeInTheDocument();
  });

  it('displays empty state when no results', () => {
    render(
      <SearchResults 
        type='flight' 
        results={[]} 
        onSort={mockOnSort}
        onFilter={mockOnFilter}
      />
    );
    
    // Check if empty state message is displayed
    expect(screen.getByText('No results found. Try adjusting your search criteria.')).toBeInTheDocument();
    
    // Results should not be displayed
    expect(screen.queryByText('Test Airline TA123')).not.toBeInTheDocument();
  });
});