"""
Generates markdown reports for specification changes and test impacts.
"""

from datetime import datetime
from typing import Dict, Any, List
import json

class ReportGenerator:
    """Generates analysis reports."""
    
    def generate_report(self, 
                       spec_changes: Dict,
                       test_impacts: Dict,
                       coverage_analysis: Dict,
                       old_version: str,
                       new_version: str) -> str:
        """
        Generate a comprehensive markdown report.
        
        Args:
            spec_changes: Dict from SpecComparator
            test_impacts: Dict from TestImpactAnalyzer.analyze_impact
            coverage_analysis: Dict from TestImpactAnalyzer.analyze_coverage
            old_version: String identifying current version
            new_version: String identifying new version
            
        Returns:
            Markdown formatted report string
        """
        report = []
        
        # Header
        report.append(f"# A2A Specification Change Analysis Report")
        report.append(f"\nGenerated: {datetime.now().isoformat()}")
        report.append(f"\n## Version Comparison")
        report.append(f"- **Current Version**: {old_version}")
        report.append(f"- **Latest Version**: {new_version}")
        
        # Executive Summary
        report.append(f"\n## Executive Summary")
        report.extend(self._generate_summary(spec_changes, test_impacts, coverage_analysis))
        
        # Detailed Changes
        report.append(f"\n## Specification Changes")
        report.extend(self._format_spec_changes(spec_changes))
        
        # Test Impacts
        report.append(f"\n## Test Impact Analysis")
        report.extend(self._format_test_impacts(test_impacts))
        
        # Coverage Analysis
        report.append(f"\n## Test Coverage Analysis")
        report.extend(self._format_coverage_analysis(coverage_analysis))
        
        # Recommendations
        report.append(f"\n## Recommendations")
        report.extend(self._generate_recommendations(spec_changes, test_impacts, coverage_analysis))
        
        return '\n'.join(report)
        
    def _generate_summary(self, spec_changes: Dict, test_impacts: Dict, coverage_analysis: Dict) -> List[str]:
        """Generate executive summary section."""
        summary = []
        
        # Count changes
        md_changes = spec_changes.get('markdown_changes', {})
        json_changes = spec_changes.get('json_changes', {})
        impact_summary = spec_changes.get('summary', {})
        
        total_changes = impact_summary.get('total_changes', 0)
        
        summary.append(f"\n- **Total Specification Changes**: {total_changes}")
        
        # Requirement changes
        req_changes = impact_summary.get('requirement_changes', {})
        req_added = req_changes.get('added', 0)
        req_removed = req_changes.get('removed', 0)
        req_modified = req_changes.get('modified', 0)
        
        if req_added + req_removed + req_modified > 0:
            summary.append(f"- **Requirement Changes**: {req_added} added, {req_removed} removed, {req_modified} modified")
        
        # Definition changes
        def_changes = impact_summary.get('definition_changes', {})
        def_added = def_changes.get('added', 0)
        def_removed = def_changes.get('removed', 0)
        def_modified = def_changes.get('modified', 0)
        
        if def_added + def_removed + def_modified > 0:
            summary.append(f"- **JSON Schema Changes**: {def_added} definitions added, {def_removed} removed, {def_modified} modified")
        
        # Method changes
        method_changes = impact_summary.get('method_changes', {})
        method_added = method_changes.get('added', 0)
        method_removed = method_changes.get('removed', 0)
        
        if method_added + method_removed > 0:
            summary.append(f"- **Method Changes**: {method_added} added, {method_removed} removed")
        
        # Test impacts
        directly_affected = len(test_impacts.get('directly_affected', []))
        new_coverage_needed = len(test_impacts.get('new_coverage_needed', []))
        obsolete_tests = len(test_impacts.get('obsolete_tests', []))
        
        summary.append(f"- **Directly Affected Tests**: {directly_affected}")
        summary.append(f"- **New Requirements Needing Tests**: {new_coverage_needed}")
        summary.append(f"- **Potentially Obsolete Tests**: {obsolete_tests}")
        
        # Coverage statistics
        overall_coverage = coverage_analysis.get('overall_coverage', {})
        req_coverage = overall_coverage.get('requirement_coverage_percentage', 0)
        test_doc = overall_coverage.get('test_documentation_percentage', 0)
        
        summary.append(f"- **Current Test Coverage**: {req_coverage:.1f}% requirements, {test_doc:.1f}% test documentation")
        
        # Risk assessment
        impact_classification = spec_changes.get('impact_classification', {})
        breaking_changes = len(impact_classification.get('breaking_changes', []))
        
        if breaking_changes > 0:
            summary.append(f"\n⚠️ **WARNING**: {breaking_changes} breaking changes detected!")
        elif obsolete_tests > 0:
            summary.append(f"\n⚠️ **ATTENTION**: {obsolete_tests} tests may be obsolete due to removed requirements")
        elif new_coverage_needed > 5:
            summary.append(f"\n📋 **NOTE**: {new_coverage_needed} new requirements need test coverage")
        else:
            summary.append(f"\n✅ **GOOD**: No critical issues detected")
            
        return summary
    
    def _format_spec_changes(self, spec_changes: Dict) -> List[str]:
        """Format specification changes section."""
        changes = []
        
        # Check if there are any changes
        total_changes = spec_changes.get('summary', {}).get('total_changes', 0)
        if total_changes == 0:
            changes.append("\n*No specification changes detected.*")
            return changes
        
        # Markdown changes
        md_changes = spec_changes.get('markdown_changes', {})
        
        # Requirement changes
        req_changes = md_changes.get('requirements', {})
        added_reqs = req_changes.get('added', [])
        removed_reqs = req_changes.get('removed', [])
        modified_reqs = req_changes.get('modified', [])
        
        if added_reqs:
            changes.append(f"\n### Added Requirements ({len(added_reqs)})")
            for req_change in added_reqs[:10]:  # Limit to first 10
                req = req_change.get('requirement')
                level = req_change.get('level', 'UNKNOWN')
                section = req_change.get('section', 'Unknown Section')
                text = getattr(req, 'text', str(req))[:100] + "..." if len(getattr(req, 'text', str(req))) > 100 else getattr(req, 'text', str(req))
                changes.append(f"\n- **{level}** in *{section}*: {text}")
        
        if removed_reqs:
            changes.append(f"\n### Removed Requirements ({len(removed_reqs)})")
            for req_change in removed_reqs[:10]:  # Limit to first 10
                req = req_change.get('requirement')
                level = req_change.get('level', 'UNKNOWN')
                section = req_change.get('section', 'Unknown Section')
                text = getattr(req, 'text', str(req))[:100] + "..." if len(getattr(req, 'text', str(req))) > 100 else getattr(req, 'text', str(req))
                changes.append(f"\n- **{level}** in *{section}*: {text}")
        
        # Section changes
        section_changes = md_changes.get('sections', {})
        added_sections = section_changes.get('added', [])
        modified_sections = section_changes.get('modified', [])
        
        if added_sections:
            changes.append(f"\n### Added Sections ({len(added_sections)})")
            for section in added_sections[:5]:  # Limit to first 5
                title = section.get('title', 'Unknown')
                changes.append(f"\n- {title}")
        
        if modified_sections:
            changes.append(f"\n### Modified Sections ({len(modified_sections)})")
            for section in modified_sections[:5]:  # Limit to first 5
                title = section.get('title', 'Unknown')
                diff = section.get('content_diff', 'Content changed')
                changes.append(f"\n- {title}: {diff}")
        
        # JSON Schema changes
        json_changes = spec_changes.get('json_changes', {})
        
        # Definition changes
        def_changes = json_changes.get('definitions', {})
        added_defs = def_changes.get('added', [])
        removed_defs = def_changes.get('removed', [])
        
        if added_defs:
            changes.append(f"\n### Added JSON Definitions ({len(added_defs)})")
            for def_change in added_defs[:10]:  # Limit to first 10
                name = def_change.get('name', 'Unknown')
                definition = def_change.get('definition', {})
                desc = definition.get('description', 'No description')[:80] + "..." if len(definition.get('description', '')) > 80 else definition.get('description', 'No description')
                changes.append(f"\n- **{name}**: {desc}")
        
        if removed_defs:
            changes.append(f"\n### Removed JSON Definitions ({len(removed_defs)})")
            for def_change in removed_defs[:10]:  # Limit to first 10
                name = def_change.get('name', 'Unknown')
                changes.append(f"\n- **{name}**")
        
        # Method changes
        method_changes = json_changes.get('methods', {})
        added_methods = method_changes.get('added', [])
        removed_methods = method_changes.get('removed', [])
        
        if added_methods:
            changes.append(f"\n### Added Methods ({len(added_methods)})")
            for method_change in added_methods:
                name = method_change.get('name', 'Unknown')
                method_info = method_change.get('method_info', {})
                desc = method_info.get('description', 'No description')[:80] + "..." if len(method_info.get('description', '')) > 80 else method_info.get('description', 'No description')
                changes.append(f"\n- **{name}**: {desc}")
        
        if removed_methods:
            changes.append(f"\n### Removed Methods ({len(removed_methods)})")
            for method_change in removed_methods:
                name = method_change.get('name', 'Unknown')
                changes.append(f"\n- **{name}**")
        
        # Impact Classification
        impact_classification = spec_changes.get('impact_classification', {})
        breaking_changes = impact_classification.get('breaking_changes', [])
        
        if breaking_changes:
            changes.append(f"\n### ⚠️ Breaking Changes ({len(breaking_changes)})")
            for breaking_change in breaking_changes:
                change_type = breaking_change.get('type', 'unknown')
                impact = breaking_change.get('impact', 'Unknown impact')
                changes.append(f"\n- **{change_type.replace('_', ' ').title()}**: {impact}")
        
        return changes
    
    def _format_test_impacts(self, test_impacts: Dict) -> List[str]:
        """Format test impact analysis section."""
        impacts = []
        
        # Check if there are any impacts
        total_impacts = sum(len(test_list) for test_list in test_impacts.values())
        if total_impacts == 0:
            impacts.append("\n*No test impacts detected.*")
            return impacts
        
        # Directly affected tests
        directly_affected = test_impacts.get('directly_affected', [])
        if directly_affected:
            impacts.append(f"\n### Directly Affected Tests ({len(directly_affected)})")
            impacts.append("\n*Tests that reference changed specification sections:*")
            for test_key in directly_affected[:10]:  # Limit to first 10
                test_name = test_key.split('::')[-1] if '::' in test_key else test_key
                test_file = test_key.split('::')[0] if '::' in test_key else 'unknown'
                impacts.append(f"\n- `{test_name}` in `{test_file}`")
            if len(directly_affected) > 10:
                impacts.append(f"\n- ... and {len(directly_affected) - 10} more")
        
        # New coverage needed
        new_coverage = test_impacts.get('new_coverage_needed', [])
        if new_coverage:
            impacts.append(f"\n### New Test Coverage Needed ({len(new_coverage)})")
            impacts.append("\n*New requirements or features that may need test coverage:*")
            for test_key in new_coverage[:10]:  # Limit to first 10
                test_name = test_key.split('::')[-1] if '::' in test_key else test_key
                test_file = test_key.split('::')[0] if '::' in test_key else 'unknown'
                impacts.append(f"\n- `{test_name}` in `{test_file}`")
            if len(new_coverage) > 10:
                impacts.append(f"\n- ... and {len(new_coverage) - 10} more")
        
        # Obsolete tests
        obsolete_tests = test_impacts.get('obsolete_tests', [])
        if obsolete_tests:
            impacts.append(f"\n### Potentially Obsolete Tests ({len(obsolete_tests)})")
            impacts.append("\n*Tests that may be testing removed requirements:*")
            for test_key in obsolete_tests[:10]:  # Limit to first 10
                test_name = test_key.split('::')[-1] if '::' in test_key else test_key
                test_file = test_key.split('::')[0] if '::' in test_key else 'unknown'
                impacts.append(f"\n- `{test_name}` in `{test_file}`")
            if len(obsolete_tests) > 10:
                impacts.append(f"\n- ... and {len(obsolete_tests) - 10} more")
        
        # Possibly affected tests
        possibly_affected = test_impacts.get('possibly_affected', [])
        if possibly_affected:
            impacts.append(f"\n### Possibly Affected Tests ({len(possibly_affected)})")
            impacts.append("\n*Tests in the same category as changes that may need review:*")
            for test_key in possibly_affected[:5]:  # Limit to first 5
                test_name = test_key.split('::')[-1] if '::' in test_key else test_key
                test_file = test_key.split('::')[0] if '::' in test_key else 'unknown'
                impacts.append(f"\n- `{test_name}` in `{test_file}`")
            if len(possibly_affected) > 5:
                impacts.append(f"\n- ... and {len(possibly_affected) - 5} more")
        
        return impacts
    
    def _format_coverage_analysis(self, coverage_analysis: Dict) -> List[str]:
        """Format test coverage analysis section."""
        coverage = []
        
        overall = coverage_analysis.get('overall_coverage', {})
        
        # Overall statistics
        coverage.append(f"\n### Overall Coverage Statistics")
        coverage.append(f"\n- **Total Requirements**: {overall.get('total_requirements', 0)}")
        coverage.append(f"- **Covered Requirements**: {overall.get('covered_requirements', 0)}")
        coverage.append(f"- **Requirement Coverage**: {overall.get('requirement_coverage_percentage', 0):.1f}%")
        coverage.append(f"- **Total Tests**: {overall.get('total_tests', 0)}")
        coverage.append(f"- **Tests with Spec References**: {overall.get('tests_with_spec_refs', 0)}")
        coverage.append(f"- **Test Documentation**: {overall.get('test_documentation_percentage', 0):.1f}%")
        
        # Coverage by requirement level
        by_level = coverage_analysis.get('coverage_by_requirement_level', {})
        if by_level:
            coverage.append(f"\n### Coverage by Requirement Level")
            coverage.append("\n| Level | Total | Covered | Coverage % |")
            coverage.append("|-------|-------|---------|------------|")
            for level, stats in by_level.items():
                total = stats.get('total_requirements', 0)
                covered = stats.get('covered_requirements', 0)
                percentage = stats.get('coverage_percentage', 0)
                coverage.append(f"| {level} | {total} | {covered} | {percentage:.1f}% |")
        
        # Coverage by category
        by_category = coverage_analysis.get('coverage_by_category', {})
        if by_category:
            coverage.append(f"\n### Test Documentation by Category")
            coverage.append("\n| Category | Total Tests | With Refs | Documentation % |")
            coverage.append("|----------|-------------|-----------|-----------------|")
            for category, stats in by_category.items():
                total = stats.get('total_tests', 0)
                with_refs = stats.get('tests_with_refs', 0)
                percentage = stats.get('coverage_percentage', 0)
                coverage.append(f"| {category} | {total} | {with_refs} | {percentage:.1f}% |")
        
        # Requirements without tests
        uncovered_reqs = coverage_analysis.get('requirements_without_tests', [])
        if uncovered_reqs:
            coverage.append(f"\n### Requirements Without Test Coverage ({len(uncovered_reqs)})")
            high_priority = [req for req in uncovered_reqs if req.get('priority', 0) >= 7]
            if high_priority:
                coverage.append(f"\n**High Priority (MUST/SHOULD/REQUIRED):**")
                for req_info in high_priority[:5]:
                    level = req_info.get('level', 'UNKNOWN')
                    text = req_info.get('text', '')[:80] + "..." if len(req_info.get('text', '')) > 80 else req_info.get('text', '')
                    section = req_info.get('section', 'Unknown Section')
                    coverage.append(f"\n- **{level}** in *{section}*: {text}")
            
            medium_priority = [req for req in uncovered_reqs if 3 <= req.get('priority', 0) < 7]
            if medium_priority:
                coverage.append(f"\n**Medium Priority (SHOULD/RECOMMENDED):**")
                for req_info in medium_priority[:3]:
                    level = req_info.get('level', 'UNKNOWN')
                    text = req_info.get('text', '')[:80] + "..." if len(req_info.get('text', '')) > 80 else req_info.get('text', '')
                    coverage.append(f"\n- **{level}**: {text}")
        
        # Tests without spec references
        tests_without_refs = coverage_analysis.get('tests_without_spec_refs', [])
        if tests_without_refs:
            coverage.append(f"\n### Tests Without Specification References ({len(tests_without_refs)})")
            for test_info in tests_without_refs:
                test_name = test_info.get('name', 'unknown')
                category = test_info.get('category', 'unknown')
                coverage.append(f"\n- `{test_name}` in *{category}* category")
        
        return coverage
    
    def _generate_recommendations(self, spec_changes: Dict, test_impacts: Dict, coverage_analysis: Dict) -> List[str]:
        """Generate actionable recommendations section."""
        recommendations = []
        
        # Analyze the situation to provide targeted recommendations
        impact_classification = spec_changes.get('impact_classification', {})
        breaking_changes = impact_classification.get('breaking_changes', [])
        behavioral_changes = impact_classification.get('behavioral_changes', [])
        
        directly_affected = test_impacts.get('directly_affected', [])
        new_coverage_needed = test_impacts.get('new_coverage_needed', [])
        obsolete_tests = test_impacts.get('obsolete_tests', [])
        
        overall_coverage = coverage_analysis.get('overall_coverage', {})
        test_doc_percentage = overall_coverage.get('test_documentation_percentage', 0)
        
        uncovered_reqs = coverage_analysis.get('requirements_without_tests', [])
        tests_without_refs = coverage_analysis.get('tests_without_spec_refs', [])
        
        # Priority-based recommendations
        
        if breaking_changes:
            recommendations.append(f"\n### 🚨 Critical Actions Required")
            recommendations.append(f"\n**{len(breaking_changes)} breaking changes detected** - immediate attention required:")
            
            for breaking_change in breaking_changes[:3]:
                change_type = breaking_change.get('type', 'unknown').replace('_', ' ').title()
                recommendations.append(f"\n- **{change_type}**: Update affected code and tests immediately")
            
            recommendations.append(f"\n**Action Items:**")
            recommendations.append(f"1. Review all breaking changes before deploying")
            recommendations.append(f"2. Update client code that depends on removed/changed APIs")
            recommendations.append(f"3. Run full test suite to identify failures")
            recommendations.append(f"4. Update documentation to reflect changes")
        
        if obsolete_tests:
            recommendations.append(f"\n### ⚠️ Test Maintenance Required")
            recommendations.append(f"\n**{len(obsolete_tests)} tests may be obsolete** due to removed requirements:")
            
            recommendations.append(f"\n**Action Items:**")
            recommendations.append(f"1. Review each obsolete test to confirm it's no longer needed")
            recommendations.append(f"2. Remove or update tests that test removed functionality")
            recommendations.append(f"3. Archive removed tests with documentation explaining why")
        
        if new_coverage_needed:
            recommendations.append(f"\n### 📋 Test Coverage Expansion")
            recommendations.append(f"\n**{len(new_coverage_needed)} new requirements** may need test coverage:")
            
            recommendations.append(f"\n**Action Items:**")
            recommendations.append(f"1. Create tests for new MUST and SHALL requirements (highest priority)")
            recommendations.append(f"2. Add tests for new SHOULD requirements (medium priority)")
            recommendations.append(f"3. Consider edge cases and error conditions for new features")
            recommendations.append(f"4. Update test documentation with new specification references")
        
        if directly_affected:
            recommendations.append(f"\n### 🔍 Test Review Required")
            recommendations.append(f"\n**{len(directly_affected)} existing tests** reference changed specification sections:")
            
            recommendations.append(f"\n**Action Items:**")
            recommendations.append(f"1. Review each affected test for accuracy")
            recommendations.append(f"2. Update test expectations if behavior has changed")
            recommendations.append(f"3. Update test documentation to reflect spec changes")
            recommendations.append(f"4. Run affected tests to ensure they still pass")
        
        # Coverage improvement recommendations
        high_priority_uncovered = [req for req in uncovered_reqs if req.get('priority', 0) >= 7]
        if high_priority_uncovered:
            recommendations.append(f"\n### 📈 Coverage Improvement Opportunities")
            recommendations.append(f"\n**{len(high_priority_uncovered)} high-priority requirements** lack test coverage:")
            
            recommendations.append(f"\n**Action Items:**")
            recommendations.append(f"1. Create tests for uncovered MUST/SHALL requirements")
            recommendations.append(f"2. Focus on core protocol functionality and error handling")
            recommendations.append(f"3. Add negative test cases for requirement violations")
            
        if tests_without_refs:
            recommendations.append(f"\n### 📚 Documentation Improvement")
            recommendations.append(f"\n**{len(tests_without_refs)} tests** lack specification references:")
            
            recommendations.append(f"\n**Action Items:**")
            recommendations.append(f"1. Add docstrings with specification references to undocumented tests")
            recommendations.append(f"2. Use format: 'Tests A2A Specification §X.Y requirement that...'")
            recommendations.append(f"3. Link tests to specific MUST/SHOULD/MAY requirements")
        
        # General recommendations based on coverage
        if test_doc_percentage < 90:
            recommendations.append(f"\n### 📖 Test Documentation Enhancement")
            recommendations.append(f"\nCurrent test documentation is {test_doc_percentage:.1f}% - aim for 95%+")
            
            recommendations.append(f"\n**Action Items:**")
            recommendations.append(f"1. Add specification references to all test docstrings")
            recommendations.append(f"2. Document the specific requirement or behavior being tested")
            recommendations.append(f"3. Include section references (A2A §X.Y) in test descriptions")
        
        # Strategic recommendations
        recommendations.append(f"\n### 🎯 Strategic Recommendations")
        
        total_changes = spec_changes.get('summary', {}).get('total_changes', 0)
        if total_changes == 0:
            recommendations.append(f"\n**No specification changes detected** - consider these maintenance tasks:")
            recommendations.append(f"1. Review test coverage for completeness")
            recommendations.append(f"2. Update test documentation where missing")
            recommendations.append(f"3. Consider adding tests for edge cases")
            recommendations.append(f"4. Run periodic compliance checks")
        else:
            recommendations.append(f"\n**Active specification evolution detected** - implement change management:")
            recommendations.append(f"1. Set up automated spec change detection")
            recommendations.append(f"2. Create a review process for specification updates")
            recommendations.append(f"3. Maintain a change log linking spec changes to test updates")
            recommendations.append(f"4. Consider backward compatibility implications")
        
        # Timeline recommendations
        recommendations.append(f"\n### ⏰ Recommended Timeline")
        
        priority_score = (len(breaking_changes) * 10 + 
                         len(obsolete_tests) * 5 + 
                         len(directly_affected) * 2 + 
                         len(new_coverage_needed))
        
        if priority_score >= 50:
            recommendations.append(f"\n**High Priority (Complete within 1-2 weeks):**")
            recommendations.append(f"- Address all breaking changes immediately")
            recommendations.append(f"- Review and update obsolete tests")
            recommendations.append(f"- Run full test suite to identify issues")
        elif priority_score >= 20:
            recommendations.append(f"\n**Medium Priority (Complete within 1 month):**")
            recommendations.append(f"- Review affected tests and update as needed")
            recommendations.append(f"- Add tests for new requirements")
            recommendations.append(f"- Update test documentation")
        else:
            recommendations.append(f"\n**Low Priority (Complete within 2-3 months):**")
            recommendations.append(f"- Improve test coverage gradually")
            recommendations.append(f"- Enhance test documentation")
            recommendations.append(f"- Consider adding edge case tests")
        
        # Quality metrics to track
        recommendations.append(f"\n### 📊 Quality Metrics to Track")
        recommendations.append(f"\n**Monitor these metrics over time:**")
        recommendations.append(f"- Requirement coverage percentage (target: 95%+)")
        recommendations.append(f"- Test documentation percentage (target: 95%+)")
        recommendations.append(f"- Breaking change impact (minimize affected tests)")
        recommendations.append(f"- Time to update tests after spec changes (target: <1 week)")
        
        return recommendations
    
    def generate_summary_report(self, spec_changes: Dict, test_impacts: Dict, coverage_analysis: Dict) -> str:
        """Generate a concise summary report for quick overview."""
        summary = []
        
        # Quick stats
        total_changes = spec_changes.get('summary', {}).get('total_changes', 0)
        total_impacted = sum(len(test_list) for test_list in test_impacts.values())
        breaking_changes = len(spec_changes.get('impact_classification', {}).get('breaking_changes', []))
        
        coverage = coverage_analysis.get('overall_coverage', {})
        req_coverage = coverage.get('requirement_coverage_percentage', 0)
        test_doc = coverage.get('test_documentation_percentage', 0)
        
        summary.append(f"# A2A Spec Change Summary")
        summary.append(f"\n**Changes**: {total_changes} total, {breaking_changes} breaking")
        summary.append(f"**Impact**: {total_impacted} tests affected")
        summary.append(f"**Coverage**: {req_coverage:.1f}% requirements, {test_doc:.1f}% test docs")
        
        # Priority assessment
        if breaking_changes > 0:
            summary.append(f"\n🚨 **CRITICAL**: {breaking_changes} breaking changes require immediate attention")
        elif total_impacted > 20:
            summary.append(f"\n⚠️ **HIGH**: {total_impacted} tests affected - review required")
        elif total_changes > 0:
            summary.append(f"\n📋 **MEDIUM**: {total_changes} changes detected - update recommended")
        else:
            summary.append(f"\n✅ **LOW**: No changes detected - routine maintenance only")
            
        return '\n'.join(summary)
    
    def export_json_report(self, spec_changes: Dict, test_impacts: Dict, coverage_analysis: Dict) -> str:
        """Export analysis results as JSON for programmatic use."""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_changes': spec_changes.get('summary', {}).get('total_changes', 0),
                'breaking_changes': len(spec_changes.get('impact_classification', {}).get('breaking_changes', [])),
                'total_impacted_tests': sum(len(test_list) for test_list in test_impacts.values()),
                'requirement_coverage': coverage_analysis.get('overall_coverage', {}).get('requirement_coverage_percentage', 0),
                'test_documentation': coverage_analysis.get('overall_coverage', {}).get('test_documentation_percentage', 0)
            },
            'spec_changes': spec_changes,
            'test_impacts': test_impacts,
            'coverage_analysis': coverage_analysis
        }
        
        return json.dumps(report_data, indent=2, default=str) 