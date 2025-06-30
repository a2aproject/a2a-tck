#!/usr/bin/env python3
"""
A2A Compliance Report Generator

Generates comprehensive compliance reports for A2A SDK testing.
Analyzes test results and provides detailed feedback on specification compliance.
"""
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import argparse


class ComplianceReportGenerator:
    """Generate comprehensive A2A compliance reports."""
    
    def __init__(self, test_results: Dict, agent_card: Optional[Dict] = None):
        """
        Initialize the report generator.
        
        Args:
            test_results: Dictionary of test results organized by category
            agent_card: Optional agent card data for capability analysis
        """
        self.test_results = test_results
        self.agent_card = agent_card or {}
        self.timestamp = datetime.utcnow().isoformat()
        
    def generate_report(self) -> Dict:
        """Generate comprehensive compliance report."""
        
        # Categorize results
        mandatory_results = self.test_results.get('mandatory', {})
        capability_results = self.test_results.get('capabilities', {})
        quality_results = self.test_results.get('quality', {})
        feature_results = self.test_results.get('features', {})
        
        # Calculate compliance scores
        mandatory_compliance = self._calculate_compliance(mandatory_results)
        capability_compliance = self._calculate_compliance(capability_results)
        quality_compliance = self._calculate_compliance(quality_results)
        feature_compliance = self._calculate_compliance(feature_results)
        
        # Overall compliance (mandatory tests determine this)
        is_compliant = mandatory_compliance['passed'] == mandatory_compliance['total'] and \
                      mandatory_compliance['total'] > 0
        
        # Determine compliance level
        compliance_level = self._determine_compliance_level(
            mandatory_compliance, capability_compliance, quality_compliance, feature_compliance
        )
        
        return {
            'timestamp': self.timestamp,
            'agent_card': self.agent_card,
            'summary': {
                'compliant': is_compliant,
                'compliance_level': compliance_level['name'],
                'compliance_badge': compliance_level['badge'],
                'overall_score': self._calculate_overall_score(
                    mandatory_compliance, capability_compliance, quality_compliance, feature_compliance
                )
            },
            'categories': {
                'mandatory': {
                    'compliance': mandatory_compliance,
                    'description': 'Core A2A specification requirements',
                    'impact': 'Failures block SDK compliance',
                    'failures': self._analyze_failures(mandatory_results),
                    'status': 'PASSED' if mandatory_compliance['success_rate'] == 100 else 'FAILED'
                },
                'capabilities': {
                    'compliance': capability_compliance,
                    'description': 'Declared capability validation',
                    'impact': 'Failures indicate false advertising',
                    'failures': self._analyze_failures(capability_results),
                    'status': 'PASSED' if capability_compliance['success_rate'] >= 90 else 'FAILED'
                },
                'quality': {
                    'compliance': quality_compliance,
                    'description': 'Production readiness validation',
                    'impact': 'Failures indicate quality concerns',
                    'failures': self._analyze_failures(quality_results),
                    'status': 'PASSED' if quality_compliance['success_rate'] >= 80 else 'ATTENTION_NEEDED'
                },
                'features': {
                    'compliance': feature_compliance,
                    'description': 'Optional feature implementation',
                    'impact': 'Failures indicate incomplete implementation',
                    'failures': self._analyze_failures(feature_results),
                    'status': 'BASIC' if feature_compliance['success_rate'] >= 70 else 'MINIMAL'
                }
            },
            'recommendations': self._generate_recommendations(
                mandatory_compliance, capability_compliance, quality_compliance, feature_compliance
            ),
            'capability_analysis': self._analyze_capabilities(),
            'next_steps': self._generate_next_steps(compliance_level, mandatory_compliance, capability_compliance)
        }
    
    def _calculate_compliance(self, results: Dict) -> Dict:
        """Calculate compliance metrics for a test category."""
        if not results:
            return {
                'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0, 'xfailed': 0,
                'success_rate': 0, 'failure_rate': 0
            }
        
        total = results.get('total', 0)
        passed = results.get('passed', 0)
        failed = results.get('failed', 0)
        skipped = results.get('skipped', 0)
        xfailed = results.get('xfailed', 0)
        
        # Calculate success rate (excluding skipped tests)
        testable = total - skipped
        success_rate = (passed / testable * 100) if testable > 0 else 0
        failure_rate = (failed / testable * 100) if testable > 0 else 0
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'xfailed': xfailed,
            'testable': testable,
            'success_rate': round(success_rate, 1),
            'failure_rate': round(failure_rate, 1)
        }
    
    def _determine_compliance_level(self, mandatory, capability, quality, feature) -> Dict:
        """Determine the overall compliance level."""
        from compliance_levels import COMPLIANCE_LEVELS
        
        # Must pass all mandatory tests for any compliance
        if mandatory['success_rate'] < 100:
            return {
                'name': 'NON_COMPLIANT',
                'badge': '🔴 Not A2A Compliant',
                'description': 'Fails mandatory A2A specification requirements'
            }
        
        # Check for full featured compliance
        if (capability['success_rate'] >= 95 and 
            quality['success_rate'] >= 90 and 
            feature['success_rate'] >= 80):
            return COMPLIANCE_LEVELS['FULL_FEATURED']
        
        # Check for recommended compliance
        if (capability['success_rate'] >= 85 and 
            quality['success_rate'] >= 75):
            return COMPLIANCE_LEVELS['RECOMMENDED']
        
        # Basic compliance
        return COMPLIANCE_LEVELS['MANDATORY']
    
    def _calculate_overall_score(self, mandatory, capability, quality, feature) -> float:
        """Calculate weighted overall compliance score."""
        # Weighted scoring: mandatory=50%, capability=25%, quality=15%, feature=10%
        score = (
            mandatory['success_rate'] * 0.50 +
            capability['success_rate'] * 0.25 +
            quality['success_rate'] * 0.15 +
            feature['success_rate'] * 0.10
        )
        return round(score, 1)
    
    def _analyze_failures(self, results: Dict) -> List[Dict]:
        """Analyze failures and provide detailed information."""
        failures = []
        
        for test_name, test_result in results.get('tests', {}).items():
            if test_result.get('outcome') == 'FAILED':
                failures.append({
                    'test': test_name,
                    'specification_reference': self._get_spec_reference(test_name),
                    'error_message': test_result.get('error_message', 'Unknown error'),
                    'impact': self._get_failure_impact(test_name),
                    'fix_suggestion': self._get_fix_suggestion(test_name)
                })
        
        return failures
    
    def _analyze_capabilities(self) -> Dict:
        """Analyze declared vs actual capabilities."""
        declared_capabilities = self.agent_card.get('capabilities', {})
        
        analysis = {
            'declared': declared_capabilities,
            'issues': [],
            'recommendations': []
        }
        
        # Check for common capability issues
        if declared_capabilities.get('streaming') and 'capability_results' in self.test_results:
            streaming_tests = [t for t in self.test_results['capability_results'].get('tests', {}) 
                             if 'stream' in t]
            if any(self.test_results['capability_results']['tests'][t].get('outcome') == 'FAILED' 
                   for t in streaming_tests):
                analysis['issues'].append(
                    "Streaming capability declared but tests fail - implementation incomplete"
                )
        
        return analysis
    
    def _generate_recommendations(self, mandatory, capability, quality, feature) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if mandatory['success_rate'] < 100:
            recommendations.append(
                "🚨 CRITICAL: Fix mandatory test failures to achieve A2A compliance"
            )
            recommendations.append(
                f"Focus on {mandatory['failed']} failing mandatory tests first"
            )
        
        if capability['success_rate'] < 90:
            recommendations.append(
                "⚠️ HIGH: Address capability validation failures - these indicate false advertising"
            )
        
        if quality['success_rate'] < 80:
            recommendations.append(
                "💡 MEDIUM: Improve quality test results for production readiness"
            )
        
        if feature['success_rate'] < 70:
            recommendations.append(
                "📈 LOW: Consider implementing more optional features for completeness"
            )
        
        return recommendations
    
    def _generate_next_steps(self, compliance_level, mandatory, capability) -> List[str]:
        """Generate specific next steps based on compliance level."""
        if compliance_level['name'] == 'NON_COMPLIANT':
            return [
                "1. Fix all mandatory test failures",
                "2. Ensure Agent Card declares all supported capabilities", 
                "3. Re-run mandatory tests to verify compliance",
                "4. Then proceed to capability validation"
            ]
        
        if compliance_level['name'] == 'MANDATORY':
            return [
                "1. Review and fix capability test failures",
                "2. Ensure declared capabilities are properly implemented",
                "3. Run quality tests to identify production issues",
                "4. Consider implementing additional features"
            ]
        
        return [
            "1. Maintain current compliance level",
            "2. Monitor for regressions in mandatory tests",
            "3. Continue improving quality and feature coverage"
        ]
    
    def _get_spec_reference(self, test_name: str) -> str:
        """Get specification reference for a test."""
        # This would be enhanced with actual specification mapping
        spec_mapping = {
            'test_message_send': 'A2A Specification §5.1 - Message Send',
            'test_tasks_get': 'A2A Specification §7.3 - Task Retrieval',
            'test_tasks_cancel': 'A2A Specification §7.4 - Task Cancellation',
            'test_message_stream': 'A2A Specification §8.1 - Message Streaming',
            'test_push_notification': 'A2A Specification §9.1 - Push Notifications'
        }
        
        for pattern, reference in spec_mapping.items():
            if pattern in test_name:
                return reference
        
        return 'A2A Specification - See test documentation'
    
    def _get_failure_impact(self, test_name: str) -> str:
        """Get the impact description for a test failure."""
        if 'mandatory' in test_name:
            return 'Blocks A2A compliance'
        elif 'capability' in test_name:
            return 'Indicates false capability advertising'
        elif 'quality' in test_name:
            return 'Affects production readiness'
        else:
            return 'Limits feature completeness'
    
    def _get_fix_suggestion(self, test_name: str) -> str:
        """Get fix suggestion for a test failure."""
        # This would be enhanced with specific fix suggestions
        fix_suggestions = {
            'historyLength': 'Implement historyLength parameter in DefaultRequestHandler',
            'message_send': 'Ensure message/send method validates required fields',
            'tasks_get': 'Verify tasks/get returns proper Task structure',
            'streaming': 'Implement message/stream if streaming capability is declared'
        }
        
        for pattern, suggestion in fix_suggestions.items():
            if pattern in test_name:
                return suggestion
        
        return 'See test documentation for requirements'

def generate_report_from_file(results_file: str, output_file: str, agent_card_file: str = None):
    """Generate compliance report from test results file."""
    
    # Load test results
    with open(results_file, 'r') as f:
        test_results = json.load(f)
    
    # Load agent card if provided
    agent_card = None
    if agent_card_file and Path(agent_card_file).exists():
        with open(agent_card_file, 'r') as f:
            agent_card = json.load(f)
    
    # Generate report
    generator = ComplianceReportGenerator(test_results, agent_card)
    report = generator.generate_report()
    
    # Save report
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report

def main():
    """Command line interface for compliance report generation."""
    parser = argparse.ArgumentParser(description='Generate A2A compliance report')
    parser.add_argument('--results', required=True, help='Test results JSON file')
    parser.add_argument('--output', required=True, help='Output report file')
    parser.add_argument('--agent-card', help='Agent card JSON file')
    parser.add_argument('--format', choices=['json', 'html', 'markdown'], default='json',
                       help='Output format')
    
    args = parser.parse_args()
    
    try:
        report = generate_report_from_file(args.results, args.output, args.agent_card)
        
        print(f"✅ Compliance report generated: {args.output}")
        print(f"📊 Overall compliance: {report['summary']['compliance_level']}")
        print(f"🏆 Badge: {report['summary']['compliance_badge']}")
        
        if not report['summary']['compliant']:
            print("❌ SDK is NOT A2A compliant - fix mandatory test failures")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 