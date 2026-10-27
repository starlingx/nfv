#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from nfv_common import validate
from nfv_unit_tests.tests import testcase


class TestValidateCertificateKeyParameters(testcase.NFVTestCase):
    """Test class for validate_certificate_key_parameters function"""

    def test_validate_certificate_key_parameters_succeeds(self):
        """Test validate_certificate_key_parameters succeeds with valid inputs"""

        valid_inputs = [
            (None, None),
            ("ECDSA", None),
            ("ECDSA", 384),
            ("ECDSA", 521),
            ("RSA", None),
            ("RSA", 4096),
        ]

        for algorithm, key_size in valid_inputs:
            with self.subTest(algorithm=algorithm, key_size=key_size):
                is_valid, reason = validate.validate_certificate_key_parameters(
                    algorithm, key_size
                )

                self.assertTrue(is_valid)
                self.assertEqual(reason, "")

    def test_validate_certificate_key_parameters_fails(self):
        """Test validate_certificate_key_parameters fails with invalid inputs"""

        invalid_inputs = [
            (None, 384),  # key size without algorithm
            ("DSA", None),  # unsupported algorithm
            ("ecdsa", 384),  # algorithm is case-sensitive
            ("ECDSA", 256),  # unsupported key size
            ("ECDSA", 4096),  # unsupported key size
            ("RSA", 2048),  # unsupported key size
            ("RSA", 384),  # unsupported key size
        ]

        for algorithm, key_size in invalid_inputs:
            with self.subTest(algorithm=algorithm, key_size=key_size):
                is_valid, reason = validate.validate_certificate_key_parameters(
                    algorithm, key_size
                )

                self.assertFalse(is_valid)
                self.assertTrue(reason)
