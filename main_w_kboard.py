import logging
import re
realtimestt_logger = logging.getLogger("realtimestt")
realtimestt_logger.setLevel(logging.WARNING)
logging.basicConfig(level=logging.WARNING)
from pydantic import BaseModel
import os
import json
import keyboard # for keyboard input
os.environ["TORCH_HOME"] = "C:/torch_cache" # this is special for my computer




from components.transcript_matcher import TranscriptMatcher # import from components
from components.chunk_generator import ChunkGenerator # import from components
from RealtimeSTT import AudioToTextRecorder # for realtime transcription



class ProcessedResult(BaseModel): # for better looking output
    matched_transcript_number: int # the number of the transcript that was matched
    operator: str # the operator that was used to match the transcript


# define chunk generator and transcript matcher
chunk_generator = ChunkGenerator()
transcript_matcher = TranscriptMatcher()

# define person name, IMPORTANT: this is the name of the person you are transcribing
PERSON_NAME = "elif"

# define chunk file and transcript file
chunk_file = f"data/chunks/{PERSON_NAME}.json"
transcript_file = f"data/transcripts/{PERSON_NAME}.json"

# define thresholds 
primary_threshold = 0.6 # primary threshold for matching, FOR MORE SPEED
secondary_threshold = 0.5 # secondary threshold for matching, FOR MORE RELIABILITY 


# note that transcripts must be available in data/transcripts/{PERSON_NAME}.json

try: # try to load chunks if they exist
    with open(chunk_file, 'r', encoding='utf-8') as f:
        chunk_data = json.load(f)
except Exception as e: # if chunks don't exist, generate them from transcripts
    print(f"Failed to load chunks from {chunk_file}: {e}")
    with open(transcript_file, 'r', encoding='utf-8') as f:
        chunk_data = chunk_generator.generate_chunks(json.load(f)) # generate chunks from transcripts
    os.makedirs(os.path.dirname(chunk_file), exist_ok=True)
    with open(chunk_file, 'w', encoding='utf-8') as f:
        json.dump(chunk_data, f, ensure_ascii=False, indent=4)
    print(f"Successfully generated and saved chunks to {chunk_file}")


# define current transcript number and word count
current_transcript_number = 1
word_count = 0


# here is the main function that processes the speech
def process_speech(live_text: str) -> str:
    # we need to use global variables to keep track of the current transcript number and word count

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
    
    # get last 7 words
    speech = " ".join(live_text.split(" ")[-7:])
    speech_for_matching = re.sub(r'[^\w\s]', '', speech.lower())
    
    # Select relevant chunks from chunk_data
    # i know its a bit complex but it works, highly ai written code to get relevant partial chunks
    p, c, n = [x for x in chunk_data if x["matched_transcript"] == current_transcript_number - 1], [x for x in chunk_data if x["matched_transcript"] == current_transcript_number], [x for x in chunk_data if x["matched_transcript"] == current_transcript_number + 1]
    partial_chunks = p[-1:] if p else []
    partial_chunks += [x for x in chunk_data if x["matched_transcript"] == -1 and x["type"] == "hybrid" and (not p or x["chunk_number"] > p[-1]["chunk_number"]) and (not c or x["chunk_number"] < c[0]["chunk_number"])]
    partial_chunks += c
    partial_chunks += [x for x in chunk_data if x["matched_transcript"] == -1 and x["type"] == "hybrid" and (not c or x["chunk_number"] > c[-1]["chunk_number"]) and (not n or x["chunk_number"] < n[0]["chunk_number"])]
    partial_chunks += n

    # primary search that are fast
    matcher_result = transcript_matcher.match_speech(speech_for_matching, partial_chunks, primary_threshold)
    
    
    if matcher_result: # if primary search is successful
        new_transcript_number = matcher_result.matched_transcript_number
        # current_transcript_number = new_transcript_number
        print( ProcessedResult(
            matched_transcript_number=new_transcript_number,
            operator="primary_matcher"
        )) # we can print the result
    else:
        # if primary search fails, try secondary search with all chunks
        matcher_result = transcript_matcher.match_speech(speech_for_matching, chunk_data, secondary_threshold)
        if matcher_result:
            new_transcript_number = matcher_result.matched_transcript_number
            # current_transcript_number = new_transcript_number
            print( ProcessedResult(
                matched_transcript_number=new_transcript_number,
                operator="secondary_matcher",
            ))
        else: # if secondary search fails, we can't match the speech
            print( ProcessedResult(
                matched_transcript_number=current_transcript_number,
                operator="none",
            ))
    difference = new_transcript_number - current_transcript_number
    current_transcript_number = new_transcript_number
    if difference > 0:
        for _ in range(difference):
            keyboard.press_and_release("right")
    elif difference < 0:
        for _ in range(-difference):
            keyboard.press_and_release("left")


if __name__ == "__main__":
    recorder = AudioToTextRecorder(
        enable_realtime_transcription=True, # must use realtime transcription for real-world
        device="cuda", # must use gpu for large tasks
        compute_type="auto", # for speed
        language="en", # for pre-defined language, improves speed
        ensure_sentence_ends_with_period=False, # for speed
        ensure_sentence_starting_uppercase=False, # for speed
        spinner=False, # unnecessary
        realtime_model_type="tiny.en", # use tiny.en instead of tiny for speed and use 'tiny' for speed
        allowed_latency_limit=10, # for speed
        realtime_processing_pause=0.3, # for ideal gpu load
        on_realtime_transcription_update=process_speech,
    )
    print("\n--- Starting RealtimeSTT Recorder ---")
    print("Speak into the microphone. Press Enter to stop.")

    recorder.start()
    input("Press Enter to stop recording...\n") # Blocks until Enter is pressed

    recorder.stop()
    exit()