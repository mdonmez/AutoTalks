import logging
import re
realtimestt_logger = logging.getLogger("realtimestt")
realtimestt_logger.setLevel(logging.WARNING)
logging.basicConfig(level=logging.WARNING)
import keyboard
from pydantic import BaseModel
import os
import json
os.environ["TORCH_HOME"] = "C:/torch_cache"




from components.transcript_matcher import TranscriptMatcher
from components.chunk_generator import ChunkGenerator
from RealtimeSTT import AudioToTextRecorder



class ProcessedResult(BaseModel):
    matched_transcript_number: int
    operator: str



chunk_generator = ChunkGenerator()
transcript_matcher = TranscriptMatcher()

PERSON_NAME = "elif"


chunk_file = f"data/chunks/{PERSON_NAME}.json"
transcript_file = f"data/transcripts/{PERSON_NAME}.json"

primary_threshold = 0.6
secondary_threshold = 0.5


try:
    with open(chunk_file, 'r', encoding='utf-8') as f:
        chunk_data = json.load(f)
except Exception as e:
    print(f"Failed to load chunks from {chunk_file}: {e}")
    with open(transcript_file, 'r', encoding='utf-8') as f:
        chunk_data = chunk_generator.generate_chunks(json.load(f))
    os.makedirs(os.path.dirname(chunk_file), exist_ok=True)
    with open(chunk_file, 'w', encoding='utf-8') as f:
        json.dump(chunk_data, f, ensure_ascii=False, indent=4)
    print(f"Successfully generated and saved chunks to {chunk_file}")


current_transcript_number = 1
word_count = 0


def process_speech(live_text: str) -> str:
    global current_transcript_number
    global word_count
    
    # Count words in the current input
    words = live_text.split()
    word_count += len(words)
    
    # Wait until we have at least 7 words
    if word_count < 7:
        print(ProcessedResult(
            matched_transcript_number=1,
            operator="waiting",
        ))
        return
    
    speech = " ".join(live_text.split(" ")[-7:])
    speech_for_matching = re.sub(r'[^\w\s]', '', speech.lower())
    
    # Select relevant chunks from chunk_data
    p, c, n = [x for x in chunk_data if x["matched_transcript"] == current_transcript_number - 1], [x for x in chunk_data if x["matched_transcript"] == current_transcript_number], [x for x in chunk_data if x["matched_transcript"] == current_transcript_number + 1]
    partial_chunks = p[-1:] if p else []
    partial_chunks += [x for x in chunk_data if x["matched_transcript"] == -1 and x["type"] == "hybrid" and (not p or x["chunk_number"] > p[-1]["chunk_number"]) and (not c or x["chunk_number"] < c[0]["chunk_number"])]
    partial_chunks += c
    partial_chunks += [x for x in chunk_data if x["matched_transcript"] == -1 and x["type"] == "hybrid" and (not c or x["chunk_number"] > c[-1]["chunk_number"]) and (not n or x["chunk_number"] < n[0]["chunk_number"])]
    partial_chunks += n

    # primary search
    matcher_result = transcript_matcher.match_speech(speech_for_matching, partial_chunks, primary_threshold)
    
    if matcher_result:
        current_transcript_number = matcher_result.matched_transcript_number
        print( ProcessedResult(
            matched_transcript_number=matcher_result.matched_transcript_number,
            operator="primary_matcher"

        ))
    else:
        # if primary search fails, try secondary search
        matcher_result = transcript_matcher.match_speech(speech_for_matching, chunk_data, secondary_threshold)
        if matcher_result:
            current_transcript_number = matcher_result.matched_transcript_number
            print( ProcessedResult(
                matched_transcript_number=matcher_result.matched_transcript_number,
                operator="secondary_matcher",
            ))
        else:
            print( ProcessedResult(
                matched_transcript_number=-1,
                operator="none",
            ))

if __name__ == "__main__":
    recorder = AudioToTextRecorder(
        enable_realtime_transcription=True,
        device="cuda",
        language="en",
        ensure_sentence_ends_with_period=False,
        ensure_sentence_starting_uppercase=False,
        spinner=False,
        realtime_model_type="tiny.en",
        allowed_latency_limit=10,
        realtime_processing_pause=0.3,
        on_realtime_transcription_update=process_speech,
    )
    print("\n--- Starting RealtimeSTT Recorder ---")
    print("Speak into the microphone. Press Enter to stop.")

    recorder.start()
    input("Press Enter to stop recording...\n") # Blocks until Enter is pressed

    recorder.stop()
    exit()