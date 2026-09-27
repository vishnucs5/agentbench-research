import io
import json
import sys

import fitz
import requests

BASE_URL = "http://127.0.0.1:8000"


def test_live_features():
    print("=== LIVE FEATURE BACKTEST ===")

    # 1. Favicon exemption (returns 204 without auth)
    res = requests.get(f"{BASE_URL}/favicon.ico")
    assert res.status_code in (200, 204), f"Favicon expected 200 or 204, got {res.status_code}"
    print(f"[PASS] 1. Favicon unauthenticated: status {res.status_code}")

    # 2. Protected endpoint without auth returns 401
    res = requests.get(f"{BASE_URL}/v1/projects")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"
    print("[PASS] 2. Protected endpoint without token returns 401")

    # 3. Auth login with demo credentials
    res = requests.post(
        f"{BASE_URL}/v1/auth/login", json={"email": "demo@test.com", "password": "Demo1234!"}
    )
    assert res.status_code == 200, f"Login failed: {res.status_code} {res.text}"
    token_data = res.json()
    token = token_data.get("access_token")
    assert token, "No access_token returned"
    print("[PASS] 3. Login successful, JWT token acquired")

    headers = {"Authorization": f"Bearer {token}"}

    # 4. Auth Me
    res = requests.get(f"{BASE_URL}/v1/auth/me", headers=headers)
    assert res.status_code == 200, f"Auth me failed: {res.status_code} {res.text}"
    user = res.json()
    print(f"[PASS] 4. Auth /me verified for user: {user.get('email')} (role: {user.get('role')})")

    # 5. List projects
    res = requests.get(f"{BASE_URL}/v1/projects", headers=headers)
    assert res.status_code == 200, f"List projects failed: {res.status_code} {res.text}"
    projects = res.json()
    print(f"[PASS] 5. Listed {len(projects)} existing projects")

    # 6. Create a test project
    new_proj = {
        "name": "Live Verification Suite Project",
        "domain": "network-intrusion-detection",
        "retention_days": 30,
    }
    res = requests.post(f"{BASE_URL}/v1/projects", json=new_proj, headers=headers)
    assert res.status_code in (200, 201), f"Create project failed: {res.status_code} {res.text}"
    created_proj = res.json()
    proj_id = created_proj.get("id")
    print(f"[PASS] 6. Created test project: {proj_id}")

    # 7. FEATURE 1: Upload and auto-process a research paper (PDF)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 72),
        "Deep Learning for Network Intrusion Detection: A Survey\n\n"
        "Abstract: Network intrusion detection systems (NIDS) are critical for securing modern cyber infrastructure. "
        "Deep learning approaches, including convolutional neural networks and transformer architectures, "
        "have shown high accuracy on benchmark datasets such as NSL-KDD and CICIDS2017. "
        "Experiments indicate that transformer-based anomaly detectors achieve 97.6% accuracy on CIC-IDS2017.",
    )
    pdf_bytes = doc.tobytes()
    doc.close()

    upload_files = {"file": ("nids_deep_learning_survey.pdf", pdf_bytes, "application/pdf")}
    upload_data = {
        "title": "Deep Learning for Network Intrusion Detection",
        "authors": json.dumps(["A. Rahman", "L. Chen"]),
    }
    res = requests.post(
        f"{BASE_URL}/v1/projects/{proj_id}/papers",
        files=upload_files,
        data=upload_data,
        headers=headers,
    )
    assert res.status_code in (200, 201), f"Paper upload failed: {res.status_code} {res.text}"
    upload_res = res.json()
    paper_id = upload_res.get("paper_id")
    assert paper_id, "No paper_id returned from upload"
    print(f"[PASS] 7. Feature 1 (Paper Upload & Auto-Process): paper_id={paper_id}")

    # 8. Verify paper pages and chunks are created
    res = requests.get(f"{BASE_URL}/v1/projects/{proj_id}/papers/{paper_id}/pages", headers=headers)
    assert res.status_code == 200, f"Get pages failed: {res.status_code} {res.text}"
    pages_data = res.json()
    assert len(pages_data.get("pages", [])) > 0, "No pages extracted from paper"
    print(f"[PASS] 8. Paper pages verified: {len(pages_data['pages'])} page(s) extracted")

    # 9. FEATURE 2: Autonomous research run execution
    run_payload = {
        "prompt": "Compare deep learning approaches for network intrusion detection (2023-2025)",
        "model_profile": "mock",
    }
    res = requests.post(
        f"{BASE_URL}/v1/dashboard/projects/{proj_id}/runs", json=run_payload, headers=headers
    )
    assert res.status_code in (200, 201), f"Run execution failed: {res.status_code} {res.text}"
    run_res = res.json()
    run_id = run_res.get("run_id")
    assert run_id, "No run_id returned from run execution"
    assert run_res.get("status") == "completed", (
        f"Run status not completed: {run_res.get('status')}"
    )
    print(
        f"[PASS] 9. Feature 2 (Autonomous Research Run): run_id={run_id}, status={run_res['status']}"
    )

    # 10. Verify run trace events
    res = requests.get(f"{BASE_URL}/v1/dashboard/runs/{run_id}/trace", headers=headers)
    assert res.status_code == 200, f"Get trace failed: {res.status_code} {res.text}"
    trace_data = res.json()
    events = trace_data.get("trace_events") or trace_data.get("events", [])
    assert len(events) >= 5, f"Expected at least 5 trace events, got {len(events)}"
    print(
        f"[PASS] 10. Trace Replay verified: {len(events)} events (planner, retrieval, extractor, synthesis, verifier)"
    )

    # 11. FEATURE 3: Plagiarism Checker (Text Check)
    sample_text = (
        "Network intrusion detection systems (NIDS) are critical for securing modern cyber infrastructure. "
        "Deep learning approaches, including convolutional neural networks and transformer architectures, "
        "have shown high accuracy on benchmark datasets such as NSL-KDD and CICIDS2017."
    )
    res = requests.post(
        f"{BASE_URL}/v1/plagiarism/check/text",
        json={"text": sample_text, "project_id": proj_id, "threshold": 0.3},
        headers=headers,
    )
    assert res.status_code in (200, 201), (
        f"Plagiarism text check failed: {res.status_code} {res.text}"
    )
    text_check = res.json()
    text_check_id = text_check.get("id")
    print(
        f"[PASS] 11. Feature 3 (Plagiarism Text Check): id={text_check_id}, status={text_check.get('status')}"
    )

    # 12. FEATURE 3: Plagiarism Checker (File Upload Check)
    file_bytes = io.BytesIO(sample_text.encode("utf-8"))
    files = {"file": ("intrusion_detection_paper.txt", file_bytes, "text/plain")}
    data = {"project_id": proj_id, "threshold": "0.30"}
    res = requests.post(
        f"{BASE_URL}/v1/plagiarism/check/file", files=files, data=data, headers=headers
    )
    assert res.status_code in (200, 201), (
        f"Plagiarism file upload check failed: {res.status_code} {res.text}"
    )
    file_check = res.json()
    file_check_id = file_check.get("id")
    print(
        f"[PASS] 12. Feature 3 (Plagiarism File Check): file={file_check.get('source_filename')}, id={file_check_id}"
    )

    # 13. Plagiarism history and detailed report
    res = requests.get(f"{BASE_URL}/v1/plagiarism/checks?page=1&page_size=10", headers=headers)
    assert res.status_code == 200, f"Plagiarism history failed: {res.status_code} {res.text}"
    history = res.json()
    assert history.get("total", 0) > 0, "No checks in plagiarism history"

    res = requests.get(f"{BASE_URL}/v1/plagiarism/checks/{text_check_id}", headers=headers)
    assert res.status_code == 200, f"Plagiarism report failed: {res.status_code} {res.text}"
    report = res.json()
    print(
        f"[PASS] 13. Plagiarism Report & History: retrieved report for {text_check_id}, originality={report['check']['originality_score']}%"
    )

    # 14. FEATURE 4: Hybrid Search Retrieval across documents
    res = requests.post(
        f"{BASE_URL}/v1/search",
        json={"query": "deep learning intrusion detection", "top_k": 5, "project_id": proj_id},
        headers=headers,
    )
    assert res.status_code == 200, f"Search query failed: {res.status_code} {res.text}"
    search_res = res.json()
    hits = search_res.get("hits", [])
    assert len(hits) > 0, f"Expected at least 1 hit, got {len(hits)}"
    print(
        f"[PASS] 14. Feature 4 (Hybrid Search Retrieval): returned {len(hits)} grounded hit(s) across ingested paper"
    )

    # 15. Claim verification
    res = requests.post(
        f"{BASE_URL}/v1/projects/{proj_id}/verification/verify",
        json={
            "draft_text": "Transformer-based anomaly detectors achieve 97.6% accuracy.",
            "strict_mode": False,
        },
        headers=headers,
    )
    assert res.status_code in (200, 201), f"Verification failed: {res.status_code} {res.text}"
    verif_res = res.json()
    print(f"[PASS] 15. Claim Verification executed: status={verif_res.get('overall_status')}")

    # 16. UI Route endpoints
    ui_routes = [
        "/",
        "/projects",
        "/reports",
        "/chat",
        "/trace",
        "/settings",
        "/dashboard/plagiarism-checker",
        "/plagiarism-checker",
        "/dashboard",
        "/plagiarism",
    ]
    for route in ui_routes:
        res = requests.get(f"{BASE_URL}{route}")
        assert res.status_code == 200, f"Route {route} expected 200, got {res.status_code}"
    print(f"[PASS] 16. All {len(ui_routes)} UI routes accessible (status 200)")

    # 17. FEATURE 5: Report Export Suite (LaTeX, BibTeX, Markdown, Audit Log)
    for rtype in ["latex", "bibtex", "markdown", "audit"]:
        res = requests.post(
            f"{BASE_URL}/v1/reports/preview",
            json={"project_id": proj_id, "report_type": rtype},
            headers=headers,
        )
        assert res.status_code == 200, (
            f"Report preview {rtype} failed: {res.status_code} {res.text}"
        )
        data = res.json()
        assert len(data["content"]) > 0, f"Empty content for {rtype}"
    # Verify file download export
    res = requests.get(
        f"{BASE_URL}/v1/reports/projects/{proj_id}/export?type=bibtex&format=file", headers=headers
    )
    assert res.status_code == 200, f"Bibtex export failed: {res.status_code}"
    assert "attachment; filename=" in res.headers.get("content-disposition", "")
    print(
        "[PASS] 17. Feature 5 (Report Export Suite): Previewed LaTeX/BibTeX/MD/Audit and downloaded .bib file"
    )

    # 18. FEATURE 6: Multi-Paper Literature Q&A ("Chat with Papers")
    res = requests.post(
        f"{BASE_URL}/v1/projects/{proj_id}/chat",
        json={
            "query": "What are the detection rates reported for transformer anomaly detection?",
            "top_k": 3,
        },
        headers=headers,
    )
    assert res.status_code == 200, f"Literature Chat failed: {res.status_code} {res.text}"
    chat_data = res.json()
    assert len(chat_data["answer"]) > 0, "No answer returned"
    assert len(chat_data["citations"]) > 0, "No citations returned"
    print(
        f"[PASS] 18. Feature 6 (Literature Q&A): Received grounded response with {len(chat_data['citations'])} citation(s)"
    )

    print("\n========================================================")
    print("ALL 18 LIVE END-TO-END CHECKS (ALL 6 FEATURES) PASSED!")
    print("========================================================")


if __name__ == "__main__":
    try:
        test_live_features()
    except Exception as e:
        print(f"[FAIL] {e}", file=sys.stderr)
        sys.exit(1)
