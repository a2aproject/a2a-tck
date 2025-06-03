"""
Analyzes which tests are impacted by specification changes.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Any

class TestImpactAnalyzer:
    """Analyzes impact of spec changes on tests."""
    
    def __init__(self, test_dir: Path = Path("tests")):
        self.test_dir = test_dir
        self.test_registry = self._build_test_registry()
    
    def analyze_impact(self, spec_changes: Dict) -> Dict[str, List[str]]:
        """
        Analyze which tests are impacted by specification changes.
        
        Args:
            spec_changes: Dict from SpecComparator with change details
            
        Returns:
            Dict mapping impact types to lists of affected tests
        """
        impact = {
            'directly_affected': [],      # Tests that reference changed sections
            'possibly_affected': [],      # Tests in same category as changes
            'new_coverage_needed': [],    # New requirements without tests
            'obsolete_tests': []          # Tests for removed requirements
        }
        
        # Analyze markdown changes
        md_changes = spec_changes.get('markdown_changes', {})
        
        # Find tests affected by requirement changes
        for req_change in md_changes.get('requirements', {}).get('added', []):
            impact['new_coverage_needed'].extend(
                self._analyze_requirement_change(req_change, 'added')
            )
            
        for req_change in md_changes.get('requirements', {}).get('removed', []):
            impact['obsolete_tests'].extend(
                self._analyze_requirement_change(req_change, 'removed')
            )
            
        for req_change in md_changes.get('requirements', {}).get('modified', []):
            impact['directly_affected'].extend(
                self._analyze_requirement_change(req_change, 'modified')
            )
        
        # Find tests affected by section changes
        for section_change in md_changes.get('sections', {}).get('added', []):
            impact['new_coverage_needed'].extend(
                self._analyze_section_change(section_change, 'added')
            )
            
        for section_change in md_changes.get('sections', {}).get('modified', []):
            impact['directly_affected'].extend(
                self._analyze_section_change(section_change, 'modified')
            )
        
        # Analyze JSON changes
        json_changes = spec_changes.get('json_changes', {})
        
        # Find tests affected by method changes
        for method_change in json_changes.get('methods', {}).get('added', []):
            impact['new_coverage_needed'].extend(
                self._analyze_method_change(method_change, 'added')
            )
            
        for method_change in json_changes.get('methods', {}).get('removed', []):
            impact['obsolete_tests'].extend(
                self._analyze_method_change(method_change, 'removed')
            )
        
        # Find tests affected by definition changes
        for def_change in json_changes.get('definitions', {}).get('added', []):
            impact['new_coverage_needed'].extend(
                self._analyze_definition_change(def_change, 'added')
            )
            
        # Find tests affected by error code changes
        for error_change in json_changes.get('error_codes', {}).get('modified', []):
            impact['directly_affected'].extend(
                self._analyze_error_change(error_change, 'modified')
            )
        
        # Remove duplicates while preserving order
        for impact_type in impact:
            impact[impact_type] = list(dict.fromkeys(impact[impact_type]))
            
        return impact
    
    def _analyze_requirement_change(self, req_change: Dict, change_type: str) -> List[str]:
        """Analyze impact of a requirement change."""
        affected_tests = []
        
        if change_type in ['added', 'removed']:
            requirement = req_change.get('requirement')
            section = req_change.get('section', '')
            level = req_change.get('level', '')
        else:  # modified
            requirement = req_change.get('new_requirement') or req_change.get('requirement')
            section = req_change.get('section', '')
            level = req_change.get('level', '')
        
        if not requirement:
            return affected_tests
            
        req_text = getattr(requirement, 'text', str(requirement))
        
        # Find tests that might reference this requirement
        search_terms = [
            section,
            level,
            # Extract key terms from requirement text
            *self._extract_key_terms(req_text)
        ]
        
        for test_key, test_info in self.test_registry.items():
            docstring = test_info['docstring'].lower()
            
            # Check if test references this requirement area
            for term in search_terms:
                if term and term.lower() in docstring:
                    affected_tests.append(test_key)
                    break
                    
        return affected_tests
    
    def _analyze_section_change(self, section_change: Dict, change_type: str) -> List[str]:
        """Analyze impact of a section change."""
        affected_tests = []
        
        section_title = section_change.get('title', '')
        if not section_title:
            return affected_tests
            
        # Extract key terms from section title
        key_terms = self._extract_key_terms(section_title)
        
        for test_key, test_info in self.test_registry.items():
            docstring = test_info['docstring'].lower()
            
            # Check if test references this section
            for term in key_terms:
                if term and term.lower() in docstring:
                    affected_tests.append(test_key)
                    break
                    
        return affected_tests
    
    def _analyze_method_change(self, method_change: Dict, change_type: str) -> List[str]:
        """Analyze impact of a method change."""
        affected_tests = []
        
        method_name = method_change.get('name', '')
        if not method_name:
            return affected_tests
            
        # Find tests that reference this method
        for test_key, test_info in self.test_registry.items():
            docstring = test_info['docstring'].lower()
            file_content = ''
            
            # Read test file to check for method usage
            try:
                with open(test_info['file'], 'r', encoding='utf-8') as f:
                    file_content = f.read().lower()
            except Exception:
                pass
            
            # Check if test uses this method
            if (method_name.lower() in docstring or 
                method_name.lower() in file_content):
                affected_tests.append(test_key)
                
        return affected_tests
    
    def _analyze_definition_change(self, def_change: Dict, change_type: str) -> List[str]:
        """Analyze impact of a definition change."""
        affected_tests = []
        
        def_name = def_change.get('name', '')
        if not def_name:
            return affected_tests
            
        # Convert CamelCase to searchable terms
        search_terms = [def_name] + self._camel_case_to_terms(def_name)
        
        for test_key, test_info in self.test_registry.items():
            docstring = test_info['docstring'].lower()
            
            # Check if test references this definition
            for term in search_terms:
                if term and term.lower() in docstring:
                    affected_tests.append(test_key)
                    break
                    
        return affected_tests
    
    def _analyze_error_change(self, error_change: Dict, change_type: str) -> List[str]:
        """Analyze impact of an error code change."""
        affected_tests = []
        
        error_name = error_change.get('name', '')
        old_code = error_change.get('old_info', {}).get('code')
        new_code = error_change.get('new_info', {}).get('code')
        
        search_terms = [error_name]
        if old_code:
            search_terms.append(str(old_code))
        if new_code:
            search_terms.append(str(new_code))
            
        for test_key, test_info in self.test_registry.items():
            docstring = test_info['docstring'].lower()
            file_content = ''
            
            # Read test file to check for error code usage
            try:
                with open(test_info['file'], 'r', encoding='utf-8') as f:
                    file_content = f.read().lower()
            except Exception:
                pass
            
            # Check if test uses this error
            for term in search_terms:
                if term and (term.lower() in docstring or term.lower() in file_content):
                    affected_tests.append(test_key)
                    break
                    
        return affected_tests
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key searchable terms from text."""
        if not text:
            return []
            
        # Remove common words and extract meaningful terms
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                       'of', 'with', 'by', 'this', 'that', 'is', 'are', 'was', 'were', 'be', 
                       'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 
                       'should', 'could', 'may', 'might', 'must', 'shall'}
        
        # Extract words (3+ characters, not common words)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        key_terms = [word for word in words if word not in common_words]
        
        return key_terms[:10]  # Limit to top 10 terms
    
    def _camel_case_to_terms(self, camel_text: str) -> List[str]:
        """Convert CamelCase to individual searchable terms."""
        # Split on capital letters
        terms = re.findall(r'[A-Z][a-z]*', camel_text)
        return [term.lower() for term in terms if len(term) > 2]
        
    def _build_test_registry(self) -> Dict[str, Dict]:
        """
        Build a registry of all tests with their spec references.
        
        Returns:
            Dict mapping test names to their metadata
        """
        registry = {}
        
        print(f"🔍 Scanning for test files in {self.test_dir}...")
        
        # Walk through all test files
        for test_file in self.test_dir.rglob("test_*.py"):
            try:
                # Parse the Python file
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Extract test functions and their docstrings
                tree = ast.parse(content, filename=str(test_file))
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        docstring = ast.get_docstring(node) or ''
                        test_key = f"{test_file.stem}::{node.name}"
                        
                        test_info = {
                            'file': str(test_file),
                            'name': node.name,
                            'docstring': docstring,
                            'spec_refs': self._extract_spec_refs(docstring),
                            'category': self._determine_category(test_file),
                            'line_number': node.lineno,
                            'is_async': isinstance(node, ast.AsyncFunctionDef) or 
                                       any(isinstance(d, ast.Name) and d.id == 'pytest_asyncio' 
                                           for d in node.decorator_list if isinstance(d, ast.Name)),
                            'markers': self._extract_markers(node)
                        }
                        registry[test_key] = test_info
                        
            except Exception as e:
                print(f"⚠️  Warning: Could not parse {test_file}: {e}")
                continue
                
        print(f"✅ Found {len(registry)} test functions across {len(list(self.test_dir.rglob('test_*.py')))} test files")
        
        return registry
        
    def _extract_spec_refs(self, docstring: str) -> List[str]:
        """Extract specification references from docstring."""
        refs = []
        
        if not docstring:
            return refs
            
        # Pattern for A2A spec references (e.g., "A2A §5.1", "A2A specification §4.2")
        a2a_pattern = re.compile(r'A2A\s+(?:specification\s+)?§[\d.]+', re.IGNORECASE)
        refs.extend(a2a_pattern.findall(docstring))
        
        # Pattern for JSON-RPC references (e.g., "JSON-RPC 2.0 §7.1")
        jsonrpc_pattern = re.compile(r'JSON-RPC\s+\d\.\d\s+§[\d.]+', re.IGNORECASE)
        refs.extend(jsonrpc_pattern.findall(docstring))
        
        # Pattern for requirement keywords followed by specific behavior
        req_pattern = re.compile(r'(MUST|SHALL|SHOULD|MAY|REQUIRED|RECOMMENDED)\s+\w+', re.IGNORECASE)
        requirement_matches = req_pattern.findall(docstring)
        refs.extend([match.upper() if isinstance(match, str) else ' '.join(match).upper() 
                    for match in requirement_matches])
        
        # Pattern for specific A2A protocol elements
        protocol_patterns = [
            r'agent[.\s]+(card|endpoint|capability)',
            r'(task|message|artifact)[.\s]+\w+',
            r'(authentication|authorization)',
            r'(websocket|sse|polling)',
            r'(modality|capability)\s+support',
            r'error\s+code\s+\d+',
            r'(request|response)\s+validation'
        ]
        
        for pattern in protocol_patterns:
            matches = re.findall(pattern, docstring, re.IGNORECASE)
            if matches:
                refs.extend([f"Protocol: {match}" if isinstance(match, str) else f"Protocol: {' '.join(match)}" 
                           for match in matches])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_refs = []
        for ref in refs:
            if ref not in seen:
                seen.add(ref)
                unique_refs.append(ref)
                
        return unique_refs
        
    def _determine_category(self, test_file: Path) -> str:
        """Determine the test category based on file path."""
        path_parts = test_file.parts
        
        if 'mandatory' in path_parts:
            if 'jsonrpc' in path_parts:
                return 'mandatory_jsonrpc'
            elif 'protocol' in path_parts:
                return 'mandatory_protocol'
            else:
                return 'mandatory'
        elif 'optional' in path_parts:
            if 'capabilities' in path_parts:
                return 'optional_capabilities'
            elif 'features' in path_parts:
                return 'optional_features'
            elif 'quality' in path_parts:
                return 'optional_quality'
            else:
                return 'optional'
        else:
            return 'unknown'
            
    def _extract_markers(self, node: ast.FunctionDef) -> List[str]:
        """Extract pytest markers from function decorators."""
        markers = []
        
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    # Handle pytest.mark.marker_name
                    if (isinstance(decorator.func.value, ast.Attribute) and 
                        decorator.func.value.attr == 'mark' and
                        isinstance(decorator.func.value.value, ast.Name) and
                        decorator.func.value.value.id == 'pytest'):
                        markers.append(decorator.func.attr)
                elif isinstance(decorator.func, ast.Name):
                    # Handle direct marker calls
                    markers.append(decorator.func.id)
            elif isinstance(decorator, ast.Attribute):
                # Handle attribute access like pytest.mark.asyncio
                if (decorator.attr and 
                    isinstance(decorator.value, ast.Attribute) and
                    decorator.value.attr == 'mark'):
                    markers.append(decorator.attr)
                    
        return markers
    
    def get_registry_summary(self) -> Dict[str, Any]:
        """Get a summary of the test registry."""
        summary = {
            'total_tests': len(self.test_registry),
            'by_category': {},
            'with_spec_refs': 0,
            'without_spec_refs': 0,
            'total_spec_refs': 0,
            'unique_spec_refs': set(),
            'by_markers': {}
        }
        
        for test_key, test_info in self.test_registry.items():
            # Count by category
            category = test_info['category']
            summary['by_category'][category] = summary['by_category'].get(category, 0) + 1
            
            # Count spec references
            spec_refs = test_info['spec_refs']
            if spec_refs:
                summary['with_spec_refs'] += 1
                summary['total_spec_refs'] += len(spec_refs)
                summary['unique_spec_refs'].update(spec_refs)
            else:
                summary['without_spec_refs'] += 1
                
            # Count markers
            for marker in test_info['markers']:
                summary['by_markers'][marker] = summary['by_markers'].get(marker, 0) + 1
        
        # Convert set to sorted list for JSON serialization
        summary['unique_spec_refs'] = sorted(list(summary['unique_spec_refs']))
        
        return summary
    
    def find_tests_by_category(self, category: str) -> List[Dict]:
        """Find all tests in a specific category."""
        return [test_info for test_info in self.test_registry.values() 
                if test_info['category'] == category]
    
    def find_tests_with_spec_ref(self, spec_ref_pattern: str) -> List[Dict]:
        """Find tests that reference a specific specification pattern."""
        matching_tests = []
        
        for test_info in self.test_registry.values():
            for ref in test_info['spec_refs']:
                if re.search(spec_ref_pattern, ref, re.IGNORECASE):
                    matching_tests.append({
                        'test': test_info,
                        'matching_ref': ref
                    })
                    break
                    
        return matching_tests
    
    def find_tests_without_spec_refs(self) -> List[Dict]:
        """Find tests that don't have any specification references."""
        return [test_info for test_info in self.test_registry.values() 
                if not test_info['spec_refs']]
    
    def analyze_coverage(self, requirements: List[Any]) -> Dict[str, Any]:
        """
        Analyze test coverage for specification requirements.
        
        Args:
            requirements: List of requirements from spec parser
            
        Returns:
            Dict with coverage analysis results
        """
        coverage = {
            'requirements_without_tests': [],
            'tests_without_spec_refs': [],
            'coverage_by_category': {},
            'coverage_by_requirement_level': {},
            'overall_coverage': {}
        }
        
        # Find requirements without tests
        for req in requirements:
            req_text = getattr(req, 'text', str(req))
            req_level = getattr(req, 'level', 'UNKNOWN')
            req_section = getattr(req, 'section', 'Unknown Section')
            
            # Search for tests that might cover this requirement
            covering_tests = self._find_covering_tests(req)
            
            if not covering_tests:
                coverage['requirements_without_tests'].append({
                    'requirement': req,
                    'text': req_text,
                    'level': req_level,
                    'section': req_section,
                    'priority': self._calculate_requirement_priority(req)
                })
        
        # Find tests without spec references
        coverage['tests_without_spec_refs'] = self.find_tests_without_spec_refs()
        
        # Calculate coverage by category
        total_by_category = {}
        covered_by_category = {}
        
        for test_info in self.test_registry.values():
            category = test_info['category']
            total_by_category[category] = total_by_category.get(category, 0) + 1
            
            if test_info['spec_refs']:
                covered_by_category[category] = covered_by_category.get(category, 0) + 1
        
        for category in total_by_category:
            covered = covered_by_category.get(category, 0)
            total = total_by_category[category]
            coverage['coverage_by_category'][category] = {
                'total_tests': total,
                'tests_with_refs': covered,
                'coverage_percentage': (covered / total * 100) if total > 0 else 0
            }
        
        # Calculate coverage by requirement level
        req_levels = {}
        covered_req_levels = {}
        
        for req in requirements:
            level = getattr(req, 'level', 'UNKNOWN')
            req_levels[level] = req_levels.get(level, 0) + 1
            
            # Check if this requirement has covering tests
            covering_tests = self._find_covering_tests(req)
            if covering_tests:
                covered_req_levels[level] = covered_req_levels.get(level, 0) + 1
        
        for level in req_levels:
            covered = covered_req_levels.get(level, 0)
            total = req_levels[level]
            coverage['coverage_by_requirement_level'][level] = {
                'total_requirements': total,
                'covered_requirements': covered,
                'coverage_percentage': (covered / total * 100) if total > 0 else 0
            }
        
        # Calculate overall coverage
        total_requirements = len(requirements)
        covered_requirements = total_requirements - len(coverage['requirements_without_tests'])
        total_tests = len(self.test_registry)
        tests_with_refs = total_tests - len(coverage['tests_without_spec_refs'])
        
        coverage['overall_coverage'] = {
            'total_requirements': total_requirements,
            'covered_requirements': covered_requirements,
            'requirement_coverage_percentage': (covered_requirements / total_requirements * 100) if total_requirements > 0 else 0,
            'total_tests': total_tests,
            'tests_with_spec_refs': tests_with_refs,
            'test_documentation_percentage': (tests_with_refs / total_tests * 100) if total_tests > 0 else 0
        }
        
        return coverage
    
    def _find_covering_tests(self, requirement: Any) -> List[str]:
        """Find tests that cover a specific requirement."""
        covering_tests = []
        
        req_text = getattr(requirement, 'text', str(requirement))
        req_section = getattr(requirement, 'section', '')
        req_level = getattr(requirement, 'level', '')
        
        # Extract key terms to search for
        search_terms = self._extract_key_terms(req_text)
        if req_section:
            search_terms.extend(self._extract_key_terms(req_section))
        
        for test_key, test_info in self.test_registry.items():
            docstring = test_info['docstring'].lower()
            
            # Check if test might cover this requirement
            match_score = 0
            for term in search_terms:
                if term and term.lower() in docstring:
                    match_score += 1
            
            # Also check for requirement level keywords
            if req_level.lower() in docstring:
                match_score += 2
                
            # Consider it a match if we have enough matching terms
            if match_score >= 2 or (match_score >= 1 and req_level.lower() in docstring):
                covering_tests.append(test_key)
                
        return covering_tests
    
    def _calculate_requirement_priority(self, requirement: Any) -> int:
        """Calculate priority score for a requirement (higher = more important)."""
        level = getattr(requirement, 'level', 'UNKNOWN').upper()
        
        priority_map = {
            'MUST': 10,
            'SHALL': 10,
            'REQUIRED': 9,
            'SHOULD': 7,
            'RECOMMENDED': 6,
            'MAY': 3,
            'OPTIONAL': 2
        }
        
        return priority_map.get(level, 1)
    
    def get_impact_summary(self, impact_analysis: Dict) -> Dict[str, Any]:
        """Generate a summary of impact analysis results."""
        summary = {
            'total_impacted_tests': 0,
            'impact_distribution': {},
            'high_priority_impacts': [],
            'categories_affected': set(),
            'recommendation_priority': 'LOW'
        }
        
        # Count total impacted tests and distribution
        for impact_type, test_list in impact_analysis.items():
            count = len(test_list)
            summary['impact_distribution'][impact_type] = count
            summary['total_impacted_tests'] += count
            
            # Identify categories affected
            for test_key in test_list:
                if test_key in self.test_registry:
                    category = self.test_registry[test_key]['category']
                    summary['categories_affected'].add(category)
        
        # Convert set to sorted list
        summary['categories_affected'] = sorted(list(summary['categories_affected']))
        
        # Identify high priority impacts
        breaking_count = summary['impact_distribution'].get('obsolete_tests', 0)
        new_coverage_count = summary['impact_distribution'].get('new_coverage_needed', 0)
        directly_affected_count = summary['impact_distribution'].get('directly_affected', 0)
        
        if breaking_count > 0:
            summary['high_priority_impacts'].append(f"{breaking_count} tests may be obsolete")
            summary['recommendation_priority'] = 'HIGH'
        
        if new_coverage_count > 0:
            summary['high_priority_impacts'].append(f"{new_coverage_count} new requirements need test coverage")
            if summary['recommendation_priority'] != 'HIGH':
                summary['recommendation_priority'] = 'MEDIUM'
        
        if directly_affected_count > 5:
            summary['high_priority_impacts'].append(f"{directly_affected_count} tests directly affected")
            if summary['recommendation_priority'] == 'LOW':
                summary['recommendation_priority'] = 'MEDIUM'
        
        return summary 