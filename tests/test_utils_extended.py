class TestUtilsExtended:
    """Extended utility tests."""

    def test_base62_large_numbers(self):
        """Test Base62 with large numbers."""
        from app.utility import base62_encoder

        large_num = 123456789012345
        encoded = base62_encoder.encode(large_num)
        decoded = base62_encoder.decode(encoded)
        assert decoded == large_num

    def test_snowflake_timestamp_ordering(self):
        """Test Snowflake IDs maintain timestamp ordering."""
        import time

        from app.utility import id_generator

        ids = []
        for _ in range(100):
            ids.append(id_generator.generate())
            time.sleep(0.001)  # 1ms delay

        # IDs should be in ascending order
        assert ids == sorted(ids)

    def test_snowflake_singleton(self):
        """Test Snowflake generator is singleton."""
        from app.utility.snowflake import SnowflakeID

        gen1 = SnowflakeID(datacenter_id=1, worker_id=1)
        gen2 = SnowflakeID(datacenter_id=2, worker_id=2)

        # Should be same instance
        assert gen1 is gen2
