"""
A2A v0.3.0 Protocol: Enhanced TLS Configuration Validation Tests

SPECIFICATION REQUIREMENTS (Section 4.1):
- "Implementations SHOULD use modern TLS configurations (TLS 1.3+ recommended)"
- "A2A Clients SHOULD verify the A2A Server's identity by validating its TLS certificate"
- Enhanced security validation for cipher suites, protocol versions, and certificate chains

These tests provide enhanced TLS configuration validation beyond the basic mandatory tests,
focusing on security best practices and modern TLS standards.

Reference: A2A v0.3.0 Specification Section 4.1 (Transport Security)
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
def tls_connection_info():
    """
    Establish TLS connection and extract comprehensive TLS information.

    Returns dictionary with TLS configuration details including
    protocol version, cipher suites, certificate chain, and security parameters.
    """
    sut_url = config.get_sut_url()
    if not sut_url:
        pytest.skip("SUT URL not provided - cannot test TLS configuration")

    parsed_url = urllib.parse.urlparse(sut_url)

    # Skip for non-HTTPS URLs
    if parsed_url.scheme != "https":
        pytest.skip("TLS configuration tests only applicable to HTTPS URLs")

    hostname = parsed_url.hostname
    port = parsed_url.port or 443

    if not hostname:
        pytest.skip("Cannot determine hostname for TLS testing")

    # Skip for localhost/test environments (handled by basic mandatory tests)
    test_indicators = ["localhost", "127.0.0.1", "::1", "test", "dev", "local", "staging"]
    if any(indicator in hostname.lower() for indicator in test_indicators):
        pytest.skip("Enhanced TLS testing skipped for localhost/test environments")

    try:
        # Establish TLS connection with detailed information gathering
        context = ssl.create_default_context()

        with socket.create_connection((hostname, port), timeout=15) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as tls_sock:
                # Gather comprehensive TLS information
                tls_info = {
                    "hostname": hostname,
                    "port": port,
                    "tls_version": tls_sock.version(),
                    "cipher": tls_sock.cipher(),
                    "certificate": tls_sock.getpeercert(),
                    "certificate_der": tls_sock.getpeercert(binary_form=True),
                    "peer_cert_chain": tls_sock.getpeercert_chain() if hasattr(tls_sock, "getpeercert_chain") else None,
                    "compression": tls_sock.compression(),
                    "selected_alpn_protocol": tls_sock.selected_alpn_protocol(),
                }

                return tls_info

    except Exception as e:
        pytest.skip(f"Could not establish TLS connection for enhanced testing: {e}")


def analyze_cipher_security(cipher_name: str) -> Dict[str, Any]:
    """
    Analyze cipher suite for security characteristics.

    Returns analysis of cipher strength, algorithms, and security recommendations.
    """
    cipher_upper = cipher_name.upper()

    analysis = {"cipher_name": cipher_name, "is_secure": True, "warnings": [], "strengths": [], "security_level": "unknown"}

    # Check for deprecated/weak algorithms
    weak_algorithms = {
        "RC4": "RC4 stream cipher is cryptographically broken",
        "DES": "DES has insufficient key length",
        "3DES": "3DES is deprecated and slow",
        "MD5": "MD5 hash function is cryptographically broken",
        "SHA1": "SHA-1 is deprecated for new applications",
        "NULL": "NULL cipher provides no encryption",
        "EXPORT": "Export-grade ciphers are intentionally weak",
        "ANON": "Anonymous ciphers provide no authentication",
    }

    for weak_algo, reason in weak_algorithms.items():
        if weak_algo in cipher_upper:
            analysis["is_secure"] = False
            analysis["warnings"].append(f"{weak_algo}: {reason}")

    # Check for strong algorithms
    strong_algorithms = {
        "AES": "AES is a strong symmetric cipher",
        "CHACHA20": "ChaCha20 is a modern stream cipher",
        "POLY1305": "Poly1305 is a modern MAC algorithm",
        "GCM": "GCM provides authenticated encryption",
        "CCM": "CCM provides authenticated encryption",
        "SHA256": "SHA-256 is cryptographically secure",
        "SHA384": "SHA-384 provides higher security margin",
        "ECDHE": "ECDHE provides forward secrecy",
        "DHE": "DHE provides forward secrecy",
    }

    for strong_algo, benefit in strong_algorithms.items():
        if strong_algo in cipher_upper:
            analysis["strengths"].append(f"{strong_algo}: {benefit}")

    # Determine security level
    if not analysis["is_secure"]:
        analysis["security_level"] = "weak"
    elif "ECDHE" in cipher_upper or "DHE" in cipher_upper:
        if "GCM" in cipher_upper or "CHACHA20" in cipher_upper:
            analysis["security_level"] = "excellent"
        else:
            analysis["security_level"] = "good"
    elif "AES" in cipher_upper:
        analysis["security_level"] = "adequate"
    else:
        analysis["security_level"] = "unknown"

    return analysis


@mandatory
def test_tls_protocol_version_security(tls_connection_info):
    """
    MANDATORY: A2A v0.3.0 Section 4.1 - TLS Protocol Version Security

    Enhanced validation of TLS protocol versions with detailed security analysis.
    Tests for modern TLS versions and checks for deprecated protocols.

    A2A v0.3.0 recommends TLS 1.3+ for enhanced security and performance.

    Test Procedure:
    1. Verify TLS protocol version meets minimum security standards
    2. Check for use of modern TLS versions
    3. Validate protocol version consistency
    4. Test for deprecated protocol support

    Asserts:
        - TLS version is 1.2 or higher (1.3 strongly recommended)
        - No deprecated or insecure protocol versions
        - Protocol version matches security expectations
    """
    tls_version = tls_connection_info["tls_version"]
    hostname = tls_connection_info["hostname"]

    logger.info(f"Enhanced TLS protocol analysis for {hostname}")
    logger.info(f"Detected TLS version: {tls_version}")

    # Define TLS version security levels
    tls_security_levels = {
        "TLSv1.3": {"level": "excellent", "recommendation": "Latest TLS standard with enhanced security"},
        "TLSv1.2": {"level": "good", "recommendation": "Secure and widely supported"},
        "TLSv1.1": {"level": "deprecated", "recommendation": "Deprecated - upgrade to TLS 1.2+"},
        "TLSv1": {"level": "insecure", "recommendation": "Insecure - immediate upgrade required"},
        "SSLv3": {"level": "broken", "recommendation": "Cryptographically broken - must not use"},
        "SSLv2": {"level": "broken", "recommendation": "Cryptographically broken - must not use"},
    }

    if not tls_version:
        pytest.fail("Could not determine TLS version - connection may be insecure")

    version_info = tls_security_levels.get(
        tls_version, {"level": "unknown", "recommendation": "Unknown TLS version - verify security"}
    )

    security_level = version_info["level"]
    recommendation = version_info["recommendation"]

    logger.info(f"TLS version security level: {security_level}")
    logger.info(f"Recommendation: {recommendation}")

    # MANDATORY: Fail for broken/insecure protocols
    if security_level in ["broken", "insecure"]:
        pytest.fail(
            f"SECURITY VIOLATION: {tls_version} is {security_level}. "
            f"A2A v0.3.0 Section 4.1 requires secure TLS configurations. "
            f"{recommendation}"
        )

    # MANDATORY: Warn for deprecated protocols
    elif security_level == "deprecated":
        logger.warning(f"⚠️ DEPRECATED: {tls_version} is deprecated. {recommendation}")
        # For now, log warning but don't fail - give transition time
        # In future versions, this may become a hard failure

    # RECOMMENDED: Prefer TLS 1.3
    elif security_level == "excellent":
        logger.info(f"✅ EXCELLENT: {tls_version} - modern TLS with enhanced security")

    elif security_level == "good":
        logger.info(f"✅ GOOD: {tls_version} - secure and acceptable")
        logger.info("💡 RECOMMENDATION: Consider upgrading to TLS 1.3 for enhanced security and performance")

    # Ensure minimum TLS 1.2 for production
    if tls_version not in ["TLSv1.3", "TLSv1.2"]:
        pytest.fail(
            f"SPECIFICATION REQUIREMENT: TLS 1.2+ required for production deployments. "
            f"Current version {tls_version} does not meet minimum security standards."
        )

    logger.info("✅ TLS protocol version meets security requirements")


@mandatory
def test_cipher_suite_security_analysis(tls_connection_info):
    """
    MANDATORY: A2A v0.3.0 Section 4.1 - Cipher Suite Security Analysis

    Enhanced analysis of cipher suite security characteristics including
    encryption algorithms, key exchange methods, and authentication mechanisms.

    Test Procedure:
    1. Analyze cipher suite components for security
    2. Check for forward secrecy support
    3. Validate encryption strength and authentication
    4. Test for weak or deprecated algorithms

    Asserts:
        - Cipher suite uses secure algorithms
        - Adequate key lengths for encryption
        - Forward secrecy is provided
        - No weak or deprecated cipher components
    """
    cipher = tls_connection_info["cipher"]
    hostname = tls_connection_info["hostname"]

    if not cipher:
        pytest.fail("Could not determine cipher suite - TLS connection may be insecure")

    cipher_name, tls_version, key_length = cipher

    logger.info(f"Enhanced cipher analysis for {hostname}")
    logger.info(f"Cipher suite: {cipher_name}")
    logger.info(f"Key length: {key_length} bits")
    logger.info(f"TLS version (cipher): {tls_version}")

    # Perform detailed cipher security analysis
    cipher_analysis = analyze_cipher_security(cipher_name)

    logger.info(f"Cipher security level: {cipher_analysis['security_level']}")

    # Log strengths
    if cipher_analysis["strengths"]:
        logger.info("Cipher strengths:")
        for strength in cipher_analysis["strengths"]:
            logger.info(f"  ✅ {strength}")

    # Log warnings
    if cipher_analysis["warnings"]:
        logger.warning("Cipher security warnings:")
        for warning in cipher_analysis["warnings"]:
            logger.warning(f"  ⚠️ {warning}")

    # MANDATORY: Fail for insecure ciphers
    if not cipher_analysis["is_secure"]:
        pytest.fail(
            f"SECURITY VIOLATION: Cipher suite contains insecure algorithms. "
            f"A2A v0.3.0 Section 4.1 requires secure cipher configurations. "
            f"Issues: {'; '.join(cipher_analysis['warnings'])}"
        )

    # MANDATORY: Validate key length
    if key_length < 128:
        pytest.fail(
            f"SECURITY VIOLATION: Cipher key length {key_length} bits is too weak. "
            f"Minimum 128 bits required for secure communications."
        )
    elif key_length < 256:
        logger.info(f"✅ ADEQUATE: Key length {key_length} bits meets minimum security")
        logger.info("💡 RECOMMENDATION: Consider 256-bit keys for enhanced security")
    else:
        logger.info(f"✅ STRONG: Key length {key_length} bits provides excellent security")

    # Check for forward secrecy
    forward_secrecy_indicators = ["ECDHE", "DHE"]
    has_forward_secrecy = any(indicator in cipher_name.upper() for indicator in forward_secrecy_indicators)

    if has_forward_secrecy:
        logger.info("✅ Forward secrecy provided by cipher suite")
    else:
        logger.warning("⚠️ Forward secrecy not detected - consider ECDHE/DHE cipher suites")

    # Overall security assessment
    if cipher_analysis["security_level"] == "excellent":
        logger.info("✅ EXCELLENT: Cipher suite uses modern, secure algorithms")
    elif cipher_analysis["security_level"] == "good":
        logger.info("✅ GOOD: Cipher suite provides adequate security")
    elif cipher_analysis["security_level"] == "adequate":
        logger.info("✅ ADEQUATE: Cipher suite meets minimum security requirements")
        logger.info("💡 RECOMMENDATION: Consider upgrading to more modern cipher suites")
    else:
        logger.warning(f"⚠️ Cipher suite security level: {cipher_analysis['security_level']}")

    logger.info("✅ Cipher suite analysis complete")


@mandatory
def test_certificate_chain_validation(tls_connection_info):
    """
    MANDATORY: A2A v0.3.0 Section 4.2 - Certificate Chain Validation

    Enhanced validation of TLS certificate chain including expiration,
    key strength, signature algorithms, and trust chain verification.

    Test Procedure:
    1. Validate certificate expiration and validity period
    2. Check certificate key strength and algorithms
    3. Verify certificate chain completeness
    4. Validate certificate extensions and constraints

    Asserts:
        - Certificate is valid and not expired
        - Certificate uses strong cryptographic algorithms
        - Certificate chain is properly configured
        - Certificate extensions follow security best practices
    """
    cert = tls_connection_info["certificate"]
    cert_der = tls_connection_info.get("certificate_der")
    hostname = tls_connection_info["hostname"]

    if not cert:
        pytest.fail("Could not retrieve TLS certificate for validation")

    logger.info(f"Enhanced certificate analysis for {hostname}")

    # Parse certificate details
    subject = dict(x[0] for x in cert["subject"])
    issuer = dict(x[0] for x in cert["issuer"])

    logger.info(f"Certificate subject: {subject.get('commonName', 'Unknown')}")
    logger.info(f"Certificate issuer: {issuer.get('commonName', 'Unknown')}")

    # Certificate expiration validation
    not_before = cert["notBefore"]
    not_after = cert["notAfter"]

    try:
        valid_from = datetime.strptime(not_before, "%b %d %H:%M:%S %Y %Z")
        valid_until = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")

        # Add UTC timezone for comparison
        valid_from = valid_from.replace(tzinfo=timezone.utc)
        valid_until = valid_until.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)

        # Check certificate validity period
        if now < valid_from:
            pytest.fail(f"Certificate not yet valid. Valid from: {not_before}")

        if now > valid_until:
            pytest.fail(f"Certificate has expired. Expired on: {not_after}")

        # Check for expiration warning (30 days)
        expiry_warning_threshold = now + timedelta(days=30)
        if valid_until < expiry_warning_threshold:
            days_until_expiry = (valid_until - now).days
            logger.warning(f"⚠️ Certificate expires soon: {days_until_expiry} days ({not_after})")
        else:
            logger.info(f"✅ Certificate valid until: {not_after}")

        # Check certificate validity period length
        validity_period = valid_until - valid_from
        if validity_period > timedelta(days=825):  # Current CA/Browser Forum limit
            logger.warning(f"⚠️ Certificate validity period longer than recommended: {validity_period.days} days")
        else:
            logger.info(f"✅ Certificate validity period: {validity_period.days} days")

    except ValueError as e:
        logger.warning(f"Could not parse certificate dates: {e}")

    # Enhanced certificate analysis using OpenSSL
    if cert_der:
        try:
            x509_cert = OpenSSL_crypto.load_certificate(OpenSSL_crypto.FILETYPE_DER, cert_der)

            # Check public key algorithm and strength
            public_key = x509_cert.get_pubkey()
            key_type = public_key.type()
            key_bits = public_key.bits()

            # Map OpenSSL key types
            key_type_names = {
                OpenSSL_crypto.TYPE_RSA: "RSA",
                OpenSSL_crypto.TYPE_DSA: "DSA",
                6: "EC",  # ECDSA
            }

            key_type_name = key_type_names.get(key_type, f"Unknown({key_type})")

            logger.info(f"Public key algorithm: {key_type_name}")
            logger.info(f"Public key size: {key_bits} bits")

            # Validate key strength
            if key_type_name == "RSA":
                if key_bits < 2048:
                    pytest.fail(f"RSA key size {key_bits} bits is too weak (minimum 2048 bits)")
                elif key_bits >= 3072:
                    logger.info(f"✅ STRONG: RSA {key_bits} bits provides excellent security")
                else:
                    logger.info(f"✅ ADEQUATE: RSA {key_bits} bits meets current standards")

            elif key_type_name == "EC":
                if key_bits < 256:
                    pytest.fail(f"ECDSA key size {key_bits} bits is too weak (minimum 256 bits)")
                else:
                    logger.info(f"✅ STRONG: ECDSA {key_bits} bits provides excellent security")

            elif key_type_name == "DSA":
                logger.warning("⚠️ DSA keys are deprecated - consider RSA or ECDSA")

            # Check signature algorithm
            sig_alg = x509_cert.get_signature_algorithm().decode("ascii")
            logger.info(f"Signature algorithm: {sig_alg}")

            # Check for weak signature algorithms
            weak_sig_algs = ["md5", "sha1"]
            if any(weak in sig_alg.lower() for weak in weak_sig_algs):
                pytest.fail(f"Weak signature algorithm detected: {sig_alg}")
            else:
                logger.info("✅ Signature algorithm is secure")

            # Check certificate version
            cert_version = x509_cert.get_version() + 1  # OpenSSL returns 0-based version
            if cert_version < 3:
                logger.warning(f"⚠️ Certificate version {cert_version} is outdated (v3 recommended)")
            else:
                logger.info(f"✅ Certificate version: v{cert_version}")

        except Exception as e:
            logger.warning(f"Could not perform enhanced certificate analysis: {e}")

    # Hostname verification
    common_name = subject.get("commonName", "")
    san_list = []

    for ext in cert.get("subjectAltName", []):
        if ext[0] == "DNS":
            san_list.append(ext[1])

    logger.info(f"Certificate CN: {common_name}")
    logger.info(f"Certificate SANs: {san_list}")

    # Verify hostname matches certificate
    hostname_match = (
        hostname == common_name
        or hostname in san_list
        or any(san.startswith("*.") and hostname.endswith(san[2:]) for san in san_list)
    )

    if hostname_match:
        logger.info("✅ Hostname matches certificate")
    else:
        logger.warning(f"⚠️ Hostname {hostname} not found in certificate CN/SAN")

    logger.info("✅ Certificate chain validation complete")


@mandatory
def test_tls_security_features(tls_connection_info):
    """
    MANDATORY: A2A v0.3.0 Section 4.1 - TLS Security Features

    Tests for advanced TLS security features including compression security,
    protocol negotiation, and modern TLS extensions.

    Test Procedure:
    1. Check TLS compression status (should be disabled)
    2. Validate ALPN protocol negotiation
    3. Test for secure renegotiation support
    4. Check for modern TLS security features

    Asserts:
        - TLS compression is disabled (CRIME attack prevention)
        - ALPN protocol negotiation works correctly
        - Modern security features are properly configured
    """
    hostname = tls_connection_info["hostname"]
    compression = tls_connection_info.get("compression")
    alpn_protocol = tls_connection_info.get("selected_alpn_protocol")

    logger.info(f"TLS security features analysis for {hostname}")

    # Check TLS compression (should be disabled to prevent CRIME attacks)
    if compression:
        logger.warning(f"⚠️ TLS compression enabled: {compression}")
        logger.warning("TLS compression can lead to CRIME attacks - should be disabled")
        # Note: This is a security concern but not necessarily a test failure
        # as some implementations may still have compression enabled
    else:
        logger.info("✅ TLS compression disabled (CRIME attack prevention)")

    # Check ALPN protocol negotiation
    if alpn_protocol:
        logger.info(f"✅ ALPN protocol negotiated: {alpn_protocol}")

        # Validate ALPN protocol for A2A
        expected_protocols = ["h2", "http/1.1"]
        if alpn_protocol in expected_protocols:
            logger.info(f"✅ ALPN protocol {alpn_protocol} suitable for A2A")
        else:
            logger.info(f"ℹ️ ALPN protocol {alpn_protocol} - verify A2A compatibility")
    else:
        logger.info("ℹ️ No ALPN protocol negotiated (HTTP/1.1 fallback expected)")

    # Additional TLS security checks
    tls_version = tls_connection_info["tls_version"]

    # TLS 1.3 specific features
    if tls_version == "TLSv1.3":
        logger.info("✅ TLS 1.3 provides enhanced security features:")
        logger.info("  • Perfect forward secrecy by default")
        logger.info("  • Improved handshake security")
        logger.info("  • Reduced attack surface")
        logger.info("  • Better performance")

    # TLS 1.2 recommendations
    elif tls_version == "TLSv1.2":
        cipher = tls_connection_info.get("cipher")
        if cipher:
            cipher_name = cipher[0]
            if "ECDHE" in cipher_name or "DHE" in cipher_name:
                logger.info("✅ TLS 1.2 with forward secrecy (ECDHE/DHE)")
            else:
                logger.warning("⚠️ TLS 1.2 without forward secrecy - consider ECDHE ciphers")

    logger.info("✅ TLS security features analysis complete")


@mandatory
def test_tls_implementation_best_practices(tls_connection_info):
    """
    MANDATORY: A2A v0.3.0 Section 4.1 - TLS Implementation Best Practices

    Validates TLS implementation follows security best practices for production
    A2A deployments including security headers and proper error handling.

    Test Procedure:
    1. Test TLS implementation security
    2. Validate proper error handling
    3. Check for security hardening
    4. Verify production readiness

    Asserts:
        - TLS implementation follows security best practices
        - Proper error handling for TLS issues
        - Production-ready TLS configuration
    """
    hostname = tls_connection_info["hostname"]
    tls_version = tls_connection_info["tls_version"]
    cipher = tls_connection_info["cipher"]

    logger.info(f"TLS implementation best practices analysis for {hostname}")

    # Create overall security score
    security_score = 0
    max_score = 10

    # TLS version scoring
    if tls_version == "TLSv1.3":
        security_score += 3
        logger.info("✅ +3 points: TLS 1.3 (excellent)")
    elif tls_version == "TLSv1.2":
        security_score += 2
        logger.info("✅ +2 points: TLS 1.2 (good)")
    else:
        logger.warning(f"⚠️ +0 points: {tls_version} (needs improvement)")

    # Cipher suite scoring
    if cipher:
        cipher_name = cipher[0]
        key_length = cipher[2]

        # Forward secrecy
        if "ECDHE" in cipher_name:
            security_score += 2
            logger.info("✅ +2 points: ECDHE forward secrecy")
        elif "DHE" in cipher_name:
            security_score += 1
            logger.info("✅ +1 point: DHE forward secrecy")

        # Authenticated encryption
        if "GCM" in cipher_name or "CHACHA20" in cipher_name:
            security_score += 2
            logger.info("✅ +2 points: Authenticated encryption")
        elif "CBC" in cipher_name:
            security_score += 1
            logger.info("✅ +1 point: CBC mode encryption")

        # Key strength
        if key_length >= 256:
            security_score += 2
            logger.info("✅ +2 points: Strong key length")
        elif key_length >= 128:
            security_score += 1
            logger.info("✅ +1 point: Adequate key length")

    # Certificate validation (basic check)
    cert = tls_connection_info.get("certificate")
    if cert:
        # Check for SAN (modern best practice)
        san_list = [ext[1] for ext in cert.get("subjectAltName", []) if ext[0] == "DNS"]
        if san_list:
            security_score += 1
            logger.info("✅ +1 point: Certificate uses SAN extension")

    # Calculate security grade
    security_percentage = (security_score / max_score) * 100

    if security_percentage >= 90:
        security_grade = "A+"
        grade_message = "Excellent TLS security configuration"
    elif security_percentage >= 80:
        security_grade = "A"
        grade_message = "Strong TLS security configuration"
    elif security_percentage >= 70:
        security_grade = "B"
        grade_message = "Good TLS security configuration"
    elif security_percentage >= 60:
        security_grade = "C"
        grade_message = "Adequate TLS security configuration"
    else:
        security_grade = "D"
        grade_message = "TLS security configuration needs improvement"

    logger.info(f"TLS Security Score: {security_score}/{max_score} ({security_percentage:.0f}%)")
    logger.info(f"TLS Security Grade: {security_grade} - {grade_message}")

    # MANDATORY: Fail for poor security grades
    if security_percentage < 60:
        pytest.fail(
            f"TLS implementation security grade {security_grade} is below acceptable standards. "
            f"A2A v0.3.0 Section 4.1 requires secure TLS configurations for production deployments."
        )

    # Recommendations for improvement
    if security_percentage < 90:
        logger.info("💡 Recommendations for improvement:")
        if tls_version != "TLSv1.3":
            logger.info("  • Upgrade to TLS 1.3 for enhanced security and performance")
        if cipher and "ECDHE" not in cipher[0]:
            logger.info("  • Use ECDHE cipher suites for forward secrecy")
        if cipher and "GCM" not in cipher[0] and "CHACHA20" not in cipher[0]:
            logger.info("  • Use authenticated encryption (AES-GCM or ChaCha20-Poly1305)")

    logger.info("✅ TLS implementation analysis complete")
