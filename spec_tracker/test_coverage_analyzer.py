#!/usr/bin/env python3
"""
Test Coverage Analyzer for A2A TCK.
Analyzes current specification coverage by the test suite.
"""

import ast
import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple

logger = logging.getLogger(__name__)

class TestCoverageAnalyzer:
    """Analyzes test coverage against current A2A specification."""
    
    def __init__(self, test_dir: Path = None):
        """Initialize analyzer with test directory."""
        self.test_dir = test_dir or Path("tests")
        self.test_registry = {}
        self.spec_refs = defaultdict(list)
        self._build_test_registry()
        
    def _build_test_registry(self):
        """Build comprehensive registry of all test functions."""
        logger.info("🔍 Building comprehensive test registry...")
        
        test_files = list(self.test_dir.rglob("test_*.py"))
        total_tests = 0
        
        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Parse the AST to extract test functions
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        # Extract test metadata
                        test_info = self._extract_test_info(node, test_file, content)
                        test_key = f"{test_file.stem}::{node.name}"
                        self.test_registry[test_key] = test_info
                        total_tests += 1
                        
                        # Index specification references
                        for ref in test_info.get('spec_refs', []):
                            self.spec_refs[ref].append(test_key)
                            
            except Exception as e:
                logger.warning(f"Failed to parse {test_file}: {e}")
                
        logger.info(f"✅ Registered {total_tests} tests from {len(test_files)} files")
        
    def _extract_test_info(self, node: ast.FunctionDef, test_file: Path, content: str) -> Dict[str, Any]:
        """Extract comprehensive information about a test function."""
        info = {
            'name': node.name,
            'file': str(test_file),
            'line': node.lineno,
            'category': self._determine_category(test_file),
            'docstring': ast.get_docstring(node) or "",
            'spec_refs': [],
            'methods_tested': [],
            'capabilities_tested': [],
            'error_codes_tested': [],
            'complexity': 'simple'
        }
        
        # Extract specification references from docstring and comments
        if info['docstring']:
            info['spec_refs'] = self._extract_spec_references(info['docstring'])
            
        # Analyze test body for method calls and complexity
        test_body = self._get_function_body(node, content)
        info.update(self._analyze_test_body(test_body))
        
        return info
        
    def _determine_category(self, test_file: Path) -> str:
        """Determine test category from file path."""
        parts = test_file.parts
        if 'mandatory' in parts:
            if 'jsonrpc' in parts:
                return 'mandatory_jsonrpc'
            elif 'protocol' in parts:
                return 'mandatory_protocol'
        elif 'optional' in parts:
            if 'capabilities' in parts:
                return 'optional_capabilities'
            elif 'quality' in parts:
                return 'optional_quality'
            elif 'features' in parts:
                return 'optional_features'
        return 'unknown'
        
    def _extract_spec_references(self, text: str) -> List[str]:
        """Extract specification references from text."""
        refs = []
        
        # Common patterns for spec references
        patterns = [
            r'(?:Section|§)\s*(\d+(?:\.\d+)*)',
            r'(?:RFC|MUST|SHOULD|MAY|REQUIRED|RECOMMENDED)\s+(\w+)',
            r'A2A\s+(\w+(?:\s+\w+)*)',
            r'JSON-RPC\s+(\d\.\d)',
            r'(?:method|endpoint):\s*([a-zA-Z/]+)',
            r'(?:error|code):\s*(-?\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            refs.extend(matches)
            
        return refs
        
    def _get_function_body(self, node: ast.FunctionDef, content: str) -> str:
        """Extract the body of a function as text."""
        lines = content.split('\n')
        start_line = node.lineno - 1
        
        # Find end of function (simple heuristic)
        end_line = len(lines)
        for i, line in enumerate(lines[start_line + 1:], start_line + 1):
            if line.strip() and not line.startswith((' ', '\t')):
                end_line = i
                break
                
        return '\n'.join(lines[start_line:end_line])
        
    def _analyze_test_body(self, body: str) -> Dict[str, Any]:
        """Analyze test body for methods, capabilities, and complexity."""
        analysis = {
            'methods_tested': [],
            'capabilities_tested': [],
            'error_codes_tested': [],
            'complexity': 'simple'
        }
        
        # Find A2A method calls
        method_patterns = [
            r'["\']method["\']\s*:\s*["\']([^"\']+)["\']',
            r'method\s*=\s*["\']([^"\']+)["\']',
            r'\.(\w+/\w+)\(',
        ]
        
        for pattern in method_patterns:
            matches = re.findall(pattern, body)
            analysis['methods_tested'].extend(matches)
            
        # Find capability references
        capability_patterns = [
            r'capabilities["\']?\s*\.\s*["\']?(\w+)',
            r'["\'](\w+)["\'].*capability',
        ]
        
        for pattern in capability_patterns:
            matches = re.findall(pattern, body)
            analysis['capabilities_tested'].extend(matches)
            
        # Find error code tests
        error_patterns = [
            r'error.*code.*?(-?\d+)',
            r'(-32\d{3})',
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, body)
            analysis['error_codes_tested'].extend([int(m) for m in matches])
            
        # Determine complexity
        complexity_indicators = [
            len(re.findall(r'await\s+', body)),
            len(re.findall(r'assert\s+', body)),
            len(re.findall(r'for\s+\w+\s+in', body)),
            len(re.findall(r'if\s+.*:', body)),
        ]
        
        total_complexity = sum(complexity_indicators)
        if total_complexity > 10:
            analysis['complexity'] = 'complex'
        elif total_complexity > 5:
            analysis['complexity'] = 'moderate'
            
        return analysis
        
    def analyze_specification_coverage(self, spec_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze how well tests cover the specification."""
        logger.info("📊 Analyzing specification coverage...")
        
        coverage_analysis = {
            'requirement_coverage': self._analyze_requirement_coverage(spec_data),
            'method_coverage': self._analyze_method_coverage(spec_data),
            'error_coverage': self._analyze_error_coverage(spec_data),
            'capability_coverage': self._analyze_capability_coverage(spec_data),
            'test_quality': self._analyze_test_quality(),
            'coverage_gaps': self._identify_coverage_gaps(spec_data),
            'recommendations': self._generate_recommendations(spec_data)
        }
        
        return coverage_analysis
        
    def _analyze_requirement_coverage(self, spec_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze coverage of specification requirements."""
        requirements = spec_data.get('markdown', {}).get('requirements', [])
        
        coverage = {
            'total_requirements': len(requirements),
            'covered_requirements': 0,
            'uncovered_requirements': [],
            'weakly_covered_requirements': [],
            'coverage_by_level': {},
            'requirement_details': {}
        }
        
        # Group requirements by level
        req_by_level = defaultdict(list)
        for req in requirements:
            level = getattr(req, 'level', 'UNKNOWN')
            req_by_level[level].append(req)
            
        for level, reqs in req_by_level.items():
            level_coverage = self._analyze_level_coverage(reqs)
            coverage['coverage_by_level'][level] = level_coverage
            
        # Find uncovered requirements
        for req in requirements:
            req_id = getattr(req, 'id', f"req_{hash(req.text[:50])}")
            req_coverage = self._get_requirement_coverage(req)
            
            coverage['requirement_details'][req_id] = {
                'requirement': req,
                'coverage': req_coverage,
                'test_count': len(req_coverage['covering_tests']),
                'quality_score': req_coverage['quality_score']
            }
            
            if req_coverage['test_count'] == 0:
                coverage['uncovered_requirements'].append(req_id)
            elif req_coverage['test_count'] < 2 or req_coverage['quality_score'] < 0.5:
                coverage['weakly_covered_requirements'].append(req_id)
            else:
                coverage['covered_requirements'] += 1
                
        return coverage
        
    def _analyze_level_coverage(self, requirements: List[Any]) -> Dict[str, Any]:
        """Analyze coverage for a specific requirement level."""
        total = len(requirements)
        covered = sum(1 for req in requirements if self._is_requirement_covered(req))
        
        return {
            'total': total,
            'covered': covered,
            'percentage': (covered / total * 100) if total > 0 else 0,
            'uncovered': total - covered
        }
        
    def _is_requirement_covered(self, requirement: Any) -> bool:
        """Check if a requirement has adequate test coverage."""
        coverage = self._get_requirement_coverage(requirement)
        return coverage['test_count'] >= 1 and coverage['quality_score'] >= 0.3
        
    def _get_requirement_coverage(self, requirement: Any) -> Dict[str, Any]:
        """Get detailed coverage information for a requirement."""
        req_text = getattr(requirement, 'text', '')
        req_section = getattr(requirement, 'section', '')
        req_level = getattr(requirement, 'level', '')
        
        # Find tests that might cover this requirement
        covering_tests = []
        quality_scores = []
        
        for test_key, test_info in self.test_registry.items():
            score = self._calculate_coverage_score(requirement, test_info)
            if score > 0.1:  # Minimum threshold for relevance
                covering_tests.append(test_key)
                quality_scores.append(score)
                
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return {
            'covering_tests': covering_tests,
            'test_count': len(covering_tests),
            'quality_score': avg_quality,
            'coverage_strength': 'strong' if avg_quality > 0.7 else 'weak' if avg_quality > 0.3 else 'none'
        }
        
    def _calculate_coverage_score(self, requirement: Any, test_info: Dict[str, Any]) -> float:
        """Calculate how well a test covers a requirement."""
        score = 0.0
        
        req_text = getattr(requirement, 'text', '').lower()
        req_section = getattr(requirement, 'section', '').lower()
        req_level = getattr(requirement, 'level', '').lower()
        
        test_doc = test_info.get('docstring', '').lower()
        test_category = test_info.get('category', '').lower()
        
        # Text similarity
        common_words = set(req_text.split()) & set(test_doc.split())
        if len(common_words) > 0:
            score += 0.3 * (len(common_words) / max(len(req_text.split()), 5))
            
        # Section matching
        if req_section and req_section in test_doc:
            score += 0.4
            
        # Level matching
        if req_level in test_doc:
            score += 0.2
            
        # Category alignment
        if req_level == 'must' and 'mandatory' in test_category:
            score += 0.3
        elif req_level in ['should', 'may'] and 'optional' in test_category:
            score += 0.2
            
        return min(score, 1.0)
        
    def _analyze_method_coverage(self, spec_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze coverage of JSON-RPC methods."""
        methods = spec_data.get('json', {}).get('methods', {})
        
        coverage = {
            'total_methods': len(methods),
            'covered_methods': 0,
            'uncovered_methods': [],
            'method_details': {}
        }
        
        # Find which methods are tested
        tested_methods = set()
        for test_info in self.test_registry.values():
            tested_methods.update(test_info.get('methods_tested', []))
            
        for method_name, method_spec in methods.items():
            tests_for_method = [
                test_key for test_key, test_info in self.test_registry.items()
                if method_name in test_info.get('methods_tested', [])
            ]
            
            coverage['method_details'][method_name] = {
                'tests': tests_for_method,
                'test_count': len(tests_for_method),
                'covered': len(tests_for_method) > 0
            }
            
            if len(tests_for_method) > 0:
                coverage['covered_methods'] += 1
            else:
                coverage['uncovered_methods'].append(method_name)
                
        return coverage
        
    def _analyze_error_coverage(self, spec_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze coverage of error codes."""
        error_codes = spec_data.get('json', {}).get('error_codes', {})
        
        coverage = {
            'total_errors': len(error_codes),
            'covered_errors': 0,
            'uncovered_errors': [],
            'error_details': {}
        }
        
        # Find which error codes are tested
        tested_errors = set()
        for test_info in self.test_registry.values():
            tested_errors.update(test_info.get('error_codes_tested', []))
            
        for error_code, error_spec in error_codes.items():
            code_int = int(error_code) if str(error_code).lstrip('-').isdigit() else None
            tests_for_error = [
                test_key for test_key, test_info in self.test_registry.items()
                if code_int in test_info.get('error_codes_tested', [])
            ]
            
            coverage['error_details'][error_code] = {
                'tests': tests_for_error,
                'test_count': len(tests_for_error),
                'covered': len(tests_for_error) > 0
            }
            
            if len(tests_for_error) > 0:
                coverage['covered_errors'] += 1
            else:
                coverage['uncovered_errors'].append(error_code)
                
        return coverage
        
    def _analyze_capability_coverage(self, spec_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze coverage of optional capabilities."""
        # Extract capabilities from AgentCard structure
        capabilities = []
        
        # Look for capability definitions in JSON schema
        json_spec = spec_data.get('json', {})
        if 'definitions' in json_spec:
            for def_name, definition in json_spec['definitions'].items():
                if 'capabilit' in def_name.lower():
                    properties = definition.get('properties', {})
                    capabilities.extend(properties.keys())
                    
        coverage = {
            'total_capabilities': len(capabilities),
            'covered_capabilities': 0,
            'uncovered_capabilities': [],
            'capability_details': {}
        }
        
        for capability in capabilities:
            tests_for_capability = [
                test_key for test_key, test_info in self.test_registry.items()
                if capability in test_info.get('capabilities_tested', [])
            ]
            
            coverage['capability_details'][capability] = {
                'tests': tests_for_capability,
                'test_count': len(tests_for_capability),
                'covered': len(tests_for_capability) > 0
            }
            
            if len(tests_for_capability) > 0:
                coverage['covered_capabilities'] += 1
            else:
                coverage['uncovered_capabilities'].append(capability)
                
        return coverage
        
    def _analyze_test_quality(self) -> Dict[str, Any]:
        """Analyze overall test quality metrics."""
        quality = {
            'total_tests': len(self.test_registry),
            'documented_tests': 0,
            'undocumented_tests': [],
            'orphaned_tests': [],
            'quality_distribution': {'high': 0, 'medium': 0, 'low': 0},
            'complexity_distribution': {'simple': 0, 'moderate': 0, 'complex': 0}
        }
        
        for test_key, test_info in self.test_registry.items():
            # Documentation quality
            if test_info.get('docstring') and len(test_info['docstring']) > 20:
                quality['documented_tests'] += 1
            else:
                quality['undocumented_tests'].append(test_key)
                
            # Orphaned tests (no spec references)
            if not test_info.get('spec_refs'):
                quality['orphaned_tests'].append(test_key)
                
            # Quality scoring
            doc_score = 1 if test_info.get('docstring') else 0
            ref_score = 1 if test_info.get('spec_refs') else 0
            method_score = 1 if test_info.get('methods_tested') else 0
            
            total_score = doc_score + ref_score + method_score
            if total_score >= 3:
                quality['quality_distribution']['high'] += 1
            elif total_score >= 2:
                quality['quality_distribution']['medium'] += 1
            else:
                quality['quality_distribution']['low'] += 1
                
            # Complexity distribution
            complexity = test_info.get('complexity', 'simple')
            quality['complexity_distribution'][complexity] += 1
            
        return quality
        
    def _identify_coverage_gaps(self, spec_data: Dict[str, Any]) -> Dict[str, Any]:
        """Identify major coverage gaps."""
        gaps = {
            'critical_gaps': [],
            'major_gaps': [],
            'minor_gaps': [],
            'recommendations': []
        }
        
        # Analyze requirement coverage gaps
        req_coverage = self._analyze_requirement_coverage(spec_data)
        for level, coverage in req_coverage['coverage_by_level'].items():
            if level.upper() == 'MUST' and coverage['percentage'] < 90:
                gaps['critical_gaps'].append(f"MUST requirements only {coverage['percentage']:.1f}% covered")
            elif level.upper() == 'SHOULD' and coverage['percentage'] < 70:
                gaps['major_gaps'].append(f"SHOULD requirements only {coverage['percentage']:.1f}% covered")
            elif coverage['percentage'] < 50:
                gaps['minor_gaps'].append(f"{level} requirements only {coverage['percentage']:.1f}% covered")
                
        # Analyze method coverage gaps
        method_coverage = self._analyze_method_coverage(spec_data)
        uncovered_count = len(method_coverage['uncovered_methods'])
        if uncovered_count > 0:
            if uncovered_count > 3:
                gaps['critical_gaps'].append(f"{uncovered_count} JSON-RPC methods have no tests")
            else:
                gaps['major_gaps'].append(f"{uncovered_count} JSON-RPC methods have no tests")
                
        return gaps
        
    def _generate_recommendations(self, spec_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations for improving test coverage."""
        recommendations = []
        
        req_coverage = self._analyze_requirement_coverage(spec_data)
        method_coverage = self._analyze_method_coverage(spec_data)
        quality = self._analyze_test_quality()
        
        # High priority recommendations
        if req_coverage.get('coverage_by_level', {}).get('MUST', {}).get('percentage', 0) < 90:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Requirements',
                'title': 'Add tests for uncovered MUST requirements',
                'description': 'MUST requirements should have near 100% test coverage',
                'action': 'Create tests for missing MUST requirements',
                'effort': 'high'
            })
            
        if len(method_coverage.get('uncovered_methods', [])) > 0:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Methods',
                'title': 'Add tests for uncovered JSON-RPC methods',
                'description': f"Methods without tests: {', '.join(method_coverage['uncovered_methods'][:3])}{'...' if len(method_coverage['uncovered_methods']) > 3 else ''}",
                'action': 'Create basic tests for each uncovered method',
                'effort': 'medium'
            })
            
        # Medium priority recommendations
        orphaned_count = len(quality.get('orphaned_tests', []))
        if orphaned_count > 5:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Quality',
                'title': 'Add specification references to tests',
                'description': f'{orphaned_count} tests lack specification references',
                'action': 'Update test docstrings with relevant spec sections',
                'effort': 'low'
            })
            
        undocumented_count = len(quality.get('undocumented_tests', []))
        if undocumented_count > quality['total_tests'] * 0.3:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Documentation',
                'title': 'Improve test documentation',
                'description': f'{undocumented_count} tests lack adequate documentation',
                'action': 'Add docstrings explaining test purpose and coverage',
                'effort': 'low'
            })
            
        return recommendations
        
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about test coverage."""
        return {
            'total_tests': len(self.test_registry),
            'test_files': len(set(info['file'] for info in self.test_registry.values())),
            'tests_with_docs': sum(1 for info in self.test_registry.values() if info.get('docstring')),
            'tests_with_spec_refs': sum(1 for info in self.test_registry.values() if info.get('spec_refs')),
            'unique_spec_refs': len(set(ref for info in self.test_registry.values() for ref in info.get('spec_refs', []))),
            'categories': list(set(info.get('category', 'unknown') for info in self.test_registry.values()))
        } 