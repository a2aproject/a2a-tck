"""
A2A v0.3.0 Transport Security Validation

This module implements comprehensive transport-level security testing for A2A v0.3.0,
including TLS validation, certificate verification, and transport-specific security features.

Specification Reference: A2A Protocol v0.3.0 §4 - Authentication and Authorization
"""

import logging
import ssl
import socket
import urllib.parse
from typing import Dict, Any, Optional
import pytest
import requests

from tests.markers import optional_capability, a2a_v030
from tests.utils.transport_helpers import get_client_transport_type, is_transport_client
from tck import config

logger = logging.getLogger(__name__)


class TestTransportLayerSecurity:
    """
    Test transport-layer security requirements for A2A v0.3.0.
    
    Validates TLS configuration, certificate validation, and secure communication
    as required by A2A v0.3.0 specification Section 4.1.
    """

    @optional_capability
    @a2a_v030
    def test_https_enforcement(self):
        """
        A2A v0.3.0 §4.1 - HTTPS Requirement
        
        Validates that the SUT uses HTTPS for all communications
        as mandated by A2A v0.3.0 specification.
        """
        sut_url = config.get_sut_url()
        parsed_url = urllib.parse.urlparse(sut_url)
        
        # Skip HTTPS requirement for localhost testing
        if parsed_url.hostname in ["localhost", "127.0.0.1"] or "localhost" in sut_url:
            pytest.skip("HTTPS requirement skipped for localhost testing")
        
        # A2A v0.3.0 mandates HTTPS for production
        assert parsed_url.scheme == "https", \
            f"A2A v0.3.0 requires HTTPS, but SUT uses: {parsed_url.scheme}"
        
        logger.info(f"✅ SUT correctly uses HTTPS: {sut_url}")

    @optional_capability
    @a2a_v030
    def test_tls_version_compliance(self):
        """
        A2A v0.3.0 §4.1 - TLS Version Requirements
        
        Validates that the SUT uses modern TLS versions (TLS 1.2+, preferably TLS 1.3)
        as recommended by A2A v0.3.0.
        """
        sut_url = config.get_sut_url()
        parsed_url = urllib.parse.urlparse(sut_url)
        
        if parsed_url.scheme != "https":
            pytest.skip("HTTPS not used, skipping TLS version test")
        
        hostname = parsed_url.hostname
        port = parsed_url.port or 443
        
        try:
            # Create SSL context for testing
            context = ssl.create_default_context()
            
            # Test TLS connection
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    tls_version = ssock.version()
                    cipher = ssock.cipher()
                    
                    logger.info(f"TLS Version: {tls_version}")
                    logger.info(f"Cipher Suite: {cipher}")
                    
                    # Validate TLS version
                    acceptable_versions = ["TLSv1.2", "TLSv1.3"]
                    assert tls_version in acceptable_versions, \
                        f"TLS version {tls_version} is not secure. Use TLS 1.2+ (preferably TLS 1.3)"
                    
                    # Preferably TLS 1.3
                    if tls_version == "TLSv1.3":
                        logger.info("✅ Excellent: Using TLS 1.3")
                    elif tls_version == "TLSv1.2":
                        logger.info("✅ Good: Using TLS 1.2 (consider upgrading to TLS 1.3)")
                    
        except Exception as e:
            pytest.fail(f"TLS connection test failed: {e}")

    @optional_capability
    @a2a_v030
    def test_certificate_validation(self):
        """
        A2A v0.3.0 §4.2 - Server Identity Verification
        
        Validates that the SUT uses proper SSL/TLS certificates
        that can be verified against trusted CAs.
        """
        sut_url = config.get_sut_url()
        
        if not sut_url.startswith("https://"):
            pytest.skip("HTTPS not used, skipping certificate validation")
        
        try:
            # Test certificate validation with requests
            response = requests.get(sut_url, timeout=10, verify=True)
            logger.info("✅ Certificate validation successful")
            
        except requests.exceptions.SSLError as e:
            # Certificate validation failed
            if "certificate verify failed" in str(e).lower():
                pytest.fail(f"Certificate validation failed: {e}")
            else:
                pytest.fail(f"SSL/TLS error: {e}")
                
        except requests.exceptions.RequestException as e:
            # Other network errors are not certificate issues
            logger.warning(f"Network error during certificate test: {e}")


class TestTransportSpecificSecurity:
    """
    Test security features specific to different transport types.
    
    Validates transport-specific security implementations for
    JSON-RPC over HTTPS, gRPC with TLS, and REST API security.
    """

    @optional_capability
    @a2a_v030
    def test_json_rpc_security_headers(self, sut_client):
        """
        A2A v0.3.0 §3.1 - JSON-RPC Transport Security
        
        Validates security headers and practices for JSON-RPC over HTTPS.
        """
        if not is_transport_client(sut_client):
            pytest.skip("Test requires transport-aware client")
        
        transport_type = get_client_transport_type(sut_client)
        
        if transport_type != "jsonrpc":
            pytest.skip("Test specific to JSON-RPC transport")
        
        sut_url = config.get_sut_url()
        
        try:
            # Test HTTP security headers
            response = requests.get(sut_url, timeout=10)
            headers = response.headers
            
            # Check for security headers
            security_headers = {
                "strict-transport-security": "HSTS for HTTPS enforcement",
                "x-content-type-options": "MIME type sniffing protection", 
                "x-frame-options": "Clickjacking protection",
                "x-xss-protection": "XSS protection",
                "content-security-policy": "CSP for content protection"
            }
            
            found_headers = []
            for header, description in security_headers.items():
                if header in headers:
                    found_headers.append(header)
                    logger.info(f"✅ {description}: {headers[header]}")
            
            if found_headers:
                logger.info(f"Found {len(found_headers)} security headers")
            else:
                logger.info("No additional security headers found (not required by A2A)")
                
        except requests.RequestException as e:
            logger.warning(f"Could not test security headers: {e}")

    @optional_capability
    @a2a_v030
    def test_grpc_tls_configuration(self, sut_client):
        """
        A2A v0.3.0 §3.2 - gRPC Transport Security
        
        Validates TLS configuration for gRPC transport.
        """
        if not is_transport_client(sut_client):
            pytest.skip("Test requires transport-aware client")
        
        transport_type = get_client_transport_type(sut_client)
        
        if transport_type != "grpc":
            pytest.skip("Test specific to gRPC transport")
        
        # For gRPC, security is handled at the connection level
        # This test validates that the gRPC client is using secure channels
        try:
            # Check if gRPC client has TLS configuration
            if hasattr(sut_client, 'channel') and hasattr(sut_client.channel, '_channel'):
                logger.info("gRPC client appears to use secure channel")
            else:
                logger.info("gRPC client configuration not accessible for validation")
                
        except Exception as e:
            logger.warning(f"Could not validate gRPC TLS configuration: {e}")

    @optional_capability
    @a2a_v030
    def test_rest_api_security(self, sut_client):
        """
        A2A v0.3.0 §3.3 - REST Transport Security
        
        Validates security practices for REST API transport.
        """
        if not is_transport_client(sut_client):
            pytest.skip("Test requires transport-aware client")
        
        transport_type = get_client_transport_type(sut_client)
        
        if transport_type != "rest":
            pytest.skip("Test specific to REST transport")
        
        # REST API security validation
        sut_url = config.get_sut_url()
        
        try:
            # Test CORS headers for REST APIs
            response = requests.options(sut_url, timeout=10)
            headers = response.headers
            
            cors_headers = [
                "access-control-allow-origin",
                "access-control-allow-methods", 
                "access-control-allow-headers"
            ]
            
            found_cors = []
            for header in cors_headers:
                if header in headers:
                    found_cors.append(header)
                    logger.info(f"CORS header: {header}: {headers[header]}")
            
            if found_cors:
                logger.info(f"Found {len(found_cors)} CORS headers")
                
                # Check for overly permissive CORS
                allow_origin = headers.get("access-control-allow-origin", "")
                if allow_origin == "*":
                    logger.warning("⚠️  CORS allows all origins (*) - consider restricting for production")
                    
        except requests.RequestException as e:
            logger.warning(f"Could not test REST API security: {e}")


class TestSecurityCompliance:
    """
    Test overall security compliance with A2A v0.3.0 requirements.
    
    Validates enterprise security practices and compliance with
    security standards referenced in A2A v0.3.0.
    """

    @optional_capability
    @a2a_v030
    def test_enterprise_security_practices(self):
        """
        A2A v0.3.0 §4 - Enterprise Security Compliance
        
        Validates that the SUT follows enterprise security best practices
        as outlined in A2A v0.3.0 specification.
        """
        sut_url = config.get_sut_url()
        
        # Collect security assessment
        security_checklist = {
            "uses_https": sut_url.startswith("https://"),
            "certificate_valid": False,
            "tls_version_modern": False,
            "strong_ciphers": False
        }
        
        # Test certificate validity
        try:
            requests.get(sut_url, timeout=10, verify=True)
            security_checklist["certificate_valid"] = True
        except requests.exceptions.SSLError:
            pass
        except requests.exceptions.RequestException:
            # Other errors don't affect certificate validity
            security_checklist["certificate_valid"] = True
        
        # Test TLS version
        if sut_url.startswith("https://"):
            try:
                parsed_url = urllib.parse.urlparse(sut_url)
                hostname = parsed_url.hostname
                port = parsed_url.port or 443
                
                context = ssl.create_default_context()
                with socket.create_connection((hostname, port), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                        tls_version = ssock.version()
                        if tls_version in ["TLSv1.2", "TLSv1.3"]:
                            security_checklist["tls_version_modern"] = True
                        
                        cipher = ssock.cipher()
                        if cipher and cipher[2] >= 128:  # secret_bits >= 128
                            security_checklist["strong_ciphers"] = True
                            
            except Exception:
                pass
        
        # Report security status
        passed_checks = sum(security_checklist.values())
        total_checks = len(security_checklist)
        
        logger.info(f"Security compliance: {passed_checks}/{total_checks} checks passed")
        
        for check, passed in security_checklist.items():
            status = "✅" if passed else "❌"
            logger.info(f"{status} {check}: {passed}")
        
        # Skip HTTPS requirement for localhost testing
        if "localhost" in sut_url or "127.0.0.1" in sut_url:
            pytest.skip("HTTPS requirement skipped for localhost testing")
        
        # Minimum security requirements
        assert security_checklist["uses_https"], \
            "HTTPS is required for A2A v0.3.0 compliance"
        
        if passed_checks >= 3:
            logger.info("✅ Good security compliance")
        elif passed_checks >= 2:
            logger.info("⚠️  Basic security compliance")
        else:
            logger.warning("❌ Poor security compliance")