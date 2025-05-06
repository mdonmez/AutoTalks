import json  # we dont care small speed things in this code, cause of pretty printing
import re
import concurrent.futures  # this is critical for speed
from nanoid import generate  # better than uuid
from typing import List, Dict, Any  # for fast data validation
import logging  # for logging
from datetime import datetime
import time  # to measure time

# Configure logging
log_directory = "logs"
log_filename = datetime.now().strftime("chunk_generator_%Y-%m-%d.log")
log_filepath = f"{log_directory}/{log_filename}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_filepath), logging.StreamHandler()],
)

CHUNK_SIZE = 7


class ChunkGenerator:
    def clean_and_split(self, text):
        text = text.lower()
        text = re.sub(r"[^\w\s]", "", text)  # remove punctuation
        return text.split()

    def _validate_transcripts(self, transcripts: List[Dict[str, Any]]):
        """Validates the input transcripts list."""
        if not isinstance(transcripts, list):
            raise TypeError("Input 'transcripts' must be a list.")
        for i, t in enumerate(transcripts):
            if not isinstance(t, dict):
                raise TypeError(
                    f"Item at index {i} in 'transcripts' must be a dictionary."
                )
            if "number" not in t or not isinstance(t["number"], int):
                raise ValueError(
                    f"Item at index {i} in 'transcripts' must have an integer key 'number'."
                )
            if "transcript" not in t or not isinstance(t["transcript"], str):
                raise ValueError(
                    f"Item at index {i} in 'transcripts' must have a string key 'transcript'."
                )

    def _create_chunk(self, chunk_num, matched_trans, chunk_type, chunk_txt):
        return {
            "chunk_number": chunk_num,
            "matched_transcript": matched_trans,
            "type": chunk_type,
            "chunk_text": chunk_txt,
            "id": str(generate()),
        }

    def _get_original_transcript_text(self, transcript_number, original_transcripts):
        original_transcript_obj = next(
            (tr for tr in original_transcripts if tr["number"] == transcript_number),
            None,
        )
        if original_transcript_obj is None:
            raise ValueError(
                f"Original transcript with number {transcript_number} not found."
            )
        return re.sub(
            r"[^\w\s]", "", original_transcript_obj["transcript"].lower()
        ).strip()

    def _handle_short_transcript(
        self, transcript, original_transcripts, chunks, chunk_number
    ):
        """Handles transcripts shorter than CHUNK_SIZE."""
        original_transcript = self._get_original_transcript_text(
            transcript["number"], original_transcripts
        )
        chunk = self._create_chunk(
            chunk_number, transcript["number"], "normal", original_transcript
        )
        chunks.append(chunk)
        return chunk_number + 1

    def _generate_normal_and_last_chunks(
        self,
        words,
        transcript_number,
        current_transcript_idx,
        total_transcripts,
        chunks,
        chunk_number,
    ):
        """Generates normal and 'last' chunks for transcripts >= CHUNK_SIZE."""
        n = len(words)
        for i in range(n - CHUNK_SIZE + 1):
            chunk_words = words[i : i + CHUNK_SIZE]
            is_last_transcript = current_transcript_idx == total_transcripts - 1
            is_last_chunk_in_transcript = i == n - CHUNK_SIZE

            # Determine chunk type (maintaining original logic)
            if is_last_chunk_in_transcript and is_last_transcript:
                chunk_type = "normal"  # Original logic had this as normal
            elif is_last_chunk_in_transcript:
                chunk_type = "last"  # Original logic had this as last, though this path was likely never hit correctly
            else:
                chunk_type = "normal"

            chunk = self._create_chunk(
                chunk_number, transcript_number, chunk_type, " ".join(chunk_words)
            )
            chunks.append(chunk)
            chunk_number += 1
        return chunk_number

    def _generate_hybrid_chunks(self, prev_words, next_words, chunks, chunk_number):
        """Generates hybrid chunks between two transcripts."""
        if prev_words and next_words:
            for k in range(CHUNK_SIZE - 1, 0, -1):
                # Ensure there are enough words for the hybrid chunk
                if len(prev_words) < k or len(next_words) < (CHUNK_SIZE - k):
                    continue
                chunk_words = prev_words[-k:] + next_words[: CHUNK_SIZE - k]
                chunk = self._create_chunk(
                    chunk_number, -1, "hybrid", " ".join(chunk_words)
                )
                chunks.append(chunk)
                chunk_number += 1
        return chunk_number

    def _preprocess_transcripts_parallel(
        self, transcripts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Preprocesses transcripts in parallel."""
        cleaned_transcripts = []
        logging.info("Starting parallel preprocessing of transcripts.")
        start_time = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self.clean_and_split, t["transcript"]): t["number"]
                for t in transcripts
            }
            for future in concurrent.futures.as_completed(futures):
                transcript_number = futures[future]
                try:
                    words = future.result()
                    cleaned_transcripts.append(
                        {"number": transcript_number, "words": words}
                    )
                except Exception as exc:
                    logging.error(
                        f"Transcript {transcript_number} generated an exception: {exc}"
                    )
        # Sort cleaned transcripts by their original number to maintain order
        cleaned_transcripts.sort(key=lambda x: x["number"])
        end_time = time.perf_counter()
        logging.info("Finished parallel preprocessing of transcripts.")
        logging.info(
            f"It took {end_time - start_time} seconds to preprocess transcripts."
        )
        return cleaned_transcripts

    def _process_transcript(
        self,
        transcript,
        cleaned_transcripts,
        original_transcripts,
        chunks,
        chunk_number,
    ):
        """Processes a single cleaned transcript to generate chunks."""
        words = transcript["words"]
        transcript_number = transcript["number"]
        n = len(words)
        idx = cleaned_transcripts.index(
            transcript
        )  # Need index for last transcript check

        if n == 0:
            return chunk_number

        # Handle transcripts shorter than CHUNK_SIZE
        if n < CHUNK_SIZE:
            chunk_number = self._handle_short_transcript(
                transcript, original_transcripts, chunks, chunk_number
            )
            return chunk_number

        # Handle normal and last chunks for transcripts >= CHUNK_SIZE
        chunk_number = self._generate_normal_and_last_chunks(
            words,
            transcript_number,
            idx,
            len(cleaned_transcripts),
            chunks,
            chunk_number,
        )

        # Insert hybrid chunks after the last chunk of the current transcript,
        # if there is a next transcript
        if idx < len(cleaned_transcripts) - 1:
            prev_words = words
            next_words = cleaned_transcripts[idx + 1]["words"]
            chunk_number = self._generate_hybrid_chunks(
                prev_words, next_words, chunks, chunk_number
            )

        return chunk_number

    def generate_chunks(
        self, transcripts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        self._validate_transcripts(transcripts)

        chunks = []
        chunk_number = 1

        cleaned_transcripts = self._preprocess_transcripts_parallel(transcripts)

        for t in cleaned_transcripts:
            chunk_number = self._process_transcript(
                t, cleaned_transcripts, transcripts, chunks, chunk_number
            )

        return chunks


if __name__ == "__main__":
    speaker_name = "mikey"
    with open(f"data/transcripts/{speaker_name}.json", "r", encoding="utf-8") as f:
        transcripts = json.loads(f.read())

    general_start_time = time.perf_counter()
    generator = ChunkGenerator()
    chunks = generator.generate_chunks(transcripts)
    general_end_time = time.perf_counter()
    logging.info(
        f"It took {general_end_time - general_start_time} seconds to make everything."
    )
    logging.info(f"{len(chunks)} chunks generated.")
    try:
        with open(f"data/chunks/{speaker_name}.json", "w") as f:
            f.write(json.dumps(chunks, indent=4))
        logging.info(f"Chunks saved to data/chunks/{speaker_name}.json")
    except IOError as e:
        logging.error(f"Error saving chunks to file: {e}")
