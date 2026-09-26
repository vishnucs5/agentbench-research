import { useState, useRef, useEffect } from "react"
import { Link } from "react-router-dom"
import {
  ChevronRight,
  Send,
  Bot,
  User as UserIcon,
  BookOpen,
  FolderOpen,
  Sparkles,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Sliders,
} from "lucide-react"
import { useProject } from "@/contexts/ProjectContext"
import { chatApi } from "@/lib/api"
import type { ChatMessage, ChatCitation } from "@/types"

interface DisplayMessage {
  id: string
  role: "user" | "assistant"
  content: string
  citations?: ChatCitation[]
  model?: string
  timestamp: string
}

const SAMPLE_PROMPTS = [
  "What detection rates and benchmark accuracies are reported across the papers?",
  "Compare the evaluation datasets and traffic distribution methodologies.",
  "What are the recurring limitations or zero-day vulnerabilities identified?",
  "Summarize the comparative trade-offs between Transformer and CNN architectures.",
]

export default function LiteratureChat() {
  const { projects, selectedProject, setSelectedProject } = useProject()
  const [messages, setMessages] = useState<DisplayMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hello! I am your literature research assistant. Ask any question about your ingested papers, and I will synthesize evidence-grounded answers with direct page and excerpt citations.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ])
  const [query, setQuery] = useState("")
  const [loading, setLoading] = useState(false)
  const [topK, setTopK] = useState(5)
  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({})
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  function toggleCitation(msgId: string, idx: number) {
    const key = `${msgId}_${idx}`
    setExpandedCitations((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  function handleReset() {
    setMessages([
      {
        id: "welcome",
        role: "assistant",
        content: `Conversation reset. Ready to answer questions on papers in ${selectedProject?.name || "your project"}.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ])
  }

  async function handleSend(textToSend?: string) {
    const text = (textToSend || query).trim()
    if (!text || !selectedProject || loading) return

    const userMsg: DisplayMessage = {
      id: `user_${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    }

    setMessages((prev) => [...prev, userMsg])
    setQuery("")
    setLoading(true)

    try {
      const history: ChatMessage[] = messages
        .filter((m) => m.id !== "welcome")
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content }))

      const res = await chatApi.sendMessage(selectedProject.id, {
        query: text,
        top_k: topK,
        conversation_history: history,
      })

      const botMsg: DisplayMessage = {
        id: `bot_${Date.now()}`,
        role: "assistant",
        content: res.answer,
        citations: res.citations,
        model: res.model,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      }

      setMessages((prev) => [...prev, botMsg])
    } catch (err) {
      const errMsg: DisplayMessage = {
        id: `err_${Date.now()}`,
        role: "assistant",
        content: `Error generating grounded response: ${err instanceof Error ? err.message : "Unknown error"}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      }
      setMessages((prev) => [...prev, errMsg])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto h-[calc(100vh-80px)] flex flex-col">
      {/* Header */}
      <div className="space-y-2 shrink-0">
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Link to="/" className="hover:text-foreground transition-colors">
            Overview
          </Link>
          <ChevronRight size={12} />
          <span className="text-foreground font-medium">Literature Q&A</span>
        </nav>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-accent">
                MULTIDOCUMENT RETRIEVAL & SYNTHESIS
              </p>
              <span className="inline-flex items-center gap-1 rounded-md bg-accent/10 px-2 py-0.5 text-[10px] font-mono font-medium text-accent">
                <Sparkles size={10} /> Hybrid BM25 · Evidence Grounding
              </span>
            </div>
            <h1 className="text-2xl font-bold text-foreground tracking-tight">
              Literature Q&A ("Chat with Papers")
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Project Selector */}
            <div className="flex items-center gap-2 bg-panel border border-border p-1.5 px-3 rounded-xl text-xs">
              <FolderOpen size={14} className="text-accent" />
              <select
                value={selectedProject?.id || ""}
                onChange={(e) => {
                  const p = projects.find((x) => x.id === e.target.value)
                  if (p) setSelectedProject(p)
                }}
                className="bg-transparent text-foreground focus:outline-none"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id} className="bg-panel text-foreground">
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Clear button */}
            <button
              onClick={handleReset}
              title="Reset Conversation"
              className="p-2 rounded-xl bg-panel border border-border hover:bg-panel-light text-muted-foreground hover:text-foreground transition-colors"
            >
              <RotateCcw size={15} />
            </button>
          </div>
        </div>
      </div>

      {/* Main Chat Container */}
      <div className="flex-1 flex flex-col rounded-2xl border border-border bg-panel overflow-hidden shadow-sm">
        {/* Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg) => {
            const isUser = msg.role === "user"
            return (
              <div
                key={msg.id}
                className={`flex gap-3 max-w-3xl ${isUser ? "ml-auto flex-row-reverse" : "mr-auto"}`}
              >
                {/* Avatar */}
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                    isUser ? "bg-accent text-accent-foreground" : "bg-panel-light border border-border text-accent"
                  }`}
                >
                  {isUser ? <UserIcon size={16} /> : <Bot size={16} />}
                </div>

                {/* Message Bubble */}
                <div className="space-y-3 flex-1">
                  <div
                    className={`p-4 rounded-2xl text-sm leading-relaxed ${
                      isUser
                        ? "bg-accent text-accent-foreground font-medium rounded-tr-none"
                        : "bg-panel-light border border-border text-foreground rounded-tl-none"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    <div
                      className={`text-[10px] mt-2 flex items-center justify-between ${
                        isUser ? "text-accent-foreground/70" : "text-muted-foreground"
                      }`}
                    >
                      <span>{msg.timestamp}</span>
                      {msg.model && <span className="font-mono text-[9px] uppercase">{msg.model}</span>}
                    </div>
                  </div>

                  {/* Grounded Citation Pills / Accordions */}
                  {!isUser && msg.citations && msg.citations.length > 0 && (
                    <div className="space-y-2 pt-1">
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                        <BookOpen size={12} className="text-accent" />
                        <span>Grounded Source Excerpts ({msg.citations.length})</span>
                      </div>

                      <div className="grid grid-cols-1 gap-2">
                        {msg.citations.map((c, i) => {
                          const key = `${msg.id}_${i}`
                          const isExpanded = !!expandedCitations[key]
                          return (
                            <div
                              key={key}
                              className="rounded-xl border border-border bg-panel text-xs overflow-hidden transition-all"
                            >
                              <button
                                onClick={() => toggleCitation(msg.id, i)}
                                className="w-full flex items-center justify-between px-3.5 py-2.5 hover:bg-panel-light transition-colors text-left"
                              >
                                <div className="flex items-center gap-2 truncate">
                                  <span className="font-mono font-bold text-accent">[{i + 1}]</span>
                                  <span className="font-medium text-foreground truncate max-w-sm">
                                    {c.paper_title}
                                  </span>
                                  {c.page && (
                                    <span className="text-[10px] text-muted-foreground shrink-0">
                                      · Page {c.page}
                                    </span>
                                  )}
                                  {c.year && (
                                    <span className="text-[10px] text-muted-foreground shrink-0">
                                      · {c.year}
                                    </span>
                                  )}
                                </div>
                                {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                              </button>

                              {isExpanded && (
                                <div className="px-3.5 pb-3 pt-1 border-t border-border/50 bg-[#0a0f1d] text-muted-foreground">
                                  <p className="font-mono text-[11px] leading-relaxed whitespace-pre-wrap text-foreground/90">
                                    "{c.chunk_text}"
                                  </p>
                                  {c.authors && c.authors.length > 0 && (
                                    <div className="mt-2 text-[10px] text-muted-foreground">
                                      Authors: {c.authors.join(", ")}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )
          })}

          {/* Loading Indicator */}
          {loading && (
            <div className="flex gap-3 mr-auto max-w-xl">
              <div className="w-8 h-8 rounded-full bg-panel-light border border-border flex items-center justify-center text-accent shrink-0">
                <Bot size={16} />
              </div>
              <div className="p-4 rounded-2xl rounded-tl-none bg-panel-light border border-border text-xs text-muted-foreground flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-accent animate-ping" />
                <span>Retrieving paper chunks & synthesizing grounded response...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Starter Prompts (if chat is short) */}
        {messages.length <= 2 && (
          <div className="px-6 py-2 border-t border-border bg-panel-light/30">
            <p className="text-[11px] font-semibold text-muted-foreground mb-2 flex items-center gap-1">
              <Sparkles size={11} className="text-accent" /> Suggested research inquiries:
            </p>
            <div className="flex flex-wrap gap-1.5">
              {SAMPLE_PROMPTS.map((p, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(p)}
                  className="text-xs px-2.5 py-1 rounded-lg bg-panel border border-border text-muted-foreground hover:text-foreground hover:border-accent transition-all text-left"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input Bar */}
        <div className="p-4 border-t border-border bg-panel-light/50">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSend()
            }}
            className="flex items-center gap-2"
          >
            {/* Top-K Selector */}
            <div className="flex items-center gap-1 bg-panel border border-border px-2 py-2 rounded-xl text-xs shrink-0 text-muted-foreground" title="Evidence chunk budget">
              <Sliders size={13} className="text-accent" />
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="bg-transparent text-foreground focus:outline-none text-xs"
              >
                <option value={3} className="bg-panel">Top 3 Chunks</option>
                <option value={5} className="bg-panel">Top 5 Chunks</option>
                <option value={8} className="bg-panel">Top 8 Chunks</option>
              </select>
            </div>

            <input
              type="text"
              placeholder={`Ask a question across papers in "${selectedProject?.name || "your project"}"...`}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={loading || !selectedProject}
              className="flex-1 text-sm px-4 py-2.5 rounded-xl bg-panel border border-border text-foreground focus:outline-none focus:border-accent"
            />

            <button
              type="submit"
              disabled={!query.trim() || loading || !selectedProject}
              className="flex items-center justify-center w-10 h-10 rounded-xl bg-accent text-accent-foreground hover:bg-accent/90 disabled:opacity-50 transition-colors shadow-sm shrink-0"
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
