'use client';
import { useState, useEffect } from 'react';
import { Send, Sparkles } from 'lucide-react';
import { api } from '@/lib/api';
import { Badge, Empty, Failure, Heading, Loading } from './ui';

export function RAGChat() {
  const [question, setQuestion] = useState('');
  const [history, setHistory] = useState<Array<{ question: string; answer: string; sources: any[] }>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const askQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api<{ answer: string; sources: any[]; num_results: number }>(
        '/simple-rag/query',
        'POST',
        { question, top_k: 3 }
      );

      setHistory([...history, { question, answer: response.answer, sources: response.sources }]);
      setQuestion('');
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Heading eyebrow="Ask about internships" title="AI-powered Q&A">
        Get answers about internship requirements, skills, and opportunities using your indexed data.
      </Heading>
      <div className="card">
        <div className="chat-container">
          {history.length === 0 ? (
            <Empty title="No questions yet">
              Ask about internship requirements, skills needed for specific roles, or general
              questions about available opportunities.
            </Empty>
          ) : (
            <div className="chat-messages">
              {history.map((msg, idx) => (
                <div key={idx} className="chat-message">
                  <div className="user-message">
                    <span className="message-label">You</span>
                    <p>{msg.question}</p>
                  </div>
                  <div className="ai-message">
                    <span className="message-label">
                      <Sparkles size={14} style={{ display: 'inline', marginRight: 4 }} />
                      AI
                    </span>
                    <p>{msg.answer}</p>
                    {msg.sources.length > 0 && (
                      <div className="sources">
                        <h4 style={{ fontSize: 12, margin: '12px 0 8px' }}>Similar internships:</h4>
                        {msg.sources.map((source, sIdx) => (
                          <div key={sIdx} className="source-item">
                            <Badge>{`${(source.similarity * 100).toFixed(0)}%`}</Badge>
                            <small>{source.title}</small>
                            <div className="chips">
                              {source.skills.slice(0, 3).map((skill: string) => (
                                <span className="chip" key={skill} style={{ fontSize: 11 }}>
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        {error && <Failure error={error} retry={() => setError(null)} />}
        <form onSubmit={askQuestion} className="chat-input">
          <input
            type="text"
            placeholder="Ask about internships (e.g., 'What skills are needed for data science roles?')"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="button" disabled={loading || !question.trim()}>
            {loading ? <Loading size={16} /> : <Send size={16} />}
          </button>
        </form>
        <p className="muted" style={{ fontSize: 12, marginTop: 12 }}>
          Answers are based on semantic similarity to indexed internships. Not hiring advice or
          guaranteed outcomes.
        </p>
      </div>
    </>
  );
}
