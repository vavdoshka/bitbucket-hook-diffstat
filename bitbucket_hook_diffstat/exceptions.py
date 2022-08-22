class BitbucketHookDiffstatError(Exception):
    """Generic base Exception, not raised directly"""


class BitbucketMaxRetryError(BitbucketHookDiffstatError):
    """A request to Bitbucket was not able to succeed after several retries"""

class BitbucketHTTPError(BitbucketHookDiffstatError):
    """A request to Bitbucket was not authorized or some other non-retryable error"""

class PayloadBadFormatError(BitbucketHookDiffstatError):
    """A webhook payload provided does satisfy expected format"""


class GenericError(BitbucketHookDiffstatError):
    """Unhandeled errors"""
