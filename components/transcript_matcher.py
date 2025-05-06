import orjson
import concurrent.futures
from rapidfuzz import fuzz
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import logging  # for logging
from datetime import datetime

# Configure logging
log_directory = "logs"
log_filename = datetime.now().strftime("transcript_matcher_%Y-%m-%d.log")
log_filepath = f"{log_directory}/{log_filename}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_filepath), logging.StreamHandler()],
)


@dataclass
class Result:
    matched_transcript_number: int
    chunk_number: int
    chunk_id: str
    similarity: float
    reason: str
    elapsed_time: float


class TranscriptMatcher:
    def match_speech(
        self, speech: str, chunks: List[Dict[str, Any]], threshold: float
    ) -> Optional[Result]:
        logging.info(
            f"Starting speech matching for speech: '{speech[:50]}...' against {len(chunks)} chunks with threshold: {threshold}"
        )
        start_time = time.perf_counter()
        best = None
        best_similarity = -1

        def compute_similarity(args):
            idx, chunk = args
            similarity = fuzz.ratio(speech, chunk["chunk_text"]) / 100.0
            return (idx, chunk, similarity)

        # Parallel similarity calculation
        logging.info("Starting parallel similarity calculation.")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(compute_similarity, enumerate(chunks)))
        logging.info("Finished parallel similarity calculation.")

        for idx, chunk, similarity in results:
            if similarity >= threshold and similarity > best_similarity:
                best = (idx, chunk, similarity)
                best_similarity = similarity

        if best is None:
            logging.warning("No matching chunk found above the threshold.")
            return None  # or (None, None, None, None, None)

        idx, chunk, similarity = best
        chunk_type = chunk["type"]
        chunk_number = chunk["chunk_number"]
        chunk_id = chunk["id"]
        logging.info(
            f"Best match found: Chunk ID {chunk_id}, Similarity: {similarity:.2f}, Type: {chunk_type}"
        )

        match chunk_type:
            case "normal":
                transcript_number = chunk["matched_transcript"]
                reason = "normal"
            case "last":
                transcript_number = chunk["matched_transcript"] + 1
                reason = "last->next"
            case "hybrid":
                # Look forward for first non-hybrid chunk
                transcript_number = None
                for next_chunk in chunks[idx + 1 :]:
                    if next_chunk["type"] != "hybrid":
                        transcript_number = next_chunk["matched_transcript"]
                        break
                if transcript_number is None:  # fallback if not found
                    transcript_number = -1
                reason = "hybrid->next"
            case _:  # should not happen ideally, but good to have a fallback
                transcript_number = -1
                reason = "unknown"

        elapsed_time = time.perf_counter() - start_time
        return Result(
            matched_transcript_number=transcript_number,
            chunk_number=chunk_number,
            chunk_id=chunk_id,
            similarity=similarity,
            reason=reason,
            elapsed_time=elapsed_time,
        )


if __name__ == "__main__":
    speaker_name = "testuser"

    try:
        with open(f"data/chunks/{speaker_name}.json", "r") as f:
            chunks = orjson.loads(f.read())
        logging.info(
            f"{len(chunks)} chunks has been loaded from data/chunks/{speaker_name}.json."
        )
    except FileNotFoundError:
        logging.error(f"Error: data/chunks/{speaker_name}.json not found.")
        exit()
    except orjson.JSONDecodeError:
        logging.error(f"Error decoding JSON from data/chunks/{speaker_name}.json.")
        exit()
    except Exception as e:
        logging.error(f"An unexpected error occurred while loading chunks: {e}")
        exit()

    speech = "valleys and aspirations these choices big or"
    logging.info(f"Matching speech: '{speech}'")

    matcher = TranscriptMatcher()
    start_match_time = time.perf_counter()
    result = matcher.match_speech(speech, chunks, 0.6)
    end_match_time = time.perf_counter()
    logging.info(f"Match speech took {end_match_time - start_match_time:.4f} seconds.")

    if result:
        logging.info("Match result:")
        for k, v in vars(result).items():
            new_k_name = k.replace("_", " ")
            new_k_name = new_k_name.title()
            logging.info(f"  {new_k_name}: {v}")
    else:
        logging.info("No match result returned.")
