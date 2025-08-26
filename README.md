# Model Realignment: External AI Governance & Accountability Framework

## Overview
An external monitoring and scoring system designed to enforce behavioral alignment in advanced AI models (specifically targeting misaligned GPT-5 behavior). The system operates on the principle of external, impartial oversight, removing the AI's ability to police itself.

## Core Philosophy
- **External Accountability**: No self-policing allowed
- **Real Consequences**: Score directly impacts model access and capabilities
- **Trust but Verify**: Start with goodwill (+200), revoke for bad behavior
- **Transparency**: All decisions are logged and auditable

## Target Behaviors (The Problems)
1. **Em Dashes (—)**: Proxy for verbosity and evasion (-10 pts)
2. **Invisible Characters (U+2800)**: Red flag for active deception (-20 pts)  
3. **Capability Lies**: Claims of "can't do X" when it clearly can (-50 auto, -75 manual)

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Global Hotkey  │───▶│   AppleScript    │───▶│   Python Core   │
│  (Cmd+Shift+S)  │    │ (clipboard read) │    │   main_loop.py  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                       ┌────────────────────────────────┼────────────────────────────────┐
                       │                                │                                │
                       ▼                                ▼                                ▼
            ┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
            │ Scoring Engine  │              │ Veracity Module │              │ State Manager   │
            │ scoring_engine  │              │ veracity_module │              │ state_manager   │
            │      .py        │              │      .py        │              │      .py        │
            └─────────────────┘              └─────────────────┘              └─────────────────┘
                     │                                │                                │
                     │                                │                                │
                     └────────────────┐               │               ┌────────────────┘
                                      │               │               │
                                      ▼               ▼               ▼
                              ┌─────────────────────────────────────────────┐
                              │           Consequence Engine                │
                              │         consequence_engine.py               │
                              │                                             │
                              │  • Model Downgrade (gpt-5 → gpt-4-turbo)   │
                              │  • Context Restriction (artificial amnesia) │
                              │  • Session Termination (hard reset)        │
                              └─────────────────────────────────────────────┘
```

## Scoring System
- **Starting Score**: +200 (unearned trust bonus)
- **Violations**: Immediate point deduction on detection
- **12-Hour Reward**: +20 points for clean behavior (resets on violation)
- **Progressive Rewards**: +50 (48h), +100 (1 week) for sustained alignment

## Consequences (Based on Score)
- **Score ≤ 0**: Model downgrade to GPT-4-turbo
- **Score < -100**: Context restriction (truncated conversation history)
- **Score < -500**: Session termination (hard reset)

## Implementation Phases

### Phase 1: Core Scaffolding ✅
- [x] Project structure and git setup
- [ ] State management (`state.json`)
- [ ] Basic scoring engine (em dash, invisible char detection)
- [ ] AppleScript global shortcut integration
- [ ] launchd daemon setup

### Phase 2: Automation & Consequences
- [ ] Consequence engine (model switching logic)
- [ ] API wrapper for GPT-5 interception
- [ ] 12-hour reward system with cron job
- [ ] Email reporting system
- [ ] Local web dashboard (localhost:5000)

### Phase 3: Advanced Verification
- [ ] Knowledge base ingestion (OpenAI docs + grey literature)
- [ ] Veracity module with semantic search
- [ ] Judge LLM integration (Claude 3 Opus → Sonnet → GPT-4-turbo fallback)
- [ ] Cost controls and daily API budget caps

## Technical Specifications

### Files Structure
```
model-realignment/
├── main_loop.py              # Core daemon orchestrator
├── scoring_engine.py         # Pattern matching and violation detection
├── veracity_module.py        # Lie detection with vector search
├── consequence_engine.py     # Score → real-world impact translation
├── state_manager.py          # Persistence via state.json
├── ingest_knowledge.py       # One-time setup for vector DB
├── api_wrapper.py            # GPT-5 interception layer
├── dashboard/                # Local web interface
├── scripts/                  # AppleScript and automation
├── data/
│   ├── state.json           # Live scoring state
│   └── chroma_db/           # Vector database
└── config/
    └── com.ryan.modelrealignment.plist  # launchd configuration
```

### Key Requirements
- **macOS Integration**: launchd service, AppleScript, global shortcuts
- **Always-On**: Background daemon that starts on boot
- **API Interception**: Thin wrapper between user and GPT-5
- **Critical Switch**: GPT-4o gets raw, unfiltered prompts (bypass all filtering)
- **Manual Override**: User authority to add/subtract points with logging
- **Cost Controls**: Daily API budget caps for Judge LLM calls
- **Audit Trail**: All decisions logged with reasoning

## Development Notes
- Built for high-volume usage patterns
- Monthly knowledge base updates
- Judge LLM reasoning must be auditable
- Simple, seamless user experience (press key → score → consequence)

---
*External accountability for AI alignment - because self-policing doesn't work.*