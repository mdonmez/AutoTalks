<div align="center">
  <a href="https://github.com/mdonmez/taibu"></a>
  <br>
  <h1>AutoTalks</h1>
  <p>
    A tool that matches live spoken text to transcripts using advanced matching algorithms in real time.
  </p>
</div>

## Introduction
The aim of this project is to enable the speaker to present fluently without using pointers, interacting with the screen or running an extra person in the background in presentations where the speech and the slide are the same. To do this, it uses a real-time STT system running in the background with two algorithms and advanced similarity algorithms.

## Operation Logic
### Chunk Generation
The transcript is divided into chunks of 7 words each. It uses a sliding window approach to generate chunks. Also it normalizes the transcript to remove any extra spaces and punctuation.
Here is the example:
```
Text: "I want to start with a question: Is there anyone here who doesn't use AI?"
Chunks: [
    "i want to start with a question",
    "question is there anyone here who doesn't",
    "is there anyone here who doesn't use",
    "there anyone here who doesn't use ai"
]
```

This approach allows the system to match the speaker's speech to the transcript with high accuracy. Instead of searching the entire transcript, it only searches the relevant chunks.

#### Chunk Labeling
The chunks are stored in a JSON file with the following format:
```json
[
    {
        "chunk_number": 1,
        "transcript": "i want to start with a question",
        "matched_transcript": 1,
        "type": "normal"
    }
]
```
#### Chunk Types
- `hybrid`: The chunk is a hybrid of the n. and n+1. transcript. This is for selecting next transcript when STT detects speech from both previous and current transcript. 
- `normal`: The chunk is from n. transcript. It's for validating the current transcript.
- `last`: The chunk is from current transcript's last chunk. This is for selecting next transcript because STT may be late and speaker may start speaking from next transcript.

### Real-time STT
The system uses [RealtimeSTT](https://github.com/KoljaB/RealtimeSTT), a real-time STT system, to transcribe the speaker's speech in real-time. It uses Whisper as the STT engine with tiny.en model for speed.

### Matching
The matching system gets revelant chunks and last 7 word from live speech to match with the transcript. The system uses two algorithms to match the speaker's speech to the transcript:

#### Primary Partial Matching (%60 threshold)
- It gets also the current_transcript_number for more fast matching.
- It uses partial matching to match the speaker's speech to the transcript. It searches across:
    - Previous transcript's last chunk
    - Hybrid chunks between previous and current transcript
    - Current transcript's all chunks
    - Hybrid chunks between current and next transcript
    - Next transcript's all chunks
- The partial and only filtered chunk matching improves the matching accuracy and speed.

#### Secondary Full Matching (%50 threshold)
- It uses full matching to match the speaker's speech to the transcript. It searches across:
    - Entire chunks from all transcripts
- The full matching allows fallback if speaker speaks too fast or system losts context. It is slow but necessary and reliable.

If both algorithms fail to match the speaker's speech to the transcript, it returns `None`. And remains on the current transcript.

There are three matched chunk types:
- `normal`: If system detects speech from this type of chunk, it means speaker is speaking from current transcript. And it returns transcript number as `matched_transcript_number` from `TranscriptMatcher.match_speech`.
- `hybrid`: If system detects speech from this type of chunk, it means speaker is speaking from both transcripts. And it returns transcript number as `matched_transcript_number + 1` from `TranscriptMatcher.match_speech`.
- `last`: If system detects speech from this type of chunk, it means speaker is speaking from next transcript's last chunk. And it returns transcript number as `matched_transcript_number + 1` from `TranscriptMatcher.match_speech`.

### Installation
works on my computer :). soon, i'll provide installation instructions.