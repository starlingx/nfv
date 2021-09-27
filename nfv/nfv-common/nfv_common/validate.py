#
# Copyright (c) 2015-2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import datetime
import re
import uuid


def valid_uuid_str(uuid_str, version=4):
    """
    Returns true if uuid string given is a valid uuid
    """
    try:
        uuid.UUID(uuid_str, version=version)

    except ValueError:
        return False

    return True


def valid_uuid_hex(uuid_hex_str, version=4):
    """
    Returns true if uuid hex string given is a valid uuid
    """
    try:
        uuid_value = uuid.UUID(uuid_hex_str, version=version)

    except ValueError:
        return False

    # Verify that the uuid_hex_str was not converted into a valid uuid.  This
    # is possible when the uuid_hex_str is a valid hex string but not a valid
    # uuid.  The uuid.UUID constructor will auto correct.
    return uuid_value.hex == uuid_hex_str


def valid_bool(boolean_str):
    """
    Returns true if string given is a valid boolean
    """
    if boolean_str.lower() in ['true', '1', 'false', '0']:
        return True
    return False


def valid_integer(integer_str):
    """
    Returns true if string given is a valid integer
    """
    try:
        int(integer_str)

    except ValueError:
        return False

    return True


def validate_certificate_subject(subject):
    """
    Duplicate the get_subject validation logic defined in:
    sysinv/api/controllers/v1/kube_rootca_update.py

    Returns a tuple of True, "" if the input is None
    Returns a tuple of True, "" if the input is valid
    Returns a tuple of False, "<error details>" if the input is invalid
    """
    if subject is None:
        return True, ""

    params_supported = ['C', 'OU', 'O', 'ST', 'CN', 'L']
    subject_pairs = re.findall(r"([^=]+=[^=]+)(?:\s|$)", subject)
    subject_dict = {}
    for pair_value in subject_pairs:
        key, value = pair_value.split("=")
        subject_dict[key] = value

    if not all([param in params_supported for param in subject_dict.keys()]):
        return False, ("There are parameters not supported "
                       "for the certificate subject specification. "
                       "The subject parameter has to be in the "
                       "format of 'C=<Country> ST=<State/Province> "
                       "L=<Locality> O=<Organization> OU=<OrganizationUnit> "
                       "CN=<commonName>")
    if 'CN' not in list(subject_dict.keys()):
        return False, ("The CN=<commonName> parameter is required to be "
                       "specified in subject argument")
    return True, ""


def validate_expiry_date(expiry_date):
    """
    Duplicate the expiry_date validation logic defined in:
    sysinv/api/controllers/v1/kube_rootca_update.py

    Returns a tuple of True, "" if the input is None
    Returns a tuple of True, "" if the input is valid
    Returns a tuple of False, "<error details>" if the input is invalid
    """
    if expiry_date is None:
        return True, ""

    try:
        date = datetime.datetime.strptime(expiry_date, "%Y-%m-%d")
    except ValueError:
        return False, ("expiry_date %s doesn't match format "
                       "YYYY-MM-DD" % expiry_date)

    delta = date - datetime.datetime.now()
    # we sum one day (24 hours) to accomplish the certificate expiry
    # during the day specified by the user
    duration = (delta.days * 24 + 24)

    # Cert-manager manages certificates and renew them some time
    # before it expires. Along this procedure we set renewBefore
    # parameter for 24h, so we are checking if the duration sent
    # has at least this amount of time. This is needed to avoid
    # cert-manager to block the creation of the resources.
    if duration <= 24:
        return False, ("New k8s rootCA should have at least 24 hours of "
                       "validation before expiry.")
    return True, ""
