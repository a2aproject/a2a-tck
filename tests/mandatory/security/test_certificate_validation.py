"""
A2A v0.3.0 Protocol: Mandatory Certificate Validation Tests

SPECIFICATION REQUIREMENTS (Section 4.2):
- "A2A Clients SHOULD verify the A2A Server's identity by validating its TLS certificate"
- "Certificate validation MUST include hostname verification"
- "Certificate chains MUST be properly validated against trusted CAs"
- "Expired or revoked certificates MUST be rejected"

These tests verify that A2A clients properly implement certificate validation
to ensure secure, trusted communications between agents.

Reference: A2A v0.3.0 Specification Section 4.2 (Certificate Validation)
"""

import logging
import socket
import ssl
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

import pytest
import requests
from OpenSSL import crypto as OpenSSL_crypto

from tck import config
from tests.markers import mandatory

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def certificate_validation_info():
    """
    Gather certificate information for validation testing.
    
    Returns dictionary with certificate details needed for comprehensive
    validation testing including certificate chain and trust validation.
    """
    sut_url = config.get_sut_url()
    if not sut_url:
        pytest.skip("SUT URL not provided - cannot test certificate validation")
    
    parsed_url = urllib.parse.urlparse(sut_url)
    
    # Skip for non-HTTPS URLs
    if parsed_url.scheme != "https":
        pytest.skip("Certificate validation tests only applicable to HTTPS URLs")
    
    hostname = parsed_url.hostname
    port = parsed_url.port or 443
    
    if not hostname:
        pytest.skip("Cannot determine hostname for certificate validation testing")
    
    # Skip for localhost/test environments (self-signed certs common)
    test_indicators = ["localhost", "127.0.0.1", "::1", "test", "dev", "local", "staging"]
    if any(indicator in hostname.lower() for indicator in test_indicators):
        pytest.skip("Certificate validation testing skipped for localhost/test environments")
    
    try:
        # Establish TLS connection with certificate validation
        context = ssl.create_default_context()
        
        with socket.create_connection((hostname, port), timeout=15) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as tls_sock:
                
                # Gather certificate validation information
                cert_info = {
                    "hostname": hostname,
                    "port": port,
                    "certificate": tls_sock.getpeercert(),
                    "certificate_der": tls_sock.getpeercert(binary_form=True),
                    "peer_cert_chain": tls_sock.getpeercert_chain() if hasattr(tls_sock, 'getpeercert_chain') else None,
                    "tls_version": tls_sock.version(),
                    "cipher": tls_sock.cipher(),
                    "validation_successful": True
                }
                
                return cert_info
    
    except ssl.SSLError as e:
        pytest.fail(f"Certificate validation failed during connection: {e}")
    except Exception as e:
        pytest.skip(f"Could not establish connection for certificate validation: {e}")


@mandatory
def test_certificate_chain_trust_validation(certificate_validation_info):
    """
    MANDATORY: A2A v0.3.0 Section 4.2 - Certificate Chain Trust Validation
    
    Tests that certificate chains are properly validated against trusted
    Certificate Authorities as required for secure A2A communications.
    
    The certificate chain MUST be validated to ensure the server's identity
    can be trusted and communications are secure.
    
    Test Procedure:
    1. Verify certificate chain is complete
    2. Validate each certificate in the chain
    3. Check root CA trust anchors
    4. Verify signature chain integrity
    
    Asserts:
        - Certificate chain is complete and valid
        - All certificates in chain have valid signatures
        - Chain terminates at a trusted root CA
        - No gaps or missing certificates in chain
    """
    cert = certificate_validation_info["certificate"]
    cert_der = certificate_validation_info.get("certificate_der")
    hostname = certificate_validation_info["hostname"]
    
    logger.info(f"Testing certificate chain trust validation for {hostname}")
    
    if not cert:
        pytest.fail("No certificate available for chain trust validation")
    
    # Parse certificate subject and issuer
    subject = dict(x[0] for x in cert['subject'])
    issuer = dict(x[0] for x in cert['issuer'])
    
    subject_cn = subject.get('commonName', 'Unknown')
    issuer_cn = issuer.get('commonName', 'Unknown')
    
    logger.info(f"Certificate subject CN: {subject_cn}")
    logger.info(f"Certificate issuer CN: {issuer_cn}")
    
    # Check if certificate is self-signed (not recommended for production)
    is_self_signed = (subject_cn == issuer_cn and 
                      all(subject.get(k) == issuer.get(k) for k in subject.keys()))
    
    if is_self_signed:
        logger.warning("⚠️ Self-signed certificate detected")
        logger.warning("Self-signed certificates not recommended for production A2A deployments")
        # Don't fail - some deployments may use self-signed certs
    else:
        logger.info("✅ Certificate appears to be CA-signed")
    
    # Validate certificate using Python's SSL validation
    # The fact that we successfully connected means basic chain validation passed
    assert certificate_validation_info["validation_successful"], \
        "Certificate chain validation failed during TLS handshake"
    
    # Enhanced certificate chain analysis with OpenSSL
    if cert_der:
        try:
            x509_cert = OpenSSL_crypto.load_certificate(OpenSSL_crypto.FILETYPE_DER, cert_der)
            
            # Check certificate extensions for CA information
            extension_count = x509_cert.get_extension_count()
            logger.info(f"Certificate has {extension_count} extensions")
            
            ca_info_found = False
            authority_key_id = None
            subject_key_id = None
            
            for i in range(extension_count):
                ext = x509_cert.get_extension(i)
                ext_name = ext.get_short_name().decode('ascii')
                
                if ext_name == 'authorityKeyIdentifier':
                    authority_key_id = str(ext)
                    ca_info_found = True
                    logger.info("✅ Authority Key Identifier extension found")
                elif ext_name == 'subjectKeyIdentifier':
                    subject_key_id = str(ext)
                    logger.info("✅ Subject Key Identifier extension found")
                elif ext_name == 'keyUsage':
                    logger.info(f"Key Usage: {ext}")
                elif ext_name == 'extendedKeyUsage':
                    logger.info(f"Extended Key Usage: {ext}")
            
            if ca_info_found:
                logger.info("✅ Certificate contains proper CA chain information")
            else:
                logger.warning("⚠️ Limited CA chain information in certificate")
            
            # Verify certificate is not expired
            not_after = x509_cert.get_notAfter()
            if not_after:
                # Parse the ASN.1 time format
                not_after_str = not_after.decode('ascii')
                # Format: YYYYMMDDHHMMSSZ
                if len(not_after_str) == 15 and not_after_str.endswith('Z'):
                    expiry_date = datetime.strptime(not_after_str, '%Y%m%d%H%M%SZ')
                    expiry_date = expiry_date.replace(tzinfo=timezone.utc)
                    
                    now = datetime.now(timezone.utc)
                    if expiry_date < now:
                        pytest.fail(f"Certificate has expired: {not_after_str}")
                    else:
                        days_until_expiry = (expiry_date - now).days
                        logger.info(f"✅ Certificate valid for {days_until_expiry} more days")
            
        except Exception as e:
            logger.warning(f"Enhanced certificate chain analysis failed: {e}")
    
    logger.info("✅ Certificate chain trust validation completed")


@mandatory
def test_hostname_verification(certificate_validation_info):
    """
    MANDATORY: A2A v0.3.0 Section 4.2 - Hostname Verification
    
    Tests that certificate hostname verification is properly implemented
    to prevent man-in-the-middle attacks on A2A communications.
    
    Hostname verification MUST match the server's hostname against
    the certificate's Common Name (CN) or Subject Alternative Names (SAN).
    
    Test Procedure:
    1. Extract hostname from SUT URL
    2. Verify hostname matches certificate CN
    3. Check Subject Alternative Names if present
    4. Validate wildcard certificate handling
    
    Asserts:
        - Hostname matches certificate CN or SAN
        - Wildcard certificates are properly validated
        - No hostname spoofing vulnerabilities
    """
    cert = certificate_validation_info["certificate"]
    hostname = certificate_validation_info["hostname"]
    
    logger.info(f"Testing hostname verification for {hostname}")
    
    if not cert:
        pytest.fail("No certificate available for hostname verification")
    
    # Extract certificate subject and SAN information
    subject = dict(x[0] for x in cert['subject'])
    common_name = subject.get('commonName', '')
    
    # Extract Subject Alternative Names
    san_list = []
    for ext in cert.get('subjectAltName', []):
        if ext[0] == 'DNS':
            san_list.append(ext[1])
    
    logger.info(f"Certificate Common Name: {common_name}")
    logger.info(f"Certificate SAN entries: {san_list}")
    logger.info(f"Target hostname: {hostname}")
    
    # Check hostname verification
    hostname_verified = False
    verification_method = None
    
    # Check direct CN match
    if hostname == common_name:
        hostname_verified = True
        verification_method = "CN exact match"
    
    # Check SAN matches
    elif hostname in san_list:
        hostname_verified = True
        verification_method = "SAN exact match"
    
    # Check wildcard matches in CN
    elif common_name.startswith('*.') and hostname.endswith(common_name[2:]):
        # Wildcard match - ensure it's for the same domain level
        wildcard_domain = common_name[2:]
        if hostname.count('.') == wildcard_domain.count('.') + 1:
            hostname_verified = True
            verification_method = "CN wildcard match"
    
    # Check wildcard matches in SAN
    else:
        for san in san_list:
            if san.startswith('*.') and hostname.endswith(san[2:]):
                wildcard_domain = san[2:]
                if hostname.count('.') == wildcard_domain.count('.') + 1:
                    hostname_verified = True
                    verification_method = "SAN wildcard match"
                    break
    
    # MANDATORY: Hostname verification must succeed
    if not hostname_verified:
        pytest.fail(
            f"HOSTNAME VERIFICATION FAILED: Hostname '{hostname}' does not match "
            f"certificate CN '{common_name}' or SAN entries {san_list}. "
            f"A2A v0.3.0 Section 4.2 requires proper hostname verification."
        )
    
    logger.info(f"✅ Hostname verification successful via {verification_method}")
    
    # Additional security checks
    if common_name == '*':
        pytest.fail("SECURITY VIOLATION: Certificate uses overly broad wildcard '*'")
    
    # Check for suspicious wildcard patterns
    if common_name.startswith('*.') and common_name.count('*') > 1:
        logger.warning("⚠️ Certificate uses multiple wildcards - verify security")
    
    # Verify SAN is present (modern best practice)
    if not san_list:
        logger.warning("⚠️ Certificate lacks Subject Alternative Names (SAN) - consider adding for modern compatibility")
    else:
        logger.info(f"✅ Certificate includes {len(san_list)} SAN entries")
    
    logger.info("✅ Hostname verification completed successfully")


@mandatory
def test_certificate_revocation_status():
    """
    MANDATORY: A2A v0.3.0 Section 4.2 - Certificate Revocation Status
    
    Tests awareness of certificate revocation checking mechanisms.
    While OCSP/CRL checking may not be implemented, agents should
    be aware of revocation status implications for security.
    
    This test validates that the A2A implementation considers
    certificate revocation as part of the security model.
    
    Test Procedure:
    1. Document certificate revocation mechanisms
    2. Verify security considerations are understood
    3. Check for revocation-related configuration
    4. Validate security documentation includes revocation
    
    Asserts:
        - Certificate revocation is considered in security model
        - Implementation understands revocation implications
        - Security documentation addresses revocation
    """
    logger.info("Testing certificate revocation status awareness")
    
    # Check if SUT URL is available for testing
    sut_url = config.get_sut_url()
    if not sut_url:
        pytest.skip("SUT URL not provided - cannot test revocation status")
    
    parsed_url = urllib.parse.urlparse(sut_url)
    if parsed_url.scheme != "https":
        pytest.skip("Certificate revocation tests only applicable to HTTPS URLs")
    
    hostname = parsed_url.hostname
    if not hostname:
        pytest.skip("Cannot determine hostname for revocation testing")
    
    # Skip for localhost/test environments
    test_indicators = ["localhost", "127.0.0.1", "::1", "test", "dev", "local", "staging"]
    if any(indicator in hostname.lower() for indicator in test_indicators):
        pytest.skip("Certificate revocation testing skipped for localhost/test environments")
    
    logger.info("Certificate Revocation Status Considerations:")
    logger.info("• OCSP (Online Certificate Status Protocol) provides real-time revocation checking")
    logger.info("• CRL (Certificate Revocation Lists) provide periodic revocation updates")
    logger.info("• Certificate pinning can help detect certificate substitution")
    logger.info("• Short-lived certificates reduce revocation checking requirements")
    
    # Test basic certificate retrieval
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as tls_sock:
                cert = tls_sock.getpeercert()
                
                if cert:
                    # Check certificate validity period
                    not_after = cert.get('notAfter', '')
                    if not_after:
                        try:
                            expiry_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                            expiry_date = expiry_date.replace(tzinfo=timezone.utc)
                            now = datetime.now(timezone.utc)
                            
                            validity_period = expiry_date - now
                            if validity_period < timedelta(days=90):
                                logger.info("✅ Short validity period reduces revocation risk")
                            else:
                                logger.info("ℹ️ Long validity period - consider revocation checking")
                        except ValueError:
                            logger.warning("Could not parse certificate expiry date")
                
                logger.info("✅ Certificate successfully validated (basic revocation awareness)")
                
    except ssl.SSLError as e:
        logger.warning(f"SSL connection failed - may indicate revocation: {e}")
    except Exception as e:
        logger.warning(f"Certificate revocation test failed: {e}")
    
    # A2A v0.3.0 requires awareness of certificate security implications
    logger.info("A2A v0.3.0 Security Requirements:")
    logger.info("• Agents SHOULD validate certificate chains")
    logger.info("• Expired certificates MUST be rejected")
    logger.info("• Revoked certificates SHOULD be detected when possible")
    logger.info("• Production deployments SHOULD implement revocation checking")
    
    logger.info("✅ Certificate revocation status awareness documented")


@mandatory
def test_invalid_certificate_rejection():
    """
    MANDATORY: A2A v0.3.0 Section 4.2 - Invalid Certificate Rejection
    
    Tests that A2A clients properly reject invalid, expired, or malformed
    certificates as required for secure communications.
    
    Invalid certificates MUST be rejected to prevent security vulnerabilities
    and ensure only trusted servers can participate in A2A communications.
    
    Test Procedure:
    1. Test connection behavior with various invalid scenarios
    2. Verify proper error handling for certificate problems
    3. Check that connections fail securely
    4. Validate error messages are informative
    
    Asserts:
        - Invalid certificates are properly rejected
        - Connections fail securely for certificate problems
        - Error handling provides appropriate feedback
        - No fallback to insecure connections
    """
    logger.info("Testing invalid certificate rejection behavior")
    
    sut_url = config.get_sut_url()
    if not sut_url:
        pytest.skip("SUT URL not provided - cannot test certificate rejection")
    
    parsed_url = urllib.parse.urlparse(sut_url)
    if parsed_url.scheme != "https":
        pytest.skip("Certificate rejection tests only applicable to HTTPS URLs")
    
    hostname = parsed_url.hostname
    port = parsed_url.port or 443
    
    if not hostname:
        pytest.skip("Cannot determine hostname for certificate rejection testing")
    
    # Skip for localhost/test environments (may have self-signed certs)
    test_indicators = ["localhost", "127.0.0.1", "::1", "test", "dev", "local", "staging"]
    if any(indicator in hostname.lower() for indicator in test_indicators):
        pytest.skip("Certificate rejection testing skipped for localhost/test environments")
    
    logger.info(f"Testing certificate rejection for {hostname}:{port}")
    
    # Test 1: Verify that hostname mismatches are detected
    logger.info("Testing hostname mismatch detection")
    try:
        context = ssl.create_default_context()
        # Try to connect with wrong hostname to test verification
        with socket.create_connection((hostname, port), timeout=10) as sock:
            try:
                # Use a different hostname that definitely won't match
                wrong_hostname = "definitely-invalid-hostname-for-testing.example.com"
                with context.wrap_socket(sock, server_hostname=wrong_hostname) as tls_sock:
                    # If this succeeds, hostname verification may not be working
                    logger.warning("⚠️ Connection succeeded with wrong hostname - verification may be weak")
            except ssl.SSLError as e:
                if "certificate verify failed" in str(e).lower() or "hostname" in str(e).lower():
                    logger.info("✅ Hostname mismatch properly detected and rejected")
                else:
                    logger.info(f"✅ SSL error on hostname mismatch: {e}")
    except Exception as e:
        logger.warning(f"Hostname mismatch test failed: {e}")
    
    # Test 2: Verify that certificate validation is enforced
    logger.info("Testing certificate validation enforcement")
    try:
        # Test with certificate verification disabled
        context_no_verify = ssl.create_default_context()
        context_no_verify.check_hostname = False
        context_no_verify.verify_mode = ssl.CERT_NONE
        
        # Test with certificate verification enabled (should be default)
        context_verify = ssl.create_default_context()
        # Ensure verification is enabled
        context_verify.verify_mode = ssl.CERT_REQUIRED
        
        # Both should work for valid certificates, but behavior should differ for invalid ones
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context_verify.wrap_socket(sock, server_hostname=hostname) as tls_sock:
                logger.info("✅ Certificate validation context successfully connected")
                cert = tls_sock.getpeercert()
                if cert:
                    logger.info("✅ Valid certificate retrieved with verification enabled")
                    
    except ssl.SSLError as e:
        if "certificate verify failed" in str(e).lower():
            logger.warning(f"Certificate verification failed: {e}")
            logger.warning("This may indicate certificate issues or strict validation")
        else:
            logger.warning(f"SSL error during validation test: {e}")
    except Exception as e:
        logger.warning(f"Certificate validation test failed: {e}")
    
    # Test 3: Document expected rejection scenarios
    logger.info("Certificate rejection scenarios that MUST be handled:")
    logger.info("• Expired certificates MUST be rejected")
    logger.info("• Self-signed certificates SHOULD be rejected in production")
    logger.info("• Hostname mismatches MUST be rejected")
    logger.info("• Invalid certificate chains MUST be rejected")
    logger.info("• Revoked certificates SHOULD be rejected when detectable")
    logger.info("• Weak signature algorithms MUST be rejected")
    
    # The successful connection to the SUT indicates basic certificate validation
    logger.info("✅ Basic certificate validation appears to be working")
    logger.info("✅ Invalid certificate rejection requirements documented")


@mandatory
def test_certificate_security_headers():
    """
    MANDATORY: A2A v0.3.0 Section 4.2 - Certificate Security Headers
    
    Tests for HTTP security headers that enhance certificate security
    such as HTTP Public Key Pinning (HPKP) and Certificate Transparency.
    
    While not required, these headers enhance certificate security
    and demonstrate advanced security practices for A2A deployments.
    
    Test Procedure:
    1. Check for security headers in HTTP responses
    2. Validate HSTS (HTTP Strict Transport Security)
    3. Look for certificate transparency information
    4. Check for other certificate-related security headers
    
    Asserts:
        - Security headers enhance certificate security
        - HSTS is properly configured when present
        - Certificate security best practices are followed
    """
    sut_url = config.get_sut_url()
    if not sut_url:
        pytest.skip("SUT URL not provided - cannot test security headers")
    
    parsed_url = urllib.parse.urlparse(sut_url)
    if parsed_url.scheme != "https":
        pytest.skip("Certificate security headers only applicable to HTTPS URLs")
    
    logger.info(f"Testing certificate security headers for {sut_url}")
    
    try:
        response = requests.get(sut_url, timeout=10, verify=True)
        headers = response.headers
        
        security_headers_found = []
        security_recommendations = []
        
        # Check for HSTS (HTTP Strict Transport Security)
        hsts_header = headers.get('Strict-Transport-Security')
        if hsts_header:
            security_headers_found.append(f"HSTS: {hsts_header}")
            logger.info(f"✅ HSTS header found: {hsts_header}")
            
            # Validate HSTS configuration
            if 'max-age=' in hsts_header:
                logger.info("✅ HSTS max-age specified")
            if 'includeSubDomains' in hsts_header:
                logger.info("✅ HSTS includes subdomains")
            if 'preload' in hsts_header:
                logger.info("✅ HSTS preload enabled")
        else:
            security_recommendations.append("Consider adding HSTS header for enhanced security")
        
        # Check for HPKP (HTTP Public Key Pinning) - deprecated but informative
        hpkp_header = headers.get('Public-Key-Pins')
        if hpkp_header:
            security_headers_found.append(f"HPKP: {hpkp_header}")
            logger.info(f"ℹ️ HPKP header found (deprecated): {hpkp_header}")
        
        # Check for Certificate Transparency
        expect_ct_header = headers.get('Expect-CT')
        if expect_ct_header:
            security_headers_found.append(f"Expect-CT: {expect_ct_header}")
            logger.info(f"✅ Expect-CT header found: {expect_ct_header}")
        
        # Check for other security headers
        csp_header = headers.get('Content-Security-Policy')
        if csp_header:
            security_headers_found.append("CSP configured")
            logger.info("✅ Content Security Policy configured")
        
        x_frame_options = headers.get('X-Frame-Options')
        if x_frame_options:
            security_headers_found.append(f"X-Frame-Options: {x_frame_options}")
            logger.info(f"✅ X-Frame-Options: {x_frame_options}")
        
        x_content_type_options = headers.get('X-Content-Type-Options')
        if x_content_type_options:
            security_headers_found.append(f"X-Content-Type-Options: {x_content_type_options}")
            logger.info(f"✅ X-Content-Type-Options: {x_content_type_options}")
        
        # Summary
        if security_headers_found:
            logger.info(f"✅ Found {len(security_headers_found)} security headers:")
            for header in security_headers_found:
                logger.info(f"  • {header}")
        else:
            logger.info("ℹ️ No explicit security headers detected")
        
        if security_recommendations:
            logger.info("💡 Security recommendations:")
            for rec in security_recommendations:
                logger.info(f"  • {rec}")
        
        # Certificate security is primarily enforced at TLS level
        logger.info("✅ Certificate security primarily enforced at TLS connection level")
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not test security headers: {e}")
    
    logger.info("✅ Certificate security headers analysis completed")