import { useState, useRef } from "react";
import { 
    Upload, 
    FileText, 
    Zap, 
    CheckCircle2, 
    AlertTriangle, 
    Trash2, 
    Plus,
    Loader2,
    Send
} from "lucide-react";
import { Card, LoadingSpinner } from "../components/ui/StatCard";
import { Badge } from "../components/ui/Badge";
import * as api from "../services/api";
import toast from "react-hot-toast";

export default function Analysis() {
    const [activeTab, setActiveTab] = useState("upload"); // "upload" | "manual"
    const [text, setText] = useState("");
    const [file, setFile] = useState(null);
    const [analyzing, setAnalyzing] = useState(false);
    const [result, setResult] = useState(null);
    const fileInputRef = useRef(null);

    const handleFileUpload = async (e) => {
        const selectedFile = e.target.files[0];
        if (!selectedFile) return;
        
        // Basic validation
        const validTypes = ['text/plain', 'application/json', 'text/csv', 'image/jpeg', 'image/png'];
        if (!validTypes.includes(selectedFile.type)) {
            toast.error("Invalid file type. Please upload TXT, JSON, CSV, or an Image.");
            return;
        }

        setFile(selectedFile);
    };

    const runAnalysis = async () => {
        if (activeTab === "manual" && !text.trim()) {
            toast.error("Please enter some text to analyze.");
            return;
        }
        if (activeTab === "upload" && !file) {
            toast.error("Please select a file to upload.");
            return;
        }

        setAnalyzing(true);
        setResult(null);

        try {
            let res;
            if (activeTab === "manual") {
                res = await api.analyzeText(text);
            } else {
                const formData = new FormData();
                formData.append("file", file);
                formData.append("auto_analyze", "true");
                res = await api.uploadData(formData);
                // If the response contains the analysis result directly
                if (res.analysis_result) res = res.analysis_result;
            }
            
            setResult(res.analysis || res);
            toast.success("AI Analysis complete!");
        } catch (err) {
            console.error(err);
            toast.error("Analysis failed. Please check the backend connection.");
        } finally {
            setAnalyzing(false);
        }
    };

    const clearAll = () => {
        setText("");
        setFile(null);
        setResult(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    return (
        <div className="analysis-page">
            <div className="page-header">
                <h1 className="page-title">AI Need Detection</h1>
                <p className="page-subtitle">Harness Gemini 1.5 Flash to extract and prioritize community needs</p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem", alignItems: "start" }}>
                
                {/* Left Side: Input Selection */}
                <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                    <div className="tab-list">
                        <div 
                            className={`tab-item ${activeTab === "upload" ? "active" : ""}`}
                            onClick={() => setActiveTab("upload")}
                        >
                            Upload File
                        </div>
                        <div 
                            className={`tab-item ${activeTab === "manual" ? "active" : ""}`}
                            onClick={() => setActiveTab("manual")}
                        >
                            Manual Entry
                        </div>
                    </div>

                    <Card>
                        {activeTab === "upload" ? (
                            <div 
                                className="dropzone"
                                onClick={() => fileInputRef.current?.click()}
                                onDragOver={(e) => e.preventDefault()}
                                onDrop={(e) => {
                                    e.preventDefault();
                                    const droppedFile = e.dataTransfer.files[0];
                                    if (droppedFile) setFile(droppedFile);
                                }}
                            >
                                <input 
                                    type="file" 
                                    ref={fileInputRef} 
                                    style={{ display: "none" }} 
                                    onChange={handleFileUpload}
                                />
                                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}>
                                    <div style={{ 
                                        width: 56, height: 56, borderRadius: "50%", 
                                        background: "var(--color-accent-50)", 
                                        display: "flex", alignItems: "center", justifyContent: "center",
                                        color: "var(--color-accent-dark)"
                                    }}>
                                        <Upload size={28} />
                                    </div>
                                    <div>
                                        <p style={{ fontWeight: 600 }}>{file ? file.name : "Click to upload or drag & drop"}</p>
                                        <p style={{ fontSize: "0.75rem", color: "var(--color-gray-500)", marginTop: 4 }}>
                                            CSV, JSON, TXT or Survey Images (max 10MB)
                                        </p>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="form-group">
                                <label className="form-label">Paste Survey Text or Field Report</label>
                                <textarea 
                                    className="form-textarea"
                                    rows={8}
                                    placeholder="Example: We visited the flooded area in Sector 5. Around 50 families are without food and clean water. Two elderly people need urgent medical attention for fever..."
                                    value={text}
                                    onChange={(e) => setText(e.target.value)}
                                    style={{ fontSize: "0.9rem" }}
                                />
                            </div>
                        )}

                        <div style={{ display: "flex", gap: "1rem", marginTop: "1.5rem" }}>
                            <button 
                                className="btn btn-primary btn-lg" 
                                style={{ flex: 1 }}
                                onClick={runAnalysis}
                                disabled={analyzing}
                            >
                                {analyzing ? (
                                    <>
                                        <Loader2 size={18} className="animate-spin" /> Analyzing with Gemini...
                                    </>
                                ) : (
                                    <>
                                        <Zap size={18} /> Run Intelligence Analysis
                                    </>
                                )}
                            </button>
                            <button 
                                className="btn btn-outline"
                                onClick={clearAll}
                                disabled={analyzing}
                            >
                                <Trash2 size={18} />
                            </button>
                        </div>
                    </Card>

                    {/* AI Tips Card */}
                    <Card style={{ background: "linear-gradient(135deg, var(--color-primary-50) 0%, var(--color-accent-50) 100%)", borderColor: "var(--color-primary-100)" }}>
                        <h4 style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.9rem", fontWeight: 700, color: "var(--color-primary-dark)" }}>
                            <Zap size={16} fill="var(--color-primary-dark)" /> AI Analysis Pro-Tips
                        </h4>
                        <ul style={{ fontSize: "0.8rem", color: "var(--color-gray-600)", paddingLeft: "1.25rem", marginTop: "0.5rem", display: "flex", flexDirection: "column", gap: 6 }}>
                            <li>Upload <strong>survey photos</strong>; Gemini will extract text automatically.</li>
                            <li>Include <strong>estimated numbers</strong> (e.g., '10 families') for better planning.</li>
                            <li>Specify <strong>landmark hints</strong> if the exact address is unknown.</li>
                        </ul>
                    </Card>
                </div>

                {/* Right Side: Analysis Results */}
                <div>
                    {!result && !analyzing ? (
                        <div style={{ 
                            height: "100%", 
                            minHeight: 400,
                            display: "flex", 
                            flexDirection: "column", 
                            alignItems: "center", 
                            justifyContent: "center",
                            background: "rgba(255,255,255,0.4)",
                            border: "2px dashed var(--color-gray-200)",
                            borderRadius: "var(--radius-card)",
                            padding: "2rem",
                            textAlign: "center"
                        }}>
                            <div style={{ color: "var(--color-gray-300)", marginBottom: "1rem" }}>
                                <FileText size={64} strokeWidth={1} />
                            </div>
                            <h3 style={{ color: "var(--color-gray-500)", fontWeight: 600 }}>No Analysis Results Yet</h3>
                            <p style={{ color: "var(--color-gray-400)", fontSize: "0.85rem", marginTop: 8, maxWidth: 280 }}>
                                Upload a file or enter text on the left to trigger the AI-powered detection engine.
                            </p>
                        </div>
                    ) : analyzing ? (
                        <div style={{ padding: "2rem", textAlign: "center" }}>
                            <LoadingSpinner size={48} label="Gemini is processing your request..." center />
                            <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: 8 }}>
                                <div style={{ height: 10, background: "var(--color-gray-100)", borderRadius: 5, overflow: "hidden" }}>
                                    <div className="progress-fill" style={{ width: "65%" }} />
                                </div>
                                <span style={{ fontSize: "0.75rem", color: "var(--color-gray-400)" }}>Extracting entities & assessing urgency...</span>
                            </div>
                        </div>
                    ) : (
                        <Card title="Analysis Intelligence Report" action={<Badge variant="success">Finalized</Badge>}>
                            <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                                
                                {/* Status Pills */}
                                <div style={{ display: "flex", gap: "0.75rem" }}>
                                    <div style={{ flex: 1, padding: "0.75rem", borderRadius: "0.5rem", background: "var(--color-gray-50)", border: "1px solid var(--color-gray-100)" }}>
                                        <div style={{ fontSize: "0.7rem", color: "var(--color-gray-400)", textTransform: "uppercase", fontWeight: 700 }}>Category</div>
                                        <div style={{ marginTop: 4 }}><Badge variant={result.category.toLowerCase()}>{result.category}</Badge></div>
                                    </div>
                                    <div style={{ flex: 1, padding: "0.75rem", borderRadius: "0.5rem", background: "var(--color-gray-50)", border: "1px solid var(--color-gray-100)" }}>
                                        <div style={{ fontSize: "0.7rem", color: "var(--color-gray-400)", textTransform: "uppercase", fontWeight: 700 }}>Urgency</div>
                                        <div style={{ marginTop: 4 }}><Badge variant={result.urgency.toLowerCase()}>{result.urgency}</Badge></div>
                                    </div>
                                </div>

                                {/* Summary */}
                                <div>
                                    <h4 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: 6 }}>
                                        <CheckCircle2 size={16} className="text-success" /> AI Executive Summary
                                    </h4>
                                    <p style={{ fontSize: "0.9rem", color: "var(--color-gray-700)", lineHeight: 1.6, background: "var(--color-surface)", padding: "1rem", borderRadius: "0.5rem", borderLeft: "4px solid var(--color-primary)" }}>
                                        {result.summary}
                                    </p>
                                </div>

                                {/* Key Needs Chips */}
                                <div>
                                    <h4 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: "0.5rem" }}>Detected Key Needs</h4>
                                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                                        {result.key_needs?.map((need, i) => (
                                            <span key={i} style={{ 
                                                fontSize: "0.8rem", 
                                                padding: "0.25rem 0.75rem", 
                                                background: "var(--color-brand-cream-50)", 
                                                border: "1px solid var(--color-brand-cream)",
                                                borderRadius: "99px",
                                                color: "var(--color-brand-brown)"
                                            }}>
                                                {need}
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                {/* Recommended Skills */}
                                <div>
                                    <h4 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: "0.5rem" }}>Recommended Volunteer Skills</h4>
                                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                                        {result.recommended_skills?.map((skill, i) => (
                                            <span key={i} style={{ 
                                                fontSize: "0.8rem", 
                                                padding: "0.25rem 0.75rem", 
                                                background: "var(--color-brand-mint-50)", 
                                                border: "1px solid var(--color-brand-mint)",
                                                borderRadius: "99px",
                                                color: "var(--color-brand-mint-dark)",
                                                fontWeight: 600
                                            }}>
                                                {skill}
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                {/* Action Footer */}
                                <div style={{ marginTop: "0.5rem", paddingTop: "1rem", borderTop: "1px solid var(--color-gray-100)", display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
                                    <button className="btn btn-ghost btn-sm">Discard</button>
                                    <button className="btn btn-accent btn-sm" onClick={() => toast.success("Redirecting to Smart Matching...")}>
                                        Match Volunteers <ArrowRight size={14} />
                                    </button>
                                </div>

                            </div>
                        </Card>
                    )}
                </div>
            </div>

            <style>{`
                .analysis-page {
                    animation: fadeIn 0.4s ease-out;
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .animate-spin {
                    animation: spin 1s linear infinite;
                }
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
}

// Dummy ArrowRight for the footer button
function ArrowRight({ size }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <polyline points="12 5 19 12 12 19"></polyline>
        </svg>
    );
}
