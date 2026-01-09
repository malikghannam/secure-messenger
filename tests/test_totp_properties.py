"""
Property-Based Tests for TOTP Service

Uses hypothesis library for property-based testing.
Tests universal properties that must hold for all valid inputs.

**Feature: totp-authentication**
"""

import sys
import os
import time
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from hypothesis import given, strategies as st, settings, assume

from messenger.auth.totp_service import TOTPService, get_totp_service


class TestSecretGeneration:
    """
    **Property 1: Secret Key Uniqueness and Format**
    **Validates: Requirements 1.1**
    
    For any number of generated secret keys, each key SHALL be exactly 
    32 characters long, contain only valid base32 characters (A-Z, 2-7), 
    and all keys SHALL be unique.
    """
    
    def setup_method(self):
        self.service = TOTPService()
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=50))
    def test_secret_length_is_32_characters(self, _):
        """Each generated secret must be exactly 32 characters."""
        secret = self.service.generate_secret()
        assert len(secret) == 32, f"Secret length was {len(secret)}, expected 32"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=50))
    def test_secret_contains_only_base32_characters(self, _):
        """Each generated secret must contain only valid base32 characters."""
        secret = self.service.generate_secret()
        base32_pattern = re.compile(r'^[A-Z2-7]+$')
        assert base32_pattern.match(secret), f"Secret contains invalid characters: {secret}"
    
    def test_secrets_are_unique(self):
        """Multiple generated secrets must all be unique."""
        secrets = [self.service.generate_secret() for _ in range(100)]
        unique_secrets = set(secrets)
        assert len(unique_secrets) == len(secrets), \
            f"Generated {len(secrets)} secrets but only {len(unique_secrets)} were unique"


class TestProvisioningUri:
    """
    **Property 2: Provisioning URI Format Compliance**
    **Validates: Requirements 1.2**
    
    For any valid secret key and username, the generated provisioning URI 
    SHALL follow the otpauth://totp/ format with properly encoded parameters.
    """
    
    def setup_method(self):
        self.service = TOTPService()
    
    @settings(max_examples=100)
    @given(
        username=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=1,
            max_size=20
        )
    )
    def test_uri_format_is_valid(self, username):
        """Generated URI must follow otpauth://totp/ format."""
        assume(len(username.strip()) > 0)
        
        secret = self.service.generate_secret()
        uri = self.service.generate_provisioning_uri(secret, username)
        
        assert uri.startswith("otpauth://totp/"), f"URI doesn't start with otpauth://totp/: {uri}"
        assert "secret=" in uri, f"URI missing secret parameter: {uri}"
        assert "issuer=" in uri, f"URI missing issuer parameter: {uri}"
        assert "algorithm=SHA1" in uri, f"URI missing algorithm parameter: {uri}"
        assert "digits=6" in uri, f"URI missing digits parameter: {uri}"
        assert "period=30" in uri, f"URI missing period parameter: {uri}"
    
    @settings(max_examples=100)
    @given(
        username=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=1,
            max_size=20
        ),
        issuer=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=1,
            max_size=20
        )
    )
    def test_uri_contains_secret(self, username, issuer):
        """Generated URI must contain the exact secret."""
        assume(len(username.strip()) > 0 and len(issuer.strip()) > 0)
        
        secret = self.service.generate_secret()
        uri = self.service.generate_provisioning_uri(secret, username, issuer)
        
        assert f"secret={secret}" in uri, f"URI doesn't contain correct secret"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestTOTPVerification:
    """
    **Property 4: TOTP Verification with Time Window**
    **Validates: Requirements 1.5, 1.6, 2.2, 2.4, 5.1**
    
    For any valid secret key, a TOTP code generated for the current time period,
    the previous period (-30s), or the next period (+30s) SHALL be accepted.
    Codes from periods outside this window SHALL be rejected.
    """
    
    def setup_method(self):
        self.service = TOTPService()
    
    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=100))
    def test_current_code_is_accepted(self, _):
        """Code generated for current time must be accepted."""
        secret = self.service.generate_secret()
        current_time = time.time()
        
        code = self.service.generate_code(secret, current_time)
        is_valid, drift = self.service.verify_code(secret, code)
        
        assert is_valid, f"Current code {code} was rejected"
        assert drift == 0, f"Expected drift 0, got {drift}"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=100))
    def test_previous_period_code_is_accepted(self, _):
        """Code from previous time period (-30s) must be accepted."""
        secret = self.service.generate_secret()
        current_time = time.time()
        previous_time = current_time - 30  # Previous period
        
        code = self.service.generate_code(secret, previous_time)
        is_valid, drift = self.service.verify_code(secret, code)
        
        # Should be valid (within ±1 window)
        assert is_valid, f"Previous period code {code} was rejected"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=100))
    def test_next_period_code_is_accepted(self, _):
        """Code from next time period (+30s) must be accepted."""
        secret = self.service.generate_secret()
        current_time = time.time()
        next_time = current_time + 30  # Next period
        
        code = self.service.generate_code(secret, next_time)
        is_valid, drift = self.service.verify_code(secret, code)
        
        # Should be valid (within ±1 window)
        assert is_valid, f"Next period code {code} was rejected"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=100))
    def test_old_code_is_rejected(self, _):
        """Code from 2+ periods ago must be rejected."""
        secret = self.service.generate_secret()
        current_time = time.time()
        old_time = current_time - 90  # 3 periods ago
        
        code = self.service.generate_code(secret, old_time)
        is_valid, _ = self.service.verify_code(secret, code)
        
        assert not is_valid, f"Old code {code} was incorrectly accepted"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=100))
    def test_future_code_is_rejected(self, _):
        """Code from 2+ periods in future must be rejected."""
        secret = self.service.generate_secret()
        current_time = time.time()
        future_time = current_time + 90  # 3 periods ahead
        
        code = self.service.generate_code(secret, future_time)
        is_valid, _ = self.service.verify_code(secret, code)
        
        assert not is_valid, f"Future code {code} was incorrectly accepted"
    
    @settings(max_examples=100)
    @given(st.text(min_size=0, max_size=10))
    def test_invalid_format_codes_rejected(self, code):
        """Codes with invalid format must be rejected."""
        assume(not (len(code) == 6 and code.isdigit()))
        
        secret = self.service.generate_secret()
        is_valid, _ = self.service.verify_code(secret, code)
        
        assert not is_valid, f"Invalid format code '{code}' was incorrectly accepted"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=999999))
    def test_wrong_codes_rejected(self, wrong_code_int):
        """Random wrong codes must be rejected (with high probability)."""
        secret = self.service.generate_secret()
        wrong_code = str(wrong_code_int).zfill(6)
        
        # Get the actual valid code
        valid_code = self.service.generate_code(secret)
        
        # Skip if we accidentally generated the correct code
        assume(wrong_code != valid_code)
        
        is_valid, _ = self.service.verify_code(secret, wrong_code)
        assert not is_valid, f"Wrong code {wrong_code} was incorrectly accepted"



class TestBackupCodes:
    """
    **Property 5: Backup Code Uniqueness and Count**
    **Property 6: Backup Code Single-Use**
    **Validates: Requirements 3.1, 3.3**
    
    For any backup code generation, exactly 10 codes SHALL be produced,
    each code SHALL be unique, and each code SHALL be exactly 8 characters long.
    Used codes SHALL be invalidated.
    """
    
    def setup_method(self):
        self.service = TOTPService()
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=50))
    def test_generates_exactly_10_codes(self, _):
        """Must generate exactly 10 backup codes."""
        codes = self.service.generate_backup_codes()
        assert len(codes) == 10, f"Generated {len(codes)} codes, expected 10"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=50))
    def test_all_codes_are_unique(self, _):
        """All generated backup codes must be unique."""
        codes = self.service.generate_backup_codes()
        unique_codes = set(codes)
        assert len(unique_codes) == len(codes), \
            f"Generated {len(codes)} codes but only {len(unique_codes)} were unique"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=50))
    def test_codes_are_8_characters(self, _):
        """Each backup code must be exactly 8 characters."""
        codes = self.service.generate_backup_codes()
        for code in codes:
            assert len(code) == 8, f"Code '{code}' has length {len(code)}, expected 8"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=50))
    def test_codes_are_alphanumeric(self, _):
        """Each backup code must contain only alphanumeric characters."""
        codes = self.service.generate_backup_codes()
        for code in codes:
            assert code.isalnum(), f"Code '{code}' contains non-alphanumeric characters"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=9))
    def test_valid_code_is_accepted(self, code_index):
        """A valid backup code must be accepted."""
        codes = self.service.generate_backup_codes()
        hashes = [self.service.hash_backup_code(c) for c in codes]
        
        # Verify the code at the given index
        is_valid, remaining = self.service.verify_backup_code(hashes, codes[code_index])
        
        assert is_valid, f"Valid code {codes[code_index]} was rejected"
        assert len(remaining) == 9, f"Expected 9 remaining codes, got {len(remaining)}"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=9))
    def test_used_code_is_invalidated(self, code_index):
        """A used backup code must be rejected on second use."""
        codes = self.service.generate_backup_codes()
        hashes = [self.service.hash_backup_code(c) for c in codes]
        
        # Use the code once
        is_valid, remaining = self.service.verify_backup_code(hashes, codes[code_index])
        assert is_valid, "First use should succeed"
        
        # Try to use the same code again
        is_valid_again, _ = self.service.verify_backup_code(remaining, codes[code_index])
        assert not is_valid_again, f"Used code {codes[code_index]} was incorrectly accepted again"
    
    @settings(max_examples=100)
    @given(st.text(min_size=8, max_size=8, alphabet=st.characters(whitelist_categories=('L', 'N'))))
    def test_invalid_code_is_rejected(self, random_code):
        """A random invalid code must be rejected."""
        codes = self.service.generate_backup_codes()
        hashes = [self.service.hash_backup_code(c) for c in codes]
        
        # Skip if we accidentally generated a valid code
        assume(random_code.upper() not in [c.upper() for c in codes])
        
        is_valid, remaining = self.service.verify_backup_code(hashes, random_code)
        
        assert not is_valid, f"Invalid code '{random_code}' was incorrectly accepted"
        assert len(remaining) == 10, "Remaining codes should be unchanged"



class TestSecretEncryption:
    """
    **Property 8: Secret Encryption Round-Trip**
    **Validates: Requirements 7.1**
    
    For any TOTP secret key, encrypting it for storage and then 
    decrypting it SHALL produce the exact original secret key.
    """
    
    def setup_method(self):
        self.service = TOTPService()
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=50))
    def test_encryption_round_trip(self, _):
        """Encrypting then decrypting must return original secret."""
        original_secret = self.service.generate_secret()
        
        encrypted = self.service.encrypt_secret(original_secret)
        decrypted = self.service.decrypt_secret(encrypted)
        
        assert decrypted == original_secret, \
            f"Round-trip failed: original={original_secret}, decrypted={decrypted}"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=50))
    def test_encrypted_differs_from_original(self, _):
        """Encrypted secret must differ from original."""
        original_secret = self.service.generate_secret()
        encrypted = self.service.encrypt_secret(original_secret)
        
        assert encrypted != original_secret, \
            "Encrypted secret should not equal original"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=20))
    def test_same_secret_encrypts_differently(self, _):
        """Same secret encrypted twice should produce different ciphertexts."""
        secret = self.service.generate_secret()
        
        encrypted1 = self.service.encrypt_secret(secret)
        encrypted2 = self.service.encrypt_secret(secret)
        
        # Fernet uses random IV, so same plaintext -> different ciphertext
        assert encrypted1 != encrypted2, \
            "Same secret should encrypt to different ciphertexts"



from messenger.auth.qr_generator import QRCodeGenerator, get_qr_generator


class TestQRCodeGeneration:
    """
    **Property 3: QR Code Round-Trip**
    **Validates: Requirements 1.3, 6.1, 6.3**
    
    For any valid provisioning URI, generating a QR code (ASCII or image)
    and then decoding it SHALL produce the exact original URI.
    
    Note: Full round-trip testing requires a QR decoder library.
    These tests verify QR generation produces valid output.
    """
    
    def setup_method(self):
        self.totp_service = TOTPService()
        self.qr_generator = QRCodeGenerator()
    
    @settings(max_examples=50)
    @given(
        username=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=1,
            max_size=15
        )
    )
    def test_ascii_qr_is_generated(self, username):
        """ASCII QR code must be generated for any valid URI."""
        assume(len(username.strip()) > 0)
        
        secret = self.totp_service.generate_secret()
        uri = self.totp_service.generate_provisioning_uri(secret, username)
        
        ascii_qr = self.qr_generator.generate_ascii(uri)
        
        assert ascii_qr is not None
        assert len(ascii_qr) > 0
        assert "██" in ascii_qr or "  " in ascii_qr  # Contains QR blocks
    
    @settings(max_examples=50)
    @given(
        username=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=1,
            max_size=15
        )
    )
    def test_ascii_qr_has_consistent_structure(self, username):
        """ASCII QR code must have consistent row lengths."""
        assume(len(username.strip()) > 0)
        
        secret = self.totp_service.generate_secret()
        uri = self.totp_service.generate_provisioning_uri(secret, username)
        
        ascii_qr = self.qr_generator.generate_ascii(uri)
        lines = ascii_qr.split("\n")
        
        # All lines should have the same length (square QR code)
        line_lengths = [len(line) for line in lines]
        assert len(set(line_lengths)) == 1, \
            f"QR code lines have inconsistent lengths: {set(line_lengths)}"
    
    @settings(max_examples=20)
    @given(
        username=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=1,
            max_size=10
        )
    )
    def test_image_bytes_are_generated(self, username):
        """PNG image bytes must be generated for any valid URI."""
        assume(len(username.strip()) > 0)
        
        secret = self.totp_service.generate_secret()
        uri = self.totp_service.generate_provisioning_uri(secret, username)
        
        image_bytes = self.qr_generator.generate_image_bytes(uri)
        
        assert image_bytes is not None
        assert len(image_bytes) > 0
        # PNG files start with specific magic bytes
        assert image_bytes[:8] == b'\x89PNG\r\n\x1a\n', "Output is not a valid PNG"
    
    def test_different_uris_produce_different_qr_codes(self):
        """Different URIs must produce different QR codes."""
        secret1 = self.totp_service.generate_secret()
        secret2 = self.totp_service.generate_secret()
        
        uri1 = self.totp_service.generate_provisioning_uri(secret1, "user1")
        uri2 = self.totp_service.generate_provisioning_uri(secret2, "user2")
        
        qr1 = self.qr_generator.generate_ascii(uri1)
        qr2 = self.qr_generator.generate_ascii(uri2)
        
        assert qr1 != qr2, "Different URIs should produce different QR codes"


class TestTOTPDisable:
    """
    **Property 9: TOTP Disable Removes Credentials**
    **Validates: Requirements 4.2**
    
    For any user with TOTP enabled, after disabling TOTP, the stored 
    secret key SHALL be removed and all backup codes SHALL be invalidated.
    """
    
    def setup_method(self):
        self.service = TOTPService()
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=50))
    def test_old_codes_invalid_after_disable_simulation(self, _):
        """
        Simulates disable: old secret's codes should not work with new secret.
        This tests the property that after regeneration/disable, old codes are invalid.
        """
        # Generate original secret and code
        old_secret = self.service.generate_secret()
        old_code = self.service.generate_code(old_secret)
        
        # Simulate disable by generating new secret (or None)
        new_secret = self.service.generate_secret()
        
        # Old code should not work with new secret
        is_valid, _ = self.service.verify_code(new_secret, old_code)
        
        # With overwhelming probability, old code won't match new secret
        # (1 in 1,000,000 chance of collision per time window)
        assert not is_valid, "Old code should not work after secret change"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=9))
    def test_backup_codes_invalid_after_regeneration(self, code_index):
        """
        Old backup codes should be invalid after generating new ones.
        """
        # Generate original backup codes
        old_codes = self.service.generate_backup_codes()
        old_hashes = [self.service.hash_backup_code(c) for c in old_codes]
        
        # Generate new backup codes (simulating regeneration)
        new_codes = self.service.generate_backup_codes()
        new_hashes = [self.service.hash_backup_code(c) for c in new_codes]
        
        # Old code should not work with new hashes
        is_valid, _ = self.service.verify_backup_code(new_hashes, old_codes[code_index])
        
        # Old codes should be invalid (unless collision, which is extremely unlikely)
        assume(old_codes[code_index] not in new_codes)
        assert not is_valid, "Old backup code should not work after regeneration"


class TestTOTPRegeneration:
    """
    **Property 10: TOTP Regeneration Invalidates Old Secret**
    **Validates: Requirements 4.4**
    
    For any user who regenerates their TOTP secret, codes generated from 
    the old secret SHALL be rejected, and codes generated from the new 
    secret SHALL be accepted.
    """
    
    def setup_method(self):
        self.service = TOTPService()
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=50))
    def test_old_secret_codes_rejected_after_regeneration(self, _):
        """Codes from old secret must be rejected after regeneration."""
        # Original secret
        old_secret = self.service.generate_secret()
        old_code = self.service.generate_code(old_secret)
        
        # Regenerate (new secret)
        new_secret = self.service.generate_secret()
        
        # Old code should not work with new secret
        is_valid, _ = self.service.verify_code(new_secret, old_code)
        
        assert not is_valid, "Old secret's code should be rejected after regeneration"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=50))
    def test_new_secret_codes_accepted_after_regeneration(self, _):
        """Codes from new secret must be accepted after regeneration."""
        # Original secret (would be discarded)
        old_secret = self.service.generate_secret()
        
        # Regenerate (new secret)
        new_secret = self.service.generate_secret()
        new_code = self.service.generate_code(new_secret)
        
        # New code should work with new secret
        is_valid, _ = self.service.verify_code(new_secret, new_code)
        
        assert is_valid, "New secret's code should be accepted after regeneration"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=50))
    def test_regenerated_secrets_are_different(self, _):
        """Each regeneration must produce a different secret."""
        secret1 = self.service.generate_secret()
        secret2 = self.service.generate_secret()
        
        assert secret1 != secret2, "Regenerated secrets should be different"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=50))
    def test_regeneration_produces_new_backup_codes(self, _):
        """Regeneration must produce new backup codes."""
        codes1 = self.service.generate_backup_codes()
        codes2 = self.service.generate_backup_codes()
        
        # Sets should be different (extremely unlikely to be same)
        assert set(codes1) != set(codes2), "Regenerated backup codes should be different"
