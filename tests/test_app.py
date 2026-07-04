"""Integration tests for the BlackBull demo application."""


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200(self, client):
        """Health endpoint should return 200 OK."""
        response = client.get('/health')
        assert response.status_code == 200

    def test_health_returns_valid_json(self, client):
        """Health endpoint should return JSON with required fields."""
        response = client.get('/health')
        data = response.json()
        assert data['status'] == 'ok'
        assert 'version' in data
        assert 'app_version' in data
        assert 'uptime' in data
        assert 'hostname' in data


class TestDashboard:
    """Tests for GET / (dashboard)."""

    def test_dashboard_returns_html(self, client):
        """Dashboard should return HTML with correct content type."""
        response = client.get('/')
        assert response.status_code == 200
        assert 'text/html' in response.headers.get('content-type', '')
        assert 'BlackBull Demo' in response.text

    def test_dashboard_size_under_10kb(self, client):
        """Dashboard response should be under 10 KB."""
        response = client.get('/')
        assert len(response.content) < 10 * 1024


class TestApiEcho:
    """Tests for GET /api/echo/{name}."""

    def test_echo_returns_name(self, client):
        """Echo endpoint should return the provided name."""
        response = client.get('/api/echo/World')
        data = response.json()
        assert data['echo'] == 'World'


class TestApiSquare:
    """Tests for GET /api/square/{n:int}."""

    def test_square_positive(self, client):
        """Square endpoint should return n squared."""
        response = client.get('/api/square/5')
        data = response.json()
        assert data['n'] == 5
        assert data['square'] == 25

    def test_square_negative(self, client):
        """Square endpoint should handle negative integers."""
        response = client.get('/api/square/-3')
        data = response.json()
        assert data['n'] == -3
        assert data['square'] == 9

    def test_square_rejects_non_integer(self, client):
        """Square endpoint should 404 on non-integer path segment."""
        response = client.get('/api/square/abc')
        assert response.status_code == 404


class TestApiInfo:
    """Tests for GET /api/info."""

    def test_info_returns_dict(self, client):
        """Info endpoint should return JSON with framework info."""
        response = client.get('/api/info')
        data = response.json()
        assert data['framework'] == 'BlackBull'
        assert 'version' in data


class TestApiHeaders:
    """Tests for GET /api/headers."""

    def test_headers_echoes_method(self, client):
        """Headers endpoint should echo the request method."""
        response = client.get('/api/headers')
        data = response.json()
        assert data['method'] == 'GET'


class TestApiMethods:
    """Tests for /api/methods method-based routing."""

    def test_get_method(self, client):
        response = client.get('/api/methods')
        data = response.json()
        assert data['method'] == 'GET'

    def test_post_method(self, client):
        response = client.post('/api/methods', content='hello')
        data = response.json()
        assert data['method'] == 'POST'

    def test_put_method(self, client):
        response = client.put('/api/methods', content='update')
        data = response.json()
        assert data['method'] == 'PUT'

    def test_delete_method(self, client):
        response = client.delete('/api/methods')
        data = response.json()
        assert data['method'] == 'DELETE'


class TestHtcpcp:
    """Tests for HTCPCP (RFC 2324) endpoints."""

    def test_pot_get_returns_200(self, client):
        """GET /pot should return pot state (coffee mode → 200)."""
        response = client.get('/pot')
        assert response.status_code == 200

    def test_brew_with_additions(self, client):
        """POST /pot with Accept-Additions should brew."""
        response = client.post(
            '/pot',
            headers={'Accept-Additions': 'cream; sugar'},
        )
        assert response.status_code == 200

    def test_pot_when_returns_200(self, client):
        """GET /pot/when should return readiness info."""
        response = client.get('/pot/when')
        assert response.status_code == 200


class TestStatsJson:
    """Tests for GET /stats.json."""

    def test_stats_returns_json(self, client):
        """Stats endpoint should return JSON with required keys."""
        response = client.get('/stats.json')
        data = response.json()
        assert 'total_requests' in data
        assert 'recent_requests' in data


class TestNotFound:
    """Tests for 404 handling."""

    def test_unknown_route_returns_404(self, client):
        """Unknown routes should return 404 JSON."""
        response = client.get('/nonexistent')
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data


class TestOpenApi:
    """Tests for OpenAPI endpoints."""

    def test_openapi_json_returns_200(self, client):
        """OpenAPI spec should be served at /openapi.json."""
        response = client.get('/openapi.json')
        assert response.status_code == 200
        data = response.json()
        assert data['openapi'] == '3.1.0'

    def test_docs_returns_html(self, client):
        """Swagger UI should be served at /docs."""
        response = client.get('/docs')
        assert response.status_code == 200
        assert 'text/html' in response.headers.get('content-type', '')
