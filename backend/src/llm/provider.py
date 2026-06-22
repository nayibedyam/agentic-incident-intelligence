import boto3
import anthropic

from src.config import settings


def _get_bedrock_kwargs() -> dict:
    if settings.aws_profile:
        session = boto3.Session(profile_name=settings.aws_profile, region_name=settings.aws_region)
        credentials = session.get_credentials().get_frozen_credentials()
        return {
            "aws_access_key": credentials.access_key,
            "aws_secret_key": credentials.secret_key,
            "aws_session_token": credentials.token,
            "aws_region": settings.aws_region,
        }
    return {
        "aws_access_key": settings.aws_access_key_id,
        "aws_secret_key": settings.aws_secret_access_key,
        "aws_region": settings.aws_region,
    }


def get_client() -> anthropic.Anthropic:
    if settings.llm_provider == "bedrock":
        return anthropic.AnthropicBedrock(**_get_bedrock_kwargs())
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def get_async_client() -> anthropic.AsyncAnthropic:
    if settings.llm_provider == "bedrock":
        return anthropic.AsyncAnthropicBedrock(**_get_bedrock_kwargs())
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


def get_model_id() -> str:
    return settings.model_id
