from __future__ import annotations

import contextlib
import os
from enum import Enum
from functools import cache
from typing import Any


DEFAULT_INDENT = 4

NotSuppliedType = Enum("NotSuppliedType", {"NOT_SUPPLIED": object()})
Number = int | float
NOT_SUPPLIED = NotSuppliedType.NOT_SUPPLIED


@cache
def aws_account_id() -> str:
    _id: str = str(
        os.environ.get(
            "AWS_ACCOUNT_ID",
            os.environ.get("CDK_DEFAULT_ACCOUNT", ""),
        )
    )
    if not _id:
        # Fallback available if boto3 is installed
        with contextlib.suppress(ImportError):
            import boto3.session  # type: ignore  # noqa: PLC0415

            session: Any = boto3.session.Session()  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
            sts_client = session.client("sts")  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
            caller_identity: Any = sts_client.get_caller_identity()  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
            _id = str(caller_identity.get("Account", ""))  # pyright: ignore[reportUnknownArgumentType, reportUnknownMemberType]
    if not _id:
        raise ValueError("AWS_ACCOUNT_ID is not set")
    return _id


@cache
def aws_region() -> str:
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


# == Rotating stack IDs by appending the STACK_SUFFIX environment variable ==


def core_stack_id() -> str:
    return "Core" + os.environ.get("STACK_SUFFIX", "")


def cog_stack_id() -> str:
    return "Cog" + os.environ.get("STACK_SUFFIX", "")


def dyna_stack_id() -> str:
    return "Dyna" + os.environ.get("STACK_SUFFIX", "")


def gate_stack_id() -> str:
    return "Gate" + os.environ.get("STACK_SUFFIX", "")


def web_stack_id() -> str:
    return "Web" + os.environ.get("STACK_SUFFIX", "")


# Feature flags

WITH_DOCKER_LOGS = True
WITH_ENVIRON_LOGS = False
WITH_EXTRA_LAMBDA_LOGGING = False
K_WITH_API_ACCESS_LOGS = "WITH_API_ACCESS_LOGS"
K_WITH_DISTRIBUTION_WAF = "WITH_DISTRIBUTION_WAF"
K_WITH_ORIGIN_REQUEST_HANDLER = "WITH_ORIGIN_REQUEST_HANDLER"
K_WITH_ORIGIN_RESPONSE_HANDLER = "WITH_ORIGIN_RESPONSE_HANDLER"
K_WITH_VIEWER_REQUEST_HANDLER = "WITH_VIEWER_REQUEST_HANDLER"
K_WITH_VIEWER_RESPONSE_HANDLER = "WITH_VIEWER_RESPONSE_HANDLER"

# Miscellaneous constants

ASSETS_DIR = ".assets"

GLOBAL_ORIGIN_KEEPALIVE_TIMEOUT = 10
GLOBAL_ORIGIN_READ_TIMEOUT = 30
IP_ADDRESS_SERVERS = ["ipv4.icanhazip.com", "ipv6.icanhazip.com"]

# Environment variable names

K_CORS_ORIGINS = "CORS_ORIGINS"
K_IP_RANGES = "IP_RANGES"
K_SOURCE_IPS = "SOURCE_IPS"

# Certificate constants

K_CLOUDFRONT_ORIGIN_EDGE_LAMBDA_ARN = "CloudfrontOriginEdgeLambdaArn"
K_CLOUDFRONT_VIEWER_CF_FUNCTION_ARN = "CloudfrontViewerCfFunctionArn"
K_DISTRIBUTION_DOMAIN = "DistributionDomain"
K_DISTRIBUTION_ID = "DistributionId"
K_DISTRIB_ORIGIN = "DistributionOrigin"
K_FLASK_SECRET_KEY = "FlaskSecretKey"
K_INTR_CA_CERT = "IntrCACert"
K_INTR_CA_CERT_ARN = "IntrCACertArn"
K_INTR_CA_CERT_KEY = "IntrCACertKey"
K_LOG_BUCKET_ARN = "LogBucketArn"
K_LOG_BUCKET_NAME = "LogBucketName"
K_ROOT_CA_CERT = "RootCACert"
K_ROOT_CA_CERT_ARN = "RootCACertArn"
K_ROOT_CA_CERT_KEY = "RootCACertKey"
K_WEB_BUCKET_ARN = "WebBucketArn"
K_WEB_BUCKET_NAME = "WebBucketName"

# Cognito constants

COGNITO_ADMIN_USERNAME = "admin"
COGNITO_RELAX_PASSWORD = "(Relax1)"
K_COGNITO_IDENTITY_POOL_ARN = "CognitoIdentityPoolArn"
K_COGNITO_IDENTITY_POOL_ID = "CognitoIdentityPoolId"
K_COGNITO_USER_POOL_ARN = "CognitoUserPoolArn"
K_COGNITO_USER_POOL_CLIENT_ID = "CognitoUserPoolClientId"
K_COGNITO_USER_POOL_DOMAIN_NAME = "CognitoUserPoolDomainName"
K_COGNITO_USER_POOL_ID = "CognitoUserPoolId"

# DynamoDB constants

DB_DEVICES_TABLE_NAME = "Devices"
DB_MEASUREMENTS_TABLE_NAME = "Measurements"
DB_OPERATORS_TABLE_NAME = "Operators"
DB_SITES_TABLE_NAME = "Sites"
DB_USERS_TABLE_NAME = "Users"
DB_USER_ACCESS_TABLE_NAME = "UserAccess"
K_DYNA_RECORDS_EVENT_SOURCE_ARN = "DynaRecordsEventStreamArn"
K_DYNA_SAMPLE_DATA_BUCKET = "DynaSampleDataBucket"
K_DYNA_SAMPLE_DATA_KEY = "DynaSampleDataKey"
K_DYNA_SAMPLE_DATA_LIMIT = "DynaSampleDataLimit"
K_DYNA_SAMPLE_DATA_TABLE = "DynaSampleDataTable"

# AWS event constants

K_REQUEST_TYPE = "RequestType"
K_RESOURCE_PROPERTIES = "ResourceProperties"

# Request/response constants

K_CACHE_COOKIES = "CacheCookies"
K_CACHE_HEADERS = "CacheHeaders"
K_CACHE_POLICY_ID = "CachePolicyId"
K_ORIGIN_REQUEST_POLICY_ID = "OriginRequestPolicyId"
K_ORIGIN_RESPONSE_HEADER_POLICY_ID = "OriginResponseHeadersPolicyId"

K_STATUS_CODE = "statusCode"
"""The HTTP status code of the response. Must be an integer between 100 and 599."""

K_STATUS = "Status"
"""Status of the response from a Custom Resource on_event_handler. Can be SUCCESS or FAILED or IN_PROGRESS."""

# Service API constants

K_SERVICE_API_ENDPOINT = "ServiceApiEndpoint"
K_SERVICE_API_ID = "ServiceApiId"
K_SERVICE_API_ORIGIN_ID = "ServiceApiOriginId"
SERVICE_API_PATH_PREFIX = "/api"

# Status API constants

K_STATUS_API_ENDPOINT = "StatusApiEndpoint"
K_STATUS_API_ID = "StatusApiId"
K_STATUS_API_ORIGIN_ID = "StatusApiOriginId"
STATUS_API_PATH_PATTERNS = ["/status*"]
STATUS_API_PREFIX = "/status"

# Cookie constants

K_ACCESS_TOKEN = "access_token"
K_ID_TOKEN = "id_token"
K_REFRESH_TOKEN = "refresh_token"
K_SESSION_ID = "session_id"
COOKIE_HTTPONLY = True  # Do not allow JavaScript access to cookies
COOKIE_MAX_AGE_SECONDS = 24 * 60 * 60
COOKIE_MAX_BYTES = 4096
COOKIE_PATH = "/"  # This must be '/', or the cookies will not be sent to the API Gateway
COOKIE_SAMESITE = "None"  # Cookies are sent on both originating and cross-site requests.
COOKIE_SECURE = True  # Only send cookies over HTTPS
ALL_COOKIES = [K_ACCESS_TOKEN, K_ID_TOKEN, K_REFRESH_TOKEN, K_SESSION_ID]

# Header constants

K_CUSTOM_ALLOWED_IPS = "X-Custom-Allowed-Ips"
K_CUSTOM_ORIGINAL_METHOD = "X-Custom-Original-Method"
K_CUSTOM_ORIGINAL_URI = "X-Custom-Original-Url"
X_CUSTOM_HEADER_NAMES = [
    K_CUSTOM_ALLOWED_IPS,
    K_CUSTOM_ORIGINAL_METHOD,
    K_CUSTOM_ORIGINAL_URI,
]

# HTTP constants

K_ERROR_MESSAGE = "error_message"
K_ERROR_TYPE = "error_type"
K_REFRESH_STATUS = "refresh_status"

HTTP_STATUS_200_OK = 200
"""The request was successful."""
HTTP_STATUS_400_BAD_REQUEST = 400
"""The request was malformed."""
HTTP_STATUS_401_UNAUTHORIZED = 401
"""The user is not logged in. Not allowed in CloudFront distribution error responses."""
HTTP_STATUS_403_FORBIDDEN = 403
"""The user is logged in but is not allowed to access the resource (eg. admins only)."""
HTTP_STATUS_404_NOT_FOUND = 404
"""The resource (uri) was not found."""
HTTP_STATUS_405_METHOD_NOT_ALLOWED = 405
"""The HTTP method (eg. POST, DELETE, etc) is not allowed."""
HTTP_STATUS_500_INTERNAL_SERVER_ERROR = 500
"""An internal server error occurred (exception)."""
HTTP_STATUS_501_NOT_IMPLEMENTED = 501
"""Method (eg. POST, DELETE, etc) is not implemented. Not allowed in CloudFront distribution error responses."""
HTTP_STATUS_502_BAD_GATEWAY = 502
"""The server received an invalid response from an upstream server."""
HTTP_STATUS_503_SERVICE_UNAVAILABLE = 503
"""The service is unavailable (eg. site down)."""
HTTP_STATUS_504_GATEWAY_TIMEOUT = 504
"""The server did not receive a timely response from an upstream server."""
HTTP_STATUS_MANAGED_ERRORS = [400, 403, 404, 405, 500, 502, 503, 504]
"""All HTTP status codes that can be handled by CloudFront."""

# CORS settings

CORS_MAX_AGE_SECONDS = 10 * 60
CORS_ALLOW_HEADERS = [
    "Access-Control-Allow-Credentials",
    "Access-Control-Allow-Headers",
    "Access-Control-Allow-Methods",
    "Access-Control-Allow-Origin",
    "Access-Control-Expose-Headers",
    "Authorization",
    "Content-Type",
    "Origin",
    "X-Amz-Date",
    "X-Amz-Security-Token",
    "X-Api-Key",
]  # + X_CUSTOM_HEADER_NAMES

CORS_EXPOSE_HEADERS = [
    "Access-Control-Allow-Origin",
    "Authorization",
    "Content-Type",
    "ETag",
    "If-Match",
    "If-Modified-Since",
    "If-None-Match",
    "If-Unmodified-Since",
    "Last-Modified",
    "Location",
    "X-Amzn-RequestId",
    "X-Amzn-Trace-Id",
]  # + X_CUSTOM_HEADER_NAMES
