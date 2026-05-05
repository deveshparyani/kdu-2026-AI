# Customer Service Agent System

This is a single project with two major capabilities:

- real-time voice handoff: `TriageAgent` -> `BillingAgent`
- coordinator-based parallel retrieval: `DB Agent` + `Vector Agent` -> `Consensus Agent`
- scaling and production controls: memory compaction, service gates, structured replay logs

The codebase is organized by responsibility, not by isolated “phase folders”:

- `customer_service/audio/` for live audio handling
- `customer_service/services/` for API clients
- `customer_service/retrieval/` for parallel worker orchestration
- `customer_service/` for shared config, state, logging, and top-level flows

## Why this design

The voice runtime and the agent runtime are intentionally separated:

- the **audio runtime** handles mic input, VAD, buffering, playback, and interruption
- the **CrewAI layer** handles intent routing and state handoff

That separation makes the system easier to reason about and much easier to explain during review.

## Architecture

```text
Mic Input
  -> Ring Buffer + VAD
  -> Finalized user turn (WAV)
  -> Whisper transcription
  -> CrewAI VoiceHandoffFlow
       -> TriageAgent
       -> explicit HandoffPayload
       -> BillingAgent
  -> response text
  -> OpenAI TTS stream (PCM)
  -> speaker playback queue

During playback:
  mic stays active
  -> barge-in detector watches live audio
  -> if sustained speech is detected:
       cancel TTS
       flush speaker queue
       preserve mic pre-roll
       capture next user turn
```

## Project layout

```text
customer_service/
  agents.py
  audio/runtime.py
  cli.py
  config.py
  event_listener.py
  logging_utils.py
  query.py
  retrieval/
  services/openai_audio.py
  state.py
  voice.py
  voice_flow.py
tests/
```

## Quick start

1. Create a virtual environment
2. Install dependencies
3. Copy `.env.example` to `.env`
4. Set `OPENAI_API_KEY`
5. Start the app

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
customer-service voice
```

## Parallel retrieval quick start

```bash
customer-service query "Why was I charged twice this month?"
```

## Replay quick start

```bash
customer-service replay trace <trace_id>
customer-service replay session <session_id>
```

## Controls

- Speak normally to start a turn
- Pause briefly to end a turn
- Speak while the assistant is talking to interrupt it
- Press `Ctrl+C` to exit

## Production-minded behaviors included

- explicit handoff schema instead of hidden in free-form text
- rolling conversation summary to keep prompts small
- speaker queue flushing on interruption
- message truncation tracking for interrupted responses
- per-service concurrency gates for shared dependencies
- degraded-mode consensus skipping under pressure
- structured JSONL logs for replay
- exact JSON payload logging for handoffs, worker outputs, and consensus inputs
- CrewAI event listener for agent-level telemetry
- no prebuilt voice wrapper usage

## Exact handoff state

The handoff object passed from triage to billing contains:

- `session_id`
- `turn_id`
- `intent`
- `confidence`
- `latest_user_utterance`
- `conversation_summary`
- `entities`
- `trace_id`

This is stored as `HandoffPayload` in `customer_service/state.py`.

## How interruption is handled

1. mic capture remains live during playback
2. input frames keep filling a ring buffer
3. if sustained speech crosses the barge-in threshold:
   - current TTS generation is canceled
   - queued audio is flushed
   - a new capture starts with pre-roll audio included
4. the interrupted assistant turn is marked as `interrupted=true`
5. only the heard prefix is kept in session history

## Logging

JSONL logs are written to the directory configured by `APP_LOG_DIR`.

You will see:

- `audio_frame_status`
- `user_turn_finalized`
- `transcription_completed`
- `handoff_created`
- `tts_started`
- `playback_interrupted`
- `agent_started`
- `agent_completed`
- `agent_failed`
- `service_gate_acquired`
- `service_gate_released`
- `service_gate_rejected`

## Scaling controls

The current codebase includes:

- memory compaction before handoffs
- bounded recent-turn windows
- summary-length caps
- DB / vector / consensus concurrency gates
- queue rejection to protect overloaded dependencies
- replay support from exact JSON event logs

## AI voice disclosure

OpenAI’s TTS guidance requires a clear disclosure that the voice is AI-generated. This app prints that disclosure at startup, and you should keep that behavior if you wrap this into a UI.

## Notes on model choices

- STT defaults to `whisper-1` to match the lab requirement
- TTS defaults to `gpt-4o-mini-tts`
- CrewAI text routing defaults to `gpt-4o-mini` for broad compatibility and low cost

If your environment supports newer nano or mini models cleanly through CrewAI/LiteLLM, switch `AGENT_MODEL` in `.env`.

## Useful references

- [OpenAI audio guide](https://developers.openai.com/api/docs/guides/audio)
- [OpenAI text-to-speech guide](https://developers.openai.com/api/docs/guides/text-to-speech)
- [OpenAI speech-to-text guide](https://developers.openai.com/api/docs/guides/speech-to-text)
- [CrewAI Flows](https://docs.crewai.com/en/concepts/flows)
- [CrewAI Agents kickoff](https://docs.crewai.com/en/concepts/agents)
- [CrewAI Event Listeners](https://docs.crewai.com/en/concepts/event-listener)
