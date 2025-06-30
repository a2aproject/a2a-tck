#!/usr/bin/env python3
"""
A2A Test Coverage Analysis Script

Analyzes the current A2A specification against the existing test suite to identify:
- Missing test coverage for requirements
- Test quality issues
- Orphaned tests
- Coverage gaps and recommendations

This is different from check_spec_changes.py which compares two spec versions.
This script analyzes the current specification in isolation.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
import os

# --- Path Correction ---
# To run this script from anywhere, we need to adjust the Python path
# and current working directory.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
os.chdir(project_root)
# --- End Path Correction ---

from spec_tracker.spec_parser import SpecParser
from spec_tracker.test_coverage_analyzer import TestCoverageAnalyzer
from spec_tracker.report_generator import ReportGenerator

logger = logging.getLogger(__name__)

class CoverageReportGenerator:
    """Generates comprehensive test coverage reports."""
    
    def generate_coverage_report(self, 
                                coverage_analysis: dict, 
                                spec_info: dict,
                                summary_only: bool = False) -> str:
        """Generate a comprehensive coverage report."""
        
        if summary_only:
            return self._generate_summary_report(coverage_analysis, spec_info)
        else:
            return self._generate_detailed_report(coverage_analysis, spec_info)
    
    def _generate_summary_report(self, coverage_analysis: dict, spec_info: dict) -> str:
        """Generate a concise summary report."""
        req_coverage = coverage_analysis.get('requirement_coverage', {})
        method_coverage = coverage_analysis.get('method_coverage', {})
        quality = coverage_analysis.get('test_quality', {})
        
        # Calculate overall coverage percentage
        total_reqs = req_coverage.get('total_requirements', 0)
        covered_reqs = req_coverage.get('covered_requirements', 0)
        overall_percentage = (covered_reqs / total_reqs * 100) if total_reqs > 0 else 0
        
        report = f"""# A2A Test Coverage Analysis Summary

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Specification:** Current A2A Specification

## 📊 Coverage Overview

| Metric | Value | Status |
|--------|-------|--------|
| **Overall Coverage** | {overall_percentage:.1f}% | {'🟢 Good' if overall_percentage >= 80 else '🟡 Needs Improvement' if overall_percentage >= 60 else '🔴 Poor'} |
| **Total Requirements** | {total_reqs} | - |
| **Covered Requirements** | {covered_reqs} | - |
| **Uncovered Requirements** | {len(req_coverage.get('uncovered_requirements', []))} | - |
| **Total Tests** | {quality.get('total_tests', 0)} | - |
| **Documented Tests** | {quality.get('documented_tests', 0)} | - |

## 🎯 Priority Actions

"""
        
        # Add critical gaps
        gaps = coverage_analysis.get('coverage_gaps', {})
        if gaps.get('critical_gaps'):
            report += "### 🚨 Critical Issues\n"
            for gap in gaps['critical_gaps'][:3]:
                report += f"- {gap}\n"
            report += "\n"
            
        # Add top recommendations
        recommendations = coverage_analysis.get('recommendations', [])
        high_priority = [r for r in recommendations if r.get('priority') == 'HIGH']
        if high_priority:
            report += "### 🔧 Immediate Actions Needed\n"
            for rec in high_priority[:3]:
                report += f"- **{rec['title']}**: {rec['description']}\n"
            report += "\n"
            
        report += f"""## 📋 Next Steps

1. **Review uncovered requirements**: Focus on {len(req_coverage.get('uncovered_requirements', []))} missing requirement tests
2. **Improve test documentation**: {len(quality.get('undocumented_tests', []))} tests need better documentation
3. **Run detailed analysis**: Use 'util_scripts/analyze_test_coverage.py' (without --summary-only) for complete report

---
*Run with `--help` for more options*
"""
        
        return report
    
    def _generate_detailed_report(self, coverage_analysis: dict, spec_info: dict) -> str:
        """Generate a comprehensive detailed report."""
        req_coverage = coverage_analysis.get('requirement_coverage', {})
        method_coverage = coverage_analysis.get('method_coverage', {})
        error_coverage = coverage_analysis.get('error_coverage', {})
        capability_coverage = coverage_analysis.get('capability_coverage', {})
        quality = coverage_analysis.get('test_quality', {})
        gaps = coverage_analysis.get('coverage_gaps', {})
        recommendations = coverage_analysis.get('recommendations', [])
        
        report = f"""# A2A Test Coverage Analysis Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Specification:** Current A2A Specification
**Analysis Type:** Comprehensive Coverage Assessment

## 📊 Executive Summary

This report analyzes the current A2A test suite against the specification to identify coverage gaps, test quality issues, and improvement opportunities.

### Key Metrics

| Category | Coverage | Status |
|----------|----------|--------|
| **Requirements** | {(req_coverage.get('covered_requirements', 0) / max(req_coverage.get('total_requirements', 1), 1) * 100):.1f}% | {self._get_status_emoji((req_coverage.get('covered_requirements', 0) / max(req_coverage.get('total_requirements', 1), 1) * 100))} |
| **JSON-RPC Methods** | {(method_coverage.get('covered_methods', 0) / max(method_coverage.get('total_methods', 1), 1) * 100):.1f}% | {self._get_status_emoji((method_coverage.get('covered_methods', 0) / max(method_coverage.get('total_methods', 1), 1) * 100))} |
| **Error Codes** | {(error_coverage.get('covered_errors', 0) / max(error_coverage.get('total_errors', 1), 1) * 100):.1f}% | {self._get_status_emoji((error_coverage.get('covered_errors', 0) / max(error_coverage.get('total_errors', 1), 1) * 100))} |
| **Test Documentation** | {(quality.get('documented_tests', 0) / max(quality.get('total_tests', 1), 1) * 100):.1f}% | {self._get_status_emoji((quality.get('documented_tests', 0) / max(quality.get('total_tests', 1), 1) * 100))} |

## 📋 Requirement Coverage Analysis

### Coverage by Requirement Level

"""
        
        # Requirement coverage by level
        for level, coverage in req_coverage.get('coverage_by_level', {}).items():
            percentage = coverage.get('percentage', 0)
            status = self._get_status_emoji(percentage)
            report += f"- **{level.upper()}**: {coverage.get('covered', 0)}/{coverage.get('total', 0)} covered ({percentage:.1f}%) {status}\n"
        
        report += "\n### Uncovered Requirements\n\n"
        
        uncovered = req_coverage.get('uncovered_requirements', [])
        if uncovered:
            report += f"**{len(uncovered)} requirements have no test coverage:**\n\n"
            for req_id in uncovered[:10]:  # Show first 10
                req_details = req_coverage.get('requirement_details', {}).get(req_id, {})
                req = req_details.get('requirement')
                if req:
                    level = getattr(req, 'level', 'UNKNOWN')
                    text = getattr(req, 'text', 'No description')[:100]
                    report += f"- **{level}**: {text}{'...' if len(getattr(req, 'text', '')) > 100 else ''}\n"
            
            if len(uncovered) > 10:
                report += f"\n*... and {len(uncovered) - 10} more*\n"
        else:
            report += "✅ All requirements have some test coverage!\n"
            
        report += "\n### Weakly Covered Requirements\n\n"
        
        weakly_covered = req_coverage.get('weakly_covered_requirements', [])
        if weakly_covered:
            report += f"**{len(weakly_covered)} requirements have weak test coverage:**\n\n"
            for req_id in weakly_covered[:5]:  # Show first 5
                req_details = req_coverage.get('requirement_details', {}).get(req_id, {})
                req = req_details.get('requirement')
                if req:
                    level = getattr(req, 'level', 'UNKNOWN')
                    text = getattr(req, 'text', 'No description')[:80]
                    test_count = req_details.get('test_count', 0)
                    quality_score = req_details.get('quality_score', 0)
                    report += f"- **{level}**: {text}... (Tests: {test_count}, Quality: {quality_score:.1f})\n"
        else:
            report += "✅ No requirements identified with weak coverage!\n"
        
        report += f"""

## 🔧 JSON-RPC Method Coverage

**Total Methods:** {method_coverage.get('total_methods', 0)}
**Covered Methods:** {method_coverage.get('covered_methods', 0)}
**Uncovered Methods:** {len(method_coverage.get('uncovered_methods', []))}

"""
        
        uncovered_methods = method_coverage.get('uncovered_methods', [])
        if uncovered_methods:
            report += "### Methods Without Tests\n\n"
            for method in uncovered_methods:
                report += f"- `{method}`\n"
        else:
            report += "✅ All JSON-RPC methods have test coverage!\n"
            
        report += f"""

## ⚠️ Error Code Coverage

**Total Error Codes:** {error_coverage.get('total_errors', 0)}
**Covered Error Codes:** {error_coverage.get('covered_errors', 0)}
**Uncovered Error Codes:** {len(error_coverage.get('uncovered_errors', []))}

"""

        uncovered_errors = error_coverage.get('uncovered_errors', [])
        if uncovered_errors:
            report += "### Error Codes Without Tests\n\n"
            for error in uncovered_errors[:10]:  # Show first 10
                report += f"- Error code `{error}`\n"
            if len(uncovered_errors) > 10:
                report += f"\n*... and {len(uncovered_errors) - 10} more*\n"
        else:
            report += "✅ All error codes have test coverage!\n"
            
        report += f"""

## 🎛️ Optional Capability Coverage

**Total Capabilities:** {capability_coverage.get('total_capabilities', 0)}
**Covered Capabilities:** {capability_coverage.get('covered_capabilities', 0)}

"""

        if capability_coverage.get('total_capabilities', 0) > 0:
            uncovered_capabilities = capability_coverage.get('uncovered_capabilities', [])
            if uncovered_capabilities:
                report += "### Capabilities Without Tests\n\n"
                for capability in uncovered_capabilities:
                    report += f"- `{capability}`\n"
            else:
                report += "✅ All capabilities have test coverage!\n"
        else:
            report += "*No optional capabilities detected in specification.*\n"
            
        report += f"""

## 📚 Test Quality Analysis

**Total Tests:** {quality.get('total_tests', 0)}
**Documented Tests:** {quality.get('documented_tests', 0)} ({(quality.get('documented_tests', 0) / max(quality.get('total_tests', 1), 1) * 100):.1f}%)
**Tests with Spec References:** {quality.get('tests_with_docs', 0)}
**Orphaned Tests:** {len(quality.get('orphaned_tests', []))}

### Quality Distribution

"""
        
        quality_dist = quality.get('quality_distribution', {})
        for level, count in quality_dist.items():
            percentage = (count / max(quality.get('total_tests', 1), 1) * 100)
            report += f"- **{level.title()} Quality**: {count} tests ({percentage:.1f}%)\n"
            
        complexity_dist = quality.get('complexity_distribution', {})
        report += "\n### Complexity Distribution\n\n"
        for level, count in complexity_dist.items():
            percentage = (count / max(quality.get('total_tests', 1), 1) * 100)
            report += f"- **{level.title()} Complexity**: {count} tests ({percentage:.1f}%)\n"
            
        # Orphaned tests
        orphaned = quality.get('orphaned_tests', [])
        if orphaned:
            report += f"\n### Orphaned Tests (No Spec References)\n\n"
            report += f"**{len(orphaned)} tests lack specification references:**\n\n"
            for test in orphaned[:10]:  # Show first 10
                report += f"- `{test}`\n"
            if len(orphaned) > 10:
                report += f"\n*... and {len(orphaned) - 10} more*\n"
                
        report += f"""

## 🎯 Coverage Gaps & Issues

"""
        
        for gap_type, gap_list in gaps.items():
            if gap_list and gap_type != 'recommendations':
                level_emoji = {'critical_gaps': '🚨', 'major_gaps': '⚠️', 'minor_gaps': '💡'}
                report += f"### {level_emoji.get(gap_type, '💡')} {gap_type.replace('_', ' ').title()}\n\n"
                for gap in gap_list:
                    report += f"- {gap}\n"
                report += "\n"
                
        report += """## 🔧 Recommendations

### Prioritized Action Plan

"""
        
        # Group recommendations by priority
        high_priority = [r for r in recommendations if r.get('priority') == 'HIGH']
        medium_priority = [r for r in recommendations if r.get('priority') == 'MEDIUM']
        low_priority = [r for r in recommendations if r.get('priority') == 'LOW']
        
        for priority, recs in [('🚨 High Priority', high_priority), ('⚠️ Medium Priority', medium_priority), ('💡 Low Priority', low_priority)]:
            if recs:
                report += f"\n#### {priority}\n\n"
                for rec in recs:
                    report += f"**{rec['title']}** ({rec.get('category', 'General')})\n"
                    report += f"- {rec['description']}\n"
                    report += f"- **Action**: {rec['action']}\n"
                    report += f"- **Effort**: {rec.get('effort', 'unknown')}\n\n"
                    
        report += f"""

## 📈 Improvement Targets

Based on this analysis, consider these improvement targets:

1. **MUST Requirement Coverage**: Achieve 95%+ coverage (currently {req_coverage.get('coverage_by_level', {}).get('MUST', {}).get('percentage', 0):.1f}%)
2. **Method Coverage**: Test all JSON-RPC methods (currently {(method_coverage.get('covered_methods', 0) / max(method_coverage.get('total_methods', 1), 1) * 100):.1f}%)
3. **Test Documentation**: Document 90%+ of tests (currently {(quality.get('documented_tests', 0) / max(quality.get('total_tests', 1), 1) * 100):.1f}%)
4. **Specification References**: Link 95%+ of tests to spec sections

## 🛠️ Tools & Commands

```bash
# Re-run this analysis
./analyze_test_coverage.py

# Generate summary report
./analyze_test_coverage.py --summary-only

# Export as JSON for automation
./analyze_test_coverage.py --json-export coverage_data.json

# Run specific test categories
./run_tck.py --category mandatory --verbose
./run_tck.py --category optional --verbose
```

---

*Generated by A2A TCK Test Coverage Analyzer*
"""
        
        return report
    
    def _get_status_emoji(self, percentage: float) -> str:
        """Get status emoji based on percentage."""
        if percentage >= 90:
            return "🟢 Excellent"
        elif percentage >= 80:
            return "🟡 Good"
        elif percentage >= 60:
            return "🟠 Needs Work"
        else:
            return "🔴 Poor"

def main():
    """Main entry point for test coverage analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze A2A test coverage against current specification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Full coverage analysis
  %(prog)s --summary-only                     # Quick summary report
  %(prog)s --output coverage_report.md        # Save to custom file
  %(prog)s --json-export coverage.json        # Export data as JSON
  %(prog)s --test-dir tests/                  # Use custom test directory
  %(prog)s --verbose                          # Enable detailed logging
        """
    )
    parser.add_argument(
        '--current-md',
        help='Path to current markdown spec file (default: current_spec/A2A_SPECIFICATION.md)',
        default='current_spec/A2A_SPECIFICATION.md'
    )
    parser.add_argument(
        '--current-json',
        help='Path to current JSON schema file (default: current_spec/a2a_schema.json)',
        default='current_spec/a2a_schema.json'
    )
    parser.add_argument(
        '--test-dir',
        help='Directory containing tests (default: tests)',
        default='tests',
        type=Path
    )
    parser.add_argument(
        '--output',
        help='Output file for the coverage report (default: reports/test_coverage_report.md)',
        default='reports/test_coverage_report.md',
        type=Path
    )
    parser.add_argument(
        '--json-export',
        help='Export coverage analysis as JSON to specified file'
    )
    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Generate only a concise summary report'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform analysis without saving reports'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        logger.info("🔍 Starting A2A Test Coverage Analysis")
        
        # Use arguments to find spec files
        current_md_path = Path(args.current_md)
        current_json_path = Path(args.current_json)

        if not current_md_path.exists():
            logger.error(f"❌ Current markdown spec not found: {current_md_path}")
            logger.info("💡 Run 'util_scripts/update_current_spec.py' to initialize baseline specifications")
            return 1
        
        if not current_json_path.exists():
            logger.error(f"❌ Current JSON schema not found: {current_json_path}")
            logger.info("💡 Run 'util_scripts/update_current_spec.py' to initialize baseline specifications")
            return 1
        
        if not args.test_dir.exists():
            logger.error(f"❌ Test directory not found: {args.test_dir}")
            return 1
            
        # Step 1: Parse current specification
        logger.info("📖 Parsing current specification...")
        spec_parser = SpecParser()
        
        try:
            with open(current_md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            with open(current_json_path, 'r', encoding='utf-8') as f:
                json_content = json.load(f)
                
            spec_data = {
                'markdown': spec_parser.parse_markdown(md_content),
                'json': spec_parser.parse_json_schema(json_content)
            }
            
            logger.info(f"✅ Parsed specification: {len(spec_data['markdown']['requirements'])} requirements, {len(spec_data['json']['definitions'])} definitions")
            
        except Exception as e:
            logger.error(f"❌ Failed to parse specification: {e}")
            return 1
            
        # Step 2: Analyze test coverage
        logger.info("🧪 Analyzing test suite...")
        coverage_analyzer = TestCoverageAnalyzer(args.test_dir)
        
        try:
            coverage_analysis = coverage_analyzer.analyze_specification_coverage(spec_data)
            summary_stats = coverage_analyzer.get_summary_stats()
            
            logger.info(f"✅ Analyzed {summary_stats['total_tests']} tests from {summary_stats['test_files']} files")
            
            # Log key findings
            req_coverage = coverage_analysis.get('requirement_coverage', {})
            overall_percentage = (req_coverage.get('covered_requirements', 0) / max(req_coverage.get('total_requirements', 1), 1) * 100)
            logger.info(f"📊 Overall requirement coverage: {overall_percentage:.1f}%")
            
            gaps = coverage_analysis.get('coverage_gaps', {})
            critical_count = len(gaps.get('critical_gaps', []))
            if critical_count > 0:
                logger.warning(f"⚠️  Found {critical_count} critical coverage gaps")
                
        except Exception as e:
            logger.error(f"❌ Failed to analyze test coverage: {e}")
            return 1
            
        # Step 3: Generate report
        logger.info("📝 Generating coverage report...")
        report_generator = CoverageReportGenerator()
        
        try:
            spec_info = {
                'requirements_count': len(spec_data['markdown']['requirements']),
                'definitions_count': len(spec_data['json']['definitions']),
                'test_count': summary_stats['total_tests']
            }
            
            report = report_generator.generate_coverage_report(
                coverage_analysis,
                spec_info,
                args.summary_only
            )
            
            logger.info(f"✅ Generated {'summary' if args.summary_only else 'detailed'} report: {len(report)} characters")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate report: {e}")
            return 1
            
        # Step 4: Save outputs
        if not args.dry_run:
            output_file = Path(args.output)
            # Create parent directory if it doesn't exist
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"✅ Report generated: {output_file}")
            
            # Save JSON export
            if args.json_export:
                json_output_file = Path(args.json_export)
                # Create parent directory if it doesn't exist
                json_output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(json_output_file, 'w') as f:
                    json.dump(coverage_analysis, f, indent=2)
                logger.info(f"✅ JSON data exported to {json_output_file}")
        else:
            logger.info("ξη Dry run complete, no reports were saved.")
            
        # Step 5: Summary
        logger.info("🎉 Test coverage analysis completed!")
        
        # Print key findings
        req_coverage = coverage_analysis.get('requirement_coverage', {})
        quality = coverage_analysis.get('test_quality', {})
        
        print(f"\n📊 Key Findings:")
        print(f"  Overall Coverage: {overall_percentage:.1f}%")
        print(f"  Total Tests: {quality.get('total_tests', 0)}")
        print(f"  Uncovered Requirements: {len(req_coverage.get('uncovered_requirements', []))}")
        print(f"  Orphaned Tests: {len(quality.get('orphaned_tests', []))}")
        
        recommendations = coverage_analysis.get('recommendations', [])
        high_priority = [r for r in recommendations if r.get('priority') == 'HIGH']
        if high_priority:
            print(f"  High Priority Actions: {len(high_priority)}")
            
        if not args.dry_run:
            print(f"\n📄 Full report saved to: {args.output}")
            
        # Return exit code based on coverage quality
        if critical_count > 0:
            logger.warning("⚠️  Critical coverage gaps detected")
            return 2  # Critical issues
        elif overall_percentage < 70:
            logger.warning("⚠️  Low overall coverage detected")
            return 1  # Improvement needed
        else:
            logger.info("✅ Coverage analysis completed successfully")
            return 0  # Good coverage
            
    except KeyboardInterrupt:
        logger.info("🛑 Analysis cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"❌ An error occurred: {e}", exc_info=args.verbose)
        return 1

if __name__ == '__main__':
    sys.exit(main()) 