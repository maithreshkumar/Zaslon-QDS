"""
Benchmark script to evaluate 1 MiB, 4 MiB, 8 MiB, and 16 MiB chunk sizes
for streaming disk I/O and SHA-512 cryptographic hashing.
"""
import os
import time
import hashlib
import tempfile

CHUNK_SIZES = {
    "1 MiB": 1 * 1024 * 1024,
    "4 MiB": 4 * 1024 * 1024,
    "8 MiB": 8 * 1024 * 1024,
    "16 MiB": 16 * 1024 * 1024,
}

TEST_DATA_SIZE = 128 * 1024 * 1024  # 128 MiB test sample

def benchmark_chunk_size(chunk_name: str, chunk_size: int):
    # Generate test chunk
    sample_chunk = os.urandom(chunk_size)
    num_chunks = TEST_DATA_SIZE // chunk_size
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        # Measure Stream Write + Hash (Alice upload pattern)
        start_time = time.perf_counter()
        hasher = hashlib.sha512()
        
        with open(tmp_path, "wb") as f:
            for _ in range(num_chunks):
                hasher.update(sample_chunk)
                f.write(sample_chunk)
            f.flush()
            os.fsync(f.fileno())
            
        elapsed = time.perf_counter() - start_time
        digest = hasher.hexdigest()
        throughput_mb_s = (TEST_DATA_SIZE / (1024 * 1024)) / elapsed
        
        # Measure Stream Read + Hash (Bob verification pattern)
        read_start = time.perf_counter()
        read_hasher = hashlib.sha512()
        with open(tmp_path, "rb") as f:
            while chunk := f.read(chunk_size):
                read_hasher.update(chunk)
        read_elapsed = time.perf_counter() - read_start
        read_throughput = (TEST_DATA_SIZE / (1024 * 1024)) / read_elapsed
        
        assert read_hasher.hexdigest() == digest
        
        return {
            "chunk_name": chunk_name,
            "chunk_bytes": chunk_size,
            "write_hash_time_s": elapsed,
            "write_hash_mb_s": throughput_mb_s,
            "read_hash_time_s": read_elapsed,
            "read_hash_mb_s": read_throughput,
            "combined_mb_s": (2 * (TEST_DATA_SIZE / (1024 * 1024))) / (elapsed + read_elapsed)
        }
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    print(f"=== Benchmarking Streaming Chunk Sizes ({TEST_DATA_SIZE // (1024 * 1024)} MiB payload) ===")
    results = []
    for name, size in CHUNK_SIZES.items():
        res = benchmark_chunk_size(name, size)
        results.append(res)
        print(f"[{name}] Write+Hash: {res['write_hash_mb_s']:.2f} MiB/s | Read+Hash: {res['read_hash_mb_s']:.2f} MiB/s | Combined: {res['combined_mb_s']:.2f} MiB/s")
        
    best = max(results, key=lambda r: r["combined_mb_s"])
    print(f"\n=> Fastest chunk size: {best['chunk_name']} ({best['chunk_bytes']} bytes) with {best['combined_mb_s']:.2f} MiB/s combined throughput.")
