import React, { useState, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import ConversationList from './components/ConversationList';
import './App.css';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);

  // Load conversations list on mount
  useEffect(() => {
    loadConversations();
  }, []);

  // Load current conversation when ID changes
  useEffect(() => {
    if (currentConversationId) {
      loadConversation(currentConversationId);
    }
  }, [currentConversationId]);

  const loadConversations = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/conversations');
      const data = await response.json();
      setConversations(data);
    } catch (error) {
      console.error('Error loading conversations:', error);
    }
  };

  const loadConversation = async (id) => {
    try {
      const response = await fetch(`http://localhost:8001/api/conversations/${id}`);
      const data = await response.json();
      setCurrentConversation(data);
    } catch (error) {
      console.error('Error loading conversation:', error);
    }
  };

  const createNewConversation = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/conversations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });
      const newConversation = await response.json();
      setCurrentConversationId(newConversation.id);
      setCurrentConversation(newConversation);
      await loadConversations();
    } catch (error) {
      console.error('Error creating conversation:', error);
    }
  };

  const handleSendMessage = async (content, mode = 'council') => {
    if (!currentConversationId) return;

    try {
      // Add user message AND empty assistant message placeholder
      setCurrentConversation(prev => ({
        ...prev,
        messages: [
          ...prev.messages,
          { role: 'user', content },
          {
            role: 'assistant',
            mode: mode,
            stage1: [],
            stage2: [],
            stage3: null,
            hybrid_phase1: [],
            hybrid_phase2: [],
            hybrid_phase3: null,
            hybrid_phase4: null,
            metadata: {}
          }
        ]
      }));

      let assistantMessage = {
        role: 'assistant',
        mode: mode,
        stage1: [],
        stage2: [],
        stage3: null,
        hybrid_phase1: [],
        hybrid_phase2: [],
        hybrid_phase3: null,
        hybrid_phase4: null,
        metadata: {}
      };

      // Choose endpoint based on mode
      const endpoint = mode === 'hybrid'
        ? `http://localhost:8001/api/conversations/${currentConversationId}/message/stream/hybrid`
        : `http://localhost:8001/api/conversations/${currentConversationId}/message/stream`;

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Decode the chunk
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));

            // --- Original council mode events ---
            if (data.type === 'stage1_complete') {
              assistantMessage.stage1 = data.data;
              setCurrentConversation(prev => {
                const updatedMessages = [...prev.messages];
                updatedMessages[updatedMessages.length - 1] = { ...assistantMessage };
                return { ...prev, messages: updatedMessages };
              });
            } else if (data.type === 'stage2_complete') {
              assistantMessage.stage2 = data.data;
              assistantMessage.metadata = data.metadata;
              setCurrentConversation(prev => {
                const updatedMessages = [...prev.messages];
                updatedMessages[updatedMessages.length - 1] = { ...assistantMessage };
                return { ...prev, messages: updatedMessages };
              });
            } else if (data.type === 'stage3_complete') {
              assistantMessage.stage3 = data.data;
              setCurrentConversation(prev => {
                const updatedMessages = [...prev.messages];
                updatedMessages[updatedMessages.length - 1] = { ...assistantMessage };
                return { ...prev, messages: updatedMessages };
              });

            // --- Hybrid mode events ---
            } else if (data.type === 'hybrid_phase1_complete') {
              assistantMessage.hybrid_phase1 = data.data;
              setCurrentConversation(prev => {
                const updatedMessages = [...prev.messages];
                updatedMessages[updatedMessages.length - 1] = { ...assistantMessage };
                return { ...prev, messages: updatedMessages };
              });
            } else if (data.type === 'hybrid_phase2_complete') {
              assistantMessage.hybrid_phase2 = data.data;
              setCurrentConversation(prev => {
                const updatedMessages = [...prev.messages];
                updatedMessages[updatedMessages.length - 1] = { ...assistantMessage };
                return { ...prev, messages: updatedMessages };
              });
            } else if (data.type === 'hybrid_phase3_complete') {
              assistantMessage.hybrid_phase3 = data.data;
              setCurrentConversation(prev => {
                const updatedMessages = [...prev.messages];
                updatedMessages[updatedMessages.length - 1] = { ...assistantMessage };
                return { ...prev, messages: updatedMessages };
              });
            } else if (data.type === 'hybrid_phase4_complete') {
              assistantMessage.hybrid_phase4 = data.data;
              setCurrentConversation(prev => {
                const updatedMessages = [...prev.messages];
                updatedMessages[updatedMessages.length - 1] = { ...assistantMessage };
                return { ...prev, messages: updatedMessages };
              });

            // --- Shared events ---
            } else if (data.type === 'title_complete') {
              setCurrentConversation(prev => ({
                ...prev,
                title: data.data.title
              }));
              loadConversations();
            } else if (data.type === 'complete') {
              loadConversations();
            } else if (data.type === 'error') {
              console.error('Stream error:', data.message);
              break;
            }
          }
        }
      }

    } catch (error) {
      console.error('Error sending message:', error);
    }
  };

  const handleUpdateTitle = (newTitle) => {
    setCurrentConversation(prev => ({
      ...prev,
      title: newTitle
    }));
    loadConversations();
  };

  const handleDeleteConversation = () => {
    setCurrentConversationId(null);
    setCurrentConversation(null);
    loadConversations();
  };

  return (
    <div className="app">
      <div className="sidebar">
        <button
          className="new-conversation-btn"
          onClick={createNewConversation}
        >
          + New Conversation
        </button>
        <ConversationList
          conversations={conversations}
          currentId={currentConversationId}
          onSelect={setCurrentConversationId}
        />
      </div>
      <div className="main">
        {currentConversation ? (
          <ChatInterface
            conversationId={currentConversationId}
            messages={currentConversation.messages}
            onSendMessage={handleSendMessage}
            onUpdateTitle={handleUpdateTitle}
            onDelete={handleDeleteConversation}
          />
        ) : (
          <div className="welcome">
            <h1>Model Behavior</h1>
            <p>Create a new conversation or select one from the sidebar to begin.</p>
<p style={{ fontSize: "12px", color: "#9ca3af", marginTop: "24px" }}>by Niiblr · based on <a href="https://github.com/karpathy/llm-council" target="_blank" style={{ color: "#9ca3af" }}>karpathy/llm-council</a></p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
