import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  const [extractionMode, setExtractionMode] = useState('auto') // 'raw', 'auto', or 'manual'
  const [vendor, setVendor] = useState(null)
  const [startMarker, setStartMarker] = useState('Line: 1')
  const [endMarker, setEndMarker] = useState('Total Price')

  // Dev helper - log URLs on mount
  useEffect(() => {
    console.log('🚀 Frontend running at: http://localhost:5173')
    console.log('🔧 Backend expected at: http://localhost:8000')
  }, [])

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleChange = (e) => {
    e.preventDefault()
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const handleFile = async (file) => {
    // File type validation
    if (file.type !== 'application/pdf') {
      setError('Invalid file type. Please upload a PDF file.')
      return
    }

    // File size validation (10MB limit)
    const maxSize = 10 * 1024 * 1024 // 10MB in bytes
    if (file.size > maxSize) {
      setError(`File is too large (${(file.size / 1024 / 1024).toFixed(2)}MB). Maximum size is 10MB.`)
      return
    }

    setLoading(true)
    setError(null)
    setData([])
    setVendor(null)

    const formData = new FormData()
    formData.append('file', file)

    // Add manual markers if in manual mode
    if (extractionMode === 'manual') {
      formData.append('start_marker', startMarker)
      formData.append('end_marker', endMarker)
    }

    try {
      // Choose endpoint based on extraction mode
      const endpoint = (extractionMode === 'auto' || extractionMode === 'manual') ? '/extract-items' : '/upload'

      const response = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Server error: ${response.status}`)
      }

      const result = await response.json()

      // Debug logging
      console.log('📦 Backend Response:', result)
      console.log('🔍 Extraction Mode:', extractionMode)

      if (extractionMode === 'auto' || extractionMode === 'manual') {
        // Handle smart extraction response
        console.log('✨ Smart Mode - Items:', result.items)
        console.log('🏢 Vendor:', result.vendor)
        setData(result.items || [])
        setVendor(result.vendor || 'Unknown')
      } else {
        // Handle raw text response
        console.log('📝 Raw Mode - Data:', result.data)
        setData(result.data || [])
      }
    } catch (err) {
      if (err.message.includes('Failed to fetch')) {
        setError('Unable to connect to server. Please ensure the backend is running on http://localhost:8000')
      } else {
        setError(err.message)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setData([])
    setError(null)
    setVendor(null)
    // Reset file input
    const fileInput = document.getElementById('file-upload')
    if (fileInput) fileInput.value = ''
  }

  const handleCopy = async () => {
    let textContent = ''

    if (extractionMode === 'auto' || extractionMode === 'manual') {
      // Format smart extraction data
      textContent = `Vendor: ${vendor}\n\n`
      textContent += data.map(item =>
        `Line ${item.line_item}: ${item.part_id || 'N/A'}\n` +
        `Description: ${item.description}\n` +
        `Qty: ${item.qty || 'N/A'} | Price: $${item.price?.toFixed(2) || 'N/A'}\n`
      ).join('\n')
    } else {
      // Format raw text data
      textContent = data.map(item =>
        `Page ${item.page} - ${item.type}\n${'='.repeat(60)}\n${item.content}\n\n`
      ).join('\n')
    }

    try {
      await navigator.clipboard.writeText(textContent)
      alert('Copied to clipboard!')
    } catch (err) {
      alert('Failed to copy to clipboard')
    }
  }

  const formatCurrency = (value) => {
    if (value === null || value === undefined) return 'N/A'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value)
  }

  const getModeDescription = () => {
    switch (extractionMode) {
      case 'raw':
        return 'Raw Text Extraction'
      case 'auto':
        return 'Auto-detect vendor'
      case 'manual':
        return 'Manual marker-based extraction'
      default:
        return ''
    }
  }

  return (
    <div className="container">
      <div className="card">
        <h1>📄 PDF Data Extractor</h1>
        <p>Upload a PDF to extract and display its contents</p>

        {/* Mode Switcher */}
        <div className="mode-switcher">
          <button
            className={`mode-btn ${extractionMode === 'raw' ? 'active' : ''}`}
            onClick={() => setExtractionMode('raw')}
          >
            📝 Raw Text
          </button>
          <button
            className={`mode-btn ${extractionMode === 'auto' ? 'active' : ''}`}
            onClick={() => setExtractionMode('auto')}
          >
            ✨ Auto-Detect
          </button>
          <button
            className={`mode-btn ${extractionMode === 'manual' ? 'active' : ''}`}
            onClick={() => setExtractionMode('manual')}
          >
            🎯 Manual
          </button>
        </div>

        {/* Manual Mode Inputs */}
        {extractionMode === 'manual' && (
          <div className="manual-controls">
            <div className="helper-tip">
              💡 <strong>Tip:</strong> Switch to Raw Text mode first to find unique phrases to use as markers.
            </div>
            <div className="marker-inputs">
              <div className="input-group">
                <label htmlFor="start-marker">Start Marker:</label>
                <input
                  type="text"
                  id="start-marker"
                  value={startMarker}
                  onChange={(e) => setStartMarker(e.target.value)}
                  placeholder="e.g., Line: 1"
                />
              </div>
              <div className="input-group">
                <label htmlFor="end-marker">End Marker:</label>
                <input
                  type="text"
                  id="end-marker"
                  value={endMarker}
                  onChange={(e) => setEndMarker(e.target.value)}
                  placeholder="e.g., Total Price"
                />
              </div>
            </div>
          </div>
        )}

        <form
          className={`drop-zone ${dragActive ? 'active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onSubmit={(e) => e.preventDefault()}
        >
          <input
            type="file"
            id="file-upload"
            accept=".pdf"
            onChange={handleChange}
            style={{ display: 'none' }}
          />
          <label htmlFor="file-upload" style={{ cursor: 'pointer' }}>
            <div>
              <p style={{ fontSize: '3rem', margin: '0' }}>📎</p>
              <p>Drag and drop your PDF here or click to browse</p>
              <p style={{ fontSize: '0.85rem', opacity: 0.7, marginTop: '0.5rem' }}>
                Mode: {getModeDescription()}
              </p>
            </div>
          </label>
        </form>

        {loading && <p>Processing PDF...</p>}
        {error && <p className="error">Error: {error}</p>}

        {data.length > 0 && (
          <div style={{ marginTop: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <h2 style={{ margin: 0 }}>Extracted Data</h2>
                {(extractionMode === 'auto' || extractionMode === 'manual') && vendor && (
                  <div className="vendor-badge">
                    🏢 Vendor: <strong>{vendor.charAt(0).toUpperCase() + vendor.slice(1)}</strong>
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button onClick={handleCopy} className="action-btn copy-btn">
                  📋 Copy All
                </button>
                <button onClick={handleClear} className="action-btn clear-btn">
                  🗑️ Clear
                </button>
              </div>
            </div>

            {/* Smart Extraction Table (Auto or Manual mode) */}
            {(extractionMode === 'auto' || extractionMode === 'manual') && (
              <table className="smart-table">
                <thead>
                  <tr>
                    <th style={{ width: '60px' }}>#</th>
                    <th style={{ width: '120px' }}>Part ID</th>
                    <th>Description</th>
                    <th style={{ width: '80px' }}>Qty</th>
                    <th style={{ width: '120px' }}>Price</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((item, index) => (
                    <tr key={index}>
                      <td style={{ textAlign: 'center', fontWeight: 'bold' }}>
                        {item.line_item ?? index + 1}
                      </td>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}>
                        {item.part_id || <span style={{ opacity: 0.5 }}>—</span>}
                      </td>
                      <td style={{ whiteSpace: 'normal', wordWrap: 'break-word' }}>
                        {item.description || <span style={{ opacity: 0.5 }}>—</span>}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        {item.qty !== null && item.qty !== undefined ? item.qty : <span style={{ opacity: 0.5 }}>—</span>}
                      </td>
                      <td style={{ textAlign: 'right', fontWeight: '600' }}>
                        {formatCurrency(item.price)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'right', fontStyle: 'italic', opacity: 0.7 }}>
                      Total Items: {data.length}
                    </td>
                  </tr>
                </tfoot>
              </table>
            )}

            {/* Raw Text Table */}
            {extractionMode === 'raw' && (
              <table>
                <thead>
                  <tr>
                    <th>Page</th>
                    <th>Type</th>
                    <th>Content</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((item, index) =>
                    item.content.split('\n').map((line, i) => (
                      <tr key={`${index}-${i}`}>
                        {i === 0 ? (
                          <>
                            <td rowSpan={item.content.split('\n').length}>{item.page}</td>
                            <td rowSpan={item.content.split('\n').length}>{item.type}</td>
                          </>
                        ) : null}
                        <td>{line}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default App