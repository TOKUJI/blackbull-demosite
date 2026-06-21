"""Unit tests for the stats ring-buffer module."""


class TestStats:
    """Tests for the Stats collector."""

    def test_new_stats_has_zero_total(self):
        """A new Stats instance should have zero total requests."""
        from blackbull_demo.stats import Stats
        s = Stats(maxlen=10)
        assert s.total_requests == 0

    def test_record_increments_total(self):
        """Recording a request should increment the total counter."""
        from blackbull_demo.stats import Stats
        s = Stats(maxlen=10)
        s.record(method='GET', path='/', status=200,
                 http_version='1.1', elapsed_ms=1.5)
        assert s.total_requests == 1
        assert len(s.recent_requests) == 1

    def test_buffer_caps_at_maxlen(self):
        """Ring buffer should not exceed maxlen."""
        from blackbull_demo.stats import Stats
        s = Stats(maxlen=3)
        for i in range(5):
            s.record(method='GET', path=f'/{i}', status=200,
                     http_version='1.1', elapsed_ms=1.0)
        assert s.total_requests == 5
        assert len(s.recent_requests) == 3

    def test_recent_requests_most_recent_first(self):
        """Recent requests should be returned most-recent-first."""
        from blackbull_demo.stats import Stats
        s = Stats(maxlen=10)
        s.record(method='GET', path='/first', status=200,
                 http_version='1.1', elapsed_ms=1.0)
        s.record(method='POST', path='/second', status=201,
                 http_version='1.1', elapsed_ms=2.0)
        assert s.recent_requests[0]['path'] == '/second'
        assert s.recent_requests[1]['path'] == '/first'

    def test_avg_response_time(self):
        """Average response time should be correctly calculated."""
        from blackbull_demo.stats import Stats
        s = Stats(maxlen=10)
        s.record(method='GET', path='/a', status=200,
                 http_version='1.1', elapsed_ms=10.0)
        s.record(method='GET', path='/b', status=200,
                 http_version='1.1', elapsed_ms=20.0)
        assert s.avg_response_time_ms == 15.0

    def test_connection_tracking(self):
        """Connection increment/decrement should track correctly."""
        from blackbull_demo.stats import Stats
        s = Stats(maxlen=10)
        assert s.active_connections == 0
        s.inc_connections()
        s.inc_connections()
        assert s.active_connections == 2
        s.dec_connections()
        assert s.active_connections == 1
        s.dec_connections()
        s.dec_connections()  # should not go negative
        assert s.active_connections == 0

    def test_to_dict_has_required_keys(self):
        """to_dict() should return all required keys."""
        from blackbull_demo.stats import Stats
        s = Stats(maxlen=10)
        d = s.to_dict()
        assert 'total_requests' in d
        assert 'active_connections' in d
        assert 'avg_response_time_ms' in d
        assert 'uptime_seconds' in d
        assert 'recent_requests' in d

    def test_user_agent_truncated(self):
        """User-Agent should be truncated to 60 characters."""
        from blackbull_demo.stats import Stats
        s = Stats(maxlen=10)
        long_ua = 'A' * 100
        s.record(method='GET', path='/', status=200,
                 http_version='1.1', elapsed_ms=1.0,
                 user_agent=long_ua)
        assert len(s.recent_requests[0]['user_agent']) <= 60
