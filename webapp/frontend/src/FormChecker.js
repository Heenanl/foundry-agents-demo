import React, { useState } from 'react';
import * as XLSX from 'xlsx';
import { useNavigate } from 'react-router-dom';
import './FormChecker.css';

const API_URL = 'http://localhost:8000';

function FormChecker() {
  const navigate = useNavigate();
  const [excelData, setExcelData] = useState([]);
  const [headers, setHeaders] = useState([]);
  const [validationResults, setValidationResults] = useState([]); // Array of validation results from agent
  const [fileName, setFileName] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [inputText, setInputText] = useState(''); // Text to validate against policies

  // Handle Excel file upload
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setFileName(file.name);
    const reader = new FileReader();

    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        
        // Get the first sheet
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];
        
        // Convert to JSON
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' });
        
        console.log('Raw Excel data:', jsonData);
        
        if (jsonData.length > 0) {
          // First row is headers
          const headerRow = jsonData[0];
          setHeaders(headerRow);
          console.log('Headers:', headerRow);
          
          // Rest are data rows - filter out completely empty rows
          const dataRows = jsonData.slice(1).filter(row => 
            row && row.length > 0 && row.some(cell => 
              cell !== null && cell !== undefined && String(cell).trim() !== ''
            )
          );
          
          console.log('Filtered data rows:', dataRows);
          console.log('Number of rows:', dataRows.length);
          
          setExcelData(dataRows);
          
          // Initialize validation results as empty
          setValidationResults([]);
        } else {
          console.warn('No data found in Excel file');
        }
      } catch (error) {
        console.error('Error reading Excel file:', error);
        console.error('Error details:', error.message, error.stack);
        
        let errorMessage = 'Error reading Excel file. ';
        
        if (error.message && error.message.includes('Encrypted')) {
          errorMessage += 'This file appears to be encrypted or password-protected. Please save it as an unencrypted Excel file (.xlsx) and try again.';
        } else if (error.message && error.message.includes('ECMA-376')) {
          errorMessage += 'This file appears to be encrypted. Please remove any password protection and save as a standard Excel file (.xlsx).';
        } else {
          errorMessage += 'Please make sure it\'s a valid Excel file (.xlsx or .xls).\n\nError: ' + error.message;
        }
        
        alert(errorMessage);
      }
    };

    reader.readAsArrayBuffer(file);
  };

  // Execute automatic validation with parallel agent calls
  const handleAutomaticValidation = async () => {
    if (!inputText.trim()) {
      alert('Please enter the information to validate against the policies.');
      return;
    }
    
    setIsValidating(true);
    
    try {
      const response = await fetch(`${API_URL}/api/form-checker/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          headers: headers,
          data: excelData,
          input_text: inputText
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setValidationResults(data.results);
      } else {
        alert('Validation failed. Please try again.');
      }
    } catch (error) {
      console.error('Error during automatic validation:', error);
      alert('Error during validation: ' + error.message);
    } finally {
      setIsValidating(false);
    }
  };

  // Clear all data
  const handleClear = () => {
    setExcelData([]);
    setHeaders([]);
    setValidationResults([]);
    setFileName('');
    setInputText('');
  };

  return (
    <div className="form-checker-container">
      {/* Header with navigation */}
      <header className="header">
        <div className="header-content">
          <button onClick={() => navigate('/')} className="nav-button">
            ← Back to Chat
          </button>
          <h1>Form Checker</h1>
          <img 
            src="/geekster.png" 
            alt="Geekster Logo" 
            className="logo" 
          />
        </div>
      </header>

      {/* Main content area */}
      <div className="form-checker-content">
        {/* Upload section */}
        <div className="upload-section">
          <h2>Upload Excel Document</h2>
          <div className="upload-controls">
            <label htmlFor="file-upload" className="file-upload-label">
              📄 Choose Excel File
            </label>
            <input
              id="file-upload"
              type="file"
              accept=".xlsx,.xls"
              onChange={handleFileUpload}
              className="file-input"
            />
            {fileName && <span className="file-name">Selected: {fileName}</span>}
          </div>
          
          {excelData.length > 0 && (
            <>
              <div className="input-text-section">
                <h3>Enter Information to Validate</h3>
                <p className="input-hint">Enter the booking details, travel information, or any data that should be checked against the policies above.</p>
                <textarea
                  className="validation-input"
                  placeholder="Example: Hotel name is Grand Plaza Hotel, located at 123 Main Street, New York. Flight number is KL1234. Checked baggage is 25kg. Traveling from Amsterdam to New York."
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  rows={6}
                />
              </div>
              
              <div className="action-buttons">
                <button 
                  onClick={handleAutomaticValidation} 
                  className="validate-button"
                  disabled={isValidating || !inputText.trim()}
                >
                  {isValidating ? '⏳ Validating...' : '✓ Validate'}
                </button>
                <button onClick={handleClear} className="clear-button">
                  🗑️ Clear All
                </button>
              </div>
            </>
          )}
        </div>

        {/* Data table */}
        {excelData.length > 0 && (
          <div className="table-section">
            <h3>Uploaded Data ({excelData.length} rows)</h3>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th className="validation-column">Validation Status</th>
                    <th>Policy nr</th>
                    <th>Policy Purpose</th>
                    <th>Check</th>
                    <th className="reason-column">Reason</th>
                    <th className="source-column">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {excelData.map((row, rowIndex) => {
                    const result = validationResults.find(r => r.row_index === rowIndex);
                    return (
                      <tr key={rowIndex} className={result ? (result.agent_result.validated ? 'validated-row' : 'not-validated-row') : ''}>
                        <td className="validation-cell">
                          {result ? (
                            <div className={`validation-status ${result.agent_result.validated ? 'valid' : 'invalid'}`}>
                              {result.agent_result.validated ? '✓ Validated' : '✗ Not Validated'}
                            </div>
                          ) : (                                                                                     
                            <div className="validation-status pending">⏳ Pending</div>
                          )}
                        </td>
                        <td>{row[0] !== undefined && row[0] !== null ? String(row[0]) : ''}</td>
                        <td>{row[1] !== undefined && row[1] !== null ? String(row[1]) : ''}</td>
                        <td className="check-cell">{row[2] !== undefined && row[2] !== null ? String(row[2]) : ''}</td>
                        <td className="reason-cell">
                          {result ? result.agent_result.reason : '-'}
                        </td>
                        <td className="source-cell">
                          {result ? (
                            <a href={result.agent_result.source} target="_blank" rel="noopener noreferrer">
                              {result.agent_result.source}
                            </a>
                          ) : '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            
            {/* Summary */}
            {validationResults.length > 0 && (
              <div className="summary">
                <p>
                  <span className="summary-item valid">
                    ✓ Validated: {validationResults.filter(r => r.agent_result.validated).length}
                  </span>
                  <span className="summary-item invalid">
                    ✗ Not Validated: {validationResults.filter(r => !r.agent_result.validated).length}
                  </span>
                </p>
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {excelData.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">📊</div>
            <h3>No Data Loaded</h3>
            <p>Upload an Excel file to get started with form validation</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default FormChecker;
