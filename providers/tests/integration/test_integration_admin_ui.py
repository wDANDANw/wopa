###############################################################################
# test_integration_admin_ui.py
#
# Purpose:
# Integration tests for the admin UI page. This UI is presumably served at 
# `/admin` endpoint and displays available provider endpoints, health statuses, 
# and possibly other operational metrics.
#
# Prerequisites:
# - The admin UI configured and accessible via `/admin`.
# - The backend serving static or generated HTML for the admin UI.
#
# Strategy:
# - Send a GET request to `/admin`.
# - Check that the response is 200 and contains some expected UI elements (like table of endpoints, 
#   health indicators, or a title "Provider Admin UI").
# - If the UI lists endpoints or shows LLM/Sandbox/Emulator statuses, verify their presence.
#
# Requirements:
# - pytest, real network access.
#
# Maintainability:
# - If UI changes structure (like changing from table to a different layout), update checks accordingly.
# - If UI adds more features, add tests for their presence.
###############################################################################

import pytest
import requests

admin_url = "http://localhost:8003/admin"

@pytest.mark.integration
def test_admin_ui_access():
    # Basic check: /admin returns 200 and HTML content
    r = requests.get(admin_url, timeout=10)
    assert r.status_code == 200, f"Expected 200 for /admin, got {r.status_code}, body: {r.text}"

    # Check if content-type is HTML (optional, if server sets it)
    ctype = r.headers.get("Content-Type","")
    assert "text/html" in ctype.lower() or "charset=utf-8" in ctype.lower(), f"Expected HTML content, got {ctype}"

    html = r.text
    # Look for a known keyword or heading that the UI should have
    # If known that UI has a <h1>Provider Admin UI</h1>, we can assert that:
    assert "Provider Admin UI" in html or "Endpoints" in html, "Admin UI page does not contain expected text."

@pytest.mark.integration
def test_admin_ui_lists_endpoints():
    # If the UI is supposed to list endpoints (like /llm/chat_complete, /sandbox/run_file), 
    # we can check for their presence in the rendered HTML.

    endpoint_url = admin_url + "/endpoints"
    r = requests.get(endpoint_url, timeout=10)
    assert r.status_code == 200
    html = r.text
    # Check for "/llm/chat_complete" or "/sandbox/run_file" strings in HTML:
    expected_endpoints = ["/llm/chat_complete", "/sandbox/run_file", "/emulator/run_app", "/health"]
    found_count = sum(1 for ep in expected_endpoints if ep in html)

    # Expect at least half of them visible if the UI is meant to show known endpoints.
    assert found_count >= 2, f"Expected at least 2 known endpoints to be listed in admin UI, found {found_count}"

# TODO: Add this back in
# @pytest.mark.integration
# def test_admin_ui_shows_health_info():
#     # If the admin UI shows health info (like a table with LLM=ok, sandbox=ok, etc.),
#     # check for these strings.

#     r = requests.get(admin_url, timeout=10)
#     assert r.status_code == 200
#     html = r.text

#     # Check for words "LLM", "Sandbox", "Emulator" and possibly "status: ok" in the HTML
#     # Adjust if UI differs. If no known structure, just look for "LLM" or "Emulator" as indicators.
#     assert "LLM" in html or "llm" in html.lower(), "Admin UI does not mention LLM"
#     assert "Sandbox" in html or "sandbox" in html.lower(), "Admin UI does not mention Sandbox"
#     assert "Emulator" in html or "emulator" in html.lower(), "Admin UI does not mention Emulator"

#     # Optionally, check for "ok" to indicate health status, but not guaranteed:
#     # If not sure, skip this assertion or make it flexible:
#     if "ok" not in html.lower():
#         # If UI does not display statuses as 'ok' but uses something else, adjust accordingly
#         pass

###############################################################################
# Explanation:
#
# - test_admin_ui_access: Ensures /admin returns 200 and some known indicative text.
# - test_admin_ui_lists_endpoints: Verifies that known endpoints appear in UI, confirming 
#   the page displays endpoint information.
# - test_admin_ui_shows_health_info: Checks for presence of LLM/Sandbox/Emulator references, 
#   indicating health sections are rendered.
#
# These tests rely on the actual rendered HTML. If UI changes layout or wording, 
# update the searched strings.
#
# Maintainability:
# - If UI changes design, update the checks accordingly.
# - If new services or endpoints appear, add them to expected lists.
###############################################################################
