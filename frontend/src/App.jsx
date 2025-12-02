import { useState } from 'react'
import './App.css'

function App() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [dragActive, setDragActive] = useState(false)

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

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Server error: ${response.status}`)
      }

      const result = await response.json()
      setData(result.data)
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
    // Reset file input
    const fileInput = document.getElementById('file-upload')
    if (fileInput) fileInput.value = ''
  }

  const handleCopy = async () => {
    const textContent = data.map(item =>
      `Page ${item.page} - ${item.type}\n${'='.repeat(60)}\n${item.content}\n\n`
    ).join('\n')

    try {
      await navigator.clipboard.writeText(textContent)
      alert('Copied to clipboard!')
    } catch (err) {
      alert('Failed to copy to clipboard')
    }
  }

  return (
    <div className="container">
      <div className="card">
        <h1>📄 PDF Data Extractor</h1>
        <p>Upload a PDF to extract and display its contents</p>

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
            </div>
          </label>
        </form>

        {loading && <p>Processing PDF...</p>}
        {error && <p className="error">Error: {error}</p>}

        {data.length > 0 && (
          <div style={{ marginTop: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h2 style={{ margin: 0 }}>Extracted Data</h2>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button onClick={handleCopy} className="action-btn copy-btn">
                  📋 Copy All
                </button>
                <button onClick={handleClear} className="action-btn clear-btn">
                  🗑️ Clear
                </button>
              </div>
            </div>
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
          </div>
        )}
      </div>
    </div>
  )
}

export default App