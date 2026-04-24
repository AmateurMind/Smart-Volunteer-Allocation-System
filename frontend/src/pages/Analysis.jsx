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
    Send,
    ArrowRight,
    Sparkles,
    FileSearch,
    ShieldCheck
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
        
        const validTypes = ['text/plain', 'application/json', 'text/csv', 'image/jpeg', 'image/png', 'application/pdf'];
        if (!validTypes.includes(selectedFile.type)) {
            toast.error("Invalid file type. Please upload TXT, JSON, CSV, PDF or an Image.");
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
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Header */}
            <div className="mb-10">
                <h1 className="font-serif text-4xl text-brand-brown-dark mb-2">AI Need Detection</h1>
                <p className="text-muted-foreground font-medium flex items-center gap-2 uppercase tracking-widest text-[10px]">
                    <Sparkles size={14} className="text-brand-gold" />
                    Harness Gemini 1.5 Flash to extract and prioritize community needs
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                
                {/* Input Panel */}
                <div className="space-y-6">
                    <div className="bg-brand-brown/5 p-1.5 rounded-xl flex gap-1">
                        <button 
                            onClick={() => setActiveTab("upload")}
                            className={`flex-1 py-2.5 px-4 rounded-lg text-xs font-bold transition-all ${
                                activeTab === "upload" 
                                    ? "bg-white text-brand-brown shadow-sm" 
                                    : "text-brand-brown/60 hover:text-brand-brown"
                            }`}
                        >
                            Upload Document
                        </button>
                        <button 
                            onClick={() => setActiveTab("manual")}
                            className={`flex-1 py-2.5 px-4 rounded-lg text-xs font-bold transition-all ${
                                activeTab === "manual" 
                                    ? "bg-white text-brand-brown shadow-sm" 
                                    : "text-brand-brown/60 hover:text-brand-brown"
                            }`}
                        >
                            Manual Entry
                        </button>
                    </div>

                    <div className="bg-white rounded-2xl p-6 border border-brand-cream/30 shadow-sm">
                        {activeTab === "upload" ? (
                            <div 
                                onClick={() => fileInputRef.current?.click()}
                                className={`group cursor-pointer border-2 border-dashed rounded-xl p-10 flex flex-col items-center text-center gap-4 transition-all ${
                                    file ? "border-brand-mint bg-brand-mint/5" : "border-brand-cream/50 hover:border-brand-gold hover:bg-brand-cream/5"
                                }`}
                            >
                                <input 
                                    type="file" 
                                    ref={fileInputRef} 
                                    className="hidden" 
                                    onChange={handleFileUpload}
                                />
                                <div className={`w-14 h-14 rounded-full flex items-center justify-center transition-colors ${
                                    file ? "bg-brand-mint text-brand-mint-dark" : "bg-brand-cream-50 text-brand-brown/40 group-hover:bg-brand-gold/10 group-hover:text-brand-gold"
                                }`}>
                                    <Upload size={24} />
                                </div>
                                <div>
                                    <p className="font-bold text-brand-brown-dark">{file ? file.name : "Click or drag to upload survey"}</p>
                                    <p className="text-[11px] text-muted-foreground mt-1 font-medium">CSV, JSON, PDF or Field Images (max 10MB)</p>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                <label className="text-xs font-bold text-brand-brown/60 uppercase tracking-widest ml-1">Survey Text or Field Report</label>
                                <textarea 
                                    className="w-full rounded-xl border border-brand-cream/50 p-4 min-h-[200px] text-sm font-medium focus:ring-4 focus:ring-brand-gold/10 focus:border-brand-gold outline-none transition-all resize-none"
                                    placeholder="Example: We visited the flooded area in Sector 5. Around 50 families are without food and clean water. Urgent medical attention needed for fever cases..."
                                    value={text}
                                    onChange={(e) => setText(e.target.value)}
                                />
                            </div>
                        )}

                        <div className="flex gap-4 mt-8">
                            <button 
                                onClick={runAnalysis}
                                disabled={analyzing}
                                className="flex-1 bg-brand-brown text-white font-bold py-3.5 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-brand-brown/20 hover:bg-brand-brown-dark hover:-translate-y-0.5 transition-all disabled:opacity-70 disabled:hover:translate-y-0"
                            >
                                {analyzing ? (
                                    <>
                                        <Loader2 size={18} className="animate-spin" />
                                        <span>Analyzing with Gemini...</span>
                                    </>
                                ) : (
                                    <>
                                        <Zap size={18} className="text-brand-gold" fill="currentColor" />
                                        <span>Run AI Intelligence</span>
                                    </>
                                )}
                            </button>
                            <button 
                                onClick={clearAll}
                                disabled={analyzing}
                                className="px-5 border border-brand-cream/50 rounded-xl text-brand-brown/40 hover:text-red-500 hover:border-red-100 hover:bg-red-50 transition-all"
                            >
                                <Trash2 size={20} />
                            </button>
                        </div>
                    </div>

                    {/* AI Info Card */}
                    <div className="bg-gradient-to-br from-brand-brown to-brand-brown-dark rounded-2xl p-6 text-white shadow-xl">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center">
                                <ShieldCheck size={18} className="text-brand-gold" />
                            </div>
                            <h4 className="font-bold text-sm">Pro Analysis Tips</h4>
                        </div>
                        <ul className="space-y-3">
                            {[
                                "Upload survey photos for OCR extraction.",
                                "Gemini detects priority based on context.",
                                "Entity detection extracts locations & counts.",
                            ].map((tip, i) => (
                                <li key={i} className="flex items-start gap-2 text-xs text-white/70 leading-relaxed">
                                    <div className="w-1.5 h-1.5 rounded-full bg-brand-gold shrink-0 mt-1.5" />
                                    <span>{tip}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>

                {/* Results Panel */}
                <div className="lg:sticky lg:top-24 h-fit">
                    {!result && !analyzing ? (
                        <div className="bg-brand-cream/5 border-2 border-dashed border-brand-cream/30 rounded-3xl p-12 flex flex-col items-center text-center justify-center min-h-[500px]">
                            <div className="w-20 h-20 rounded-full bg-white flex items-center justify-center text-brand-brown/10 shadow-inner mb-6">
                                <FileSearch size={40} />
                            </div>
                            <h3 className="text-xl font-bold text-brand-brown/40">Waiting for Data</h3>
                            <p className="text-sm text-brand-brown/30 mt-2 max-w-[280px]">
                                Upload a document or type a report to see AI-powered detection in action.
                            </p>
                        </div>
                    ) : analyzing ? (
                        <div className="bg-white rounded-3xl p-12 flex flex-col items-center text-center justify-center min-h-[500px] border border-brand-cream/30 shadow-sm relative overflow-hidden">
                            <div className="absolute top-0 left-0 w-full h-1 bg-brand-cream/20">
                                <div className="h-full bg-brand-gold animate-pulse w-2/3" />
                            </div>
                            <LoadingSpinner size={48} color="var(--color-brand-brown)" />
                            <p className="mt-6 font-bold text-brand-brown-dark">Gemini 1.5 Flash is thinking...</p>
                            <p className="text-xs text-muted-foreground mt-2">Extracting needs and assessing community urgency</p>
                        </div>
                    ) : (
                        <div className="bg-white rounded-3xl border border-brand-cream/30 shadow-xl overflow-hidden animate-in zoom-in-95 duration-300">
                            <div className="bg-brand-brown p-6 text-white flex justify-between items-center">
                                <div>
                                    <h3 className="font-bold text-lg">Intelligence Report</h3>
                                    <p className="text-[10px] text-brand-cream/50 uppercase tracking-widest font-bold">Processed by AI Engine</p>
                                </div>
                                <Badge variant="success" className="bg-brand-gold text-brand-brown border-none font-bold">Finalized</Badge>
                            </div>

                            <div className="p-8 space-y-8">
                                {/* Stats */}
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-brand-cream-50 p-4 rounded-2xl border border-brand-cream/30">
                                        <p className="text-[10px] font-bold text-brand-brown/40 uppercase tracking-widest mb-1">Category</p>
                                        <Badge variant={result.category?.toLowerCase()} className="text-[10px] uppercase font-bold px-2 py-0.5">{result.category}</Badge>
                                    </div>
                                    <div className="bg-brand-cream-50 p-4 rounded-2xl border border-brand-cream/30">
                                        <p className="text-[10px] font-bold text-brand-brown/40 uppercase tracking-widest mb-1">Urgency</p>
                                        <Badge variant={result.urgency?.toLowerCase()} className="text-[10px] uppercase font-bold px-2 py-0.5">{result.urgency}</Badge>
                                    </div>
                                </div>

                                {/* Summary */}
                                <div className="space-y-3">
                                    <div className="flex items-center gap-2">
                                        <Sparkles size={16} className="text-brand-gold" />
                                        <h4 className="text-xs font-bold text-brand-brown/60 uppercase tracking-widest">Executive Summary</h4>
                                    </div>
                                    <p className="text-sm font-medium leading-relaxed text-brand-brown-dark bg-brand-cream-50/50 p-5 rounded-2xl border-l-4 border-brand-gold italic">
                                        "{result.summary}"
                                    </p>
                                </div>

                                {/* Detected Needs */}
                                <div className="space-y-3">
                                    <h4 className="text-xs font-bold text-brand-brown/60 uppercase tracking-widest ml-1">Key Needs Detected</h4>
                                    <div className="flex flex-wrap gap-2">
                                        {result.key_needs?.map((need, i) => (
                                            <span key={i} className="px-3 py-1.5 rounded-lg bg-brand-cream-50 border border-brand-cream/30 text-xs font-bold text-brand-brown-dark">
                                                {need}
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                {/* Recommended Skills */}
                                <div className="space-y-3">
                                    <h4 className="text-xs font-bold text-brand-brown/60 uppercase tracking-widest ml-1">Required Volunteer Skills</h4>
                                    <div className="flex flex-wrap gap-2">
                                        {result.recommended_skills?.map((skill, i) => (
                                            <span key={i} className="px-3 py-1.5 rounded-lg bg-brand-mint/20 border border-brand-mint/30 text-xs font-bold text-brand-mint-dark">
                                                {skill}
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                {/* Footer Action */}
                                <div className="pt-6 border-t border-brand-cream/20 flex gap-3">
                                    <button className="flex-1 py-3 text-xs font-bold text-brand-brown/60 hover:bg-brand-cream-50 rounded-xl transition-colors">Discard</button>
                                    <button 
                                        className="flex-[2] py-3 bg-brand-gold text-brand-brown font-bold rounded-xl text-xs flex items-center justify-center gap-2 hover:bg-brand-gold-dark transition-all shadow-lg shadow-brand-gold/20"
                                        onClick={() => toast.success("Redirecting to Smart Matching...")}
                                    >
                                        <span>Proceed to Matching</span>
                                        <ArrowRight size={14} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
