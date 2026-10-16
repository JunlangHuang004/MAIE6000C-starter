"""Check Qwen configuration without exposing secrets; --live calls the provider."""
import argparse
import sys
from urllib.parse import urlparse

from services.ai.app.qwen import analyze_with_qwen
from services.common.config import get_settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Send a synthetic meal to Qwen')
    args = parser.parse_args()
    settings = get_settings()
    missing = []
    if not settings.dashscope_api_key.get_secret_value().strip():
        missing.append('DASHSCOPE_API_KEY')
    if not settings.qwen_base_url.strip():
        missing.append('QWEN_BASE_URL')
    if missing:
        print('Missing configuration: ' + ', '.join(missing))
        print('Set these in the project .env; do not paste secrets into logs or chat.')
        return 1
    endpoint = urlparse(settings.qwen_base_url)
    if (endpoint.scheme != 'https' or not endpoint.hostname or endpoint.username
            or endpoint.password or endpoint.query or endpoint.fragment
            or endpoint.path.rstrip('/').endswith('/chat/completions')):
        print('QWEN_BASE_URL must be HTTPS, without credentials, query or /chat/completions.')
        return 1
    if settings.worker_request_timeout_seconds <= settings.qwen_timeout_seconds:
        print('WORKER_REQUEST_TIMEOUT_SECONDS must exceed QWEN_TIMEOUT_SECONDS.')
        return 1
    print('Required settings are present. Credentials and model access are not yet verified.')
    if settings.nutrition_provider != 'qwen':
        print('The application is in demo mode. Set NUTRITION_PROVIDER=qwen to enable Qwen.')
    if not args.live:
        print('Run with --live to verify a real request using a 100g boiled-egg meal.')
        return 0
    try:
        result = analyze_with_qwen('100克去壳水煮鸡蛋，熟重', settings)
    except (ValueError, RuntimeError) as exc:
        print('Live check failed: ' + str(exc))
        return 1
    from services.common.meal_engine import catalogue
    egg = next(f for f in catalogue()['foods'] if f['id']=='egg')
    if result.questions or result.calories != egg['nutrients']['calories']:
        print('Live check failed: reference meal was not resolved.')
        return 1
    print('Live check passed: source-backed cooked egg estimate.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
