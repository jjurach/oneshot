import json
import os
import pytest
from src.oneshot.protocol import ResultExtractor, ResultSummary

def test_result_summary_bool():
    summary = ResultSummary(result="test")
    assert bool(summary) is True
    
    empty_summary = ResultSummary(result="")
    assert bool(empty_summary) is False

def test_score_text_basic():
    extractor = ResultExtractor()
    
    # High score for DONE
    score_done = extractor._score_text("Task is DONE")
    assert score_done >= extractor.score_weights['done_keyword']
    
    # Penalty for human intervention
    score_human = extractor._score_text("I need HUMAN intervention")
    assert score_human < score_done
    
    # Valid JSON bonus
    score_json = extractor._score_text('{"status": "success", "result": "completed"}')
    assert score_json > extractor.score_weights['json_valid']

def test_extract_result_with_context(tmp_path):
    log_file = tmp_path / "test-log.json"
    
    events = [
        {"stdout": "Initializing..."},
        {"stdout": "Starting step 1"},
        {"stdout": "Step 1 finished"},
        {"stdout": "Working on step 2"},
        {"stdout": "DONE! All steps completed."}, # Best result (index 4)
        {"stdout": "Cleaning up..."},
        {"stdout": "Exiting."}
    ]
    
    with open(log_file, "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")
            
    extractor = ResultExtractor()
    summary = extractor.extract_result(str(log_file))
    
    assert summary is not None
    assert "DONE!" in summary.result
    
    # Context check (indices 2, 3 and 5, 6)
    assert len(summary.leading_context) == 2
    assert "Step 1 finished" in summary.leading_context[0]
    assert "Working on step 2" in summary.leading_context[1]
    
    assert len(summary.trailing_context) == 2
    assert "Cleaning up" in summary.trailing_context[0]
    assert "Exiting" in summary.trailing_context[1]

def test_extract_result_no_high_score(tmp_path):
    log_file = tmp_path / "test-log-low.json"
    
    events = [
        {"stdout": "nothing interesting"},
        {"stdout": "still nothing"},
        {"stdout": "the end"}
    ]
    
    with open(log_file, "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")
            
    extractor = ResultExtractor()
    summary = extractor.extract_result(str(log_file))
    
    assert summary is not None
    # Should fallback to last event if no high scores
    assert summary.result == "the end"
    assert len(summary.leading_context) == 2
    assert len(summary.trailing_context) == 0

def test_extract_result_empty_log(tmp_path):
    log_file = tmp_path / "empty.json"
    log_file.write_text("")
    
    extractor = ResultExtractor()
    assert extractor.extract_result(str(log_file)) is None

def test_extract_result_malformed_json(tmp_path):
    log_file = tmp_path / "malformed.json"
    log_file.write_text("not json\n{'also': 'not json'}\n")
    
    extractor = ResultExtractor()
    assert extractor.extract_result(str(log_file)) is None
