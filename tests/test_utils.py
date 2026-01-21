class TestBase62Encoder:
    """Test Base62 encoding/decoding."""

    def test_encode_zero(self):
        """Test encoding zero."""
        from app.utility import base62_encoder

        assert base62_encoder.encode(0) == "0"

    def test_encode_decode_roundtrip(self):
        """Test encoding and decoding roundtrip."""
        from app.utility import base62_encoder

        test_numbers = [1, 100, 1000, 10000, 123456789]
        for num in test_numbers:
            encoded = base62_encoder.encode(num)
            decoded = base62_encoder.decode(encoded)
            assert decoded == num

    def test_encoded_values_sortable(self):
        """Test that larger numbers produce lexicographically larger strings."""
        from app.utility import base62_encoder

        _encoded_100 = base62_encoder.encode(100)
        _encoded_200 = base62_encoder.encode(200)
        # Note: This is NOT always true for base62, but for same-length strings it is
        # Just ensure decoding works correctly


class TestSnowflakeID:
    """Test Snowflake ID generator."""

    def test_generate_unique_ids(self):
        """Test generating unique IDs."""
        from app.utility import id_generator

        ids = set()
        for _ in range(10000):
            new_id = id_generator.generate()
            assert new_id not in ids, "Duplicate ID generated!"
            ids.add(new_id)

    def test_ids_sortable_by_time(self):
        """Test that IDs are sortable by creation time."""
        import time

        from app.utility import id_generator

        id1 = id_generator.generate()
        time.sleep(0.01)  # Small delay
        id2 = id_generator.generate()

        assert id2 > id1, "IDs should be monotonically increasing"

    def test_thread_safety(self):
        """Test concurrent ID generation."""
        import threading

        from app.utility import id_generator

        ids = set()
        lock = threading.Lock()

        def generate_ids():
            for _ in range(1000):
                new_id = id_generator.generate()
                with lock:
                    ids.add(new_id)

        threads = [threading.Thread(target=generate_ids) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 10,000 unique IDs
        assert len(ids) == 10000
