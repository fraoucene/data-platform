import boto3
import pytest
from moto import mock_aws

REGION = "eu-west-3"


@pytest.fixture
def aws_credentials(monkeypatch):
    """Faux identifiants : sans eux, boto3 lirait le profil local et viserait le vrai compte."""
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)


@pytest.fixture
def s3(aws_credentials):
    """Client S3 branché sur moto (en mémoire) le temps du test."""
    with mock_aws():
        yield boto3.client("s3", region_name=REGION)


@pytest.fixture
def bucket(s3):
    name = "data-platform-test-raw"
    s3.create_bucket(Bucket=name, CreateBucketConfiguration={"LocationConstraint": REGION})
    return name
