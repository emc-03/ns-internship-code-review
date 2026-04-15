import React, { useState } from 'react';
import './App.css';

function App() {
  const [left, setLeft] = useState('');
  const [right, setRight] = useState('');
  const [operation, setOperation] = useState('+');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleCalculate = async () => {
    try {
      const response = await fetch('http://localhost:8000/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ left: parseFloat(left), right: parseFloat(right), operation }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Calculation failed');
      }
      setResult(data.result);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="App">
      <h1>Basic Calculator</h1>
      <div className="calculator">
      <input type="number" value={left} onChange={(e) => setLeft(e.target.value)} placeholder="Left operand" />
      <select value={operation} onChange={(e) => setOperation(e.target.value)}>
        <option value="+">+</option>
        <option value="-">-</option>
        <option value="*">*</option>
        <option value="/">/</option>
      </select>
      <input type="number" value={right} onChange={(e) => setRight(e.target.value)} placeholder="Right operand" />
      <button onClick={handleCalculate}>Calculate</button>
      </div>
      {result !== null && <h2>Result: {result}</h2>}
      {error && <h2 style={{ color: 'red' }}>Error: {error}</h2>}
    </div>
  );
} 
export default App;
