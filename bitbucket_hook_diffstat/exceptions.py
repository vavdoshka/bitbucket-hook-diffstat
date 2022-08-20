class BitbucketHookDiffstatError(Exception):
    """Generic base Exception, not raised directly"""


class BitbucketMaxRetryError(BitbucketHookDiffstatError):
    """A request to Bitbucket was not able to succeed after several retries"""


class BitbucketPayloadBadFormatError(BitbucketHookDiffstatError):
    """A webhook payload provided does satisfy expected format"""


class BitbucketGenericError(BitbucketHookDiffstatError):
    """Unhandeled errors"""
