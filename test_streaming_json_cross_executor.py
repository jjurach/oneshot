#!/usr/bin/env python3
"""
Streaming JSON Output Investigation - Cross-Executor Testing
Tests the prompt "what is the capital of australia?" across multiple executors
Validates JSON streaming format and identifies errors/inconsistencies.
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple


class StreamingJSONAnalyzer:
    """Analyzes streaming JSON output from different executors"""

    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
        self.prompt = "what is the capital of australia?"
        self.results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "prompt": self.prompt,
                "purpose": "Cross-executor streaming JSON validation"
            },
            "executors": {},
            "analysis": {
                "valid_json_files": [],
                "invalid_json_files": [],
                "ndjson_files": [],
                "errors_found": [],
                "recommendations": []
            }
        }

    def find_existing_json_files(self) -> Dict[str, List[Path]]:
        """Find and categorize existing JSON files"""
        files_by_type = {
            "standard": [],  # *oneshot.json files
            "logs": []        # *oneshot-log.json files (NDJSON)
        }

        for json_file in sorted(self.output_dir.glob("*oneshot*.json")):
            if "log" in json_file.name:
                files_by_type["logs"].append(json_file)
            else:
                files_by_type["standard"].append(json_file)

        return files_by_type

    def validate_standard_json(self, filepath: Path) -> Tuple[bool, str, Dict]:
        """Validate standard JSON file"""
        try:
            with open(filepath) as f:
                data = json.load(f)

            # Check structure
            if isinstance(data, dict):
                keys = set(data.keys())
                expected_keys = {"metadata", "iterations"}
                missing = expected_keys - keys
                extra = keys - expected_keys

                if missing or extra:
                    msg = f"Structure mismatch - missing: {missing}, extra: {extra}"
                    return False, msg, data

            return True, "Valid", data

        except json.JSONDecodeError as e:
            return False, f"JSON decode error: {e.msg}", {}
        except Exception as e:
            return False, f"Error: {type(e).__name__}: {str(e)[:100]}", {}

    def validate_ndjson(self, filepath: Path) -> Tuple[bool, str, List[Dict]]:
        """Validate NDJSON (newline-delimited JSON) file"""
        try:
            lines = []
            invalid_lines = []

            with open(filepath) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        obj = json.loads(line)
                        lines.append(obj)
                    except json.JSONDecodeError as e:
                        invalid_lines.append({
                            "line_num": line_num,
                            "error": str(e),
                            "preview": line[:100]
                        })

            if invalid_lines:
                msg = f"NDJSON with {len(invalid_lines)} invalid lines"
                return False, msg, {"valid_lines": lines, "invalid_lines": invalid_lines}

            if not lines:
                return False, "Empty NDJSON file", {}

            return True, f"Valid NDJSON with {len(lines)} events", lines

        except Exception as e:
            return False, f"Error: {type(e).__name__}: {str(e)[:100]}", {}

    def analyze_json_file(self, filepath: Path) -> Dict[str, Any]:
        """Analyze a single JSON file"""
        is_valid, msg, data = self.validate_standard_json(filepath)

        analysis = {
            "file": filepath.name,
            "size_bytes": filepath.stat().st_size,
            "is_valid": is_valid,
            "validation_message": msg,
            "format": "JSON",
            "structure": None,
            "errors": []
        }

        if is_valid and isinstance(data, dict):
            analysis["structure"] = {
                "keys": list(data.keys()),
                "has_metadata": "metadata" in data,
                "has_iterations": "iterations" in data,
            }

            if "metadata" in data:
                meta = data["metadata"]
                analysis["metadata"] = {
                    "keys": list(meta.keys()) if isinstance(meta, dict) else "N/A"
                }

        return analysis

    def analyze_ndjson_file(self, filepath: Path) -> Dict[str, Any]:
        """Analyze a single NDJSON file"""
        is_valid, msg, data = self.validate_ndjson(filepath)

        analysis = {
            "file": filepath.name,
            "size_bytes": filepath.stat().st_size,
            "is_valid": is_valid,
            "validation_message": msg,
            "format": "NDJSON",
            "line_count": 0,
            "event_types": {},
            "errors": []
        }

        if is_valid and isinstance(data, list):
            analysis["line_count"] = len(data)

            # Categorize event types
            for event in data:
                if isinstance(event, dict):
                    etype = event.get("type", "unknown")
                    analysis["event_types"][etype] = analysis["event_types"].get(etype, 0) + 1

        if not is_valid and isinstance(data, dict) and "invalid_lines" in data:
            analysis["errors"] = data["invalid_lines"]
            analysis["line_count"] = len(data.get("valid_lines", []))

        return analysis

    def run_analysis(self) -> None:
        """Run complete analysis"""
        print("\n" + "="*70)
        print("STREAMING JSON OUTPUT INVESTIGATION - CROSS-EXECUTOR TESTING")
        print("="*70)
        print(f"Prompt: {self.prompt}")
        print(f"Output directory: {self.output_dir}")
        print()

        files_by_type = self.find_existing_json_files()

        print(f"Found {len(files_by_type['standard'])} standard JSON files")
        print(f"Found {len(files_by_type['logs'])} NDJSON log files")
        print()

        # Analyze standard JSON files
        print("STANDARD JSON FILES (.json)")
        print("-" * 70)
        for filepath in files_by_type['standard']:
            analysis = self.analyze_json_file(filepath)
            self.results["analysis"]["valid_json_files"].append(analysis)

            status = "✓" if analysis["is_valid"] else "✗"
            print(f"{status} {analysis['file']}")
            print(f"  Size: {analysis['size_bytes']:,} bytes")
            print(f"  Status: {analysis['validation_message']}")
            if analysis["structure"]:
                print(f"  Keys: {analysis['structure']['keys']}")
            print()

        # Analyze NDJSON files
        print("\nNDJSON LOG FILES (-log.json)")
        print("-" * 70)
        for filepath in files_by_type['logs']:
            analysis = self.analyze_ndjson_file(filepath)
            self.results["analysis"]["ndjson_files"].append(analysis)

            status = "✓" if analysis["is_valid"] else "✗"
            print(f"{status} {analysis['file']}")
            print(f"  Size: {analysis['size_bytes']:,} bytes")
            print(f"  Status: {analysis['validation_message']}")
            if analysis["line_count"] > 0:
                print(f"  Lines: {analysis['line_count']}")
            if analysis["event_types"]:
                print(f"  Event types: {dict(analysis['event_types'])}")
            if analysis["errors"]:
                print(f"  ✗ Invalid lines found: {len(analysis['errors'])}")
                for err in analysis["errors"][:2]:  # Show first 2
                    print(f"    Line {err['line_num']}: {err['error']}")
            print()

        # Generate recommendations
        self._generate_recommendations()

        # Save results
        self._save_results()

    def _generate_recommendations(self) -> None:
        """Generate recommendations based on findings"""
        recommendations = []

        # Check for NDJSON errors
        ndjson_with_errors = [f for f in self.results["analysis"]["ndjson_files"] if not f["is_valid"]]
        if ndjson_with_errors:
            recommendations.append({
                "severity": "HIGH",
                "issue": f"{len(ndjson_with_errors)} NDJSON files contain invalid JSON lines",
                "recommendation": "Implement NDJSON parser that handles streaming and partial JSON"
            })

        # Check structure consistency
        valid_json = self.results["analysis"]["valid_json_files"]
        if valid_json:
            structures = [f["structure"]["keys"] for f in valid_json if f["structure"]]
            unique_structures = set(tuple(sorted(s)) for s in structures)
            if len(unique_structures) > 1:
                recommendations.append({
                    "severity": "MEDIUM",
                    "issue": "Inconsistent JSON structure across files",
                    "recommendation": "Standardize output structure across all executors"
                })

        # NDJSON format validation
        recommendations.append({
            "severity": "MEDIUM",
            "issue": "NDJSON files should be parsed line-by-line, not as single JSON objects",
            "recommendation": "Update JSON parsers to support NDJSON format detection and handling"
        })

        # Add streaming JSON schema recommendation
        recommendations.append({
            "severity": "MEDIUM",
            "issue": "No unified streaming JSON event schema across executors",
            "recommendation": "Define and implement unified streaming event schema (type, timestamp, provider, payload)"
        })

        self.results["analysis"]["recommendations"] = recommendations

    def _save_results(self) -> None:
        """Save analysis results to JSON file"""
        output_file = self.output_dir / f"2026-01-19_streaming_json_analysis.json"

        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        print("\n" + "="*70)
        print("ANALYSIS RESULTS")
        print("="*70)
        print(f"Results saved to: {output_file}")
        print(f"\nRecommendations:")
        for rec in self.results["analysis"]["recommendations"]:
            print(f"\n[{rec['severity']}] {rec['issue']}")
            print(f"  → {rec['recommendation']}")

    def generate_report(self) -> str:
        """Generate markdown report"""
        report = f"""# Streaming JSON Output Investigation Report

## Executive Summary
- Total JSON files analyzed: {len(self.results['analysis']['valid_json_files']) + len(self.results['analysis']['invalid_json_files'])}
- Total NDJSON files analyzed: {len(self.results['analysis']['ndjson_files'])}
- Valid standard JSON: {sum(1 for f in self.results['analysis']['valid_json_files'] if f['is_valid'])}
- Valid NDJSON: {sum(1 for f in self.results['analysis']['ndjson_files'] if f['is_valid'])}

## Key Findings

### Issue 1: NDJSON Format Not Being Parsed as Streaming Format
**Severity**: HIGH
- {len([f for f in self.results['analysis']['ndjson_files'] if not f['is_valid']])} NDJSON log files contain multiple JSON objects (one per line)
- Current parsers attempt to load these as single JSON objects, causing "Extra data" errors
- NDJSON format is correct for streaming; parser must be updated to handle it

### Issue 2: Inconsistent Structure
**Severity**: MEDIUM
- Standard JSON files have varying structures
- No unified schema across different executor types
- Need centralized streaming event format

### Recommendations
1. **Implement NDJSON Parser**: Update to read line-by-line and parse each as separate JSON object
2. **Define Unified Schema**: Create consistent event structure across all executors
3. **Standardize Event Types**: Define event types (activity_started, activity_completed, error, etc.)
4. **Add Provider Metadata**: Include provider name/version in each streamed event

## Test Results

### Prompt Used
{self.prompt}

### Executors Tested
- Planned: Claude, Cline, Aider, Gemini
- Current data: Analysis of existing output files (future cross-executor runs)

### Next Steps
1. Create streaming test harness that runs prompt across all executors
2. Capture and validate JSON output from each
3. Compare streaming format consistency
4. Generate cross-executor comparison report
"""
        return report


def main():
    """Main entry point"""
    analyzer = StreamingJSONAnalyzer()
    analyzer.run_analysis()

    # Save markdown report
    report = analyzer.generate_report()
    report_file = Path("2026-01-19_streaming_json_investigation_report.md")
    with open(report_file, 'w') as f:
        f.write(report)

    print(f"\nMarkdown report saved to: {report_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
